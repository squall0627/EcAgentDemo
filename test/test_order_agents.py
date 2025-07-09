#!/usr/bin/env python3
"""
注文エージェント機能のテストスクリプト
Order Agents Functionality Test Script
"""

import os
import sys
from dotenv import load_dotenv

# 環境変数を読み込み
load_dotenv()

def test_order_detail_agent():
    """注文詳細エージェントのテスト"""
    print("=== 注文詳細エージェントテスト ===")
    try:
        from ai_agents.order_center.order_detail_agent import OrderDetailAgent

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("✗ OPENAI_API_KEY が設定されていません")
            return False

        agent = OrderDetailAgent(api_key=api_key, llm_type="openai_gpt4")
        print("✓ OrderDetailAgent インスタンス作成成功")

        # エージェント能力の確認
        capability = agent.get_agent_capability()
        print(f"✓ エージェント能力: {capability.agent_type}")
        print(f"  説明: {capability.description}")

        return True

    except Exception as e:
        print(f"✗ OrderDetailAgent テストエラー: {str(e)}")
        return False

def test_order_item_modification_agent():
    """注文商品変更エージェントのテスト"""
    print("\n=== 注文商品変更エージェントテスト ===")
    try:
        from ai_agents.order_center.order_item_modification_agent import OrderItemModificationAgent

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("✗ OPENAI_API_KEY が設定されていません")
            return False

        agent = OrderItemModificationAgent(api_key=api_key, llm_type="openai_gpt4")
        print("✓ OrderItemModificationAgent インスタンス作成成功")

        # エージェント能力の確認
        capability = agent.get_agent_capability()
        print(f"✓ エージェント能力: {capability.agent_type}")
        print(f"  説明: {capability.description}")

        return True

    except Exception as e:
        print(f"✗ OrderItemModificationAgent テストエラー: {str(e)}")
        return False

def test_order_status_change_agent():
    """注文状態変更エージェントのテスト"""
    print("\n=== 注文状態変更エージェントテスト ===")
    try:
        from ai_agents.order_center.order_status_change_agent import OrderStatusChangeAgent

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("✗ OPENAI_API_KEY が設定されていません")
            return False

        agent = OrderStatusChangeAgent(api_key=api_key, llm_type="openai_gpt4")
        print("✓ OrderStatusChangeAgent インスタンス作成成功")

        # エージェント能力の確認
        capability = agent.get_agent_capability()
        print(f"✓ エージェント能力: {capability.agent_type}")
        print(f"  説明: {capability.description}")

        return True

    except Exception as e:
        print(f"✗ OrderStatusChangeAgent テストエラー: {str(e)}")
        return False

def test_order_cancellation_agent():
    """注文取消・返品エージェントのテスト"""
    print("\n=== 注文取消・返品エージェントテスト ===")
    try:
        from ai_agents.order_center.order_cancellation_agent import OrderCancellationAgent

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("✗ OPENAI_API_KEY が設定されていません")
            return False

        agent = OrderCancellationAgent(api_key=api_key, llm_type="openai_gpt4")
        print("✓ OrderCancellationAgent インスタンス作成成功")

        # エージェント能力の確認
        capability = agent.get_agent_capability()
        print(f"✓ エージェント能力: {capability.agent_type}")
        print(f"  説明: {capability.description}")

        return True

    except Exception as e:
        print(f"✗ OrderCancellationAgent テストエラー: {str(e)}")
        return False

def test_order_center_agent_manager():
    """注文センターエージェントマネージャーのテスト"""
    print("\n=== 注文センターエージェントマネージャーテスト ===")
    try:
        from ai_agents.order_center.order_center_agent_manager import OrderCenterAgentManager

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("✗ OPENAI_API_KEY が設定されていません")
            return False

        manager = OrderCenterAgentManager(api_key=api_key, llm_type="openai_gpt4")
        print("✓ OrderCenterAgentManager インスタンス作成成功")

        # エージェント能力の確認
        capability = manager.get_agent_capability()
        print(f"✓ エージェント能力: {capability.agent_type}")
        print(f"  説明: {capability.description}")

        return True

    except Exception as e:
        print(f"✗ OrderCenterAgentManager テストエラー: {str(e)}")
        return False

def test_agent_tools():
    """エージェントツールのテスト"""
    print("\n=== エージェントツールテスト ===")
    try:
        from ai_agents.order_center.tools.order_detail_agent_tool import OrderDetailAgentTool
        from ai_agents.order_center.tools.order_item_modification_agent_tool import OrderItemModificationAgentTool
        from ai_agents.order_center.tools.order_status_change_agent_tool import OrderStatusChangeAgentTool
        from ai_agents.order_center.tools.order_cancellation_agent_tool import OrderCancellationAgentTool

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("✗ OPENAI_API_KEY が設定されていません")
            return False

        # 各ツールのインスタンス作成テスト
        tools = [
            ("OrderDetailAgentTool", OrderDetailAgentTool),
            ("OrderItemModificationAgentTool", OrderItemModificationAgentTool),
            ("OrderStatusChangeAgentTool", OrderStatusChangeAgentTool),
            ("OrderCancellationAgentTool", OrderCancellationAgentTool)
        ]

        for tool_name, tool_class in tools:
            try:
                tool = tool_class(api_key=api_key, llm_type="openai_gpt4")
                print(f"✓ {tool_name} インスタンス作成成功")
            except Exception as e:
                print(f"✗ {tool_name} エラー: {str(e)}")
                return False

        return True

    except Exception as e:
        print(f"✗ エージェントツールテストエラー: {str(e)}")
        return False

def test_agent_director_integration():
    """エージェントディレクターとの統合テスト"""
    print("\n=== エージェントディレクター統合テスト ===")
    try:
        from ai_agents.agent_director import AgentDirector

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("✗ OPENAI_API_KEY が設定されていません")
            return False

        director = AgentDirector(api_key=api_key, llm_type="openai_gpt4")
        print("✓ AgentDirector インスタンス作成成功")

        # 登録されたエージェントマネージャーの確認
        registry = director.agent_manager_registry
        if "OrderCenterAgentManager" in registry.registered_managers:
            print("✓ OrderCenterAgentManager が正常に登録されています")
        else:
            print("✗ OrderCenterAgentManager が登録されていません")
            return False

        return True

    except Exception as e:
        print(f"✗ AgentDirector統合テストエラー: {str(e)}")
        return False

def test_agent_hierarchy_config():
    """エージェント階層設定のテスト"""
    print("\n=== エージェント階層設定テスト ===")
    try:
        import json

        with open("../config/agent_hierarchy.json", "r", encoding="utf-8") as f:
            config = json.load(f)

        # OrderCenterAgentManagerの存在確認
        hierarchy = config.get("agent_hierarchy", {}).get("AgentDirector", {}).get("children", {})
        if "OrderCenterAgentManager" in hierarchy:
            print("✓ OrderCenterAgentManager が階層設定に存在します")

            # 子エージェントの確認
            order_children = hierarchy["OrderCenterAgentManager"].get("children", {})
            expected_children = [
                "OrderDetailAgent",
                "OrderItemModificationAgent", 
                "OrderStatusChangeAgent",
                "OrderCancellationAgent"
            ]

            for child in expected_children:
                if child in order_children:
                    print(f"✓ {child} が設定されています")
                else:
                    print(f"✗ {child} が設定されていません")
                    return False
        else:
            print("✗ OrderCenterAgentManager が階層設定に存在しません")
            return False

        # エントリーポイントの確認
        entry_points = config.get("entry_points", [])
        order_entry_points = [ep for ep in entry_points if "order" in ep.get("id", "")]
        if len(order_entry_points) >= 5:  # manager + 4 agents
            print(f"✓ 注文関連エントリーポイントが {len(order_entry_points)} 個設定されています")
        else:
            print(f"✗ 注文関連エントリーポイントが不足しています (現在: {len(order_entry_points)})")
            return False

        return True

    except Exception as e:
        print(f"✗ エージェント階層設定テストエラー: {str(e)}")
        return False

def main():
    """メイン関数"""
    print("注文エージェント機能の包括的テスト")
    print("Comprehensive Order Agents Functionality Test")
    print("=" * 60)

    tests = [
        ("注文詳細エージェント", test_order_detail_agent),
        ("注文商品変更エージェント", test_order_item_modification_agent),
        ("注文状態変更エージェント", test_order_status_change_agent),
        ("注文取消・返品エージェント", test_order_cancellation_agent),
        ("注文センターエージェントマネージャー", test_order_center_agent_manager),
        ("エージェントツール", test_agent_tools),
        ("エージェントディレクター統合", test_agent_director_integration),
        ("エージェント階層設定", test_agent_hierarchy_config)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed += 1
            print(f"✓ {test_name} テスト成功")
        else:
            print(f"✗ {test_name} テスト失敗")

    print("\n" + "=" * 60)
    print(f"テスト結果: {passed}/{total} 成功")

    if passed == total:
        print("🎉 すべてのテストが成功しました！")
        print("🎉 All tests passed successfully!")
        return 0
    else:
        print("❌ 一部のテストが失敗しました")
        print("❌ Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
