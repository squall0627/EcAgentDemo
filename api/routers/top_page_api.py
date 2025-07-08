from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from config.llm_config_loader import llm_config
from config.agent_hierarchy_loader import agent_hierarchy_loader
import json
from pathlib import Path

router = APIRouter()

def _build_hierarchical_options(hierarchy, options_list, prefix, level):
    """階層構造に基づいてエージェント選択肢を構築"""
    items = list(hierarchy.items())
    for i, (key, agent_info) in enumerate(items):
        is_last = i == len(items) - 1

        # 階層表示用のプレフィックスを生成（レベルに応じてより多くの缩进を追加）
        if level == 0:
            display_prefix = ""
        elif level == 1:
            current_prefix = "└─" if is_last else "├─"
            display_prefix = "　　" + current_prefix  # 全角スペース2個 + 記号
        elif level == 2:
            current_prefix = "└─" if is_last else "├─"
            display_prefix = "　　　　　　" + current_prefix  # 全角スペース6個 + 記号
        else:
            current_prefix = "└─" if is_last else "├─"
            # レベル3以上の場合はさらに缩进を増やす
            spaces = "　　" * (level * 3)
            display_prefix = spaces + current_prefix

        # 表示名を生成
        japanese_name = agent_info.get("japanese_name", key)
        display_name = f"{display_prefix}{japanese_name}" if display_prefix else japanese_name

        # オプションデータを追加
        option_data = {
            "agent_key": key,
            "id": key.lower(),
            "level": level,
            "description": agent_info.get("description", ""),
            "display_name": display_name
        }
        options_list.append(option_data)

        # 子階層がある場合は再帰的に処理
        if "children" in agent_info and agent_info["children"]:
            # 次のレベルのプレフィックスも調整
            if level == 0:
                next_prefix = "　　│　"  # 全角スペース2個 + │ + 全角スペース1個
            elif level == 1:
                next_prefix = "　　　　　　│　" if not is_last else "　　　　　　　　"  # より多くの缩进
            else:
                next_prefix = prefix + ("　　　　" if is_last else "│　　　")
            _build_hierarchical_options(agent_info["children"], options_list, next_prefix, level + 1)

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

    # エージェント階層情報を取得
    hierarchy = agent_hierarchy_loader.get_agent_hierarchy()

    # 階層構造に基づいたエージェント選択肢の生成
    agent_options = ""
    agent_options_list = []
    _build_hierarchical_options(hierarchy, agent_options_list, "", 0)

    for i, option_data in enumerate(agent_options_list):
        selected = 'selected' if i == 0 else ''  # 最初のエージェントをデフォルト選択
        # HTMLエスケープ処理
        description = option_data["description"].replace('"', '&quot;')
        agent_options += f'''<option value="{option_data["agent_key"]}" 
                           data-id="{option_data["id"]}"
                           data-level="{option_data["level"]}"
                           data-description="{description}" 
                           {selected}>{option_data["display_name"]}</option>\n'''

    # JavaScript用のエージェント設定
    entry_points = agent_hierarchy_loader.get_entry_points()
    agent_js_config = {
        "entry_points": entry_points,
        "hierarchy": hierarchy,
        "hierarchical_options": agent_options_list
    }

    # 外部テンプレートファイルのパスを取得（HTMLとCSSを分離したファイル構造）
    template_path = Path(__file__).parent.parent.parent / "static" / "templates" / "top_page_template.html"

    # 外部HTMLテンプレートファイルを読み込み（UTF-8エンコーディング）
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    # テンプレート内のプレースホルダーを動的な値で置換
    # {{LLM_OPTIONS}} → 生成されたLLMオプションのHTMLに置換
    html = html_template.replace('{{LLM_OPTIONS}}', llm_options)
    # {{AGENT_OPTIONS}} → 生成されたエージェントオプションのHTMLに置換
    html = html.replace('{{AGENT_OPTIONS}}', agent_options)
    # "{{LLM_JS_CONFIG}}" → JSON形式のJavaScript設定オブジェクトに置換
    html = html.replace('"{{LLM_JS_CONFIG}}"', json.dumps(llm_js_config, ensure_ascii=False))
    # "{{AGENT_JS_CONFIG}}" → JSON形式のエージェント設定オブジェクトに置換
    html = html.replace('"{{AGENT_JS_CONFIG}}"', json.dumps(agent_js_config, ensure_ascii=False))

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

@router.get("/agent-hierarchy")
async def get_agent_hierarchy():
    """エージェント階層情報を取得するAPI"""
    return {
        "entry_points": agent_hierarchy_loader.get_entry_points(),
        "hierarchy": agent_hierarchy_loader.get_agent_hierarchy(),
        "tree_display": agent_hierarchy_loader.get_hierarchy_tree_display()
    }

@router.post("/agent-hierarchy/reload")
async def reload_agent_hierarchy():
    """エージェント階層設定を再読み込み"""
    agent_hierarchy_loader.reload_config()
    return {"message": "エージェント階層設定が再読み込みされました"}
