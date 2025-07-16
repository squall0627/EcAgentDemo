import csv
from collections import Counter

def verify_products_csv():
    """商品CSVデータの検証"""
    print("=== 商品データ検証 ===")

    try:
        with open('test/csv_data/products.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            products = list(reader)

        print(f"商品データ件数: {len(products)}")

        # カテゴリ統計
        categories = [product['category'] for product in products]
        category_counts = Counter(categories)
        print(f"カテゴリ数: {len(category_counts)}")
        print("カテゴリ一覧:")
        for category, count in category_counts.items():
            print(f"  - {category}: {count}件")

        print("\n商品データサンプル:")
        for i in range(min(3, len(products))):
            product = products[i]
            print(f"  JANコード: {product['jancode']}")
            print(f"  商品名(日): {product['name_jp']}")
            print(f"  カテゴリ: {product['category']}")
            print(f"  価格: {product['price']}円")
            print(f"  在庫: {product['stock']}")
            print(f"  ステータス: {product['status']}")
            print("  ---")

    except Exception as e:
        print(f"商品データ検証エラー: {e}")

def verify_orders_csv():
    """注文CSVデータの検証"""
    print("\n=== 注文データ検証 ===")

    try:
        with open('test/csv_data/orders.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            orders = list(reader)

        print(f"注文データ件数: {len(orders)}")

        # 注文ステータス統計
        order_statuses = [order['order_status'] for order in orders]
        status_counts = Counter(order_statuses)
        print(f"注文ステータス分布:")
        for status, count in status_counts.items():
            print(f"  - {status}: {count}件")

        print("\n注文データサンプル:")
        for i in range(min(2, len(orders))):
            order = orders[i]
            print(f"  注文ID: {order['order_id']}")
            print(f"  顧客名: {order['customer_name']}")
            print(f"  メール: {order['customer_email']}")
            print(f"  電話: {order['customer_phone']}")
            print(f"  配送先: {order['shipping_address']}")
            print(f"  合計金額: {order['total_amount']}円")
            print(f"  注文ステータス: {order['order_status']}")
            print("  ---")

    except Exception as e:
        print(f"注文データ検証エラー: {e}")

def verify_order_items_csv():
    """注文アイテムCSVデータの検証"""
    print("\n=== 注文アイテムデータ検証 ===")

    try:
        with open('test/csv_data/order_items.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            order_items = list(reader)

        print(f"注文アイテム件数: {len(order_items)}")

        # 注文あたりのアイテム数統計
        order_item_counts = Counter([item['order_id'] for item in order_items])
        items_per_order = list(order_item_counts.values())

        if items_per_order:
            avg_items = sum(items_per_order) / len(items_per_order)
            print(f"注文あたりの平均アイテム数: {avg_items:.2f}")
            print(f"最大アイテム数: {max(items_per_order)}")
            print(f"最小アイテム数: {min(items_per_order)}")

        print("\n注文アイテムサンプル:")
        for i in range(min(5, len(order_items))):
            item = order_items[i]
            print(f"  注文ID: {item['order_id']}")
            print(f"  商品名: {item['product_name']}")
            print(f"  数量: {item['quantity']}")
            print(f"  単価: {item['unit_price']}円")
            print(f"  小計: {item['total_price']}円")
            print("  ---")

    except Exception as e:
        print(f"注文アイテムデータ検証エラー: {e}")

def verify_data_relationships():
    """データ関係性の検証"""
    print("\n=== データ関係性検証 ===")

    try:
        # 商品データ読み込み
        with open('test/csv_data/products.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            products = list(reader)

        # 注文データ読み込み
        with open('test/csv_data/orders.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            orders = list(reader)

        # 注文アイテムデータ読み込み
        with open('test/csv_data/order_items.csv', 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            order_items = list(reader)

        # 商品とオーダーアイテムの関係性チェック
        product_jancodes = set([product['jancode'] for product in products])
        order_item_jancodes = set([item['jancode'] for item in order_items])

        missing_products = order_item_jancodes - product_jancodes
        if missing_products:
            print(f"⚠️ 商品テーブルに存在しないJANコード: {len(missing_products)}件")
        else:
            print("✓ すべての注文アイテムの商品が商品テーブルに存在します")

        # 注文とオーダーアイテムの関係性チェック
        order_ids = set([order['order_id'] for order in orders])
        order_item_order_ids = set([item['order_id'] for item in order_items])

        missing_orders = order_item_order_ids - order_ids
        if missing_orders:
            print(f"⚠️ 注文テーブルに存在しない注文ID: {len(missing_orders)}件")
        else:
            print("✓ すべての注文アイテムの注文IDが注文テーブルに存在します")

        print(f"✓ データ整合性チェック完了")

    except Exception as e:
        print(f"データ関係性検証エラー: {e}")

def main():
    """メイン検証関数"""
    print("CSVデータ検証ツール")
    verify_products_csv()
    verify_orders_csv()
    verify_order_items_csv()
    verify_data_relationships()
    print("\n=== 検証完了 ===")

if __name__ == "__main__":
    main()
