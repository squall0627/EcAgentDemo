#!/usr/bin/env python3
"""
階層表示機能のテストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.routers.top_page_api import _build_hierarchical_options
from config.agent_hierarchy_loader import agent_hierarchy_loader

def test_hierarchical_options():
    """階層表示オプション生成のテスト"""
    print("=== 階層表示オプション生成テスト ===")
    
    try:
        # 階層構造を取得
        hierarchy = agent_hierarchy_loader.get_agent_hierarchy()
        print(f"✅ 階層構造取得成功")
        
        # 階層オプションを生成
        agent_options_list = []
        _build_hierarchical_options(hierarchy, agent_options_list, "", 0)
        
        print(f"✅ 階層オプション生成成功: {len(agent_options_list)}個のオプション")
        
        # 生成されたオプションを表示
        print("\n=== 生成された階層表示オプション ===")
        for i, option in enumerate(agent_options_list):
            print(f"{i+1}. {option['display_name']}")
            print(f"   - Agent Key: {option['agent_key']}")
            print(f"   - Level: {option['level']}")
            print(f"   - Description: {option['description']}")
            print()
        
        # HTMLオプション文字列を生成
        print("=== 生成されるHTMLオプション ===")
        for i, option_data in enumerate(agent_options_list):
            selected = 'selected' if i == 0 else ''
            html_option = f'''<option value="{option_data["agent_key"]}" 
                           data-id="{option_data["id"]}"
                           data-level="{option_data["level"]}"
                           data-description="{option_data["description"]}" 
                           {selected}>{option_data["display_name"]}</option>'''
            print(html_option)
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """メイン関数"""
    print("階層表示機能テスト開始\n")
    
    # テスト実行
    test_result = test_hierarchical_options()
    
    # 結果表示
    print("\n=== テスト結果 ===")
    print(f"階層表示オプション生成テスト: {'✅ 成功' if test_result else '❌ 失敗'}")
    
    if test_result:
        print("\n🎉 階層表示機能のテストが成功しました！")
        return 0
    else:
        print("\n❌ 階層表示機能のテストが失敗しました。")
        return 1

if __name__ == "__main__":
    sys.exit(main())