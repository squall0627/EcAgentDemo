#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AgentManagerRegistry機能テストスクリプト
セッション・ユーザー別のAgentManagerインスタンス管理をテスト
"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from llm.llm_handler import LLMHandler
from ai_agents.task_planner import AgentManagerRegistry
from ai_agents.product_center.product_center_agent_manager import ProductCenterAgentManager


def test_agent_manager_registry():
    """AgentManagerRegistryの基本機能をテスト"""
    print("🧪 AgentManagerRegistry機能テスト開始")
    
    # LLMHandlerを初期化
    llm_handler = LLMHandler(
        api_key="test_key",
        llm_type="ollama_qwen3"
    )
    
    # 登録済みマネージャーを定義
    registered_managers = {
        "ProductCenterAgentManager": ProductCenterAgentManager
    }
    
    # AgentManagerRegistryを初期化
    registry = AgentManagerRegistry(
        llm_handler=llm_handler,
        registered_managers=registered_managers
    )
    
    print("✅ AgentManagerRegistry初期化完了")
    
    # テストケース1: 同じセッション・ユーザーで同じインスタンスが返されることを確認
    print("\n📋 テストケース1: 同一セッション・ユーザーでのインスタンス一意性")
    
    user_id = "test_user_1"
    session_id = "test_session_1"
    agent_name = "ProductCenterAgentManager"
    
    # 最初の取得
    instance1 = registry.get_or_create_agent_manager(agent_name, user_id, session_id)
    print(f"インスタンス1 ID: {id(instance1)}")
    
    # 2回目の取得（同じインスタンスが返されるはず）
    instance2 = registry.get_or_create_agent_manager(agent_name, user_id, session_id)
    print(f"インスタンス2 ID: {id(instance2)}")
    
    if instance1 is instance2:
        print("✅ 同一セッション・ユーザーで同じインスタンスが返されました")
    else:
        print("❌ 異なるインスタンスが返されました")
        return False
    
    # テストケース2: 異なるセッションで異なるインスタンスが返されることを確認
    print("\n📋 テストケース2: 異なるセッションでのインスタンス分離")
    
    session_id_2 = "test_session_2"
    instance3 = registry.get_or_create_agent_manager(agent_name, user_id, session_id_2)
    print(f"インスタンス3 ID (異なるセッション): {id(instance3)}")
    
    if instance1 is not instance3:
        print("✅ 異なるセッションで異なるインスタンスが返されました")
    else:
        print("❌ 同じインスタンスが返されました")
        return False
    
    # テストケース3: 異なるユーザーで異なるインスタンスが返されることを確認
    print("\n📋 テストケース3: 異なるユーザーでのインスタンス分離")
    
    user_id_2 = "test_user_2"
    instance4 = registry.get_or_create_agent_manager(agent_name, user_id_2, session_id)
    print(f"インスタンス4 ID (異なるユーザー): {id(instance4)}")
    
    if instance1 is not instance4:
        print("✅ 異なるユーザーで異なるインスタンスが返されました")
    else:
        print("❌ 同じインスタンスが返されました")
        return False
    
    # テストケース4: キャッシュ統計情報の確認
    print("\n📋 テストケース4: キャッシュ統計情報")
    
    stats = registry.get_cache_stats()
    print(f"キャッシュ統計: {stats}")
    
    expected_sessions = 3  # (test_user_1, test_session_1), (test_user_1, test_session_2), (test_user_2, test_session_1)
    if stats["total_sessions"] == expected_sessions:
        print(f"✅ 期待されるセッション数 ({expected_sessions}) と一致しました")
    else:
        print(f"❌ セッション数が期待値と異なります。期待値: {expected_sessions}, 実際: {stats['total_sessions']}")
        return False
    
    # テストケース5: セッションキャッシュのクリア
    print("\n📋 テストケース5: セッションキャッシュクリア")
    
    registry.clear_session_cache(user_id, session_id)
    stats_after_clear = registry.get_cache_stats()
    print(f"クリア後のキャッシュ統計: {stats_after_clear}")
    
    if stats_after_clear["total_sessions"] == expected_sessions - 1:
        print("✅ セッションキャッシュが正常にクリアされました")
    else:
        print("❌ セッションキャッシュのクリアが失敗しました")
        return False
    
    # クリア後に新しいインスタンスが作成されることを確認
    instance5 = registry.get_or_create_agent_manager(agent_name, user_id, session_id)
    print(f"インスタンス5 ID (クリア後): {id(instance5)}")
    
    if instance1 is not instance5:
        print("✅ クリア後に新しいインスタンスが作成されました")
    else:
        print("❌ クリア後も同じインスタンスが返されました")
        return False
    
    print("\n🎉 全てのテストケースが成功しました！")
    return True


def test_integration_with_task_planner():
    """TaskPlannerとの統合テスト"""
    print("\n🔗 TaskPlannerとの統合テスト開始")
    
    try:
        from ai_agents.agent_director import AgentDirector
        
        # AgentDirectorを初期化
        director = AgentDirector(
            api_key="test_key",
            llm_type="ollama_qwen3"
        )
        
        print("✅ AgentDirector初期化完了")
        
        # AgentManagerRegistryが正しく設定されていることを確認
        if hasattr(director, 'agent_manager_registry'):
            print("✅ AgentManagerRegistryが正しく設定されています")
            
            # 統計情報を確認
            stats = director.agent_manager_registry.get_cache_stats()
            print(f"初期キャッシュ統計: {stats}")
            
            return True
        else:
            print("❌ AgentManagerRegistryが設定されていません")
            return False
            
    except Exception as e:
        print(f"❌ 統合テストエラー: {e}")
        return False


if __name__ == "__main__":
    print("🚀 AgentManagerRegistry機能テスト実行")
    
    # 基本機能テスト
    basic_test_result = test_agent_manager_registry()
    
    # 統合テスト
    integration_test_result = test_integration_with_task_planner()
    
    if basic_test_result and integration_test_result:
        print("\n🎊 全てのテストが成功しました！")
        sys.exit(0)
    else:
        print("\n💥 一部のテストが失敗しました")
        sys.exit(1)