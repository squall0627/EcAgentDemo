import PyInstaller.__main__
import os
import shutil
import zipfile
from datetime import datetime

def build_executable():
    """
    PyInstallerを使用してEcAgentDemoを実行可能ファイルにパッケージ化
    """
    print("EcAgentDemoの実行可能ファイルを作成中...")

    # 以前のビルドをクリーンアップ
    if os.path.exists('dist'):
        shutil.rmtree('dist')
        print("古いdistディレクトリを削除しました")

    if os.path.exists('build'):
        shutil.rmtree('build')
        print("古いbuildディレクトリを削除しました")

    # PyInstallerの設定
    args = [
        'api/main.py',                          # メインエントリーポイント
        '--onedir',                             # 単一実行フォルダとして作成
        '--name=EcAgentDemo',                   # 実行ファイル名
        '--add-data=static:static',             # 静的ファイルを含める
        '--add-data=config:config',             # 設定ファイルを含める
        '--hidden-import=uvicorn.main',         # uvicornの明示的インポート
        '--hidden-import=uvicorn.server',
        '--hidden-import=uvicorn.config',
        '--hidden-import=fastapi',
        '--hidden-import=fastapi.staticfiles',
        '--hidden-import=sqlalchemy',
        '--hidden-import=sqlite3',
        '--hidden-import=pydantic',
        '--collect-all=langchain',              # langchainの全モジュールを収集
        '--collect-all=openai',                 # OpenAIライブラリを収集
        '--collect-all=anthropic',              # Anthropicライブラリを収集
        '--collect-all=google',                 # Googleライブラリを収集
        '--collect-submodules=api',             # apiモジュールのサブモジュールを収集
        '--collect-submodules=db',              # dbモジュールのサブモジュールを収集
        '--collect-submodules=models',          # modelsモジュールのサブモジュールを収集
        '--noconsole',                          # Windowsでコンソールウィンドウを非表示
        '--clean',                              # 一時ファイルをクリーンアップ
    ]

    # アイコンファイルが存在する場合は追加
    if os.path.exists('static/favicon.ico'):
        args.append('--icon=static/favicon.ico')

    try:
        # PyInstallerを実行
        PyInstaller.__main__.run(args)
        print("\n✅ ビルドが完了しました！")
        print("📁 実行ファイルは 'dist' フォルダにあります")

        # ビルド後の処理
        post_build_setup()

    except Exception as e:
        print(f"❌ ビルド中にエラーが発生しました: {e}")
        return False

    return True

def create_distribution_zip():
    """
    distフォルダの内容をZIPファイルにパッケージ化
    """
    print("\n📦 配布用ZIPファイルを作成中...")

    # ZIPファイル名を生成（タイムスタンプ付き）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"EcAgentDemo_v1.0_{timestamp}.zip"
    zip_path = os.path.join('dist', zip_filename)

    try:
        # distディレクトリに移動してZIPを作成
        original_dir = os.getcwd()
        os.chdir('dist')

        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # distディレクトリ内のすべてのファイルとフォルダを追加
            for root, dirs, files in os.walk('.'):
                # ZIPファイル自体は除外
                if root == '.' and zip_filename in files:
                    files.remove(zip_filename)

                for file in files:
                    file_path = os.path.join(root, file)
                    # アーカイブ内のパスは相対パスにする
                    arcname = file_path
                    zipf.write(file_path, arcname)

        # 元のディレクトリに戻る
        os.chdir(original_dir)

        # ZIPファイルのサイズを取得
        zip_size = os.path.getsize(zip_path)
        zip_size_mb = zip_size / (1024 * 1024)

        print(f"📦 ZIPファイルを作成しました: {zip_filename}")
        print(f"📊 ファイルサイズ: {zip_size_mb:.1f} MB")
        print(f"📁 保存場所: dist/{zip_filename}")

    except Exception as e:
        print(f"❌ ZIPファイルの作成に失敗しました: {e}")
        # エラーが発生しても元のディレクトリに戻る
        try:
            os.chdir(original_dir)
        except:
            pass

def post_build_setup():
    """
    ビルド後のセットアップ処理
    """
    print("\nビルド後のセットアップを実行中...")

    # 設定ファイルのテンプレートを作成
    env_template_path = os.path.join('dist', '.env')
    if not os.path.exists(env_template_path):
        with open(env_template_path, 'w', encoding='utf-8') as f:
            f.write("""# API設定（起動後に設定ページで変更可能）
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# システム設定
ACCESS_TOKEN_EXPIRE_MINUTES=180
API_BASE_URL=http://localhost:8000

# Langfuse設定（オプション）
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_HOST=https://us.cloud.langfuse.com
""")
        print("📝 .envテンプレートファイルを作成しました")

    # 日本語READMEをコピー
    readme_src = 'README_日本語.md'
    readme_dst = os.path.join('dist', 'README_日本語.md')
    if os.path.exists(readme_src):
        shutil.copy2(readme_src, readme_dst)
        print("📖 日本語READMEをコピーしました")

    # 起動スクリプトをコピー
    # Windows用バッチファイル
    bat_src = '起動スクリプト.bat'
    bat_dst = os.path.join('dist', '起動スクリプト.bat')
    if os.path.exists(bat_src):
        shutil.copy2(bat_src, bat_dst)
        print("🖥️  Windows起動スクリプトをコピーしました")

    # Mac/Linux用シェルスクリプト
    sh_src = '起動スクリプト.sh'
    sh_dst = os.path.join('dist', '起動スクリプト.sh')
    if os.path.exists(sh_src):
        shutil.copy2(sh_src, sh_dst)
        # 実行権限を付与
        import stat
        os.chmod(sh_dst, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
        print("🐧 Mac/Linux起動スクリプトをコピーしました")

    # 静的ファイルを明示的にコピー
    static_src = 'static'
    static_dst = os.path.join('dist', 'EcAgentDemo', 'static')
    if os.path.exists(static_src):
        shutil.copytree(static_src, static_dst, dirs_exist_ok=True)
        print("📁 静的ファイルをコピーしました")

    # ZIPパッケージを作成
    create_distribution_zip()

    print("✅ セットアップが完了しました！")

if __name__ == "__main__":
    success = build_executable()
    if success:
        print("\n🎉 EcAgentDemoの実行可能ファイルが正常に作成されました！")
        print("📖 使用方法については README_日本語.md をご確認ください")
    else:
        print("\n❌ ビルドに失敗しました")
