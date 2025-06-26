import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# SQLiteインメモリデータベースを使用
SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"  # ローカルファイルデータベースを作成

# インメモリSQLite用のSQLAlchemyエンジンを作成
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,  # 本番環境ではFalseに設定
    connect_args={"check_same_thread": False},  # SQLiteに必要
)

# SessionLocalクラスを作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Baseクラスを作成
Base = declarative_base()


# DBセッションを取得する依存関数
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# すべてのテーブルを作成する関数
def init_db():
    Base.metadata.create_all(bind=engine)