from dotenv import load_dotenv
from langchain.tools import BaseTool
from langchain.tools import Tool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Type
import requests
import json
import os

load_dotenv()

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# 输入模型定义
class ProductSearchInput(BaseModel):
    status: Optional[str] = Field(default=None, description="Product status filter (Legal values: 'published', 'unpublished')")
    category: Optional[str] = Field(default=None, description="Product category filter")
    name_zh: Optional[str] = Field(default=None, description="Chinese product name filter")
    name_en: Optional[str] = Field(default=None, description="English product name filter")
    name_jp: Optional[str] = Field(default=None, description="Japanese product name filter")
    jancode: Optional[str] = Field(default=None, description="JAN code (Jancode) filter")
    stock_min: Optional[int] = Field(default=None, description="Minimum stock quantity filter")
    stock_max: Optional[int] = Field(default=None, description="Maximum stock quantity filter")
    price_min: Optional[float] = Field(default=None, description="Minimum price filter")
    price_max: Optional[float] = Field(default=None, description="Maximum price filter")
    description: Optional[str] = Field(default=None, description="Product description filter")
    order_by: Optional[str] = Field(default="jancode", description="Field to order results by")
    order_direction: Optional[str] = Field(default="asc", description="Order direction ('asc' for ascending, 'desc' for descending)")
    limit: Optional[int] = Field(default=10, description="Maximum number of results to return")

class StockUpdateInput(BaseModel):
    jancode: str = Field(description="更新する商品のJANコード")
    stock_amount: int = Field(description="新しい在庫数")

# 新しい価格更新用の入力モデル
class PriceUpdateInput(BaseModel):
    jancode: str = Field(description="更新する商品のJANコード")
    price: float = Field(description="新しい価格")

# 新しい商品説明更新用の入力モデル
class DescriptionUpdateInput(BaseModel):
    jancode: str = Field(description="更新する商品のJANコード")
    description: str = Field(description="新しい商品説明")

class CategoryUpdateInput(BaseModel):
    jancode: str = Field(description="更新する商品のJANコード")
    category: str = Field(description="新しいカテゴリー")

class BulkStockUpdateInput(BaseModel):
    products: List[Dict[str, Any]] = Field(description="一括在庫更新のリスト")

# 新しい一括価格更新用の入力モデル
class BulkPriceUpdateInput(BaseModel):
    products: List[Dict[str, Any]] = Field(description="一括価格更新のリスト")

class ValidateProductInput(BaseModel):
    jancode: str = Field(description="検証する商品のJANコード")

class GenerateHtmlInput(BaseModel):
    page_type: str = Field(description="生成するページタイプ: product_list(商品明細一覧画面を生成)/category_form(商品カテゴリー管理画面を生成)/stock_form(在庫管理画面を生成)/price_form(価格管理画面を生成)/description_form(商品説明管理画面を生成)/error_page(エラー発生時のエラーメッセージ画面を生成)")
    data: Optional[Dict[str, Any]] = Field(default=None, description="ページ生成に必要なデータ")

class PublishProductsInput(BaseModel):
    jancodes: List[str] = Field(description="棚上げする商品のJANコードリスト")

class UnpublishProductsInput(BaseModel):
    jancodes: List[str] = Field(description="棚下げする商品のJANコードリスト")

class SearchProductsTool(BaseTool):
    name: str = "search_products"
    description: str = """Product Search & Filter Tool
This tool provides comprehensive product database search functionality with advanced filtering capabilities.

## Core Features
- Basic product information search (JAN code, product name, category)
- Multi-language product name search (Chinese, English, Japanese)
- Product status filtering (published=棚上げ, unpublished=棚下げ)
- Price range filtering (minimum price ~ maximum price)
- Stock quantity range filtering (minimum stock ~ maximum stock)
- Product description text search
- Search result sorting (by price, stock, etc.)

## Usage Examples
- "カテゴリーが食品の商品を検索" → category="食品"
- "価格が1000円以下の商品" → price_max=1000
- "在庫が10個以上の商品" → stock_min=10
- "販売中の商品のみ" → status="published"
- "JAN『4901234567890』の商品" → jancode="4901234567890"
- "商品説明に『オーガニック』が含まれる商品" → description="オーガニック"

Multiple conditions can be combined. Results are returned in structured JSON format."""
    args_schema: Type[BaseModel] = ProductSearchInput
    
    def _run(self, **kwargs) -> str:

        search_input = ProductSearchInput(**kwargs)

        # Print all parameters' names and values
        print("Parameters:")
        print(f"status: {search_input.status}")
        print(f"category: {search_input.category}")
        print(f"name_zh: {search_input.name_zh}")
        print(f"name_en: {search_input.name_en}")
        print(f"name_jp: {search_input.name_jp}")
        print(f"jancode: {search_input.jancode}")
        print(f"stock_min: {search_input.stock_min}")
        print(f"stock_max: {search_input.stock_max}")
        print(f"price_min: {search_input.price_min}")
        print(f"price_max: {search_input.price_max}")
        print(f"description: {search_input.description}")
        print(f"order_by: {search_input.order_by}")
        print(f"order_direction: {search_input.order_direction}")
        print(f"limit: {search_input.limit}")


        try:
            # Create input data dictionary
            input_data = {
                "status": search_input.status,
                "category": search_input.category,
                "name_zh": search_input.name_zh,
                "name_en": search_input.name_en,
                "name_jp": search_input.name_jp,
                "jancode": search_input.jancode,
                "stock_min": search_input.stock_min,
                "stock_max": search_input.stock_max,
                "price_min": search_input.price_min,
                "price_max": search_input.price_max,
                "description": search_input.description,
                "order_by": search_input.order_by,
                "order_direction": search_input.order_direction,
                "limit": search_input.limit
            }

            # 空のパラメータを除去
            params = {k: v for k, v in input_data.items() if v is not None}

            response = requests.get(f"{API_BASE_URL}/api/product/products", params=params)

            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"検索APIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except json.JSONDecodeError as e:
            return json.dumps({
                "error": f"JSON解析エラー: {str(e)}"
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
                json={"jancode": jancode, "stock_amount": stock_amount}
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

# 新しい価格更新ツール
class UpdatePriceTool(BaseTool):
    name: str = "update_price"
    description: str = "商品価格更新ツール"
    args_schema: Type[BaseModel] = PriceUpdateInput

    def _run(self, jancode: str, price: float) -> str:
        try:
            response = requests.put(
                f"{API_BASE_URL}/api/product/products/{jancode}/price",
                json={"jancode": jancode, "price": price}
            )

            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"価格更新APIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"価格更新エラー: {str(e)}"
            }, ensure_ascii=False)

# 新しい商品説明更新ツール
class UpdateDescriptionTool(BaseTool):
    name: str = "update_description"
    description: str = "商品説明更新ツール"
    args_schema: Type[BaseModel] = DescriptionUpdateInput

    def _run(self, jancode: str, description: str) -> str:
        try:
            response = requests.put(
                f"{API_BASE_URL}/api/product/products/{jancode}/description",
                json={"jancode": jancode, "description": description}
            )

            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"商品説明更新APIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"商品説明更新エラー: {str(e)}"
            }, ensure_ascii=False)

class UpdateCategoryTool(BaseTool):
    name: str = "update_category"
    description: str = "商品カテゴリー更新ツール"
    args_schema: Type[BaseModel] = CategoryUpdateInput

    def _run(self, jancode: str, category: str) -> str:
        try:
            response = requests.put(
                f"{API_BASE_URL}/api/product/products/{jancode}/category",
                json={"jancode": jancode, "category": category}
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
                f"{API_BASE_URL}/api/product/products/bulk/stock",
                json={"products": products}
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

# 新しい一括価格更新ツール
class BulkUpdatePriceTool(BaseTool):
    name: str = "bulk_update_price"
    description: str = "商品価格一括更新ツール"
    args_schema: Type[BaseModel] = BulkPriceUpdateInput

    def _run(self, products: List[Dict[str, Any]]) -> str:
        try:
            response = requests.put(
                f"{API_BASE_URL}/api/product/products/bulk/price",
                json={"products": products}
            )

            if response.status_code == 200:
                return json.dumps(response.json(), ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "error": f"一括価格更新APIエラー: {response.status_code}",
                    "detail": response.text
                }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({
                "error": f"一括価格更新エラー: {str(e)}"
            }, ensure_ascii=False)

class ValidateCanPublishProductTool(BaseTool):
    name: str = "validate_can_publish_product"
    description: str = "商品を棚上げ操作する前に、棚上げできるかをチェックするツール。"
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
    description: str = """引数「page_type」に応じるHTML画面を動的生成します。
page_type:
- product_list　(商品明細一覧画面を生成)
  data: 
    {
      products: [
        {
          status: {
            anyOf: [
              0
              :
              {
                type: "string"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
          category: {
            anyOf: [
              0
              :
              {
                type: "string"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
          name_zh: {
            anyOf: [
              0
              :
              {
                type: "string"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
          name_en: {
            anyOf: [
              0
              :
              {
                type: "string"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
          name_jp: {
            anyOf: [
              0
              :
              {
                type: "string"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
          jancode: {
            anyOf: [
              0
              :
              {
                type: "string"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
          stock: {
            anyOf: [
              0
              :
              {
                type: "integer"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
          price: {
            anyOf: [
              0
              :
              {
                type: "decimal"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
          description: {
            anyOf: [
              0
              :
              {
                type: "string"
              }
              1
              :
              {
                type: null
              }
            ]
            default: null
          }
        }
      ]
    }
- category_form　(商品カテゴリー管理画面を生成)  
- stock_form　(在庫管理画面を生成)
- price_form　(価格管理画面を生成)
- description_form　(商品説明管理画面を生成)
- error_page　(エラー発生時のエラーメッセージ画面を生成)"""
    args_schema: Type[BaseModel] = GenerateHtmlInput

    def _run(self, page_type: str, data: Optional[Dict[str, Any]]) -> str:
        print(f"page_type: {page_type}")
        print(f"data: {data}")
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