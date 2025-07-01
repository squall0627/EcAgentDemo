import os
from typing import Dict, Optional


# Langfuse V3 imports
LANGFUSE_AVAILABLE = False

try:
    from langfuse import Langfuse
    from langfuse.langchain import CallbackHandler
    from langfuse import observe
    LANGFUSE_AVAILABLE = True
    print("✅ Langfuse V3 CallbackHandler正常にインポートされました")
except ImportError as e:
    print(f"❌ Langfuse V3 CallbackHandlerが利用できません: {e}")
    LANGFUSE_AVAILABLE = False


class LangfuseHandler:
    """Langfuse管理用クラス - 複数のエージェントで再利用可能"""

    def __init__(self, use_langfuse: bool = True):
        """Langfuse ハンドラーを初期化"""
        self.use_langfuse = use_langfuse and LANGFUSE_AVAILABLE
        self.langfuse_client = None
        self.callback_handler = None

        if self.use_langfuse:
            self._initialize_langfuse()

    def _initialize_langfuse(self):
        """Langfuse V3 を初期化"""
        try:
            public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
            secret_key = os.getenv("LANGFUSE_SECRET_KEY")
            host = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

            if public_key and secret_key:
                self.langfuse_client = Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host,
                )
                self.callback_handler = CallbackHandler()
                print("✅ Langfuse V3が正常に初期化されました")
            else:
                print("⚠️  Langfuse認証情報が見つかりません")
                self.use_langfuse = False
        except Exception as e:
            print(f"❌ Langfuse初期化に失敗しました: {e}")
            self.use_langfuse = False

    def get_callback_handler(self) -> Optional[CallbackHandler]:
        """Langfuse CallbackHandlerを取得"""
        return self.callback_handler if self.use_langfuse else None

    def get_config(self, step_name: str = None, session_id: str = None, user_id: str = None) -> Dict:
        """Langfuse設定を取得"""
        if self.use_langfuse and self.callback_handler:
            return {
                "callbacks": [self.callback_handler],
                "metadata": {
                    "langfuse.user_id": user_id,
                    "langfuse.session_id": session_id,
                    "langfuse.step_name": step_name
                }
            }
        return {}

    def is_available(self) -> bool:
        """Langfuseが利用可能かどうか"""
        return self.use_langfuse and self.callback_handler is not None

    def observe_decorator(self, name: str):
        """observeデコレータを取得（利用可能な場合のみ）"""
        if LANGFUSE_AVAILABLE:
            return observe(name=name)
        else:
            # Langfuseが利用できない場合は何もしないデコレータを返す
            def dummy_decorator(func):
                return func
            return dummy_decorator

    def get_current_trace_id(self) -> Optional[str]:
        """現在のtrace_idを取得（Langfuse V3対応）"""
        if not self.is_available():
            return None

        try:
            # CallbackHandlerからcurrent trace_idを取得
            if hasattr(self.callback_handler, 'get_current_trace_id'):
                return self.callback_handler.get_current_trace_id()

            # 代替方法: CallbackHandlerの内部状態から取得
            if hasattr(self.callback_handler, '_current_trace_id'):
                return self.callback_handler._current_trace_id

            # さらなる代替方法: langfuse clientから取得
            if hasattr(self.langfuse_client, 'get_current_trace_id'):
                return self.langfuse_client.get_current_trace_id()

            return None
        except Exception as e:
            print(f"⚠️ trace_id取得エラー: {e}")
            return None


# グローバルなLangfuseハンドラーインスタンス（オプション）
_global_langfuse_handler = None


def get_global_langfuse_handler() -> LangfuseHandler:
    """グローバルなLangfuseハンドラーを取得（シングルトンパターン）"""
    global _global_langfuse_handler
    if _global_langfuse_handler is None:
        _global_langfuse_handler = LangfuseHandler()
    return _global_langfuse_handler


def create_langfuse_handler(use_langfuse: bool = True) -> LangfuseHandler:
    """新しいLangfuseハンドラーインスタンスを作成"""
    return LangfuseHandler(use_langfuse=use_langfuse)
