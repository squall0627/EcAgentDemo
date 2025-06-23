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
    # status: Optional[str] = Field(default=None, description="Product publication status (published/unpublished)")
    # category: Optional[str] = Field(default=None, description="Product category")
    # name_zh: Optional[str] = Field(default=None, description="Chinese product name")
    # name_en: Optional[str] = Field(default=None, description="English product name")
    # name_jp: Optional[str] = Field(default=None, description="Japanese product name")
    # jancode: Optional[str] = Field(default=None, description="Product JAN code")
    # stock_min: Optional[int] = Field(default=None, description="Minimum stock quantity")
    # stock_max: Optional[int] = Field(default=None, description="Maximum stock quantity")
    # order_by: Optional[str] = Field(default="jancode", description="Sort field")
    # order_direction: Optional[str] = Field(default="asc", description="Sort direction (asc/desc)")
    # limit: Optional[int] = Field(default=10, description="Result limit count")
    status: str | None = None
    category: str | None = None
    name_zh: str | None = None
    name_en: str | None = None
    name_jp: str | None = None
    jancode: str | None = None
    stock_min: int | None = None
    stock_max: int | None = None
    order_by: str | None = "jancode"
    order_direction: str | None = "asc"
    limit: int | None = 10

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
    page_type: str = Field(description="生成するページタイプ: product_list(商品明細一覧画面を生成)/category_form(商品カテゴリー管理画面を生成)/stock_form(在庫管理画面を生成)/error_page(エラー発生時のエラーメッセージ画面を生成)")
    data: Optional[Dict[str, Any]] = Field(default=None, description="ページ生成に必要なデータ")

class PublishProductsInput(BaseModel):
    jancodes: List[str] = Field(description="棚上げする商品のJANコードリスト")

class UnpublishProductsInput(BaseModel):
    jancodes: List[str] = Field(description="棚下げする商品のJANコードリスト")

# Tool クラス定義 - Pydantic v2 対応
def search_products_tool_fn(jancode: str | None = None, status: str | None = None, category: str | None = None,
                            name_zh: str | None = None,
                            name_en: str | None = None,
                            name_jp: str | None = None,
                            stock_min: int | None = None,
                            stock_max: int | None = None,
                            order_by: str | None = "jancode",
                            order_direction: str | None = "asc",
                            limit: int | None = 10) -> str:
    # Print all parameters' names and values
    print("Parameters:")
    print(f"jancode: {jancode}")
    print(f"status: {status}")
    print(f"category: {category}")
    print(f"name_zh: {name_zh}")
    print(f"name_en: {name_en}")
    print(f"name_jp: {name_jp}")
    print(f"stock_min: {stock_min}")
    print(f"stock_max: {stock_max}")
    print(f"order_by: {order_by}")
    print(f"order_direction: {order_direction}")
    print(f"limit: {limit}")

    try:
        # Create input data dictionary
        input_data = {
            "jancode": jancode,
            "status": status,
            "category": category,
            "name_zh": name_zh,
            "name_en": name_en,
            "name_jp": name_jp,
            "stock_min": stock_min,
            "stock_max": stock_max,
            "order_by": order_by,
            "order_direction": order_direction,
            "limit": limit
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


search_products_tool = Tool(
    name="search_products",
    description="商品検索ツール - 自然言語で商品を検索・フィルタリング",
    func=search_products_tool_fn,
    args_schema=ProductSearchInput,
    return_direct=False  # 如需直接返回结果而不让模型解释，可设为 True
)
# class SearchProductsTool(BaseTool):
#     name: str = "search_products"
#     description: str = "Product search tool - Search and filter products using natural language queries"
#     args_schema: Type[BaseModel] = ProductSearchInput
#
#     def _run(self, **kwargs) -> str:
#         try:
#             # 空のパラメータを除去
#             params = {k: v for k, v in kwargs.items() if v is not None}
#
#             response = requests.get(f"{API_BASE_URL}/api/product/products", params=params)
#
#             if response.status_code == 200:
#                 return json.dumps(response.json(), ensure_ascii=False, indent=2)
#             else:
#                 return json.dumps({
#                     "error": f"検索APIエラー: {response.status_code}",
#                     "detail": response.text
#                 }, ensure_ascii=False)
#         except Exception as e:
#             return json.dumps({
#                 "error": f"検索エラー: {str(e)}"
#             }, ensure_ascii=False)

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
        }
      ]
    }
- category_form　(商品カテゴリー管理画面を生成)
- stock_form　(在庫管理画面を生成)
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

# if __name__ == "__main__":
#     print(search_products_tool_fn({"jancode": "1000000000001"}))