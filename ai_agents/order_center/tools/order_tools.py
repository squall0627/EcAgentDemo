from dotenv import load_dotenv
from langchain.tools import BaseTool
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Type
import requests
import json
import os

# 環境変数を読み込み
load_dotenv()

# APIベースURL設定
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Input schema definitions
class OrderSearchInput(BaseModel):
    order_id: Optional[str] = Field(None, description="Specific order ID to search for exact order matching")
    customer_id: Optional[str] = Field(None, description="Customer ID to filter orders by specific customer")
    customer_name: Optional[str] = Field(None, description="Customer name to search for (supports partial matching for flexible customer search)")
    customer_email: Optional[str] = Field(None, description="Customer email address to search for order identification")
    order_status: Optional[str] = Field(None, description="Order status filter for order lifecycle management. Valid values: pending (awaiting confirmation), confirmed (order confirmed), processing (being prepared), shipped (dispatched), delivered (completed), cancelled (order cancelled)")
    payment_status: Optional[str] = Field(None, description="Payment status filter for financial tracking. Valid values: unpaid (payment pending), paid (payment completed), refunded (full refund processed), partial_refund (partial refund processed)")
    shipping_status: Optional[str] = Field(None, description="Shipping status filter for logistics tracking. Valid values: not_shipped (not yet dispatched), preparing (being prepared for shipment), shipped (dispatched from warehouse), in_transit (on delivery route), delivered (successfully delivered)")
    total_amount_min: Optional[float] = Field(None, description="Minimum total amount filter for price range search (inclusive lower bound)")
    total_amount_max: Optional[float] = Field(None, description="Maximum total amount filter for price range search (inclusive upper bound)")
    order_by: Optional[str] = Field("order_date", description="Field to sort search results by for organized data presentation. Valid values: order_id (sort by order identifier), customer_name (alphabetical by customer), order_status (group by order status), payment_status (group by payment status), shipping_status (group by shipping status), total_amount (sort by order value), order_date (chronological sorting)")
    order_direction: Optional[str] = Field("desc", description="Sort direction for result ordering. Valid values: asc (ascending order - oldest/lowest first) or desc (descending order - newest/highest first)")
    limit: Optional[int] = Field(10, description="Maximum number of results to return for pagination control (default: 10, helps manage large result sets)")

class CreateOrderInput(BaseModel):
    customer_id: str = Field(description="Unique customer identifier for order association and customer tracking")
    customer_name: str = Field(description="Full name of the customer placing the order for delivery and billing purposes")
    customer_email: Optional[str] = Field(None, description="Customer's email address for order confirmation notifications and communication")
    customer_phone: Optional[str] = Field(None, description="Customer's phone number for delivery coordination and urgent contact")
    shipping_address: Optional[str] = Field(None, description="Complete shipping address including street, city, postal code for accurate delivery")
    billing_address: Optional[str] = Field(None, description="Billing address for payment processing and invoice generation (if different from shipping)")
    notes: Optional[str] = Field(None, description="Additional notes or special instructions for order processing, delivery, or handling")
    order_items: List[Dict[str, Any]] = Field(description="List of order items for purchase, each containing 'jancode' (product identifier) and 'quantity' (number of items) fields")

class OrderStatusUpdateInput(BaseModel):
    order_id: str = Field(description="Unique order identifier to update status for order lifecycle management")
    order_status: str = Field(description="New order status for order progression tracking. Valid values: pending (awaiting confirmation), confirmed (order confirmed), processing (being prepared), shipped (dispatched), delivered (completed), cancelled (order cancelled)")

class PaymentStatusUpdateInput(BaseModel):
    order_id: str = Field(description="Unique order identifier to update payment status for financial tracking")
    payment_status: str = Field(description="New payment status for financial management. Valid values: unpaid (payment pending), paid (payment completed), refunded (full refund processed), partial_refund (partial refund processed)")

class ShippingStatusUpdateInput(BaseModel):
    order_id: str = Field(description="Unique order identifier to update shipping status for logistics tracking")
    shipping_status: str = Field(description="New shipping status for delivery management. Valid values: not_shipped (not yet dispatched), preparing (being prepared for shipment), shipped (dispatched from warehouse), in_transit (on delivery route), delivered (successfully delivered)")
    tracking_number: Optional[str] = Field(None, description="Tracking number for shipment monitoring and customer delivery tracking (optional, can be added when available)")

class OrderDetailInput(BaseModel):
    order_id: str = Field(description="Unique order identifier to retrieve comprehensive detailed information including items, customer data, and status")

class CancelOrderInput(BaseModel):
    order_id: str = Field(description="Unique order identifier to cancel and restore inventory for all associated order items")

# 注文検索ツール
class SearchOrdersTool(BaseTool):
    name: str = "search_orders"
    description: str = """Order Search & Filter Tool
This tool provides comprehensive order database search functionality with advanced filtering capabilities for order management operations.

## Core Features
- Order identification search (order ID, customer information)
- Multi-status filtering (order status, payment status, shipping status)
- Customer-based search (ID, name, email with partial matching support)
- Financial range filtering (minimum and maximum total amount)
- Advanced sorting and pagination for large result sets
- Real-time order data retrieval with comprehensive details
- Flexible search combinations for complex queries

## Usage Examples
- "注文ORD123456を検索" → order_id="ORD123456"
- "顧客John Smithの注文を検索" → customer_name="John Smith"
- "すべての保留中の注文を表示" → order_status="pending"
- "100ドル以上の支払い済み注文を検索" → payment_status="paid", total_amount_min=100
- "発送済み注文を日付順で取得" → shipping_status="shipped", order_by="order_date"
- "顧客メールアドレスで注文を検索" → customer_email="customer@example.com"
- "50ドルから200ドルの間の注文を検索" → total_amount_min=50, total_amount_max=200

## Operation Flow
1. Parse and validate search parameters
2. Apply filters to order database query
3. Execute search with sorting and pagination
4. Return structured results with order details
5. Provide comprehensive search statistics

## Return Format
Returns structured JSON response with:
- success: Boolean indicating search operation success
- data: Array of matching orders with complete details
- total_count: Total number of matching orders
- message: Search operation summary

Multiple conditions can be combined for precise order filtering. Results include complete order information for comprehensive order management."""
    args_schema: Type[BaseModel] = OrderSearchInput

    def _run(self, 
             order_id: Optional[str] = None,
             customer_id: Optional[str] = None,
             customer_name: Optional[str] = None,
             customer_email: Optional[str] = None,
             order_status: Optional[str] = None,
             payment_status: Optional[str] = None,
             shipping_status: Optional[str] = None,
             total_amount_min: Optional[float] = None,
             total_amount_max: Optional[float] = None,
             order_by: Optional[str] = "order_date",
             order_direction: Optional[str] = "desc",
             limit: Optional[int] = 10) -> str:
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
                return json.dumps({
                    "success": True,
                    "data": data,
                    "message": f"Found {data.get('total_count', 0)} orders"
                }, ensure_ascii=False, indent=2)
            else:
                return json.dumps({
                    "success": False,
                    "error": f"API error: {response.status_code} - {response.text}",
                    "message": "Failed to search orders"
                }, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e),
                "message": "Error occurred while searching orders"
            }, ensure_ascii=False)

# 注文作成ツール
class CreateOrderTool(BaseTool):
    name: str = "create_order"
    description: str = """Order Creation Tool
This tool provides comprehensive order creation functionality for processing new customer orders with automatic calculations and validation.

## Core Features
- Complete order creation with customer information and order items
- Automatic total amount calculation including taxes and shipping fees
- Real-time inventory validation and reservation
- Customer information management and validation
- Order item processing with product verification
- Immediate order confirmation and ID generation
- Comprehensive error handling for invalid data

## Usage Examples
- "顧客CUST001の商品付き注文を作成" → customer_id="CUST001", customer_name="John Smith", order_items=[{"jancode": "123456789", "quantity": 2}]
- "配送先住所付きの新規注文" → customer_id="CUST002", customer_name="Jane Doe", shipping_address="123 Main St", order_items=[...]
- "特別指示付きの注文" → customer_id="CUST003", customer_name="Bob Wilson", notes="Handle with care", order_items=[...]
- "メール通知付きの注文を作成" → customer_id="CUST004", customer_name="Alice Brown", customer_email="alice@example.com", order_items=[...]

## Operation Flow
1. Validate customer information and order items
2. Check product availability and inventory levels
3. Calculate order totals, taxes, and shipping fees
4. Reserve inventory for order items
5. Generate unique order ID and create order record
6. Return order confirmation with details

## Prerequisites
- Valid customer ID and name are required
- Order items must contain valid JAN codes and quantities
- Products must exist in inventory with sufficient stock
- All monetary calculations are performed automatically

## Return Format
Returns order creation confirmation with:
- Order ID: Unique identifier for the created order
- Total Amount: Complete order total including taxes and fees
- Success message with order details

This tool handles the complete order creation process from validation to confirmation."""
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
    description: str = """Order Status Update Tool
This tool provides order lifecycle management functionality by updating order status for order progression tracking and workflow management.

## Core Features
- Update order status for order lifecycle progression
- Real-time status change with validation
- Order workflow management and tracking
- Status transition validation and error handling
- Immediate database synchronization
- Comprehensive operation result reporting
- Order history tracking for status changes

## Valid Order Statuses
- **pending**: Order awaiting confirmation (initial status)
- **confirmed**: Order confirmed and accepted for processing
- **processing**: Order being prepared and items being gathered
- **shipped**: Order dispatched from warehouse for delivery
- **delivered**: Order successfully delivered to customer
- **cancelled**: Order cancelled and inventory restored

## Usage Examples
- "注文ORD123456を確認済みにする" → order_id="ORD123456", order_status="confirmed"
- "注文を処理中にマークする" → order_id="ORD789012", order_status="processing"
- "注文を発送済みステータスに更新" → order_id="ORD345678", order_status="shipped"
- "注文を配達済みに設定" → order_id="ORD901234", order_status="delivered"
- "注文ORD567890をキャンセル" → order_id="ORD567890", order_status="cancelled"

## Operation Flow
1. Validate order ID existence
2. Check current order status
3. Validate status transition rules
4. Update order status in database
5. Record status change history
6. Return operation result with status details

## Return Format
Returns status update confirmation with:
- Order ID: Identifier of the updated order
- Old Status: Previous order status
- New Status: Updated order status
- Success message with operation details

This tool manages order progression through the complete order lifecycle."""
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
    description: str = """Payment Status Update Tool
This tool provides financial management functionality by updating payment status for order financial tracking and accounting operations.

## Core Features
- Update payment status for financial tracking and management
- Real-time payment status change with validation
- Financial workflow management and accounting integration
- Payment processing validation and error handling
- Immediate database synchronization for financial records
- Comprehensive operation result reporting
- Payment history tracking for audit purposes

## Valid Payment Statuses
- **unpaid**: Payment pending or not yet processed (initial status)
- **paid**: Payment completed and confirmed successfully
- **refunded**: Full refund processed and completed
- **partial_refund**: Partial refund processed for order adjustment

## Usage Examples
- "注文ORD123456を支払い済みにマーク" → order_id="ORD123456", payment_status="paid"
- "注文ORD789012の返金を処理" → order_id="ORD789012", payment_status="refunded"
- "注文ORD345678を部分返金に設定" → order_id="ORD345678", payment_status="partial_refund"
- "支払いを未払いステータスにリセット" → order_id="ORD901234", payment_status="unpaid"

## Operation Flow
1. Validate order ID existence
2. Check current payment status
3. Validate payment status transition rules
4. Update payment status in database
5. Record payment change history for audit
6. Return operation result with payment details

## Financial Impact
- **paid**: Confirms revenue recognition and order fulfillment eligibility
- **refunded**: Processes full refund and inventory restoration
- **partial_refund**: Handles partial refunds with amount adjustments
- **unpaid**: Maintains pending payment status for follow-up

## Return Format
Returns payment status update confirmation with:
- Order ID: Identifier of the updated order
- Old Status: Previous payment status
- New Status: Updated payment status
- Success message with financial operation details

This tool manages the complete payment lifecycle for order financial management."""
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
    description: str = """Shipping Status Update Tool
This tool provides logistics management functionality by updating shipping status for order delivery tracking and logistics coordination.

## Core Features
- Update shipping status for delivery tracking and logistics management
- Real-time shipping status change with validation
- Logistics workflow management and carrier integration
- Tracking number assignment and management
- Delivery progress monitoring and customer notification
- Immediate database synchronization for logistics records
- Comprehensive operation result reporting with tracking details

## Valid Shipping Statuses
- **not_shipped**: Order not yet dispatched from warehouse (initial status)
- **preparing**: Order being prepared for shipment and packaging
- **shipped**: Order dispatched from warehouse and in carrier possession
- **in_transit**: Order on delivery route and being transported
- **delivered**: Order successfully delivered to customer destination

## Usage Examples
- "注文ORD123456の発送準備を開始" → order_id="ORD123456", shipping_status="preparing"
- "注文を追跡番号付きで発送済みにマーク" → order_id="ORD789012", shipping_status="shipped", tracking_number="TRK123456789"
- "注文を配送中ステータスに更新" → order_id="ORD345678", shipping_status="in_transit"
- "注文の配達を確認" → order_id="ORD901234", shipping_status="delivered"
- "発送済み注文に追跡番号を追加" → order_id="ORD567890", shipping_status="shipped", tracking_number="TRK987654321"

## Operation Flow
1. Validate order ID existence
2. Check current shipping status
3. Validate shipping status transition rules
4. Update shipping status in database
5. Process tracking number if provided
6. Record shipping change history for logistics tracking
7. Return operation result with shipping and tracking details

## Tracking Number Management
- Optional tracking number can be provided with any status update
- Tracking numbers enable customer delivery monitoring
- Supports various carrier tracking formats
- Automatically included in customer notifications

## Return Format
Returns shipping status update confirmation with:
- Order ID: Identifier of the updated order
- Old Status: Previous shipping status
- New Status: Updated shipping status
- Tracking Number: Shipment tracking identifier (if provided)
- Success message with logistics operation details

This tool manages the complete shipping lifecycle for order delivery coordination."""
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
    description: str = """Order Detail Retrieval Tool
This tool provides comprehensive order information retrieval functionality for detailed order analysis and customer service operations.

## Core Features
- Complete order information retrieval with all associated data
- Detailed order item breakdown with product information
- Comprehensive customer information display
- Multi-status tracking (order, payment, shipping status)
- Financial breakdown including taxes and shipping fees
- Delivery tracking information with dates and tracking numbers
- Order history and timeline information
- Formatted output for easy reading and analysis

## Retrieved Information
### Order Overview
- Order ID, customer details, and contact information
- Order date, shipped date, and delivered date
- Complete status information (order, payment, shipping)
- Financial summary (subtotal, tax, shipping, total)

### Order Items Details
- Product information (name, JAN code)
- Quantity and unit pricing
- Individual item totals
- Complete order item breakdown

### Logistics Information
- Shipping and billing addresses
- Tracking number and delivery status
- Special notes and instructions

## Usage Examples
- "注文ORD123456の詳細を取得" → order_id="ORD123456"
- "注文ORD789012の完全な情報を表示" → order_id="ORD789012"
- "カスタマーサービス用の注文詳細を取得" → order_id="ORD345678"
- "ORD901234の注文ステータスと商品を確認" → order_id="ORD901234"

## Operation Flow
1. Validate order ID existence
2. Retrieve complete order information from database
3. Format order details for comprehensive display
4. Include all related order items with product details
5. Present organized information for analysis

## Return Format
Returns formatted order details including:
- **Order Information**: ID, customer, dates, status summary
- **Financial Details**: Amounts, taxes, fees, totals
- **Order Items**: Complete product breakdown with quantities and pricing
- **Logistics**: Addresses, tracking, delivery information
- **Additional**: Notes, special instructions, order history

This tool provides complete order visibility for customer service, order management, and analysis purposes."""
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
    description: str = """Order Cancellation Tool
This tool provides order cancellation functionality with automatic inventory restoration and comprehensive cancellation management.

## Core Features
- Complete order cancellation with status update to 'cancelled'
- Automatic inventory restoration for all order items
- Cancellation validation based on order status and shipping progress
- Financial impact management for payment processing
- Customer notification support for cancellation confirmation
- Comprehensive error handling for invalid cancellation attempts
- Order history tracking for cancellation records

## Cancellation Rules
- **Allowed**: Orders with status 'pending', 'confirmed', or 'processing'
- **Restricted**: Orders that are 'shipped', 'in_transit', or 'delivered'
- **Inventory**: All order items are automatically returned to available stock
- **Payment**: Payment status considerations for refund processing

## Usage Examples
- "注文ORD123456をキャンセル" → order_id="ORD123456"
- "保留中の注文ORD789012をキャンセル" → order_id="ORD789012"
- "確認済み注文ORD345678をキャンセル" → order_id="ORD345678"
- "処理中の注文ORD901234をキャンセル" → order_id="ORD901234"

## Operation Flow
1. Validate order ID existence
2. Check current order status for cancellation eligibility
3. Verify order has not been shipped or delivered
4. Update order status to 'cancelled'
5. Restore inventory quantities for all order items
6. Record cancellation in order history
7. Return cancellation confirmation

## Inventory Impact
- All order item quantities are restored to available inventory
- Product stock levels are automatically updated
- Inventory reservations are released immediately
- Stock becomes available for new orders

## Restrictions
Cannot cancel orders that are:
- **shipped**: Already dispatched from warehouse
- **in_transit**: Currently being delivered
- **delivered**: Successfully completed delivery
- **already cancelled**: Previously cancelled orders

## Return Format
Returns cancellation confirmation with:
- Order ID: Identifier of the cancelled order
- Success message confirming cancellation completion
- Inventory restoration confirmation

This tool manages complete order cancellation with proper inventory and status management."""
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
    description: str = """Order Statistics & Analytics Tool
This tool provides comprehensive order analytics and statistical reporting functionality for business intelligence and performance monitoring.

## Core Features
- Complete order statistics across all status categories
- Revenue analysis and financial performance metrics
- Order volume tracking and trend analysis
- Payment status distribution for financial insights
- Shipping status breakdown for logistics monitoring
- Real-time data aggregation and reporting
- Comprehensive business intelligence dashboard data

## Statistical Categories
### Order Status Analytics
- **Pending**: Orders awaiting confirmation
- **Confirmed**: Orders accepted for processing
- **Processing**: Orders being prepared
- **Shipped**: Orders dispatched for delivery
- **Delivered**: Successfully completed orders
- **Cancelled**: Cancelled orders with inventory restoration

### Payment Status Analytics
- **Unpaid**: Orders with pending payments
- **Paid**: Orders with completed payments
- **Refunded**: Orders with full refunds processed
- **Partial Refund**: Orders with partial refunds

### Financial Metrics
- **Total Revenue**: Sum of all paid order amounts
- **Revenue Analysis**: Financial performance indicators
- **Payment Distribution**: Payment status breakdown

## Usage Examples
- "現在の注文統計を取得" → (no parameters required)
- "注文パフォーマンス指標を表示" → (no parameters required)
- "注文分析レポートを生成" → (no parameters required)
- "注文と支払いステータスの分布を確認" → (no parameters required)

## Operation Flow
1. Query order database for all status categories
2. Calculate order counts by status type
3. Aggregate payment status distribution
4. Calculate total revenue from paid orders
5. Format comprehensive statistics report
6. Return organized analytics data

## Return Format
Returns comprehensive statistics including:
- **Order Status Counts**: Breakdown by order lifecycle status
- **Payment Status Counts**: Financial status distribution
- **Total Revenue**: Revenue from paid orders
- **Summary Metrics**: Key performance indicators

## Business Intelligence Value
- Monitor order processing efficiency
- Track payment completion rates
- Analyze delivery performance
- Identify bottlenecks in order workflow
- Support data-driven business decisions

This tool provides essential business analytics for order management performance monitoring and strategic planning."""
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
