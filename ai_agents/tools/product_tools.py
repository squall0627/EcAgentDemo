from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Type
import requests
import json
import os

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# 输入模型定义
class ProductSearchInput(BaseModel):
    status: Optional[str] = Field(default=None, description="商品状态 (published/unpublished)")
    category: Optional[str] = Field(default=None, description="商品カテゴリー")
    name_zh: Optional[str] = Field(default=None, description="中文商品名検索")
    name_en: Optional[str] = Field(default=None, description="英文商品名検索")
    name_jp: Optional[str] = Field(default=None, description="日文商品名検索")
    jancode: Optional[str] = Field(default=None, description="JANコード検索")
    stock_min: Optional[int] = Field(default=None, description="最小在庫数")
    stock_max: Optional[int] = Field(default=None, description="最大在庫数")
    order_by: Optional[str] = Field(default="id", description="並び順フィールド")
    order_direction: Optional[str] = Field(default="asc", description="並び順方向 (asc/desc)")
    limit: Optional[int] = Field(default=10, description="結果件数制限")

class StockUpdateInput(BaseModel):
    jancode: str = Field(description="更新する商品のJANコード")
    stock_amount: int = Field(description="新しい在庫数")

class CategoryUpdateInput(BaseModel):
    jancode: str = Field(description="更新する商品のJANコード")
    category: str = Field(description="新しいカテゴリー")

class BulkStockUpdateInput(BaseModel):
    products: List[Dict[str, Any]] = Field(description="一括在庫更新のリスト")

class ValidateProductInput(BaseModel):
    jancode: str = Field(description="検証する商品のJANコード")

class GenerateHtmlInput(BaseModel):
    page_type: str = Field(description="生成するページタイプ")
    data: Dict[str, Any] = Field(description="ページ生成に必要なデータ")

class PublishProductsInput(BaseModel):
    jancodes: List[str] = Field(description="棚上げする商品のJANコードリスト")

class UnpublishProductsInput(BaseModel):
    jancodes: List[str] = Field(description="棚下げする商品のJANコードリスト")

# Tool クラス定義 - Pydantic v2 対応
class SearchProductsTool(BaseTool):
    name: str = "search_products"
    description: str = "商品検索ツール - 自然言語で商品を検索・フィルタリング"
    args_schema: Type[BaseModel] = ProductSearchInput
    
    def _run(self, **kwargs) -> str:
        try:
            # 空のパラメータを除去
            params = {k: v for k, v in kwargs.items() if v is not None}
            
            response = requests.get(f"{API_BASE_URL}/api/product/products", params=params)
            
            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"検索APIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"検索エラー: {str(e)}"
            }, ensure_ascii=False)

class UpdateStockTool(BaseTool):
    name: str = "update_stock"
    description: str = "商品在庫更新ツール"
    args_schema: Type[BaseModel] = StockUpdateInput
    
    def _run(self, jancode: str, stock_amount: int) -> str:
        try:
            response = requests.put(
                f"{API_BASE_URL}/api/product/products/{jancode}/stock",
                json={"stock": stock_amount}
            )
            
            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"在庫更新APIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"在庫更新エラー: {str(e)}"
            }, ensure_ascii=False)

class UpdateCategoryTool(BaseTool):
    name: str = "update_category"
    description: str = "商品カテゴリー更新ツール"
    args_schema: Type[BaseModel] = CategoryUpdateInput
    
    def _run(self, jancode: str, category: str) -> str:
        try:
            response = requests.put(
                f"{API_BASE_URL}/api/product/products/{jancode}/category",
                json={"category": category}
            )
            
            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"カテゴリー更新APIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"カテゴリー更新エラー: {str(e)}"
            }, ensure_ascii=False)

class BulkUpdateStockTool(BaseTool):
    name: str = "bulk_update_stock"
    description: str = "商品在庫一括更新ツール"
    args_schema: Type[BaseModel] = BulkStockUpdateInput
    
    def _run(self, products: List[Dict[str, Any]]) -> str:
        try:
            response = requests.put(
                f"{API_BASE_URL}/api/product/products/bulk-stock",
                json={"updates": products}
            )
            
            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"一括在庫更新APIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"一括在庫更新エラー: {str(e)}"
            }, ensure_ascii=False)

class ValidateProductTool(BaseTool):
    name: str = "validate_product_status"
    description: str = "商品の棚上げ前提条件を検証します"
    args_schema: Type[BaseModel] = ValidateProductInput
    
    def _run(self, jancode: str) -> str:
        try:
            response = requests.get(
                f"{API_BASE_URL}/api/product/products/{jancode}/validation"
            )
            
            if response.status_code == 200:
                result = response.json()
                return json.dumps(result, ensure_ascii=False, indent=2)
            elif response.status_code == 404:
                return json.dumps({
                    "valid": False,
                    "error": "商品が見つかりません",
                    "jancode": jancode
                }, ensure_ascii=False)
            else:
                error_detail = response.json().get("detail", response.text)
                return json.dumps({
                    "valid": False,
                    "error": f"バリデーションAPI呼び出しエラー: {error_detail}",
                    "jancode": jancode
                }, ensure_ascii=False)
                
        except Exception as e:
            return json.dumps({
                "valid": False,
                "error": f"バリデーションエラー: {str(e)}",
                "jancode": jancode
            }, ensure_ascii=False)

class GenerateHtmlTool(BaseTool):
    name: str = "generate_html_page"
    description: str = "商品管理用のHTML画面を動的生成します"
    args_schema: Type[BaseModel] = GenerateHtmlInput
    
    def _run(self, page_type: str, data: Dict[str, Any]) -> str:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/html/generate-page",
                json={
                    "page_type": page_type,
                    "data": data
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                return json.dumps(result, ensure_ascii=False, indent=2)
            else:
                error_detail = response.json().get("detail", response.text) if response.headers.get("content-type", "").startswith("application/json") else response.text
                return json.dumps({
                    "success": False,
                    "error": f"HTML生成APIエラー: {error_detail}"
                }, ensure_ascii=False)
                
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": f"HTML生成エラー: {str(e)}"
            }, ensure_ascii=False)

class PublishProductsTool(BaseTool):
    name: str = "publish_products"
    description: str = "商品を棚上げ（公開）します"
    args_schema: Type[BaseModel] = PublishProductsInput
    
    def _run(self, jancodes: List[str]) -> str:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/product/products/publish",
                json={"jancodes": jancodes}
            )
            
            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"棚上げAPIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"棚上げエラー: {str(e)}"
            }, ensure_ascii=False)

class UnpublishProductsTool(BaseTool):
    name: str = "unpublish_products"
    description: str = "商品を棚下げ（非公開）します"
    args_schema: Type[BaseModel] = UnpublishProductsInput
    
    def _run(self, jancodes: List[str]) -> str:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/product/products/unpublish",
                json={"jancodes": jancodes}
            )
            
            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"棚下げAPIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"棚下げエラー: {str(e)}"
            }, ensure_ascii=False)