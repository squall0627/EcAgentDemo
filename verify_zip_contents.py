#!/usr/bin/env python3
import os
import zipfile
import platform
from pathlib import Path

def verify_zip_contents():
    """
    ZIPファイルの内容を確認し、実行ファイルの存在を検証する
    """
    print("=== EcAgentDemo ZIP内容確認ツール ===")
    print(f"現在のプラットフォーム: {platform.system()}")
    
    # distディレクトリ内のZIPファイルを検索
    dist_dir = Path('dist')
    if not dist_dir.exists():
        print("❌ distディレクトリが見つかりません")
        print("   まず build_executable.py を実行してください")
        return False
    
    zip_files = list(dist_dir.glob('EcAgentDemo_v*.zip'))
    if not zip_files:
        print("❌ ZIPファイルが見つかりません")
        print("   まず build_executable.py を実行してください")
        return False
    
    # 最新のZIPファイルを選択
    latest_zip = max(zip_files, key=lambda x: x.stat().st_mtime)
    print(f"📦 検証対象: {latest_zip.name}")
    
    try:
        with zipfile.ZipFile(latest_zip, 'r') as zipf:
            file_list = zipf.namelist()
            
            print(f"📊 総ファイル数: {len(file_list)}")
            
            # 実行ファイルを検索
            executables = []
            for file_path in file_list:
                if 'EcAgentDemo/EcAgentDemo' in file_path and not file_path.endswith('/'):
                    executables.append(file_path)
            
            print("\n🔍 実行ファイルの確認:")
            if executables:
                for exe in executables:
                    file_info = zipf.getinfo(exe)
                    size_mb = file_info.file_size / (1024 * 1024)
                    print(f"  ✅ {exe} ({size_mb:.1f} MB)")
            else:
                print("  ❌ 実行ファイルが見つかりません")
            
            # 重要なファイルの確認
            important_files = [
                '起動スクリプト.bat',
                '起動スクリプト.sh', 
                '.env',
                'README_日本語.md'
            ]
            
            print("\n📋 重要ファイルの確認:")
            for important_file in important_files:
                if important_file in file_list:
                    print(f"  ✅ {important_file}")
                else:
                    print(f"  ❌ {important_file} (見つかりません)")
            
            # プラットフォーム固有の説明
            print("\n💡 プラットフォームについて:")
            current_platform = platform.system()
            if current_platform == "Darwin":  # macOS
                print("  📱 macOSでビルドされたため、実行ファイルは Unix形式 です")
                print("  🖥️  Windows用の .exe ファイルが必要な場合は、Windows環境でビルドしてください")
                print("  🐧 Linux環境でも動作します")
            elif current_platform == "Windows":
                print("  🖥️  Windowsでビルドされたため、実行ファイルは .exe形式 です")
                print("  📱 macOS/Linux環境では動作しません")
            else:
                print("  🐧 Linux環境でビルドされました")
                print("  🖥️  Windows用の .exe ファイルが必要な場合は、Windows環境でビルドしてください")
            
            # ファイルサイズ情報
            zip_size = latest_zip.stat().st_size
            zip_size_mb = zip_size / (1024 * 1024)
            print(f"\n📊 ZIPファイル情報:")
            print(f"  📦 ファイル名: {latest_zip.name}")
            print(f"  📏 サイズ: {zip_size_mb:.1f} MB")
            print(f"  📁 場所: {latest_zip}")
            
            return True
            
    except Exception as e:
        print(f"❌ ZIPファイルの読み込みに失敗しました: {e}")
        return False

def show_cross_platform_build_info():
    """
    クロスプラットフォームビルドの情報を表示
    """
    print("\n" + "="*50)
    print("🌍 クロスプラットフォームビルドについて")
    print("="*50)
    print("""
PyInstallerは実行環境と同じプラットフォーム用の実行ファイルのみを作成できます：

📱 macOS環境:
  - 作成される実行ファイル: EcAgentDemo (Unix実行ファイル)
  - 動作環境: macOS, Linux
  - 拡張子: なし

🖥️  Windows環境:
  - 作成される実行ファイル: EcAgentDemo.exe
  - 動作環境: Windows
  - 拡張子: .exe

🐧 Linux環境:
  - 作成される実行ファイル: EcAgentDemo (Unix実行ファイル)
  - 動作環境: Linux, (macOS)
  - 拡張子: なし

💡 解決方法:
1. Windows用 .exe が必要 → Windows環境でビルド
2. macOS用が必要 → macOS環境でビルド  
3. Linux用が必要 → Linux環境でビルド

🔧 各環境での起動方法:
- Windows: 起動スクリプト.bat をダブルクリック
- macOS/Linux: 起動スクリプト.sh を実行
""")

if __name__ == "__main__":
    success = verify_zip_contents()
    if success:
        show_cross_platform_build_info()
        print("\n✅ ZIP内容の確認が完了しました")
    else:
        print("\n❌ ZIP内容の確認に失敗しました")