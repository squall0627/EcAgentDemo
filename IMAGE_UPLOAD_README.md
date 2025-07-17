# 画像アップロード機能

このドキュメントでは、EcAgentDemoに新しく追加された画像アップロード機能について説明します。

## 概要

画像アップロード機能により、ユーザーは会話の中で画像をアップロードし、AIに画像の内容を分析させることができます。システムはOpenAIのGPT-4o Vision APIを使用して画像を解析し、その結果をユーザーのテキスト指示と組み合わせてLLMに送信します。

## 機能の流れ

1. **画像アップロード**: ユーザーが画像ファイルをアップロード
2. **画像分析**: OpenAI Vision APIが画像内容を分析
3. **メッセージマージ**: 画像分析結果とユーザーのテキスト指示を結合
4. **LLM処理**: マージされたメッセージをエージェントAPIに送信
5. **応答生成**: LLMが画像分析結果を踏まえた応答を生成

## 新しく追加されたファイル

### 1. `services/image_service.py`
画像処理を担当するサービスクラス。

**主な機能:**
- OpenAI Vision APIを使用した画像分析
- 複数の画像形式をサポート（JPG, PNG, GIF, WebP）
- Langfuse追跡対応
- 画像分析結果とユーザーテキストのマージ

**主要メソッド:**
- `analyze_image()`: 画像を分析してテキスト説明を生成
- `merge_image_analysis_with_text()`: 画像分析結果とユーザーテキストを結合
- `is_available()`: サービスの利用可能性をチェック
- `get_supported_formats()`: サポートされている画像形式を取得

### 2. `api/routers/chat_api.py` への追加
新しいエンドポイント `/image_input` を追加。

## API エンドポイント

### POST `/api/chat/image_input`

画像ファイルをアップロードして分析し、チャットワークフローに送信します。

**パラメータ:**
- `image_file` (ファイル, 必須): アップロードする画像ファイル
- `user_message` (文字列, オプション): ユーザーからの追加指示
- `session_id` (文字列, オプション): セッションID
- `user_id` (文字列, オプション): ユーザーID
- `agent_type` (文字列, オプション): エージェントタイプ（デフォルト: "default"）
- `llm_type` (文字列, オプション): LLMタイプ（デフォルト: "ollama"）
- `context` (文字列, オプション): コンテキスト情報

**レスポンス:**
```json
{
  "status": "success",
  "image_analysis": "画像分析結果のテキスト",
  "user_message": "ユーザーからのメッセージ",
  "merged_message": "マージされた最終メッセージ",
  "agent_response": "エージェントからの応答",
  "message": "画像入力が正常に処理されました"
}
```

## サポートされている画像形式

- JPG/JPEG
- PNG
- GIF
- WebP

## 設定要件

### 環境変数
`.env` ファイルに以下の設定が必要です：

```env
OPENAI_API_KEY=your_openai_api_key_here
```

### 依存関係
画像処理機能は以下のライブラリを使用します：
- `openai`: OpenAI API クライアント
- `base64`: 画像データのエンコーディング
- `fastapi`: ファイルアップロード処理

## 使用方法

### 1. サーバーの起動
```bash
cd /path/to/EcAgentDemo
python api/main.py
# または
uvicorn api.main:app --reload
```

### 2. 画像アップロードのテスト
```bash
python test_image_functionality.py
```

### 3. APIの使用例

**cURL を使用した例:**
```bash
curl -X POST "http://localhost:8000/api/chat/image_input" \
  -F "image_file=@/path/to/your/image.jpg" \
  -F "user_message=この画像について詳しく教えてください" \
  -F "session_id=test_session" \
  -F "user_id=test_user"
```

**Python requests を使用した例:**
```python
import requests

files = {'image_file': open('image.jpg', 'rb')}
data = {
    'user_message': 'この画像について教えてください',
    'session_id': 'my_session',
    'user_id': 'my_user'
}

response = requests.post(
    'http://localhost:8000/api/chat/image_input',
    files=files,
    data=data
)

print(response.json())
```

## エラーハンドリング

### よくあるエラー

1. **503 Service Unavailable**: OpenAI APIキーが設定されていない
   - 解決方法: `.env` ファイルに `OPENAI_API_KEY` を設定

2. **400 Bad Request**: サポートされていないファイル形式
   - 解決方法: JPG, PNG, GIF, WebP のいずれかの形式を使用

3. **400 Bad Request**: 画像から情報を抽出できない
   - 解決方法: より明確で読み取り可能な画像を使用

4. **504 Gateway Timeout**: エージェント応答がタイムアウト
   - 解決方法: しばらく待ってから再試行

## Langfuse 追跡

画像分析処理は Langfuse で追跡され、以下の情報が記録されます：
- 入力: モデル名、ファイル名、画像形式、画像サイズ、ユーザープロンプト
- 出力: 分析結果、結果の長さ
- メタデータ: セッションID、ユーザーID、サービス名、APIプロバイダー

## 技術的詳細

### 画像処理フロー
1. アップロードされた画像をバイト列として読み込み
2. Base64エンコーディングで画像データを変換
3. OpenAI Vision API（GPT-4o）に送信
4. 分析結果をテキストとして受信
5. ユーザーメッセージと結合してエージェントAPIに送信

### セキュリティ考慮事項
- ファイル形式の検証
- ファイルサイズの制限（OpenAI APIの制限に準拠）
- 適切なエラーハンドリング

## トラブルシューティング

### 画像分析が失敗する場合
1. OpenAI APIキーが正しく設定されているか確認
2. 画像ファイルが破損していないか確認
3. サポートされている形式かどうか確認
4. インターネット接続を確認

### パフォーマンスの最適化
- 大きな画像は事前にリサイズすることを推奨
- 高解像度画像は処理時間が長くなる可能性があります

## 今後の拡張予定

- 複数画像の同時アップロード対応
- 画像内テキストの OCR 機能強化
- ローカル画像処理モデルのサポート
- 画像履歴の保存機能

## 関連ファイル

- `services/image_service.py`: 画像処理サービス
- `api/routers/chat_api.py`: API エンドポイント
- `test_image_functionality.py`: テストスクリプト
- `services/voice_service.py`: 参考にした音声処理サービス