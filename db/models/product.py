from sqlalchemy import Column, String, Integer, Numeric, Text

from db.database import Base


class Product(Base):
    __tablename__ = "products"
    
    jancode = Column(String(50), primary_key=True)  # JANコード（主キー）
    name_zh = Column(String(255))  # 中国語商品名
    name_en = Column(String(255))  # 英語商品名
    name_jp = Column(String(255))  # 日本語商品名
    category = Column(String(255), nullable=True)  # 商品カテゴリ
    status = Column(String(255))  # ステータス（'unpublished' / 'published'）
    stock = Column(Integer, default=0)  # 在庫数
    price = Column(Numeric(10, 2), default=0, nullable=False)  # 価格（小数点以下2桁まで、デフォルト値0）
    description = Column(Text, nullable=True)  # 商品説明