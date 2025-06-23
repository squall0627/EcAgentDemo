from sqlalchemy import Column, String, Integer

from db.database import Base


class Product(Base):
    __tablename__ = "products"
    
    jancode = Column(String(50), primary_key=True)
    name_zh = Column(String(255))
    name_en = Column(String(255))
    name_jp = Column(String(255))
    category = Column(String(255), nullable=True)
    status = Column(String(255))  # 'unpublished' / 'published'
    stock = Column(Integer, default=0)