from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from config.llm_config_loader import llm_config
import json
from pathlib import Path

router = APIRouter()

@router.get("", response_class=HTMLResponse)
async def get_management_interface():
    """商品管理メインインターフェース - 設定ファイルベース"""

    # 設定ファイルからLLM設定を取得
    llm_models = llm_config.get_all_models()
    default_model = llm_config.get_default_model()

    # 選択肢の生成
    llm_options = ""
    for model_config in llm_models:
        selected = 'selected' if model_config["value"] == default_model else ''
        llm_options += f'''<option value="{model_config["value"]}" 
                         data-provider="{model_config["provider"]}" 
                         data-model="{model_config["model"]}" 
                         data-color="{model_config["color"]}"
                         data-description="{model_config.get("description", "")}" 
                         {selected}>{model_config["label"]}</option>\n'''

    # JavaScript用の設定
    llm_js_config = llm_config.get_frontend_config()

    # 外部テンプレートファイルのパスを取得（HTMLとCSSを分離したファイル構造）
    template_path = Path(__file__).parent.parent.parent / "static" / "templates" / "top_page_template.html"

    # 外部HTMLテンプレートファイルを読み込み（UTF-8エンコーディング）
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    # テンプレート内のプレースホルダーを動的な値で置換
    # {{LLM_OPTIONS}} → 生成されたLLMオプションのHTMLに置換
    html = html_template.replace('{{LLM_OPTIONS}}', llm_options)
    # "{{LLM_JS_CONFIG}}" → JSON形式のJavaScript設定オブジェクトに置換
    html = html.replace('"{{LLM_JS_CONFIG}}"', json.dumps(llm_js_config, ensure_ascii=False))

    return HTMLResponse(content=html)

@router.get("/llm-config")
async def get_llm_config():
    """LLM設定情報を取得するAPI"""
    return {
        "models": llm_config.get_all_models(),
        "default_model": llm_config.get_default_model(),
        "provider_settings": llm_config._config_cache.get("provider_settings", {})
    }

@router.post("/llm-config/reload")
async def reload_llm_config():
    """LLM設定を再読み込み"""
    llm_config.reload_config()
    return {"message": "LLM設定が再読み込みされました"}
