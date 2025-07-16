import os
import tempfile
from typing import Optional
import openai
from fastapi import HTTPException
import logging
from utils.langfuse_handler import get_global_langfuse_handler

logger = logging.getLogger(__name__)

class VoiceService:
    """
    音声処理サービス - OpenAI Whisper APIを使用して音声をテキストに変換
    """

    def __init__(self):
        """
        VoiceServiceを初期化
        OpenAI APIキーを環境変数から取得
        """
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            logger.warning("OPENAI_API_KEY が設定されていません。音声機能は利用できません。")
        else:
            openai.api_key = self.api_key

        # Langfuseハンドラーを初期化
        self.langfuse_handler = get_global_langfuse_handler()

    async def transcribe_audio(self, audio_data: bytes, filename: str = "audio.wav", 
                             session_id: Optional[str] = None, user_id: Optional[str] = None) -> Optional[str]:
        """
        音声データをテキストに変換（Langfuse追跡対応）

        Args:
            audio_data: 音声データのバイト列
            filename: 音声ファイル名（拡張子を含む）
            session_id: セッションID（Langfuse追跡用）
            user_id: ユーザーID（Langfuse追跡用）

        Returns:
            変換されたテキスト、エラーの場合はNone

        Raises:
            HTTPException: API呼び出しエラーの場合
        """
        if not self.api_key:
            raise HTTPException(
                status_code=500, 
                detail="OpenAI APIキーが設定されていません。音声機能を使用するにはAPIキーが必要です。"
            )

        # Langfuse追跡用のobserveデコレータを取得
        observe_decorator = self.langfuse_handler.observe_decorator("voice_transcription")

        @observe_decorator
        async def _transcribe_with_tracking():
            """Langfuse追跡付きの音声変換処理"""
            try:
                # 一時ファイルに音声データを保存
                with tempfile.NamedTemporaryFile(delete=False, suffix=self._get_file_extension(filename)) as temp_file:
                    temp_file.write(audio_data)
                    temp_file_path = temp_file.name

                try:
                    # OpenAI Whisper APIを使用して音声をテキストに変換
                    with open(temp_file_path, "rb") as audio_file:
                        client = openai.OpenAI(api_key=self.api_key)
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file,
                            language="ja"  # 日本語を指定
                        )

                    transcribed_text = transcript.text
                    logger.info(f"音声変換成功: {len(transcribed_text)} 文字")

                    # Langfuseが利用可能な場合、追加のメタデータを記録
                    if self.langfuse_handler.is_available():
                        try:
                            # 直接Langfuseクライアントを使用してスパンを作成
                            self.langfuse_handler.langfuse_client.create_span(
                                name="whisper_api_call",
                                input={
                                    "model": "whisper-1",
                                    "filename": filename,
                                    "language": "ja",
                                    "audio_size_bytes": len(audio_data)
                                },
                                output={
                                    "transcribed_text": transcribed_text,
                                    "text_length": len(transcribed_text)
                                },
                                metadata={
                                    "session_id": session_id,
                                    "user_id": user_id,
                                    "service": "voice_service",
                                    "api_provider": "openai"
                                }
                            )
                        except Exception as langfuse_error:
                            logger.warning(f"Langfuse記録エラー: {langfuse_error}")

                    return transcribed_text

                finally:
                    # 一時ファイルを削除
                    if os.path.exists(temp_file_path):
                        os.unlink(temp_file_path)

            except openai.OpenAIError as e:
                logger.error(f"OpenAI API エラー: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"音声変換に失敗しました: {str(e)}"
                )
            except Exception as e:
                logger.error(f"音声変換エラー: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"音声処理中にエラーが発生しました: {str(e)}"
                )

        return await _transcribe_with_tracking()

    def _get_file_extension(self, filename: str) -> str:
        """
        ファイル名から拡張子を取得

        Args:
            filename: ファイル名

        Returns:
            拡張子（ドット付き）
        """
        if '.' in filename:
            return '.' + filename.split('.')[-1]
        return '.wav'  # デフォルト拡張子

    def is_available(self) -> bool:
        """
        音声サービスが利用可能かチェック

        Returns:
            利用可能な場合True
        """
        return self.api_key is not None

    def get_supported_formats(self) -> list:
        """
        サポートされている音声フォーマットのリストを取得

        Returns:
            サポートされているフォーマットのリスト
        """
        return [
            "mp3", "mp4", "mpeg", "mpga", "m4a", 
            "wav", "webm", "flac", "ogg"
        ]
