from fastapi import Query, Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, text
from db.models.product import Product
from db.models.order import Order, OrderItem
from db.database import get_db
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime
from test.test_data_generator import CSVDataImporter

router = APIRouter()

# データ更新用のリクエストモデル
class ProductUpdateRequest(BaseModel):
    name_zh: Optional[str] = None
    name_en: Optional[str] = None
    name_jp: Optional[str] = None
    category: Optional[str] = None
    status: Optional[str] = None
    stock: Optional[int] = None
    price: Optional[float] = None
    description: Optional[str] = None

class OrderUpdateRequest(BaseModel):
    customer_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    order_status: Optional[str] = None
    payment_status: Optional[str] = None
    shipping_status: Optional[str] = None
    total_amount: Optional[float] = None
    tax_amount: Optional[float] = None
    shipping_fee: Optional[float] = None
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    tracking_number: Optional[str] = None

class OrderItemUpdateRequest(BaseModel):
    jancode: Optional[str] = None
    product_name: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None

# 商品テーブル管理API
@router.get("/table/products")
def get_products_table(
    jancode: str = Query(None, description="JANコードフィルター"),
    name_zh: str = Query(None, description="中国語名フィルター"),
    name_en: str = Query(None, description="英語名フィルター"),
    name_jp: str = Query(None, description="日本語名フィルター"),
    category: str = Query(None, description="カテゴリフィルター"),
    status: str = Query(None, description="ステータスフィルター"),
    stock_min: int = Query(None, description="最小在庫数"),
    stock_max: int = Query(None, description="最大在庫数"),
    price_min: float = Query(None, description="最小価格"),
    price_max: float = Query(None, description="最大価格"),
    order_by: str = Query("jancode", description="ソートフィールド"),
    order_direction: str = Query("asc", description="ソート方向: asc または desc"),
    page: int = Query(1, ge=1, description="ページ番号"),
    limit: int = Query(25, description="1ページあたりの件数"),
    db: Session = Depends(get_db)
):
    """商品テーブルデータを取得"""
    try:
        query = db.query(Product)

        # フィルター適用
        if jancode:
            query = query.filter(Product.jancode.contains(jancode))
        if name_zh:
            query = query.filter(Product.name_zh.contains(name_zh))
        if name_en:
            query = query.filter(Product.name_en.contains(name_en))
        if name_jp:
            query = query.filter(Product.name_jp.contains(name_jp))
        if category:
            query = query.filter(Product.category.contains(category))
        if status:
            query = query.filter(Product.status == status)
        if stock_min is not None:
            query = query.filter(Product.stock >= stock_min)
        if stock_max is not None:
            query = query.filter(Product.stock <= stock_max)
        if price_min is not None:
            query = query.filter(Product.price >= price_min)
        if price_max is not None:
            query = query.filter(Product.price <= price_max)

        # ソート適用
        if hasattr(Product, order_by):
            column = getattr(Product, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(desc(column))
            else:
                query = query.order_by(column)

        total = query.count()
        products = query.offset((page - 1) * limit).limit(limit).all()

        result = []
        for p in products:
            result.append({
                "jancode": p.jancode,
                "name_zh": p.name_zh,
                "name_en": p.name_en,
                "name_jp": p.name_jp,
                "category": p.category,
                "status": p.status,
                "stock": p.stock,
                "price": float(p.price) if p.price else 0.0,
                "description": p.description
            })

        return {
            "data": result,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"商品データ取得エラー: {str(e)}")

@router.put("/table/products/{jancode}")
def update_product_table(
    jancode: str,
    request: ProductUpdateRequest,
    db: Session = Depends(get_db)
):
    """商品データを更新"""
    try:
        product = db.query(Product).filter(Product.jancode == jancode).first()
        if not product:
            raise HTTPException(status_code=404, detail="商品が見つかりません")

        # 更新可能なフィールドのみ更新
        if request.name_zh is not None:
            product.name_zh = request.name_zh
        if request.name_en is not None:
            product.name_en = request.name_en
        if request.name_jp is not None:
            product.name_jp = request.name_jp
        if request.category is not None:
            product.category = request.category
        if request.status is not None:
            product.status = request.status
        if request.stock is not None:
            product.stock = request.stock
        if request.price is not None:
            product.price = Decimal(str(request.price))
        if request.description is not None:
            product.description = request.description

        db.commit()
        return {"message": "商品データが正常に更新されました"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"商品データ更新エラー: {str(e)}")

# 注文テーブル管理API
@router.get("/table/orders")
def get_orders_table(
    order_id: str = Query(None, description="注文IDフィルター"),
    customer_id: str = Query(None, description="顧客IDフィルター"),
    customer_name: str = Query(None, description="顧客名フィルター"),
    customer_email: str = Query(None, description="顧客メールフィルター"),
    order_status: str = Query(None, description="注文ステータスフィルター"),
    payment_status: str = Query(None, description="支払いステータスフィルター"),
    shipping_status: str = Query(None, description="配送ステータスフィルター"),
    total_amount_min: float = Query(None, description="最小注文金額"),
    total_amount_max: float = Query(None, description="最大注文金額"),
    order_by: str = Query("order_date", description="ソートフィールド"),
    order_direction: str = Query("desc", description="ソート方向: asc または desc"),
    page: int = Query(1, ge=1, description="ページ番号"),
    limit: int = Query(25, description="1ページあたりの件数"),
    db: Session = Depends(get_db)
):
    """注文テーブルデータを取得"""
    try:
        query = db.query(Order)

        # フィルター適用
        if order_id:
            query = query.filter(Order.order_id.contains(order_id))
        if customer_id:
            query = query.filter(Order.customer_id.contains(customer_id))
        if customer_name:
            query = query.filter(Order.customer_name.contains(customer_name))
        if customer_email:
            query = query.filter(Order.customer_email.contains(customer_email))
        if order_status:
            query = query.filter(Order.order_status == order_status)
        if payment_status:
            query = query.filter(Order.payment_status == payment_status)
        if shipping_status:
            query = query.filter(Order.shipping_status == shipping_status)
        if total_amount_min is not None:
            query = query.filter(Order.total_amount >= total_amount_min)
        if total_amount_max is not None:
            query = query.filter(Order.total_amount <= total_amount_max)

        # ソート適用
        if hasattr(Order, order_by):
            column = getattr(Order, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(desc(column))
            else:
                query = query.order_by(column)

        total = query.count()
        orders = query.offset((page - 1) * limit).limit(limit).all()

        result = []
        for o in orders:
            result.append({
                "order_id": o.order_id,
                "customer_id": o.customer_id,
                "customer_name": o.customer_name,
                "customer_email": o.customer_email,
                "customer_phone": o.customer_phone,
                "order_status": o.order_status,
                "payment_status": o.payment_status,
                "shipping_status": o.shipping_status,
                "total_amount": float(o.total_amount),
                "tax_amount": float(o.tax_amount),
                "shipping_fee": float(o.shipping_fee),
                "shipping_address": o.shipping_address,
                "billing_address": o.billing_address,
                "order_date": o.order_date.isoformat() if o.order_date else None,
                "shipped_date": o.shipped_date.isoformat() if o.shipped_date else None,
                "delivered_date": o.delivered_date.isoformat() if o.delivered_date else None,
                "notes": o.notes,
                "tracking_number": o.tracking_number
            })

        return {
            "data": result,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注文データ取得エラー: {str(e)}")

@router.put("/table/orders/{order_id}")
def update_order_table(
    order_id: str,
    request: OrderUpdateRequest,
    db: Session = Depends(get_db)
):
    """注文データを更新"""
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")

        # 更新可能なフィールドのみ更新
        if request.customer_id is not None:
            order.customer_id = request.customer_id
        if request.customer_name is not None:
            order.customer_name = request.customer_name
        if request.customer_email is not None:
            order.customer_email = request.customer_email
        if request.customer_phone is not None:
            order.customer_phone = request.customer_phone
        if request.order_status is not None:
            order.order_status = request.order_status
        if request.payment_status is not None:
            order.payment_status = request.payment_status
        if request.shipping_status is not None:
            order.shipping_status = request.shipping_status
        if request.total_amount is not None:
            order.total_amount = Decimal(str(request.total_amount))
        if request.tax_amount is not None:
            order.tax_amount = Decimal(str(request.tax_amount))
        if request.shipping_fee is not None:
            order.shipping_fee = Decimal(str(request.shipping_fee))
        if request.shipping_address is not None:
            order.shipping_address = request.shipping_address
        if request.billing_address is not None:
            order.billing_address = request.billing_address
        if request.notes is not None:
            order.notes = request.notes
        if request.tracking_number is not None:
            order.tracking_number = request.tracking_number

        db.commit()
        return {"message": "注文データが正常に更新されました"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注文データ更新エラー: {str(e)}")

# 注文アイテムテーブル管理API
@router.get("/table/order_items")
def get_order_items_table(
    order_id: str = Query(None, description="注文IDフィルター"),
    jancode: str = Query(None, description="JANコードフィルター"),
    product_name: str = Query(None, description="商品名フィルター"),
    quantity_min: int = Query(None, description="最小数量"),
    quantity_max: int = Query(None, description="最大数量"),
    unit_price_min: float = Query(None, description="最小単価"),
    unit_price_max: float = Query(None, description="最大単価"),
    order_by: str = Query("item_id", description="ソートフィールド"),
    order_direction: str = Query("asc", description="ソート方向: asc または desc"),
    page: int = Query(1, ge=1, description="ページ番号"),
    limit: int = Query(25, description="1ページあたりの件数"),
    db: Session = Depends(get_db)
):
    """注文アイテムテーブルデータを取得"""
    try:
        query = db.query(OrderItem)

        # フィルター適用
        if order_id:
            query = query.filter(OrderItem.order_id.contains(order_id))
        if jancode:
            query = query.filter(OrderItem.jancode.contains(jancode))
        if product_name:
            query = query.filter(OrderItem.product_name.contains(product_name))
        if quantity_min is not None:
            query = query.filter(OrderItem.quantity >= quantity_min)
        if quantity_max is not None:
            query = query.filter(OrderItem.quantity <= quantity_max)
        if unit_price_min is not None:
            query = query.filter(OrderItem.unit_price >= unit_price_min)
        if unit_price_max is not None:
            query = query.filter(OrderItem.unit_price <= unit_price_max)

        # ソート適用
        if hasattr(OrderItem, order_by):
            column = getattr(OrderItem, order_by)
            if order_direction.lower() == "desc":
                query = query.order_by(desc(column))
            else:
                query = query.order_by(column)

        total = query.count()
        order_items = query.offset((page - 1) * limit).limit(limit).all()

        result = []
        for oi in order_items:
            result.append({
                "item_id": oi.item_id,
                "order_id": oi.order_id,
                "jancode": oi.jancode,
                "product_name": oi.product_name,
                "quantity": oi.quantity,
                "unit_price": float(oi.unit_price),
                "total_price": float(oi.total_price)
            })

        return {
            "data": result,
            "total": total,
            "page": page,
            "limit": limit,
            "total_pages": (total + limit - 1) // limit
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注文アイテムデータ取得エラー: {str(e)}")

@router.put("/table/order_items/{item_id}")
def update_order_item_table(
    item_id: int,
    request: OrderItemUpdateRequest,
    db: Session = Depends(get_db)
):
    """注文アイテムデータを更新"""
    try:
        order_item = db.query(OrderItem).filter(OrderItem.item_id == item_id).first()
        if not order_item:
            raise HTTPException(status_code=404, detail="注文アイテムが見つかりません")

        # 更新可能なフィールドのみ更新
        if request.jancode is not None:
            order_item.jancode = request.jancode
        if request.product_name is not None:
            order_item.product_name = request.product_name
        if request.quantity is not None:
            order_item.quantity = request.quantity
        if request.unit_price is not None:
            order_item.unit_price = Decimal(str(request.unit_price))
        if request.total_price is not None:
            order_item.total_price = Decimal(str(request.total_price))

        db.commit()
        return {"message": "注文アイテムデータが正常に更新されました"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注文アイテムデータ更新エラー: {str(e)}")

# 削除API
@router.delete("/table/products/{jancode}")
def delete_product_table(
    jancode: str,
    db: Session = Depends(get_db)
):
    """商品データを削除"""
    try:
        product = db.query(Product).filter(Product.jancode == jancode).first()
        if not product:
            raise HTTPException(status_code=404, detail="商品が見つかりません")

        db.delete(product)
        db.commit()
        return {"message": "商品データが正常に削除されました"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"商品データ削除エラー: {str(e)}")

@router.delete("/table/orders/{order_id}")
def delete_order_table(
    order_id: str,
    db: Session = Depends(get_db)
):
    """注文データを削除"""
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")

        db.delete(order)
        db.commit()
        return {"message": "注文データが正常に削除されました"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注文データ削除エラー: {str(e)}")

@router.delete("/table/order_items/{item_id}")
def delete_order_item_table(
    item_id: int,
    db: Session = Depends(get_db)
):
    """注文アイテムデータを削除"""
    try:
        order_item = db.query(OrderItem).filter(OrderItem.item_id == item_id).first()
        if not order_item:
            raise HTTPException(status_code=404, detail="注文アイテムが見つかりません")

        db.delete(order_item)
        db.commit()
        return {"message": "注文アイテムデータが正常に削除されました"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注文アイテムデータ削除エラー: {str(e)}")

# データクリア・再インポートAPI
@router.post("/table/clear_and_reimport")
def clear_and_reimport_data():
    """全データをクリアしてテストデータを再インポート"""
    try:
        importer = CSVDataImporter()
        importer.import_all_from_csv()
        return {"message": "データのクリアと再インポートが正常に完了しました"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"データ再インポートエラー: {str(e)}")
