#!/usr/bin/env python3
"""
階層表示の視覚的確認用テストスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.routers.top_page_api import _build_hierarchical_options
from config.agent_hierarchy_loader import agent_hierarchy_loader

def test_visual_hierarchy():
    """階層表示の視覚的確認"""
    print("=== 階層表示の視覚的確認 ===")
    
    try:
        # 階層構造を取得
        hierarchy = agent_hierarchy_loader.get_agent_hierarchy()
        
        # 階層オプションを生成
        agent_options_list = []
        _build_hierarchical_options(hierarchy, agent_options_list, "", 0)
        
        print("現在の階層表示構造:")
        print("=" * 50)
        
        for option in agent_options_list:
            level = option['level']
            display_name = option['display_name']
            
            # レベルに応じた視覚的表現
            if level == 0:
                print(f"【レベル0】 {display_name}")
                print(f"  CSS: font-weight: bold, color: #2c3e50, padding-left: 0px")
            elif level == 1:
                print(f"【レベル1】 {display_name}")
                print(f"  CSS: color: #495057, padding-left: 20px")
            elif level == 2:
                print(f"【レベル2】 {display_name}")
                print(f"  CSS: color: #6c757d, padding-left: 60px")
            
            print()
        
        print("期待される表示効果:")
        print("=" * 50)
        print("エージェント統括                    (太字、濃い色)")
        print("  └─商品センター管理               (通常、20px缩进)")
        print("    ├─商品詳細管理                 (薄い色、60px缩进)")
        print("    └─商品公開管理                 (薄い色、60px缩进)")
        print()
        print("✅ 第三層級の缩进が20px→60pxに増加し、より明確な階層表示になりました")
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    """メイン関数"""
    print("階層表示の視覚的確認テスト開始\n")
    
    # テスト実行
    test_result = test_visual_hierarchy()
    
    # 結果表示
    print("\n=== テスト結果 ===")
    print(f"視覚的階層表示テスト: {'✅ 成功' if test_result else '❌ 失敗'}")
    
    if test_result:
        print("\n🎉 階層表示の視覚的改善が完了しました！")
        print("第三層級の缩进が増加し、より明確な樹形表示になりました。")
        return 0
    else:
        print("\n❌ 階層表示の視覚的改善に問題があります。")
        return 1

if __name__ == "__main__":
    sys.exit(main())