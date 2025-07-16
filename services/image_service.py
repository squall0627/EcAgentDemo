import os
import base64
from typing import Optional
import openai
from fastapi import HTTPException
import logging
from utils.langfuse_handler import get_global_langfuse_handler

logger = logging.getLogger(__name__)

class ImageService:
    """
    画像処理サービス - OpenAI Vision APIを使用して画像を分析
    """

    def __init__(self):
        """
        ImageServiceを初期化
        OpenAI APIキーを環境変数から取得
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY が設定されていません。画像分析機能は利用できません。")
        else:
            openai.api_key = self.api_key

        # Langfuseハンドラーを初期化
        self.langfuse_handler = get_global_langfuse_handler()

    async def analyze_image(self, image_data: bytes, filename: str = "image.jpg", 
                           user_prompt: Optional[str] = None,
                           session_id: Optional[str] = None, user_id: Optional[str] = None) -> Optional[str]:
        """
        画像データを分析してテキスト説明を生成（Langfuse追跡対応）

        Args:
            image_data: 画像データのバイト列
            filename: 画像ファイル名（拡張子を含む）
            user_prompt: ユーザーからの追加指示（オプション）
            session_id: セッションID（Langfuse追跡用）
            user_id: ユーザーID（Langfuse追跡用）

        Returns:
            画像の分析結果テキスト、エラーの場合はNone

        Raises:
            HTTPException: API呼び出しエラーの場合
        """
        if not self.api_key:
            raise HTTPException(
                status_code=500, 
                detail="OpenAI APIキーが設定されていません。画像分析機能を使用するにはAPIキーが必要です。"
            )

        # Langfuse追跡用のobserveデコレータを取得
        observe_decorator = self.langfuse_handler.observe_decorator("image_analysis")

        @observe_decorator
        async def _analyze_with_tracking():
            """Langfuse追跡付きの画像分析処理"""
            try:
                # 画像データをbase64エンコード
                base64_image = base64.b64encode(image_data).decode('utf-8')
                
                # 画像の形式を判定
                image_format = self._get_image_format(filename)
                
                # プロンプトを構築
                system_prompt = "You are an AI assistant that analyzes images in detail and explains them clearly."
                
                if user_prompt:
                    content_prompt = f"Please analyze the following image according to the user’s instructions.\n\nUser instructions: {user_prompt}\n\nPlease describe the content of the image in detail."
                else:
                    content_prompt = "Please describe the content of this image in detail. Include an analysis of elements such as objects, people, text, colors, and composition."

                # OpenAI Vision APIを使用して画像を分析
                client = openai.OpenAI(api_key=self.api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",  # Vision対応モデル
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": content_prompt
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/{image_format};base64,{base64_image}",
                                        "detail": "high"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=1000,
                    temperature=0.1
                )

                analysis_result = response.choices[0].message.content
                logger.info(f"画像分析成功: {len(analysis_result)} 文字")

                # Langfuseが利用可能な場合、追加のメタデータを記録
                if self.langfuse_handler.is_available():
                    try:
                        # 直接Langfuseクライアントを使用してスパンを作成
                        self.langfuse_handler.langfuse_client.create_span(
                            name="vision_api_call",
                            input={
                                "model": "gpt-4o",
                                "filename": filename,
                                "image_format": image_format,
                                "image_size_bytes": len(image_data),
                                "user_prompt": user_prompt
                            },
                            output={
                                "analysis_result": analysis_result,
                                "result_length": len(analysis_result)
                            },
                            metadata={
                                "session_id": session_id,
                                "user_id": user_id,
                                "service": "image_service",
                                "api_provider": "openai"
                            }
                        )
                    except Exception as langfuse_error:
                        logger.warning(f"Langfuse記録エラー: {langfuse_error}")

                return analysis_result

            except openai.OpenAIError as e:
                logger.error(f"OpenAI API エラー: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"画像分析に失敗しました: {str(e)}"
                )
            except Exception as e:
                logger.error(f"画像分析エラー: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"画像処理中にエラーが発生しました: {str(e)}"
                )

        return await _analyze_with_tracking()

    def _get_image_format(self, filename: str) -> str:
        """
        ファイル名から画像形式を取得

        Args:
            filename: ファイル名

        Returns:
            画像形式（jpeg, png, gif, webp）
        """
        if '.' in filename:
            extension = filename.split('.')[-1].lower()
            if extension in ['jpg', 'jpeg']:
                return 'jpeg'
            elif extension in ['png']:
                return 'png'
            elif extension in ['gif']:
                return 'gif'
            elif extension in ['webp']:
                return 'webp'
        return 'jpeg'  # デフォルト形式

    def is_available(self) -> bool:
        """
        画像分析サービスが利用可能かチェック

        Returns:
            利用可能な場合True
        """
        return self.api_key is not None

    def get_supported_formats(self) -> list:
        """
        サポートされている画像フォーマットのリストを取得

        Returns:
            サポートされているフォーマットのリスト
        """
        return [
            "jpg", "jpeg", "png", "gif", "webp"
        ]

    def merge_image_analysis_with_text(self, image_analysis: str, user_text: Optional[str] = None) -> str:
        """
        画像分析結果とユーザーのテキスト入力をマージ

        Args:
            image_analysis: 画像分析結果
            user_text: ユーザーのテキスト入力

        Returns:
            マージされたメッセージ
        """
        if user_text and user_text.strip():
            return f"[Image Analysis Result]\n{image_analysis}\n\n[Instruction from User]\n{user_text}\n\nBased on the above image analysis, please respond according to the user’s instructions."
        else:
            return f"[Image Analysis Result]\n{image_analysis}\n\nIf you have any questions about this image, please feel free to ask."