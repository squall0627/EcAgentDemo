import json
import os
from typing import Dict, List, Optional, Any
from pathlib import Path

class LLMConfigLoader:
    """LLM設定ローダー"""
    
    def __init__(self, config_path: str = Path(__file__).parent / "llm_config.json"):
        self.config_path = Path(config_path)
        self._config_cache = None
        self._load_config()
    
    def _load_config(self) -> None:
        """設定ファイルを読み込む"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config_cache = json.load(f)
            else:
                # デフォルト設定を作成
                self._create_default_config()
                print(f"⚠️ 設定ファイルが存在しません。デフォルト設定を作成しました: {self.config_path}")
        except Exception as e:
            print(f"❌ 設定ファイルの読み込みに失敗しました: {e}")
            self._config_cache = self._get_fallback_config()
    
    def _create_default_config(self) -> None:
        """デフォルト設定ファイルを作成"""
        # configディレクトリを作成（存在しない場合）
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        default_config = self._get_fallback_config()
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        self._config_cache = default_config
    
    def _get_fallback_config(self) -> Dict[str, Any]:
        """フォールバック設定を取得"""
        return {
            "llm_models": [
                {
                    "value": "ollama_qwen3",
                    "label": "🦙 Ollama - Qwen3 30B",
                    "provider": "ollama",
                    "model": "qwen3:30b",
                    "base_url": "http://localhost:11434",
                    "temperature": 0.7,
                    "color": "ollama",
                    "description": "デフォルトローカルモデル",
                    "default": True
                }
            ],
            "provider_settings": {
                "ollama": {
                    "requires_api_key": False,
                    "default_base_url": "http://localhost:11434",
                    "fallback_model": "qwen3:30b"
                }
            }
        }
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """すべてのLLMモデル設定を取得"""
        return self._config_cache.get("llm_models", [])
    
    def get_model_config(self, model_value: str) -> Optional[Dict[str, Any]]:
        """特定のモデル設定を取得"""
        models = self.get_all_models()
        for model in models:
            if model.get("value") == model_value:
                return model
        return None
    
    def get_default_model(self) -> str:
        """デフォルトモデルの値を取得"""
        models = self.get_all_models()
        for model in models:
            if model.get("default", False):
                return model.get("value")
        # デフォルトが設定されていない場合、最初のモデルを返す
        return models[0].get("value") if models else "ollama_qwen"
    
    def get_provider_settings(self, provider: str) -> Dict[str, Any]:
        """プロバイダー設定を取得"""
        provider_settings = self._config_cache.get("provider_settings", {})
        return provider_settings.get(provider, {})
    
    def get_models_by_provider(self, provider: str) -> List[Dict[str, Any]]:
        """プロバイダー別のモデルリストを取得"""
        models = self.get_all_models()
        return [model for model in models if model.get("provider") == provider]
    
    def validate_model_availability(self, model_value: str) -> tuple[bool, str]:
        """モデルの利用可能性を検証"""
        model_config = self.get_model_config(model_value)
        if not model_config:
            return False, f"モデル '{model_value}' は設定されていません"
        
        provider = model_config.get("provider")
        provider_settings = self.get_provider_settings(provider)
        
        # APIキーが必要な場合の検証
        if provider_settings.get("requires_api_key", False):
            api_key_env = provider_settings.get("api_key_env")
            if api_key_env and not os.getenv(api_key_env):
                return False, f"{provider} APIキーが設定されていません ({api_key_env})"
        
        return True, "利用可能"
    
    def get_frontend_config(self) -> str:
        """フロントエンド用のJavaScript設定を生成"""
        models = self.get_all_models()
        return json.dumps(models, ensure_ascii=False)
    
    def reload_config(self) -> None:
        """設定を再読み込み"""
        self._config_cache = None
        self._load_config()
        print("✅ LLM設定が再読み込みされました")

# グローバルインスタンス
llm_config = LLMConfigLoader()