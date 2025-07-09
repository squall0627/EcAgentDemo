from dotenv import load_dotenv
from langchain.tools import BaseTool
from langchain.tools import Tool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Type
import requests
import json
import os

# 環境変数を読み込み
load_dotenv()

# APIベースURL設定
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# 入力スキーマ定義
class OrderSearchInput(BaseModel):
    order_id: Optional[str] = Field(None, description="Order ID to search for")
    customer_id: Optional[str] = Field(None, description="Customer ID to filter by")
    customer_name: Optional[str] = Field(None, description="Customer name to search for")
    customer_email: Optional[str] = Field(None, description="Customer email to search for")
    order_status: Optional[str] = Field(None, description="Order status filter: pending, confirmed, processing, shipped, delivered, cancelled")
    payment_status: Optional[str] = Field(None, description="Payment status filter: unpaid, paid, refunded, partial_refund")
    shipping_status: Optional[str] = Field(None, description="Shipping status filter: not_shipped, preparing, shipped, in_transit, delivered")
    total_amount_min: Optional[float] = Field(None, description="Minimum total amount filter")
    total_amount_max: Optional[float] = Field(None, description="Maximum total amount filter")
    order_by: Optional[str] = Field("order_date", description="Sort field: order_id, customer_name, order_status, payment_status, shipping_status, total_amount, order_date")
    order_direction: Optional[str] = Field("desc", description="Sort direction: asc or desc")
    limit: Optional[int] = Field(10, description="Maximum number of results to return")

class CreateOrderInput(BaseModel):
    customer_id: str = Field(description="Customer ID")
    customer_name: str = Field(description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email address")
    customer_phone: Optional[str] = Field(None, description="Customer phone number")
    shipping_address: Optional[str] = Field(None, description="Shipping address")
    billing_address: Optional[str] = Field(None, description="Billing address")
    notes: Optional[str] = Field(None, description="Order notes")
    order_items: List[Dict[str, Any]] = Field(description="List of order items with jancode and quantity")

class OrderStatusUpdateInput(BaseModel):
    order_id: str = Field(description="Order ID to update")
    order_status: str = Field(description="New order status: pending, confirmed, processing, shipped, delivered, cancelled")

class PaymentStatusUpdateInput(BaseModel):
    order_id: str = Field(description="Order ID to update")
    payment_status: str = Field(description="New payment status: unpaid, paid, refunded, partial_refund")

class ShippingStatusUpdateInput(BaseModel):
    order_id: str = Field(description="Order ID to update")
    shipping_status: str = Field(description="New shipping status: not_shipped, preparing, shipped, in_transit, delivered")
    tracking_number: Optional[str] = Field(None, description="Tracking number for shipment")

class OrderDetailInput(BaseModel):
    order_id: str = Field(description="Order ID to get details for")

class CancelOrderInput(BaseModel):
    order_id: str = Field(description="Order ID to cancel")

# 注文検索ツール関数
def search_orders_tool_fn(
    order_id: str | None = None,
    customer_id: str | None = None,
    customer_name: str | None = None,
    customer_email: str | None = None,
    order_status: str | None = None,
    payment_status: str | None = None,
    shipping_status: str | None = None,
    total_amount_min: float | None = None,
    total_amount_max: float | None = None,
    order_by: str | None = "order_date",
    order_direction: str | None = "desc",
    limit: int | None = 10
):
    """Search for orders with various filters and sorting options"""
    try:
        # パラメータ構築
        params = {}
        if order_id:
            params["order_id"] = order_id
        if customer_id:
            params["customer_id"] = customer_id
        if customer_name:
            params["customer_name"] = customer_name
        if customer_email:
            params["customer_email"] = customer_email
        if order_status:
            params["order_status"] = order_status
        if payment_status:
            params["payment_status"] = payment_status
        if shipping_status:
            params["shipping_status"] = shipping_status
        if total_amount_min is not None:
            params["total_amount_min"] = total_amount_min
        if total_amount_max is not None:
            params["total_amount_max"] = total_amount_max
        if order_by:
            params["order_by"] = order_by
        if order_direction:
            params["order_direction"] = order_direction
        if limit:
            params["limit"] = limit

        # API呼び出し
        response = requests.get(f"{API_BASE_URL}/api/order/orders", params=params)

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "data": data,
                "message": f"Found {data.get('total_count', 0)} orders"
            }
        else:
            return {
                "success": False,
                "error": f"API error: {response.status_code} - {response.text}",
                "message": "Failed to search orders"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Error occurred while searching orders"
        }

# 注文検索ツール
search_orders_tool = Tool(
    name="search_orders",
    description="Search for orders with various filters including order ID, customer information, status, and amount ranges. Supports sorting and pagination.",
    func=search_orders_tool_fn
)

# 注文作成ツール
class CreateOrderTool(BaseTool):
    name: str = "create_order"
    description: str = "Create a new order with customer information and order items. Automatically calculates totals, taxes, and shipping fees."
    args_schema: Type[BaseModel] = CreateOrderInput

    def _run(self, customer_id: str, customer_name: str, order_items: List[Dict[str, Any]], 
             customer_email: Optional[str] = None, customer_phone: Optional[str] = None,
             shipping_address: Optional[str] = None, billing_address: Optional[str] = None,
             notes: Optional[str] = None) -> str:
        """注文を作成する"""
        try:
            # リクエストデータ構築
            request_data = {
                "customer_id": customer_id,
                "customer_name": customer_name,
                "order_items": order_items
            }

            if customer_email:
                request_data["customer_email"] = customer_email
            if customer_phone:
                request_data["customer_phone"] = customer_phone
            if shipping_address:
                request_data["shipping_address"] = shipping_address
            if billing_address:
                request_data["billing_address"] = billing_address
            if notes:
                request_data["notes"] = notes

            # API呼び出し
            response = requests.post(f"{API_BASE_URL}/api/order/orders", json=request_data)

            if response.status_code == 200:
                data = response.json()
                return f"Order created successfully. Order ID: {data.get('order_id')}, Total Amount: {data.get('total_amount')}"
            else:
                return f"Failed to create order: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error creating order: {str(e)}"

# 注文ステータス更新ツール
class UpdateOrderStatusTool(BaseTool):
    name: str = "update_order_status"
    description: str = "Update the status of an existing order. Valid statuses: pending, confirmed, processing, shipped, delivered, cancelled."
    args_schema: Type[BaseModel] = OrderStatusUpdateInput

    def _run(self, order_id: str, order_status: str) -> str:
        """注文ステータスを更新する"""
        try:
            request_data = {"order_status": order_status}

            response = requests.put(f"{API_BASE_URL}/api/order/orders/{order_id}/status", json=request_data)

            if response.status_code == 200:
                data = response.json()
                return f"Order status updated successfully. Order ID: {order_id}, Old Status: {data.get('old_status')}, New Status: {data.get('new_status')}"
            else:
                return f"Failed to update order status: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error updating order status: {str(e)}"

# 支払いステータス更新ツール
class UpdatePaymentStatusTool(BaseTool):
    name: str = "update_payment_status"
    description: str = "Update the payment status of an existing order. Valid statuses: unpaid, paid, refunded, partial_refund."
    args_schema: Type[BaseModel] = PaymentStatusUpdateInput

    def _run(self, order_id: str, payment_status: str) -> str:
        """支払いステータスを更新する"""
        try:
            request_data = {"payment_status": payment_status}

            response = requests.put(f"{API_BASE_URL}/api/order/orders/{order_id}/payment", json=request_data)

            if response.status_code == 200:
                data = response.json()
                return f"Payment status updated successfully. Order ID: {order_id}, Old Status: {data.get('old_status')}, New Status: {data.get('new_status')}"
            else:
                return f"Failed to update payment status: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error updating payment status: {str(e)}"

# 配送ステータス更新ツール
class UpdateShippingStatusTool(BaseTool):
    name: str = "update_shipping_status"
    description: str = "Update the shipping status of an existing order. Valid statuses: not_shipped, preparing, shipped, in_transit, delivered. Can also set tracking number."
    args_schema: Type[BaseModel] = ShippingStatusUpdateInput

    def _run(self, order_id: str, shipping_status: str, tracking_number: Optional[str] = None) -> str:
        """配送ステータスを更新する"""
        try:
            request_data = {"shipping_status": shipping_status}
            if tracking_number:
                request_data["tracking_number"] = tracking_number

            response = requests.put(f"{API_BASE_URL}/api/order/orders/{order_id}/shipping", json=request_data)

            if response.status_code == 200:
                data = response.json()
                result = f"Shipping status updated successfully. Order ID: {order_id}, Old Status: {data.get('old_status')}, New Status: {data.get('new_status')}"
                if data.get('tracking_number'):
                    result += f", Tracking Number: {data.get('tracking_number')}"
                return result
            else:
                return f"Failed to update shipping status: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error updating shipping status: {str(e)}"

# 注文詳細取得ツール
class GetOrderDetailTool(BaseTool):
    name: str = "get_order_detail"
    description: str = "Get detailed information about a specific order including all order items, customer information, and status details."
    args_schema: Type[BaseModel] = OrderDetailInput

    def _run(self, order_id: str) -> str:
        """注文詳細を取得する"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/order/orders/{order_id}")

            if response.status_code == 200:
                data = response.json()

                # 注文詳細を整形して返す
                result = f"""Order Details:
Order ID: {data.get('order_id')}
Customer: {data.get('customer_name')} (ID: {data.get('customer_id')})
Email: {data.get('customer_email', 'N/A')}
Phone: {data.get('customer_phone', 'N/A')}
Order Status: {data.get('order_status')}
Payment Status: {data.get('payment_status')}
Shipping Status: {data.get('shipping_status')}
Total Amount: ¥{data.get('total_amount')}
Tax Amount: ¥{data.get('tax_amount')}
Shipping Fee: ¥{data.get('shipping_fee')}
Order Date: {data.get('order_date')}
Shipped Date: {data.get('shipped_date', 'N/A')}
Delivered Date: {data.get('delivered_date', 'N/A')}
Tracking Number: {data.get('tracking_number', 'N/A')}
Shipping Address: {data.get('shipping_address', 'N/A')}
Notes: {data.get('notes', 'N/A')}

Order Items:"""

                for item in data.get('order_items', []):
                    result += f"""
- Product: {item.get('product_name')} (JAN: {item.get('jancode')})
  Quantity: {item.get('quantity')}
  Unit Price: ¥{item.get('unit_price')}
  Total: ¥{item.get('total_price')}"""

                return result
            else:
                return f"Failed to get order details: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error getting order details: {str(e)}"

# 注文キャンセルツール
class CancelOrderTool(BaseTool):
    name: str = "cancel_order"
    description: str = "Cancel an existing order. This will restore inventory for all order items and set the order status to cancelled. Cannot cancel shipped or delivered orders."
    args_schema: Type[BaseModel] = CancelOrderInput

    def _run(self, order_id: str) -> str:
        """注文をキャンセルする"""
        try:
            response = requests.delete(f"{API_BASE_URL}/api/order/orders/{order_id}")

            if response.status_code == 200:
                data = response.json()
                return f"Order cancelled successfully. Order ID: {order_id}"
            else:
                return f"Failed to cancel order: {response.status_code} - {response.text}"

        except Exception as e:
            return f"Error cancelling order: {str(e)}"

# 注文統計ツール（追加機能）
class OrderStatisticsTool(BaseTool):
    name: str = "get_order_statistics"
    description: str = "Get order statistics including counts by status, total revenue, and other metrics."
    args_schema: Type[BaseModel] = BaseModel

    def _run(self) -> str:
        """注文統計を取得する"""
        try:
            # 各ステータスの注文数を取得
            statuses = ['pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled']
            payment_statuses = ['unpaid', 'paid', 'refunded', 'partial_refund']

            stats = {
                "order_counts": {},
                "payment_counts": {},
                "total_revenue": 0
            }

            # 各ステータスの件数を取得
            for status in statuses:
                response = requests.get(f"{API_BASE_URL}/api/order/orders", params={"order_status": status, "limit": 1})
                if response.status_code == 200:
                    data = response.json()
                    stats["order_counts"][status] = data.get("total_count", 0)

            # 支払いステータス別件数を取得
            for payment_status in payment_statuses:
                response = requests.get(f"{API_BASE_URL}/api/order/orders", params={"payment_status": payment_status, "limit": 1})
                if response.status_code == 200:
                    data = response.json()
                    stats["payment_counts"][payment_status] = data.get("total_count", 0)

            # 売上計算（支払い済み注文のみ）
            response = requests.get(f"{API_BASE_URL}/api/order/orders", params={"payment_status": "paid", "limit": 100})
            if response.status_code == 200:
                data = response.json()
                total_revenue = sum(order.get("total_amount", 0) for order in data.get("orders", []))
                stats["total_revenue"] = total_revenue

            # 結果を整形
            result = "Order Statistics:\n\nOrder Status Counts:\n"
            for status, count in stats["order_counts"].items():
                result += f"- {status.capitalize()}: {count}\n"

            result += "\nPayment Status Counts:\n"
            for status, count in stats["payment_counts"].items():
                result += f"- {status.replace('_', ' ').capitalize()}: {count}\n"

            result += f"\nTotal Revenue (Paid Orders): ¥{stats['total_revenue']}"

            return result

        except Exception as e:
            return f"Error getting order statistics: {str(e)}"
