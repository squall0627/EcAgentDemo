from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routers import product_api, agent_api, html_api
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 起動時：アプリケーション開始前にテーブルを作成
    init_db()
    yield
    # 終了時：必要に応じてリソースをクリーンアップ
    # ここにクリーンアップコードを追加

app = FastAPI(title="EC商品管理システム", version="1.0.0", lifespan=lifespan)

# ルーター追加
app.include_router(product_api.router, prefix="/api/product", tags=["products"])
app.include_router(agent_api.router, prefix="/api/agent", tags=["agent"])
app.include_router(html_api.router, prefix="/api/html", tags=["html"])


@app.get("/")
async def root():
    return {
        "message": "EC商品管理システム", 
        "features": [
            "自然言語による商品検索",
            "動的HTML画面生成",
            "商品棚上げ・棚下げ管理",
            "エラー処理と解決誘導"
        ]
    }