import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Optional
from pathlib import Path

router = APIRouter()

class EnvironmentVariable(BaseModel):
    """環境変数設定のモデル"""
    key: str
    value: str
    description: Optional[str] = None

class SettingsUpdate(BaseModel):
    """設定更新のモデル"""
    variables: Dict[str, str]

# 環境変数の説明マップ（日本語）
ENV_DESCRIPTIONS = {
    "OPENAI_API_KEY": "OpenAI APIキー - ChatGPTやGPT-4を使用するために必要",
    "ANTHROPIC_API_KEY": "Claude APIキー - Anthropic Claudeを使用するために必要",
    "GOOGLE_API_KEY": "Gemini APIキー - Google Geminiを使用するために必要",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "アクセストークンの有効期限（分）",
    "API_BASE_URL": "APIのベースURL",
    "LANGFUSE_PUBLIC_KEY": "Langfuse公開キー - トレーシング用",
    "LANGFUSE_SECRET_KEY": "Langfuseシークレットキー - トレーシング用",
    "LANGFUSE_HOST": "Langfuseホスト - トレーシングサーバーのURL"
}

def get_env_file_path():
    """環境変数ファイルのパスを取得"""
    return Path(__file__).parent.parent.parent / ".env"

def read_env_file():
    """環境変数ファイルを読み込み"""
    env_path = get_env_file_path()
    env_vars = {}

    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()

    return env_vars

def write_env_file(env_vars: Dict[str, str]):
    """環境変数ファイルに書き込み"""
    env_path = get_env_file_path()

    with open(env_path, 'w', encoding='utf-8') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

        # Langfuse設定のコメントを追加
        if "LANGFUSE_HOST" in env_vars:
            f.write("\n# Langfuse配置\n")

@router.get("/page", response_class=HTMLResponse)
async def get_settings_page():
    """設定ページを取得"""
    # 設定ページのテンプレートファイルのパス
    template_path = Path(__file__).parent.parent.parent / "static" / "templates" / "settings_page_template.html"

    # テンプレートファイルを読み込み
    with open(template_path, 'r', encoding='utf-8') as f:
        html_template = f.read()

    # 現在の環境変数を取得
    current_env = read_env_file()

    # 環境変数の設定フォームを生成
    env_form_html = generate_env_form_html(current_env)

    # テンプレートのプレースホルダーを置換
    html = html_template.replace('{{ENV_FORM}}', env_form_html)

    return HTMLResponse(content=html)

@router.get("/variables")
async def get_environment_variables():
    """現在の環境変数設定を取得"""
    try:
        env_vars = read_env_file()

        # 環境変数を説明付きで返す
        result = []
        for key, value in env_vars.items():
            result.append({
                "key": key,
                "value": value,
                "description": ENV_DESCRIPTIONS.get(key, "")
            })

        return {"variables": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"環境変数の読み込みに失敗しました: {str(e)}")

@router.post("/variables")
async def update_environment_variables(settings: SettingsUpdate):
    """環境変数設定を更新"""
    try:
        # 現在の環境変数を読み込み
        current_env = read_env_file()

        # 新しい設定で更新
        current_env.update(settings.variables)

        # ファイルに書き込み
        write_env_file(current_env)

        # 環境変数を実際のプロセスにも反映
        for key, value in settings.variables.items():
            os.environ[key] = value

        return {"message": "環境変数が正常に更新されました", "updated_count": len(settings.variables)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"環境変数の更新に失敗しました: {str(e)}")

def generate_env_form_html(env_vars: Dict[str, str]) -> str:
    """環境変数設定フォームのHTMLを生成（3つのセクションに分けて表示）"""
    form_html = ""

    # セクション1: LLM APIキー設定
    llm_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
    form_html += generate_section_header("🤖 LLM APIキー設定", "各種大規模言語モデルのAPIキーを設定します")
    form_html += '<div class="settings-section">'
    for key in llm_keys:
        value = env_vars.get(key, "")
        description = ENV_DESCRIPTIONS.get(key, "")
        form_html += generate_input_field(key, value, description, is_password=True)
    form_html += '</div>'

    # セクション2: FastAPI設定
    fastapi_keys = ["ACCESS_TOKEN_EXPIRE_MINUTES", "API_BASE_URL"]
    form_html += generate_section_header("⚙️ FastAPI設定", "APIサーバーの基本設定を行います")
    form_html += '<div class="settings-section">'
    for key in fastapi_keys:
        if key in env_vars:
            value = env_vars[key]
            description = ENV_DESCRIPTIONS.get(key, "")
            form_html += generate_input_field(key, value, description, is_password=False)
    form_html += '</div>'

    # セクション3: Langfuse設定
    langfuse_keys = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"]
    form_html += generate_section_header("📊 Langfuse設定", "トレーシングとモニタリング用の設定を行います")
    form_html += '<div class="settings-section">'
    for key in langfuse_keys:
        if key in env_vars:
            value = env_vars[key]
            description = ENV_DESCRIPTIONS.get(key, "")
            is_password = "KEY" in key or "SECRET" in key
            form_html += generate_input_field(key, value, description, is_password)
    form_html += '</div>'

    # その他の環境変数（上記3つのセクションに含まれないもの）
    all_categorized_keys = llm_keys + fastapi_keys + langfuse_keys
    other_keys = [key for key in env_vars.keys() if key not in all_categorized_keys]

    if other_keys:
        form_html += generate_section_header("🔧 その他の設定", "その他の環境変数設定")
        form_html += '<div class="settings-section">'
        for key in other_keys:
            value = env_vars[key]
            description = ENV_DESCRIPTIONS.get(key, "")
            is_password = "KEY" in key or "SECRET" in key
            form_html += generate_input_field(key, value, description, is_password)
        form_html += '</div>'

    return form_html

def generate_section_header(title: str, description: str) -> str:
    """セクションヘッダーのHTMLを生成"""
    return f'''
    <div class="section-header">
        <h3 class="section-title">{title}</h3>
        <p class="section-description">{description}</p>
    </div>
    '''

def generate_input_field(key: str, value: str, description: str, is_password: bool = False) -> str:
    """入力フィールドのHTMLを生成（横並びレイアウト）"""
    input_type = "password" if is_password else "text"

    if is_password:
        # パスワードフィールドには目のアイコンを追加
        return f'''
    <div class="env-field">
        <div class="env-label-container">
            <label for="{key}" class="env-label">{key}</label>
            {f'<span class="env-description">{description}</span>' if description else ''}
        </div>
        <div class="env-input-container">
            <div class="input-with-eye">
                <input type="{input_type}" id="{key}" name="{key}" value="{value}" class="env-input">
                <button type="button" class="eye-toggle" onclick="togglePasswordVisibility('{key}')" title="パスワードの表示/非表示を切り替え">
                    <span class="eye-icon" id="eye-{key}">👁️</span>
                </button>
            </div>
        </div>
    </div>
    '''
    else:
        # 通常のテキストフィールド
        return f'''
    <div class="env-field">
        <div class="env-label-container">
            <label for="{key}" class="env-label">{key}</label>
            {f'<span class="env-description">{description}</span>' if description else ''}
        </div>
        <div class="env-input-container">
            <input type="{input_type}" id="{key}" name="{key}" value="{value}" class="env-input">
        </div>
    </div>
    '''
