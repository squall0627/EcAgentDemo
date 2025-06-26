from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.routers import product_api, agent_api, html_api, top_page_api
from db.database import init_db
from fastapi.middleware.cors import CORSMiddleware


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


# ルーター追加
app.include_router(top_page_api.router, prefix="/api/top", tags=["top"])
app.include_router(product_api.router, prefix="/api/product", tags=["products"])
app.include_router(agent_api.router, prefix="/api/agent", tags=["agent"])
app.include_router(html_api.router, prefix="/api/html", tags=["html"])


@app.get("/")
async def root():
    return {"message": "ECバックオフィス管理システム API"}
