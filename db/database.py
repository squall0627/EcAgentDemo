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
    # データベースモデルをインポートしてテーブル定義を登録
    from db.models.product import Product
    from db.models.order import Order, OrderItem

    Base.metadata.create_all(bind=engine)

    # データベースが空かどうかをチェック（初回起動かどうかの判定）
    if _is_database_empty():
        print("データベースが空です。初回起動時のテストデータを導入します。")
        _import_test_data_on_first_startup()
    else:
        print("データベースにデータが存在します。テストデータの導入をスキップします。")


def _is_database_empty():
    """データベースが空かどうかをチェック"""
    db = SessionLocal()
    try:
        # 主要なテーブルにデータがあるかチェック
        from db.models.product import Product
        from db.models.order import Order, OrderItem

        product_count = db.query(Product).count()
        order_count = db.query(Order).count()
        order_item_count = db.query(OrderItem).count()

        # すべてのテーブルが空の場合のみTrue
        return product_count == 0 and order_count == 0 and order_item_count == 0
    except Exception as e:
        print(f"データベース状態チェック中にエラーが発生しました: {e}")
        # エラーが発生した場合は安全のため空と判定
        return True
    finally:
        db.close()


def _import_test_data_on_first_startup():
    """初回起動時のみテストデータを導入"""
    # 開発環境でのみテストデータを導入（CSV ファイルが存在する場合）
    csv_files = [
        "test/csv_data/products.csv",
        "test/csv_data/orders.csv", 
        "test/csv_data/order_items.csv"
    ]

    # CSVファイルの存在をチェックし、不足している場合は生成
    missing_files = [f for f in csv_files if not os.path.exists(f)]

    if missing_files:
        print(f"CSV ファイルが見つかりません: {missing_files}")
        print("TestDataGenerator を使用してCSVファイルを生成中...")

        try:
            from test.test_data_generator import TestDataGenerator
            generator = TestDataGenerator()
            generator.generate_all_test_data()
            print("CSV ファイルの生成が完了しました。")
        except Exception as e:
            print(f"CSV ファイル生成中にエラーが発生しました: {e}")
            print("アプリケーションは空のデータベースで起動します。")
            return

    # CSVファイルからテストデータをインポート
    try:
        print("CSV ファイルからテストデータを導入中...")
        from test.test_data_generator import CSVDataImporter
        importer = CSVDataImporter()
        importer.import_all_from_csv()
        print("テストデータの導入が完了しました。")
    except Exception as e:
        print(f"テストデータの導入中にエラーが発生しました: {e}")
        print("アプリケーションは空のデータベースで起動します。")
