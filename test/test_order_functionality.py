#!/usr/bin/env python3
"""
注文センター機能のテストスクリプト
Order Center Functionality Test Script
"""

import requests
import json
import sys
from typing import Dict, Any

# APIベースURL
API_BASE_URL = "http://localhost:5004"

def test_api_endpoint(method: str, url: str, data: Dict[Any, Any] = None, params: Dict[str, Any] = None) -> Dict[Any, Any]:
    """API エンドポイントをテストする"""
    try:
        if method.upper() == "GET":
            response = requests.get(url, params=params)
        elif method.upper() == "POST":
            response = requests.post(url, json=data)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data)
        elif method.upper() == "DELETE":
            response = requests.delete(url)
        else:
            return {"success": False, "error": f"Unsupported method: {method}"}

        return {
            "success": response.status_code < 400,
            "status_code": response.status_code,
            "data": response.json() if response.content else None,
            "error": response.text if response.status_code >= 400 else None
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def test_order_tools():
    """注文ツールの機能をテストする"""
    print("=== 注文センター機能テスト ===")
    print("Testing Order Center Functionality")

    # 1. 注文検索テスト
    print("\n1. 注文検索テスト (Order Search Test)")
    search_result = test_api_endpoint("GET", f"{API_BASE_URL}/api/order/orders", params={"limit": 5})
    print(f"Status: {'✓' if search_result['success'] else '✗'}")
    if search_result['success']:
        orders_count = search_result['data'].get('total_count', 0)
        print(f"Found {orders_count} orders")
    else:
        print(f"Error: {search_result['error']}")

    # 2. 注文作成テスト（まず商品を確認）
    print("\n2. 商品確認 (Product Check)")
    products_result = test_api_endpoint("GET", f"{API_BASE_URL}/api/product/products", params={"limit": 1})
    if products_result['success'] and products_result['data']['products']:
        # 最初の商品を使用
        first_product = products_result['data']['products'][0]
        jancode = first_product['jancode']
        print(f"Using product: {jancode}")

        # 3. 注文作成テスト
        print("\n3. 注文作成テスト (Order Creation Test)")
        order_data = {
            "customer_id": "CUST001",
            "customer_name": "テスト顧客",
            "customer_email": "test@example.com",
            "customer_phone": "090-1234-5678",
            "shipping_address": "東京都渋谷区テスト町1-2-3",
            "billing_address": "東京都渋谷区テスト町1-2-3",
            "notes": "テスト注文です",
            "order_items": [
                {
                    "jancode": jancode,
                    "quantity": 1
                }
            ]
        }

        create_result = test_api_endpoint("POST", f"{API_BASE_URL}/api/order/orders", data=order_data)
        print(f"Status: {'✓' if create_result['success'] else '✗'}")

        if create_result['success']:
            order_id = create_result['data']['order_id']
            print(f"Created order: {order_id}")

            # 4. 注文詳細取得テスト
            print("\n4. 注文詳細取得テスト (Order Detail Test)")
            detail_result = test_api_endpoint("GET", f"{API_BASE_URL}/api/order/orders/{order_id}")
            print(f"Status: {'✓' if detail_result['success'] else '✗'}")
            if detail_result['success']:
                print(f"Order status: {detail_result['data']['order_status']}")
                print(f"Payment status: {detail_result['data']['payment_status']}")
                print(f"Total amount: ¥{detail_result['data']['total_amount']}")

            # 5. 注文ステータス更新テスト
            print("\n5. 注文ステータス更新テスト (Order Status Update Test)")
            status_update_result = test_api_endpoint(
                "PUT", 
                f"{API_BASE_URL}/api/order/orders/{order_id}/status",
                data={"order_status": "confirmed"}
            )
            print(f"Status: {'✓' if status_update_result['success'] else '✗'}")
            if status_update_result['success']:
                print(f"Updated to: {status_update_result['data']['new_status']}")

            # 6. 支払いステータス更新テスト
            print("\n6. 支払いステータス更新テスト (Payment Status Update Test)")
            payment_update_result = test_api_endpoint(
                "PUT",
                f"{API_BASE_URL}/api/order/orders/{order_id}/payment",
                data={"payment_status": "paid"}
            )
            print(f"Status: {'✓' if payment_update_result['success'] else '✗'}")
            if payment_update_result['success']:
                print(f"Updated to: {payment_update_result['data']['new_status']}")

            # 7. 配送ステータス更新テスト
            print("\n7. 配送ステータス更新テスト (Shipping Status Update Test)")
            shipping_update_result = test_api_endpoint(
                "PUT",
                f"{API_BASE_URL}/api/order/orders/{order_id}/shipping",
                data={
                    "shipping_status": "shipped",
                    "tracking_number": "TRACK123456789"
                }
            )
            print(f"Status: {'✓' if shipping_update_result['success'] else '✗'}")
            if shipping_update_result['success']:
                print(f"Updated to: {shipping_update_result['data']['new_status']}")
                print(f"Tracking: {shipping_update_result['data']['tracking_number']}")

            # 8. 注文キャンセルテスト（新しい注文を作成してテスト）
            print("\n8. 注文キャンセルテスト (Order Cancellation Test)")
            # 新しい注文を作成
            cancel_order_data = {
                "customer_id": "CUST002",
                "customer_name": "キャンセルテスト顧客",
                "order_items": [{"jancode": jancode, "quantity": 1}]
            }
            cancel_create_result = test_api_endpoint("POST", f"{API_BASE_URL}/api/order/orders", data=cancel_order_data)

            if cancel_create_result['success']:
                cancel_order_id = cancel_create_result['data']['order_id']
                cancel_result = test_api_endpoint("DELETE", f"{API_BASE_URL}/api/order/orders/{cancel_order_id}")
                print(f"Status: {'✓' if cancel_result['success'] else '✗'}")
                if cancel_result['success']:
                    print(f"Cancelled order: {cancel_order_id}")

        else:
            print(f"Order creation failed: {create_result['error']}")
    else:
        print("No products found for testing. Please add some products first.")

def test_order_tools_functionality():
    """注文ツールクラスの機能をテストする"""
    print("\n=== 注文ツール機能テスト ===")
    print("Testing Order Tools Functionality")

    try:
        # 注文ツールをインポート
        from ai_agents.order_center.tools.order_tools import (
            search_orders_tool_fn,
            CreateOrderTool,
            UpdateOrderStatusTool,
            GetOrderDetailTool,
            CancelOrderTool,
            OrderStatisticsTool
        )

        # 1. 検索ツール関数テスト
        print("\n1. 検索ツール関数テスト (Search Tool Function Test)")
        search_result = search_orders_tool_fn(limit=3)
        print(f"Status: {'✓' if search_result['success'] else '✗'}")
        if search_result['success']:
            print(f"Message: {search_result['message']}")

        # 2. 統計ツールテスト
        print("\n2. 統計ツールテスト (Statistics Tool Test)")
        stats_tool = OrderStatisticsTool()
        stats_result = stats_tool._run()
        print(f"Status: {'✓' if 'Error' not in stats_result else '✗'}")
        print("Statistics preview:")
        print(stats_result[:200] + "..." if len(stats_result) > 200 else stats_result)

        print("\n✓ 注文ツール機能テスト完了")

    except ImportError as e:
        print(f"✗ Import error: {e}")
    except Exception as e:
        print(f"✗ Tool test error: {e}")

def main():
    """メイン関数"""
    print("注文センター機能の包括的テスト")
    print("Comprehensive Order Center Functionality Test")
    print("=" * 50)

    # APIテスト
    test_order_tools()

    # ツール機能テスト
    test_order_tools_functionality()

    print("\n" + "=" * 50)
    print("テスト完了 (Test Completed)")
    print("\n注意: このテストを実行する前に、以下を確認してください:")
    print("Note: Before running this test, please ensure:")
    print("1. FastAPIサーバーが起動している (FastAPI server is running)")
    print("2. データベースが初期化されている (Database is initialized)")
    print("3. 商品データが存在する (Product data exists)")

if __name__ == "__main__":
    main()
