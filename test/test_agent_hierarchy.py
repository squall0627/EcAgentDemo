#!/usr/bin/env python3
"""
エージェント階層システムのテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.agent_hierarchy_loader import agent_hierarchy_loader

def test_agent_hierarchy_loader():
    """エージェント階層ローダーのテスト"""
    print("=== エージェント階層ローダーテスト ===")
    
    try:
        # エントリーポイント一覧を取得
        entry_points = agent_hierarchy_loader.get_entry_points()
        print(f"✅ エントリーポイント数: {len(entry_points)}")
        
        for entry_point in entry_points:
            print(f"  - {entry_point['japanese_name']} ({entry_point['agent_key']})")
        
        # 階層構造を取得
        hierarchy = agent_hierarchy_loader.get_agent_hierarchy()
        print(f"✅ 階層構造取得成功")
        
        # ツリー表示
        tree_display = agent_hierarchy_loader.get_hierarchy_tree_display()
        print("✅ 階層ツリー表示:")
        print(tree_display)
        
        # 各エージェントの情報を取得
        print("\n=== エージェント情報テスト ===")
        for entry_point in entry_points:
            agent_key = entry_point['agent_key']
            agent_info = agent_hierarchy_loader.get_agent_info(agent_key)
            if agent_info:
                print(f"✅ {agent_key}: {agent_info['japanese_name']}")
                print(f"   モジュール: {agent_info['module_path']}")
                print(f"   注入方法: {agent_info['injection_method']}")
            else:
                print(f"❌ {agent_key}: 情報取得失敗")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def test_agent_instance_creation():
    """エージェントインスタンス作成のテスト"""
    print("\n=== エージェントインスタンス作成テスト ===")
    
    # テスト用のAPIキー（実際の処理では環境変数から取得）
    api_key = os.getenv("OPENAI_API_KEY", "test_api_key")
    
    try:
        # ProductDetailAgentのインスタンス作成をテスト
        print("ProductDetailAgentのインスタンス作成をテスト...")
        agent = agent_hierarchy_loader.create_agent_instance(
            agent_key="ProductDetailAgent",
            api_key=api_key,
            llm_type="ollama",
            use_langfuse=False  # テスト時はLangfuseを無効化
        )
        print(f"✅ ProductDetailAgent作成成功: {type(agent).__name__}")
        
        # ProductCenterAgentManagerのインスタンス作成をテスト
        print("ProductCenterAgentManagerのインスタンス作成をテスト...")
        manager = agent_hierarchy_loader.create_agent_instance(
            agent_key="ProductCenterAgentManager",
            api_key=api_key,
            llm_type="ollama",
            use_langfuse=False
        )
        print(f"✅ ProductCenterAgentManager作成成功: {type(manager).__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン関数"""
    print("エージェント階層システムテスト開始\n")
    
    # テスト実行
    test1_result = test_agent_hierarchy_loader()
    test2_result = test_agent_instance_creation()
    
    # 結果表示
    print("\n=== テスト結果 ===")
    print(f"階層ローダーテスト: {'✅ 成功' if test1_result else '❌ 失敗'}")
    print(f"インスタンス作成テスト: {'✅ 成功' if test2_result else '❌ 失敗'}")
    
    if test1_result and test2_result:
        print("\n🎉 全てのテストが成功しました！")
        return 0
    else:
        print("\n❌ 一部のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    sys.exit(main())