@echo off
chcp 65001 > nul
echo ========================================
echo    EcAgentDemo を起動しています...
echo ========================================
echo.
echo ✅ プログラムを開始中...
echo.
echo ⚠️  このウィンドウを閉じるとプログラムが終了します
echo    使用中はこのウィンドウを開いたままにしてください
echo.
echo ========================================

REM 実行可能ファイルのパスを決定
set EXECUTABLE=
if exist "EcAgentDemo\EcAgentDemo.exe" (
    set EXECUTABLE=EcAgentDemo\EcAgentDemo.exe
    echo 🔧 onedir形式の実行ファイルを検出しました
) else if exist "EcAgentDemo.exe" (
    set EXECUTABLE=EcAgentDemo.exe
    echo 🔧 単一実行ファイルを検出しました
) else (
    echo ❌ 実行可能ファイルが見つかりません
    echo    以下のいずれかが存在することを確認してください：
    echo    - EcAgentDemo\EcAgentDemo.exe ^(onedir形式^)
    echo    - EcAgentDemo.exe ^(単一実行ファイル^)
    echo.
    echo ========================================
    pause
    exit /b 1
)

REM プログラムを実行
echo 🚀 実行中: %EXECUTABLE%
"%EXECUTABLE%"

echo.
echo ========================================
echo    プログラムが終了しました
echo ========================================
pause
