#!/usr/bin/env python3
"""
音声入力機能のテストスクリプト
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 環境変数を.envファイルから読み込み
load_dotenv()

from services.voice_service import VoiceService

async def test_voice_service():
    """VoiceServiceの基本機能をテスト"""
    print("🎤 音声サービステストを開始...")

    # VoiceServiceを初期化
    voice_service = VoiceService()

    # 利用可能性をチェック
    if not voice_service.is_available():
        print("❌ 音声サービスが利用できません。OPENAI_API_KEYを設定してください。")
        return False

    print("✅ 音声サービスが利用可能です")

    # サポートされているフォーマットを表示
    supported_formats = voice_service.get_supported_formats()
    print(f"📋 サポートされている音声フォーマット: {', '.join(supported_formats)}")

    # テスト用の音声ファイルがある場合のテスト（実際の音声ファイルが必要）
    test_audio_path = project_root / "test_audio.wav"
    if test_audio_path.exists():
        print(f"🔊 テスト音声ファイルを処理中: {test_audio_path}")
        try:
            with open(test_audio_path, "rb") as f:
                audio_data = f.read()

            transcribed_text = await voice_service.transcribe_audio(audio_data, "test_audio.wav")
            print(f"📝 変換結果: {transcribed_text}")

        except Exception as e:
            print(f"❌ 音声変換テストに失敗: {e}")
            return False
    else:
        print("ℹ️  テスト音声ファイル (test_audio.wav) が見つかりません。実際の音声ファイルでテストしてください。")

    return True

def test_environment():
    """環境設定をテスト"""
    print("🔧 環境設定をチェック中...")

    # 必要な環境変数をチェック
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY が設定されていません")
        print("   .env ファイルまたは環境変数に OPENAI_API_KEY を設定してください")
        return False
    else:
        print("✅ OPENAI_API_KEY が設定されています")

    # 必要なパッケージをチェック
    try:
        import openai
        print("✅ openai パッケージが利用可能です")
    except ImportError:
        print("❌ openai パッケージがインストールされていません")
        print("   pip install openai を実行してください")
        return False

    try:
        import fastapi
        print("✅ fastapi パッケージが利用可能です")
    except ImportError:
        print("❌ fastapi パッケージがインストールされていません")
        return False

    return True

def test_api_structure():
    """API構造をテスト"""
    print("🔗 API構造をチェック中...")

    # chat_api.pyの存在確認
    chat_api_path = project_root / "api" / "routers" / "chat_api.py"
    if not chat_api_path.exists():
        print("❌ chat_api.py が見つかりません")
        return False

    # voice_input エンドポイントの存在確認
    with open(chat_api_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if '/voice_input' in content and 'process_voice_input' in content:
            print("✅ voice_input エンドポイントが実装されています")
        else:
            print("❌ voice_input エンドポイントが見つかりません")
            return False

    # voice_service.pyの存在確認
    voice_service_path = project_root / "services" / "voice_service.py"
    if not voice_service_path.exists():
        print("❌ voice_service.py が見つかりません")
        return False
    else:
        print("✅ voice_service.py が存在します")

    return True

def test_frontend_integration():
    """フロントエンド統合をテスト"""
    print("🎨 フロントエンド統合をチェック中...")

    # HTMLテンプレートの確認
    template_path = project_root / "static" / "templates" / "top_page_template.html"
    if not template_path.exists():
        print("❌ top_page_template.html が見つかりません")
        return False

    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()

        # 音声ボタンの存在確認
        if 'voice-button' in content and 'toggleVoiceRecording' in content:
            print("✅ 音声入力ボタンが実装されています")
        else:
            print("❌ 音声入力ボタンが見つかりません")
            return False

        # JavaScript関数の存在確認
        required_functions = [
            'toggleVoiceRecording',
            'startVoiceRecording', 
            'stopVoiceRecording',
            'processVoiceInput'
        ]

        missing_functions = []
        for func in required_functions:
            if func not in content:
                missing_functions.append(func)

        if missing_functions:
            print(f"❌ 以下のJavaScript関数が見つかりません: {', '.join(missing_functions)}")
            return False
        else:
            print("✅ 必要なJavaScript関数が実装されています")

    # CSSファイルの確認
    css_path = project_root / "static" / "css" / "top_page_styles.css"
    if not css_path.exists():
        print("❌ top_page_styles.css が見つかりません")
        return False

    with open(css_path, 'r', encoding='utf-8') as f:
        content = f.read()
        if '.voice-button' in content:
            print("✅ 音声ボタンのCSSスタイルが実装されています")
        else:
            print("❌ 音声ボタンのCSSスタイルが見つかりません")
            return False

    return True

async def main():
    """メインテスト関数"""
    print("=" * 60)
    print("🎤 音声入力機能テストスクリプト")
    print("=" * 60)

    all_tests_passed = True

    # 環境設定テスト
    if not test_environment():
        all_tests_passed = False

    print()

    # API構造テスト
    if not test_api_structure():
        all_tests_passed = False

    print()

    # フロントエンド統合テスト
    if not test_frontend_integration():
        all_tests_passed = False

    print()

    # 音声サービステスト（環境が整っている場合のみ）
    if os.getenv("OPENAI_API_KEY"):
        if not await test_voice_service():
            all_tests_passed = False
    else:
        print("⚠️  OPENAI_API_KEY が設定されていないため、音声サービステストをスキップします")

    print()
    print("=" * 60)

    if all_tests_passed:
        print("✅ すべてのテストが成功しました！")
        print("🚀 音声入力機能の実装が完了しています")
        print()
        print("📋 使用方法:")
        print("1. .env ファイルに OPENAI_API_KEY を設定")
        print("2. アプリケーションを起動: python api/main.py")
        print("3. ブラウザでチャット画面を開く")
        print("4. 🎤 ボタンをクリックして音声入力を開始")
        print("5. もう一度クリックして録音を停止・処理")
    else:
        print("❌ 一部のテストが失敗しました")
        print("上記のエラーメッセージを確認して修正してください")

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
