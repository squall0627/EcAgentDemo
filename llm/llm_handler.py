import os
from typing import Optional
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from config.llm_config_loader import llm_config


class LLMHandler:
    """
    汎用LLMハンドラー、各種LLMの初期化、切り替え、管理を担当
    異なるAgentで再利用可能
    """
    
    def __init__(self, api_key: str, llm_type: Optional[str] = None):
        """
        LLMハンドラーを初期化
        
        Args:
            api_key: APIキー（主にOpenAI用）
            llm_type: LLMタイプ、Noneの場合はデフォルトモデルを使用
        """
        self.api_key = api_key
        self.llm_type = llm_type or llm_config.get_default_model()
        self.llm = self._initialize_llm()
    
    def _initialize_llm(self):
        """設定ファイルに基づいてLLMを初期化"""
        # モデル利用可能性を検証
        is_available, message = llm_config.validate_model_availability(self.llm_type)
        if not is_available:
            print(f"⚠️ {message}")
            # フォールバックモデルを使用
            self.llm_type = llm_config.get_default_model()
            print(f"🔄 フォールバックモデル {self.llm_type} を使用します")
        
        model_config = llm_config.get_model_config(self.llm_type)
        if not model_config:
            raise ValueError(f"モデル設定が見つかりません: {self.llm_type}")
        
        provider = model_config["provider"]
        model_name = model_config["model"]
        temperature = model_config.get("temperature", 0.7)
        
        try:
            if provider == "ollama":
                print(f"🦙 Ollama LLM ({model_name}) を初期化中...")
                return ChatOllama(
                    model=model_name,
                    base_url=model_config.get("base_url", "http://localhost:11434"),
                    temperature=temperature,
                )
            elif provider == "openai":
                print(f"🤖 OpenAI LLM ({model_name}) を初期化中...")
                return ChatOpenAI(
                    openai_api_key=self.api_key,
                    model=model_name,
                    temperature=temperature
                )
            elif provider == "anthropic":
                print(f"🧠 Anthropic LLM ({model_name}) を初期化中...")
                try:
                    from langchain_anthropic import ChatAnthropic
                    return ChatAnthropic(
                        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
                        model=model_name,
                        temperature=temperature
                    )
                except ImportError:
                    print("❌ langchain_anthropicがインストールされていません")
                    return self._fallback_to_default()
            else:
                print(f"❌ 未対応のプロバイダー: {provider}")
                return self._fallback_to_default()
                
        except Exception as e:
            print(f"❌ LLM初期化に失敗しました: {e}")
            return self._fallback_to_default()

    def _fallback_to_default(self):
        """デフォルトモデルにフォールバック"""
        default_model = llm_config.get_default_model()
        default_config = llm_config.get_model_config(default_model)
        
        print(f"🔄 デフォルトモデル {default_model} にフォールバックします")
        
        if default_config["provider"] == "ollama":
            return ChatOllama(
                model=default_config["model"],
                base_url=default_config.get("base_url", "http://localhost:11434"),
                temperature=default_config.get("temperature", 0.7),
            )
        else:
            # 最後の手段としてOpenAI
            return ChatOpenAI(
                openai_api_key=self.api_key,
                model="gpt-4o-mini",
                temperature=0.1
            )

    def switch_llm(self, new_llm_type: str):
        """実行時にLLMタイプを切り替え"""
        if new_llm_type != self.llm_type:
            old_type = self.llm_type
            self.llm_type = new_llm_type
            self.llm = self._initialize_llm()
            
            new_config = llm_config.get_model_config(new_llm_type)
            if new_config:
                print(f"✅ LLMを{old_type}から{new_config['provider']}:{new_config['model']}に切り替えました")
            else:
                print(f"✅ LLMを{new_llm_type}に切り替えました")

    def get_available_llms(self):
        """利用可能なLLMのリストを取得"""
        return [model["value"] for model in llm_config.get_all_models()]
    
    def get_llm_info(self, llm_type: Optional[str] = None):
        """LLM情報を取得"""
        target_type = llm_type or self.llm_type
        model_config = llm_config.get_model_config(target_type)
        
        if model_config:
            return {
                "type": target_type,
                "provider": model_config.get("provider", "unknown"),
                "model": model_config.get("model", "unknown"),
                "temperature": model_config.get("temperature", 0.7),
                "label": model_config.get("label", target_type),
                "description": model_config.get("description", "")
            }
        else:
            return {
                "type": target_type,
                "provider": "unknown",
                "model": "unknown",
                "temperature": 0.7,
                "label": target_type,
                "description": "設定が見つかりません"
            }
    
    def get_llm(self):
        """現在使用中のLLMインスタンスを取得"""
        return self.llm
    
    def get_llm_with_tools(self, tools):
        """ツール付きLLMを取得"""
        return self.llm.bind_tools(tools)
    
    def get_current_llm_type(self):
        """現在のLLMタイプを取得"""
        return self.llm_type