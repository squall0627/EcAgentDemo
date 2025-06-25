from fastapi import Query, Depends, APIRouter, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from db.models.product import Product
from db.database import get_db
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from decimal import Decimal

router = APIRouter()

def localize_name(product, lang: str):
    if lang == "en":
        return product.name_en
    elif lang == "jp":
        return product.name_jp
    return product.name_zh

def apply_search_filters(query, search_conditions: Dict[str, Any]):
    """Apply dynamic search conditions to the query"""
    for field, value in search_conditions.items():
        if value is not None and value != "":
            if hasattr(Product, field):
                column = getattr(Product, field)
                if isinstance(value, str):
                    # Use ilike for string fields for case-insensitive partial matching
                    query = query.filter(column.ilike(f"%{value}%"))
                else:
                    # Use exact match for non-string fields
                    query = query.filter(column == value)
    return query

def apply_dynamic_order(query, order_by: str, order_direction: str):
    """Apply dynamic ordering to the query"""
    if order_by and hasattr(Product, order_by):
        column = getattr(Product, order_by)
        if order_direction.lower() == "desc":
            query = query.order_by(desc(column))
        else:
            query = query.order_by(column)
    else:
        # Default ordering (required by SQL Server for pagination)
        query = query.order_by(Product.jancode)
    return query

@router.get("/products")
def get_products(
        status: str = Query(None),
        category: str = Query(None),
        name_zh: str = Query(None),
        name_en: str = Query(None),
        name_jp: str = Query(None),
        jancode: str = Query(None),
        stock_min: int = Query(None),
        stock_max: int = Query(None),
        price_min: float = Query(None, description="最小価格フィルター"),
        price_max: float = Query(None, description="最大価格フィルター"),
        description: str = Query(None, description="商品説明での検索"),
        order_by: str = Query("jancode", description="Field to order by: jancode, name_zh, name_en, name_jp, category, status, stock, price"),
        order_direction: str = Query("asc", regex="^(asc|desc)$", description="Order direction: asc or desc"),
        lang: str = Query("jp"),
        page: int = Query(1, ge=1),
        limit: int = Query(20, le=100),
        db: Session = Depends(get_db)
):
    # Start with base query
    query = db.query(Product)

    # Add status filter if specified
    if status:
        query = query.filter(Product.status == status)
    
    # Add category filter if specified
    if category:
        query = query.filter(Product.category == category)
    
    # Collect dynamic search conditions
    search_conditions = {
        "name_zh": name_zh,
        "name_en": name_en,
        "name_jp": name_jp,
        "jancode": jancode,
        "description": description
    }
    
    # Apply dynamic search filters
    query = apply_search_filters(query, search_conditions)
    
    # Add stock range filters if specified
    if stock_min is not None:
        query = query.filter(Product.stock >= stock_min)
    if stock_max is not None:
        query = query.filter(Product.stock <= stock_max)

    # Add price range filters if specified
    if price_min is not None:
        query = query.filter(Product.price >= price_min)
    if price_max is not None:
        query = query.filter(Product.price <= price_max)

    # Apply dynamic ordering
    query = apply_dynamic_order(query, order_by, order_direction)

    total = query.count()
    
    # Apply pagination
    products = query.offset((page - 1) * limit).limit(limit).all()

    result = []
    for p in products:
        result.append({
            "jancode": p.jancode,
            "name": localize_name(p, lang),
            "category": p.category,
            "status": p.status,
            "stock": p.stock,
            "price": float(p.price) if p.price else 0.0,
            "description": p.description,
        })

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "products": result
    }


class PublishRequest(BaseModel):
    ids: list[str]

@router.post("/products/publish")
def publish_products(data: PublishRequest, db: Session = Depends(get_db)):
    products = db.query(Product).filter(Product.jancode.in_(data.ids)).all()
    errors = []
    valid_ids = []

    for p in products:
        if p.stock <= 0:
            errors.append(f"{p.jancode} 在庫なし")
        elif not p.category:
            errors.append(f"{p.jancode} オンライン販売カテゴリーと紐付けていない")
        else:
            p.status = "published"
            valid_ids.append(p.jancode)

    if valid_ids:
        db.commit()

    return {
        "status": "partial" if errors else "success",
        "updated": valid_ids,
        "errors": errors
    }


class StockUpdateRequest(BaseModel):
    jancode: str
    stock_amount: int

@router.put("/products/{jancode}/stock")
def update_product_stock(jancode: str, request: StockUpdateRequest, db: Session = Depends(get_db)):
    """特定商品の在庫を更新"""
    product = db.query(Product).filter(Product.jancode == jancode).first()
    
    if not product:
        raise HTTPException(status_code=404, detail=f"JANコード {jancode} の商品が見つかりません")
    
    try:
        old_stock = product.stock
        product.stock = request.stock_amount
        db.commit()
        
        return {
            "success": True,
            "message": f"{product.name_jp} (JAN: {jancode}) の在庫を {old_stock} から {request.stock_amount} に更新しました",
            "jancode": jancode,
            "old_stock": old_stock,
            "new_stock": request.stock_amount,
            "product_name": product.name_jp
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"在庫更新エラー: {str(e)}")

# 新しい価格更新API
class PriceUpdateRequest(BaseModel):
    jancode: str
    price: float

@router.put("/products/{jancode}/price")
def update_product_price(jancode: str, request: PriceUpdateRequest, db: Session = Depends(get_db)):
    """特定商品の価格を更新"""
    product = db.query(Product).filter(Product.jancode == jancode).first()
    
    if not product:
        raise HTTPException(status_code=404, detail=f"JANコード {jancode} の商品が見つかりません")
    
    if request.price < 0:
        raise HTTPException(status_code=400, detail="価格は0以上である必要があります")
    
    try:
        old_price = float(product.price) if product.price else 0.0
        product.price = Decimal(str(request.price))
        db.commit()
        
        return {
            "success": True,
            "message": f"{product.name_jp} (JAN: {jancode}) の価格を ¥{old_price:,.2f} から ¥{request.price:,.2f} に更新しました",
            "jancode": jancode,
            "old_price": old_price,
            "new_price": request.price,
            "product_name": product.name_jp
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"価格更新エラー: {str(e)}")

# 新しい商品説明更新API
class DescriptionUpdateRequest(BaseModel):
    jancode: str
    description: str

@router.put("/products/{jancode}/description")
def update_product_description(jancode: str, request: DescriptionUpdateRequest, db: Session = Depends(get_db)):
    """特定商品の説明を更新"""
    product = db.query(Product).filter(Product.jancode == jancode).first()
    
    if not product:
        raise HTTPException(status_code=404, detail=f"JANコード {jancode} の商品が見つかりません")
    
    try:
        old_description = product.description or ""
        product.description = request.description
        db.commit()
        
        return {
            "success": True,
            "message": f"{product.name_jp} (JAN: {jancode}) の商品説明を更新しました",
            "jancode": jancode,
            "old_description": old_description,
            "new_description": request.description,
            "product_name": product.name_jp
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"商品説明更新エラー: {str(e)}")

class CategoryUpdateRequest(BaseModel):
    jancode: str
    category: str

@router.put("/products/{jancode}/category")
def update_product_category(jancode: str, request: CategoryUpdateRequest, db: Session = Depends(get_db)):
    """特定商品のカテゴリーを更新"""
    product = db.query(Product).filter(Product.jancode == jancode).first()
    
    if not product:
        raise HTTPException(status_code=404, detail=f"JANコード {jancode} の商品が見つかりません")
    
    try:
        old_category = product.category
        product.category = request.category
        db.commit()
        
        return {
            "success": True,
            "message": f"{product.name_jp} (JAN: {jancode}) のカテゴリーを '{old_category}' から '{request.category}' に更新しました",
            "jancode": jancode,
            "old_category": old_category,
            "new_category": request.category,
            "product_name": product.name_jp
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"カテゴリー更新エラー: {str(e)}")

class BulkStockUpdateRequest(BaseModel):
    products: List[Dict[str, Any]]

@router.put("/products/bulk/stock")
def bulk_update_stock(request: BulkStockUpdateRequest, db: Session = Depends(get_db)):
    """複数商品の在庫を一括更新"""
    results = []
    errors = []
    
    try:
        for item in request.products:
            jancode = item.get('jancode')
            stock_amount = item.get('stock_amount')
            
            if not jancode or stock_amount is None:
                errors.append(f"無効なデータ: {item}")
                continue
            
            product = db.query(Product).filter(Product.jancode == jancode).first()
            if not product:
                errors.append(f"商品 {jancode} が見つかりません")
                continue
            
            old_stock = product.stock
            product.stock = stock_amount
            results.append({
                "jancode": jancode,
                "product_name": product.name_jp,
                "old_stock": old_stock,
                "new_stock": stock_amount,
                "message": f"{product.name_jp} (JAN: {jancode}): {old_stock} → {stock_amount}"
            })
        
        if results:
            db.commit()
        
        return {
            "success": True,
            "updated_count": len(results),
            "updated_products": results,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"一括在庫更新エラー: {str(e)}")

# 新しい一括価格更新API
class BulkPriceUpdateRequest(BaseModel):
    products: List[Dict[str, Any]]

@router.put("/products/bulk/price")
def bulk_update_price(request: BulkPriceUpdateRequest, db: Session = Depends(get_db)):
    """複数商品の価格を一括更新"""
    results = []
    errors = []
    
    try:
        for item in request.products:
            jancode = item.get('jancode')
            price = item.get('price')
            
            if not jancode or price is None:
                errors.append(f"無効なデータ: {item}")
                continue
                
            if price < 0:
                errors.append(f"商品 {jancode}: 価格は0以上である必要があります")
                continue
            
            product = db.query(Product).filter(Product.jancode == jancode).first()
            if not product:
                errors.append(f"商品 {jancode} が見つかりません")
                continue
            
            old_price = float(product.price) if product.price else 0.0
            product.price = Decimal(str(price))
            results.append({
                "jancode": jancode,
                "product_name": product.name_jp,
                "old_price": old_price,
                "new_price": price,
                "message": f"{product.name_jp} (JAN: {jancode}): ¥{old_price:,.2f} → ¥{price:,.2f}"
            })
        
        if results:
            db.commit()
        
        return {
            "success": True,
            "updated_count": len(results),
            "updated_products": results,
            "errors": errors
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"一括価格更新エラー: {str(e)}")

class AutoReplenishRequest(BaseModel):
    threshold: int = 10
    replenish_amount: int = 100

@router.post("/products/unpublish")
def unpublish_products(data: PublishRequest, db: Session = Depends(get_db)):
    """商品を棚下げ（非公開に）"""
    products = db.query(Product).filter(Product.jancode.in_(data.ids)).all()
    updated_ids = []

    for p in products:
        p.status = "unpublished"
        updated_ids.append(p.jancode)

    if updated_ids:
        db.commit()

    return {
        "status": "success",
        "updated": updated_ids,
        "message": f"{len(updated_ids)}商品を棚下げしました"
    }

@router.get("/products/{jancode}/validation")
def validate_product_for_publish(jancode: str, db: Session = Depends(get_db)):
    """商品の棚上げ前提条件を検証"""
    product = db.query(Product).filter(Product.jancode == jancode).first()
    
    if not product:
        raise HTTPException(status_code=404, detail="商品が見つかりません")
    
    issues = []
    
    # カテゴリーチェック
    if not product.category or product.category.strip() == "":
        issues.append({
            "type": "category",
            "message": "商品カテゴリーが設定されていません",
            "field": "category",
            "current_value": product.category
        })
    
    # 在庫チェック
    if product.stock <= 0:
        issues.append({
            "type": "stock", 
            "message": "商品在庫が0です",
            "field": "stock",
            "current_value": product.stock
        })

    # 価格チェック
    if not product.price or product.price <= 0:
        issues.append({
            "type": "price",
            "message": "商品価格が設定されていないか0円です",
            "field": "price",
            "current_value": float(product.price) if product.price else 0.0
        })
    
    return {
        "jancode": jancode,
        "valid": len(issues) == 0,
        "product": {
            "jancode": product.jancode,
            "name_jp": product.name_jp,
            "name_zh": product.name_zh,
            "name_en": product.name_en,
            "category": product.category,
            "stock": product.stock,
            "price": float(product.price) if product.price else 0.0,
            "description": product.description,
            "status": product.status
        },
        "issues": issues
    }