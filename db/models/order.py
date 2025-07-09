from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from db.database import Base


class Order(Base):
    """注文モデル"""
    __tablename__ = "orders"
    
    order_id = Column(String(50), primary_key=True)  # 注文ID（主キー）
    customer_id = Column(String(50), nullable=False)  # 顧客ID
    customer_name = Column(String(255), nullable=False)  # 顧客名
    customer_email = Column(String(255), nullable=True)  # 顧客メールアドレス
    customer_phone = Column(String(50), nullable=True)  # 顧客電話番号
    
    # 注文ステータス: 'pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled'
    order_status = Column(String(50), default='pending', nullable=False)  
    
    # 支払いステータス: 'unpaid', 'paid', 'refunded', 'partial_refund'
    payment_status = Column(String(50), default='unpaid', nullable=False)
    
    # 配送ステータス: 'not_shipped', 'preparing', 'shipped', 'in_transit', 'delivered'
    shipping_status = Column(String(50), default='not_shipped', nullable=False)
    
    total_amount = Column(Numeric(10, 2), default=0, nullable=False)  # 合計金額
    tax_amount = Column(Numeric(10, 2), default=0, nullable=False)  # 税額
    shipping_fee = Column(Numeric(10, 2), default=0, nullable=False)  # 送料
    
    shipping_address = Column(Text, nullable=True)  # 配送先住所
    billing_address = Column(Text, nullable=True)  # 請求先住所
    
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False)  # 注文日時
    shipped_date = Column(DateTime, nullable=True)  # 発送日時
    delivered_date = Column(DateTime, nullable=True)  # 配達日時
    
    notes = Column(Text, nullable=True)  # 備考
    tracking_number = Column(String(100), nullable=True)  # 追跡番号
    
    # リレーション
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """注文アイテムモデル"""
    __tablename__ = "order_items"
    
    item_id = Column(Integer, primary_key=True, autoincrement=True)  # アイテムID（主キー）
    order_id = Column(String(50), ForeignKey('orders.order_id'), nullable=False)  # 注文ID（外部キー）
    jancode = Column(String(50), nullable=False)  # 商品JANコード
    product_name = Column(String(255), nullable=False)  # 商品名（注文時点での名前）
    quantity = Column(Integer, default=1, nullable=False)  # 数量
    unit_price = Column(Numeric(10, 2), nullable=False)  # 単価
    total_price = Column(Numeric(10, 2), nullable=False)  # 小計
    
    # リレーション
    order = relationship("Order", back_populates="order_items")