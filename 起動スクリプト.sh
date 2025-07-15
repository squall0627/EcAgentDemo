#!/bin/bash

echo "========================================"
echo "    EcAgentDemo を起動しています..."
echo "========================================"
echo ""
echo "✅ プログラムを開始中..."
echo ""
echo "⚠️  このターミナルを閉じるとプログラムが終了します"
echo "    使用中はこのターミナルを開いたままにしてください"
echo ""
echo "========================================"

# 実行可能ファイルのパスを決定
EXECUTABLE=""
if [ -x "./EcAgentDemo/EcAgentDemo" ]; then
    # onedir形式の実行ファイル
    EXECUTABLE="./EcAgentDemo/EcAgentDemo"
    echo "🔧 onedir形式の実行ファイルを検出しました"
elif [ -x "./EcAgentDemo.app/Contents/MacOS/EcAgentDemo" ]; then
    # macOS app bundle形式の実行ファイル
    EXECUTABLE="./EcAgentDemo.app/Contents/MacOS/EcAgentDemo"
    echo "🔧 macOS app bundle形式の実行ファイルを検出しました"
elif [ -x "./EcAgentDemo" ]; then
    # 単一実行ファイル（Linux等）
    EXECUTABLE="./EcAgentDemo"
    echo "🔧 単一実行ファイルを検出しました"
else
    echo "❌ 実行可能ファイルが見つかりません"
    echo "   以下のいずれかが存在することを確認してください："
    echo "   - ./EcAgentDemo/EcAgentDemo (onedir形式)"
    echo "   - ./EcAgentDemo.app/Contents/MacOS/EcAgentDemo (macOS app bundle)"
    echo "   - ./EcAgentDemo (単一実行ファイル)"
    exit 1
fi

# 実行権限を確認・設定
if [ ! -x "$EXECUTABLE" ]; then
    echo "🔧 実行権限を設定中..."
    chmod +x "$EXECUTABLE"
fi

# プログラムを実行
echo "🚀 実行中: $EXECUTABLE"
"$EXECUTABLE"

echo ""
echo "========================================"
echo "    プログラムが終了しました"
echo "========================================"
echo "何かキーを押してください..."
read -n 1
