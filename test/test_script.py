from test_data_generator import TestDataGenerator, CSVDataImporter

def test_data_generation():
    """テストデータ生成のテスト"""
    print("=== テストデータ生成テスト開始 ===")
    
    try:
        # データ生成テスト
        generator = TestDataGenerator()
        generator.generate_all_test_data()
        
        print("✓ テストデータ生成成功")
        
        # CSVファイルの存在確認
        import os
        csv_files = ["csv_data/products.csv", "csv_data/orders.csv", "csv_data/order_items.csv"]
        for csv_file in csv_files:
            if os.path.exists(csv_file):
                print(f"✓ CSVファイル作成成功: {csv_file}")
            else:
                print(f"✗ CSVファイル作成失敗: {csv_file}")
        
        # データベースインポートテスト
        print("\n=== データベースインポートテスト開始 ===")
        importer = CSVDataImporter()
        importer.import_all_from_csv()
        
        print("✓ データベースインポート成功")
        print("=== すべてのテスト完了 ===")
        
    except Exception as e:
        print(f"✗ テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_data_generation()