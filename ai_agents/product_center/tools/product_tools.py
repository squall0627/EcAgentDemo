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
    jancode: str = Field(description="JAN code of the product to validate for publishing eligibility")

class GenerateHtmlInput(BaseModel):
    page_type: str = Field(description="""Page types to generate:
•	product_list: Generate the product detail list page
•	category_form: Generate the product category management page
•	stock_form: Generate the inventory management page
•	price_form: Generate the price management page
•	description_form: Generate the product description management page
•	error_page: Generate the error message page to be displayed when an error occurs""")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Data required for page generation")

class PublishProductsInput(BaseModel):
    jancodes: List[str] = Field(description="List of JAN codes for products to be published (made available for sale)")

class UnpublishProductsInput(BaseModel):
    jancodes: List[str] = Field(description="List of JAN codes for products to be unpublished (removed from sale)")

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
    description: str = """Product Publishing Validation Tool
This tool validates whether a product meets all the required conditions to be published (棚上げ) to the online store.

## Core Features
- Comprehensive product validation checks before publishing
- Category validation (ensures product has assigned category)
- Stock quantity validation (ensures stock > 0)
- Price validation (ensures price is set and > 0)
- Detailed issue reporting with specific validation failures
- Product information retrieval with current status

## Validation Rules
- **Status Check**: Product must not be already published (status should be 'unpublished' or Not set)
- **Category Check**: Product must have a valid category assigned
- **Stock Check**: Product must have stock quantity greater than 0
- **Price Check**: Product must have a valid price set (> 0)

## Usage Examples
- "JAN『4901234567890』の商品が棚上げできるかチェック" → jancode="4901234567890"
- "商品ABC123を販売開始前に検証" → jancode="ABC123"
- "この商品を公開前に条件確認" → jancode="[specific_jancode]"

## Return Format
Returns JSON structured validation results including:
- `valid`: Boolean indicating if product can be published
- `product`: Complete product information
- `issues`: Array of specific validation failures with details
- `jancode`: The validated product's JAN code

Use this tool before attempting to publish products to ensure all prerequisites are met."""
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
                    "issues": "商品が見つかりません",
                    "jancode": jancode
                }, ensure_ascii=False)
            else:
                error_detail = response.json().get("detail", response.text)
                return json.dumps({
                    "valid": False,
                    "issues": f"バリデーションAPI呼び出しエラー: {error_detail}",
                    "jancode": jancode
                }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "valid": False,
                "issues": f"バリデーションエラー: {str(e)}",
                "jancode": jancode
            }, ensure_ascii=False)

class GenerateHtmlTool(BaseTool):
    name: str = "generate_html_page"
    description: str = """Dynamically generate an HTML page corresponding to the argument page_type.
page_type:
- product_list　(Generate an HTML page that displays a list of product details.)
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
- category_form　(Generate an HTML page for managing product categories.)  
- stock_form　(Generate an HTML page for managing product inventory.)
- price_form　(Generate an HTML page for managing product prices.)
- description_form　(Generate an HTML page for managing product prices.)
- error_page　(Generate an error message page for error occurrences.)"""
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
    description: str = """Product Publishing Tool
This tool publishes products to make them available for sale on the online store (棚上げ operation).

## Core Features
- Publish single or multiple products simultaneously
- Batch publishing operation for efficiency
- Status change from 'unpublished' to 'published'
- Comprehensive error handling for failed operations
- Detailed operation results reporting

## Prerequisites
- Products must exist in the system
- Products should pass validation checks (use ValidateCanPublishProductTool first)
- Products must have valid category, stock > 0, and price > 0

## Usage Examples
- "JAN『4901234567890』を棚上げして" → jancodes=["4901234567890"]
- "コーヒー商品を一括で棚上げ" → jancodes=["123456789", "987654321", ...]
- "商品ABC123とXYZ789を販売開始" → jancodes=["ABC123", "XYZ789"]
- "在庫のある商品をすべて棚上げ" → jancodes=[list_of_valid_jancodes]

## Operation Flow
1. Validate input JAN codes
2. Check current product status
3. Execute publish operation
4. Update product status to 'published'
5. Return operation results

## Return Format
Returns JSON structured results with the following fields:
- success: Boolean indicating overall operation success
- message: Summary message of the operation
- published_count: Number of successfully published products
- results: Array of individual product operation results
  - jancode: Product's JAN code
  - status: Individual operation status (success/error)
  - message: Specific operation message for this product
  - product_name: Name of the product (may be null)

Use this tool after validating products to make them available for customer purchase."""
    args_schema: Type[BaseModel] = PublishProductsInput

    def _run(self, jancodes: List[str]) -> str:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/product/products/publish",
                json={"jancodes": jancodes}
            )

            if response.status_code == 200:
                api_result = response.json()
                
                updated_jancodes = api_result.get('updated', [])
                errors = api_result.get('errors', [])
                
                # Create individual results for each jancode
                results = []
                for jancode in jancodes:
                    if jancode in updated_jancodes:
                        results.append({
                            "jancode": jancode,
                            "status": "success",
                            "message": "商品が正常に棚上げされました",
                            "product_name": None  # API doesn't return product names
                        })
                    else:
                        # Find specific error message for this jancode
                        error_msg = "棚上げ処理に失敗しました"
                        for error in errors:
                            if jancode in error:
                                error_msg = error
                                break
                        results.append({
                            "jancode": jancode,
                            "status": "error",
                            "message": error_msg,
                            "product_name": None
                        })
                
                published_count = len(updated_jancodes)
                overall_success = published_count > 0
                
                return json.dumps({
                    "success": overall_success,
                    "message": f"棚上げ処理が完了しました（成功: {published_count}件、失敗: {len(errors)}件）",
                    "published_count": published_count,
                    "results": results
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "message": f"棚上げAPIエラー（ステータス: {response.status_code}）",
                    "published_count": 0,
                    "results": [
                        {
                            "jancode": jancode,
                            "status": "error",
                            "message": f"APIエラー: {response.status_code}",
                            "product_name": None
                        } for jancode in jancodes
                    ]
                }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"棚上げ処理で予期しないエラーが発生しました: {str(e)}",
                "published_count": 0,
                "results": [
                    {
                        "jancode": jancode,
                        "status": "error",
                        "message": f"システムエラー: {str(e)}",
                        "product_name": None
                    } for jancode in jancodes
                ]
            }, ensure_ascii=False, indent=2)

class UnpublishProductsTool(BaseTool):
    name: str = "unpublish_products"
    description: str = """Product Unpublishing Tool
This tool unpublishes products to remove them from sale on the online store (棚下げ operation).

## Core Features
- Unpublish single or multiple products simultaneously
- Batch unpublishing operation for efficiency
- Status change from 'published' to 'unpublished'
- Comprehensive error handling for failed operations
- Detailed operation results reporting

## Use Cases
- Remove out-of-stock products from sale
- Temporarily hide products during updates
- Discontinue products that are no longer available
- Emergency removal of problematic products
- Seasonal product management

## Usage Examples
- "JAN『4901234567890』を棚下げして" → jancodes=["4901234567890"]
- "在庫不足の商品をすべて棚下げ" → jancodes=["123456789", "987654321", ...]
- "商品ABC123を販売停止" → jancodes=["ABC123"]
- "エラーのある商品を一括で棚下げ" → jancodes=[list_of_problematic_jancodes]

## Operation Flow
1. Validate input JAN codes
2. Check current product status, only products that are currently published can be unpublish(You should check the latest status before using this tool)
3. Execute unpublish operation
4. Return operation results

## Return Format
Returns JSON structured results with the following fields:
- success: Boolean indicating overall operation success
- message: Summary message of the operation
- unpublished_count: Number of successfully unpublished products
- results: Array of individual product operation results
  - jancode: Product's JAN code
  - status: Individual operation status (success/error)
  - message: Specific operation message for this product
  - product_name: Name of the product (may be null)

Use this tool when products need to be temporarily or permanently removed from customer-facing sales."""
    args_schema: Type[BaseModel] = UnpublishProductsInput

    def _run(self, jancodes: List[str]) -> str:
        try:
            response = requests.post(
                f"{API_BASE_URL}/api/product/products/unpublish",
                json={"jancodes": jancodes}
            )

            if response.status_code == 200:
                api_result = response.json()
                
                updated_jancodes = api_result.get('updated', [])
                api_message = api_result.get('message', '')
                
                # Create individual results for each jancode
                results = []
                for jancode in jancodes:
                    if jancode in updated_jancodes:
                        results.append({
                            "jancode": jancode,
                            "status": "success",
                            "message": "商品が正常に棚下げされました",
                            "product_name": None  # API doesn't return product names
                        })
                    else:
                        results.append({
                            "jancode": jancode,
                            "status": "error",
                            "message": "棚下げ処理に失敗しました",
                            "product_name": None
                        })
                
                unpublished_count = len(updated_jancodes)
                overall_success = unpublished_count > 0
                
                return json.dumps({
                    "success": overall_success,
                    "message": f"棚下げ処理が完了しました（成功: {unpublished_count}件）",
                    "unpublished_count": unpublished_count,
                    "results": results
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "message": f"棚下げAPIエラー（ステータス: {response.status_code}）",
                    "unpublished_count": 0,
                    "results": [
                        {
                            "jancode": jancode,
                            "status": "error",
                            "message": f"APIエラー: {response.status_code}",
                            "product_name": None
                        } for jancode in jancodes
                    ]
                }, ensure_ascii=False, indent=2)
        except Exception as e:
            return json.dumps({
                "success": False,
                "message": f"棚下げ処理で予期しないエラーが発生しました: {str(e)}",
                "unpublished_count": 0,
                "results": [
                    {
                        "jancode": jancode,
                        "status": "error",
                        "message": f"システムエラー: {str(e)}",
                        "product_name": None
                    } for jancode in jancodes
                ]
            }, ensure_ascii=False, indent=2)