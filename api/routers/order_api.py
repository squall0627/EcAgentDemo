from fastapi import Query, Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from db.models.order import Order, OrderItem
from db.models.product import Product
from db.database import get_db
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime
import uuid

router = APIRouter()

def apply_order_search_filters(query, search_conditions: Dict[str, Any]):
    """注文検索フィルターを適用"""
    for field, value in search_conditions.items():
        if value is not None:
            if field == "customer_name":
                query = query.filter(Order.customer_name.contains(value))
            elif field == "customer_email":
                query = query.filter(Order.customer_email.contains(value))
            elif field == "order_status":
                query = query.filter(Order.order_status == value)
            elif field == "payment_status":
                query = query.filter(Order.payment_status == value)
            elif field == "shipping_status":
                query = query.filter(Order.shipping_status == value)
            elif field == "total_amount_min":
                query = query.filter(Order.total_amount >= value)
            elif field == "total_amount_max":
                query = query.filter(Order.total_amount <= value)
    return query

def apply_order_dynamic_order(query, order_by: str, order_direction: str):
    """動的ソート適用"""
    order_field = getattr(Order, order_by, None)
    if order_field is not None:
        if order_direction == "desc":
            query = query.order_by(desc(order_field))
        else:
            query = query.order_by(order_field)
    return query

@router.get("/orders")
def get_orders(
    order_id: str = Query(None, description="Order ID filter"),
    customer_id: str = Query(None, description="Customer ID filter"),
    customer_name: str = Query(None, description="Customer name filter"),
    customer_email: str = Query(None, description="Customer email filter"),
    order_status: str = Query(None, description="Order status filter: pending, confirmed, processing, shipped, delivered, cancelled"),
    payment_status: str = Query(None, description="Payment status filter: unpaid, paid, refunded, partial_refund"),
    shipping_status: str = Query(None, description="Shipping status filter: not_shipped, preparing, shipped, in_transit, delivered"),
    total_amount_min: float = Query(None, description="最小注文金額フィルター"),
    total_amount_max: float = Query(None, description="最大注文金額フィルター"),
    order_by: str = Query("order_date", description="並び順フィールド: order_id, customer_name, order_status, payment_status, shipping_status, total_amount, order_date"),
    order_direction: str = Query("desc", regex="^(asc|desc)$", description="並び順方向: asc または desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """Get orders with filtering and pagination"""
    try:
        # ベースクエリ
        query = db.query(Order)
        
        # 個別フィルター
        if order_id:
            query = query.filter(Order.order_id == order_id)
        if customer_id:
            query = query.filter(Order.customer_id == customer_id)
        
        # 検索条件適用
        search_conditions = {
            "customer_name": customer_name,
            "customer_email": customer_email,
            "order_status": order_status,
            "payment_status": payment_status,
            "shipping_status": shipping_status,
            "total_amount_min": total_amount_min,
            "total_amount_max": total_amount_max
        }
        query = apply_order_search_filters(query, search_conditions)
        
        # ソート適用
        query = apply_order_dynamic_order(query, order_by, order_direction)
        
        # 総件数取得
        total_count = query.count()
        
        # ページネーション適用
        offset = (page - 1) * limit
        orders = query.offset(offset).limit(limit).all()
        
        # レスポンス構築
        order_list = []
        for order in orders:
            order_dict = {
                "order_id": order.order_id,
                "customer_id": order.customer_id,
                "customer_name": order.customer_name,
                "customer_email": order.customer_email,
                "customer_phone": order.customer_phone,
                "order_status": order.order_status,
                "payment_status": order.payment_status,
                "shipping_status": order.shipping_status,
                "total_amount": float(order.total_amount),
                "tax_amount": float(order.tax_amount),
                "shipping_fee": float(order.shipping_fee),
                "shipping_address": order.shipping_address,
                "billing_address": order.billing_address,
                "order_date": order.order_date.isoformat() if order.order_date else None,
                "shipped_date": order.shipped_date.isoformat() if order.shipped_date else None,
                "delivered_date": order.delivered_date.isoformat() if order.delivered_date else None,
                "notes": order.notes,
                "tracking_number": order.tracking_number,
                "order_items": [
                    {
                        "item_id": item.item_id,
                        "jancode": item.jancode,
                        "product_name": item.product_name,
                        "quantity": item.quantity,
                        "unit_price": float(item.unit_price),
                        "total_price": float(item.total_price)
                    }
                    for item in order.order_items
                ]
            }
            order_list.append(order_dict)
        
        return {
            "orders": order_list,
            "total_count": total_count,
            "page": page,
            "limit": limit,
            "total_pages": (total_count + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注文検索中にエラーが発生しました: {str(e)}")

class OrderItemRequest(BaseModel):
    jancode: str
    quantity: int

class CreateOrderRequest(BaseModel):
    customer_id: str
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    shipping_address: Optional[str] = None
    billing_address: Optional[str] = None
    notes: Optional[str] = None
    order_items: List[OrderItemRequest]

@router.post("/orders")
def create_order(request: CreateOrderRequest, db: Session = Depends(get_db)):
    """Create a new order"""
    try:
        # 注文IDを生成
        order_id = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        
        # 注文アイテムの検証と価格計算
        total_amount = Decimal('0')
        order_items_data = []
        
        for item_req in request.order_items:
            # 商品存在確認
            product = db.query(Product).filter(Product.jancode == item_req.jancode).first()
            if not product:
                raise HTTPException(status_code=404, detail=f"商品が見つかりません: {item_req.jancode}")
            
            # 在庫確認
            if product.stock < item_req.quantity:
                raise HTTPException(status_code=400, detail=f"在庫不足です。商品: {item_req.jancode}, 在庫: {product.stock}, 要求数量: {item_req.quantity}")
            
            unit_price = product.price
            total_price = unit_price * item_req.quantity
            total_amount += total_price
            
            order_items_data.append({
                "jancode": item_req.jancode,
                "product_name": product.name_jp or product.name_en or product.name_zh,
                "quantity": item_req.quantity,
                "unit_price": unit_price,
                "total_price": total_price
            })
        
        # 税額計算（10%）
        tax_amount = total_amount * Decimal('0.1')
        
        # 送料計算（簡単な例：5000円以上で送料無料）
        shipping_fee = Decimal('500') if total_amount < Decimal('5000') else Decimal('0')
        
        final_total = total_amount + tax_amount + shipping_fee
        
        # 注文作成
        new_order = Order(
            order_id=order_id,
            customer_id=request.customer_id,
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            customer_phone=request.customer_phone,
            total_amount=final_total,
            tax_amount=tax_amount,
            shipping_fee=shipping_fee,
            shipping_address=request.shipping_address,
            billing_address=request.billing_address,
            notes=request.notes
        )
        
        db.add(new_order)
        db.flush()  # IDを取得するためにflush
        
        # 注文アイテム作成
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order_id,
                **item_data
            )
            db.add(order_item)
            
            # 在庫減少
            product = db.query(Product).filter(Product.jancode == item_data["jancode"]).first()
            product.stock -= item_data["quantity"]
        
        db.commit()
        
        return {
            "message": "注文が正常に作成されました",
            "order_id": order_id,
            "total_amount": float(final_total)
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注文作成中にエラーが発生しました: {str(e)}")

class OrderStatusUpdateRequest(BaseModel):
    order_status: str

@router.put("/orders/{order_id}/status")
def update_order_status(order_id: str, request: OrderStatusUpdateRequest, db: Session = Depends(get_db)):
    """Update order status"""
    try:
        valid_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
        if request.order_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"無効な注文ステータスです。有効な値: {', '.join(valid_statuses)}")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")
        
        old_status = order.order_status
        order.order_status = request.order_status
        
        # ステータス変更に応じた追加処理
        if request.order_status == 'shipped' and old_status != 'shipped':
            order.shipped_date = datetime.utcnow()
            order.shipping_status = 'shipped'
        elif request.order_status == 'delivered' and old_status != 'delivered':
            order.delivered_date = datetime.utcnow()
            order.shipping_status = 'delivered'
        elif request.order_status == 'cancelled':
            # キャンセル時は在庫を戻す
            for item in order.order_items:
                product = db.query(Product).filter(Product.jancode == item.jancode).first()
                if product:
                    product.stock += item.quantity
        
        db.commit()
        
        return {
            "message": "注文ステータスが正常に更新されました",
            "order_id": order_id,
            "old_status": old_status,
            "new_status": request.order_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注文ステータス更新中にエラーが発生しました: {str(e)}")

class PaymentStatusUpdateRequest(BaseModel):
    payment_status: str

@router.put("/orders/{order_id}/payment")
def update_payment_status(order_id: str, request: PaymentStatusUpdateRequest, db: Session = Depends(get_db)):
    """Update payment status"""
    try:
        valid_statuses = ['unpaid', 'paid', 'refunded', 'partial_refund']
        if request.payment_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"無効な支払いステータスです。有効な値: {', '.join(valid_statuses)}")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")
        
        old_status = order.payment_status
        order.payment_status = request.payment_status
        
        db.commit()
        
        return {
            "message": "支払いステータスが正常に更新されました",
            "order_id": order_id,
            "old_status": old_status,
            "new_status": request.payment_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"支払いステータス更新中にエラーが発生しました: {str(e)}")

class ShippingStatusUpdateRequest(BaseModel):
    shipping_status: str
    tracking_number: Optional[str] = None

@router.put("/orders/{order_id}/shipping")
def update_shipping_status(order_id: str, request: ShippingStatusUpdateRequest, db: Session = Depends(get_db)):
    """Update shipping status"""
    try:
        valid_statuses = ['not_shipped', 'preparing', 'shipped', 'in_transit', 'delivered']
        if request.shipping_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"無効な配送ステータスです。有効な値: {', '.join(valid_statuses)}")
        
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")
        
        old_status = order.shipping_status
        order.shipping_status = request.shipping_status
        
        if request.tracking_number:
            order.tracking_number = request.tracking_number
        
        # ステータス変更に応じた日時更新
        if request.shipping_status == 'shipped' and old_status != 'shipped':
            order.shipped_date = datetime.utcnow()
        elif request.shipping_status == 'delivered' and old_status != 'delivered':
            order.delivered_date = datetime.utcnow()
        
        db.commit()
        
        return {
            "message": "配送ステータスが正常に更新されました",
            "order_id": order_id,
            "old_status": old_status,
            "new_status": request.shipping_status,
            "tracking_number": order.tracking_number
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"配送ステータス更新中にエラーが発生しました: {str(e)}")

@router.delete("/orders/{order_id}")
def cancel_order(order_id: str, db: Session = Depends(get_db)):
    """Cancel an order"""
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")
        
        if order.order_status in ['shipped', 'delivered']:
            raise HTTPException(status_code=400, detail="発送済みまたは配達済みの注文はキャンセルできません")
        
        # 在庫を戻す
        for item in order.order_items:
            product = db.query(Product).filter(Product.jancode == item.jancode).first()
            if product:
                product.stock += item.quantity
        
        # 注文ステータスをキャンセルに変更
        order.order_status = 'cancelled'
        
        db.commit()
        
        return {
            "message": "注文が正常にキャンセルされました",
            "order_id": order_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"注文キャンセル中にエラーが発生しました: {str(e)}")

@router.get("/orders/{order_id}")
def get_order_detail(order_id: str, db: Session = Depends(get_db)):
    """Get detailed information of a specific order"""
    try:
        order = db.query(Order).filter(Order.order_id == order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail="注文が見つかりません")
        
        return {
            "order_id": order.order_id,
            "customer_id": order.customer_id,
            "customer_name": order.customer_name,
            "customer_email": order.customer_email,
            "customer_phone": order.customer_phone,
            "order_status": order.order_status,
            "payment_status": order.payment_status,
            "shipping_status": order.shipping_status,
            "total_amount": float(order.total_amount),
            "tax_amount": float(order.tax_amount),
            "shipping_fee": float(order.shipping_fee),
            "shipping_address": order.shipping_address,
            "billing_address": order.billing_address,
            "order_date": order.order_date.isoformat() if order.order_date else None,
            "shipped_date": order.shipped_date.isoformat() if order.shipped_date else None,
            "delivered_date": order.delivered_date.isoformat() if order.delivered_date else None,
            "notes": order.notes,
            "tracking_number": order.tracking_number,
            "order_items": [
                {
                    "item_id": item.item_id,
                    "jancode": item.jancode,
                    "product_name": item.product_name,
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "total_price": float(item.total_price)
                }
                for item in order.order_items
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注文詳細取得中にエラーが発生しました: {str(e)}")