from contextlib import asynccontextmanager
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.routers import product_api, agent_api, html_api, top_page_api, chat_api, order_api, settings_api, table_api
from db.database import init_db
from fastapi.middleware.cors import CORSMiddleware


# 環境変数のロード
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時：アプリケーション開始前にテーブルを作成
    init_db()
    yield
    # 終了時：必要に応じてリソースをクリーンアップ
    # ここにクリーンアップコードを追加

app = FastAPI(title="EC商品管理システム", version="1.0.0", lifespan=lifespan)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルの設定（CSS、JS、画像などを提供）
def get_static_directory():
    """PyInstallerでパッケージ化された場合の静的ファイルディレクトリを取得"""
    if getattr(sys, 'frozen', False):
        # PyInstallerでパッケージ化された場合
        bundle_dir = sys._MEIPASS
        static_dir = os.path.join(bundle_dir, 'static')
    else:
        # 通常の開発環境
        static_dir = "static"

    return static_dir

static_directory = get_static_directory()
if os.path.exists(static_directory):
    app.mount("/static", StaticFiles(directory=static_directory), name="static")
else:
    print(f"⚠️ 静的ファイルディレクトリが見つかりません: {static_directory}")

# ルーター追加
app.include_router(top_page_api.router, prefix="/api/top", tags=["top"])
app.include_router(product_api.router, prefix="/api/product", tags=["products"])
app.include_router(order_api.router, prefix="/api/order", tags=["orders"])
app.include_router(agent_api.router, prefix="/api/agent", tags=["agent"])
app.include_router(html_api.router, prefix="/api/html", tags=["html"])
app.include_router(chat_api.router, prefix="/api/chat", tags=["chat"])
app.include_router(settings_api.router, prefix="/api/settings", tags=["settings"])
app.include_router(table_api.router, prefix="/api", tags=["table"])


@app.get("/")
async def root():
    return {"message": "ECバックオフィス管理システム API"}


if __name__ == "__main__":
    import uvicorn
    import os
    from urllib.parse import urlparse

    # 環境変数からAPI_BASE_URLを取得してホストとポートを動的に設定
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    parsed_url = urlparse(api_base_url)

    # ホストとポートを抽出
    host = parsed_url.hostname or "localhost"
    port = parsed_url.port or 8000

    print(f"🚀 EcAgentDemo を起動中...")
    print(f"📱 ブラウザで {api_base_url}/api/top にアクセスしてください")
    print(f"⚙️  設定変更は {api_base_url}/api/html/settings にアクセス")
    print("=" * 50)

    # Uvicornサーバーを起動
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )
