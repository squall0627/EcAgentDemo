from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json

router = APIRouter()

class HtmlGenerateRequest(BaseModel):
    page_type: str
    data: Optional[Dict[str, Any]]

class HtmlGenerateResponse(BaseModel):
    success: bool
    page_type: str
    html_content: str
    error: str = None

@router.post("/generate-page", response_model=HtmlGenerateResponse)
async def generate_html_page(request: HtmlGenerateRequest):
    """動的HTML画面生成 - JSON応答"""
    try:
        html_templates = {
            "product_list": _generate_product_list_html,
            "category_form": _generate_category_form_html,
            "stock_form": _generate_stock_form_html,
            "error_page": _generate_error_page_html
        }
        
        if request.page_type not in html_templates:
            return HtmlGenerateResponse(
                success=False,
                page_type=request.page_type,
                html_content="",
                error=f"未対応のページタイプ: {request.page_type}"
            )
        
        html_content = html_templates[request.page_type](request.data)
        
        return HtmlGenerateResponse(
            success=True,
            page_type=request.page_type,
            html_content=html_content
        )
        
    except Exception as e:
        return HtmlGenerateResponse(
            success=False,
            page_type=request.page_type,
            html_content="",
            error=f"HTML生成エラー: {str(e)}"
        )

@router.get("/generate-page-html/{page_type}", response_class=HTMLResponse)
async def generate_html_page_direct(page_type: str, data: str = "{}"):
    """動的HTML画面生成 - 直接HTML応答"""
    try:
        data_dict = json.loads(data)
        request = HtmlGenerateRequest(page_type=page_type, data=data_dict)
        response = await generate_html_page(request)
        
        if response.success:
            return HTMLResponse(content=response.html_content)
        else:
            raise HTTPException(status_code=400, detail=response.error)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HTML生成エラー: {str(e)}")

# HTML生成関数（これらは内部関数として使用）
def _generate_product_list_html(data: Dict[str, Any]) -> str:
    products = data.get("products", [])
    
    html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>商品管理 - 検索結果</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #f2f2f2; }
            .btn { padding: 5px 10px; margin: 2px; border: none; cursor: pointer; }
            .btn-publish { background-color: #4CAF50; color: white; }
            .btn-unpublish { background-color: #f44336; color: white; }
            .btn-edit { background-color: #008CBA; color: white; }
            .status-published { color: #4CAF50; font-weight: bold; }
            .status-unpublished { color: #f44336; font-weight: bold; }
            .error { color: #f44336; font-size: 12px; }
        </style>
    </head>
    <body>
        <h2>商品管理 - 検索結果</h2>
        <table>
            <thead>
                <tr>
                    <th>JANコード</th>
                    <th>商品名</th>
                    <th>カテゴリー</th>
                    <th>在庫</th>
                    <th>ステータス</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for product in products:
        status_class = "status-published" if product.get("status") == "published" else "status-unpublished"
        status_text = "公開中" if product.get("status") == "published" else "非公開"
        
        # 上架前提条件チェック
        can_publish = bool(product.get("category")) and product.get("stock", 0) > 0
        publish_disabled = "" if can_publish else "disabled"
        
        error_messages = []
        if not product.get("category"):
            error_messages.append("カテゴリー未設定")
        if product.get("stock", 0) <= 0:
            error_messages.append("在庫不足")
        
        error_html = f"<br><span class='error'>{', '.join(error_messages)}</span>" if error_messages else ""
        
        html += f"""
                <tr>
                    <td>{product.get('jancode', '')}</td>
                    <td>{product.get('name_jp', '')}</td>
                    <td>{product.get('category', '未設定')}</td>
                    <td>{product.get('stock', 0)}</td>
                    <td class="{status_class}">{status_text}{error_html}</td>
                    <td>
                        <button class="btn btn-publish" {publish_disabled} onclick="executeCommand('JANコード{product.get('jancode')}の商品を棚上げしてください')">上架</button>
                        <button class="btn btn-unpublish" onclick="executeCommand('JANコード{product.get('jancode')}の商品を棚下げしてください')">下架</button>
                        <button class="btn btn-edit" onclick="executeCommand('JANコード{product.get('jancode')}の商品のカテゴリーを設定してください')">カテゴリー</button>
                        <button class="btn btn-edit" onclick="executeCommand('JANコード{product.get('jancode')}の商品の在庫を更新してください')">在庫</button>
                    </td>
                </tr>
        """
    
    html += """
            </tbody>
        </table>
        
        <script>
            function executeCommand(command) {
                if (confirm('この操作を実行しますか？\\n' + command)) {
                    // 実際の実装では、ここでエージェントAPIにコマンドを送信
                    fetch('/api/agent/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: command })
                    })
                    .then(response => response.json())
                    .then(data => {
                        alert('実行結果: ' + data.response);
                        location.reload(); // ページを再読み込み
                    })
                    .catch(error => {
                        alert('エラー: ' + error.message);
                    });
                }
            }
        </script>
    </body>
    </html>
    """
    
    return html

def _generate_category_form_html(data: Dict[str, Any]) -> str:
    product = data.get("product", {})
    categories = ["飲料", "お菓子", "冷凍食品", "日用品", "その他"]

    html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>カテゴリー設定 - {product.get('name_jp', '')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .form-group {{ margin: 15px 0; }}
                .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                .form-group select, .form-group input {{ width: 300px; padding: 8px; }}
                .btn {{ padding: 10px 20px; margin: 10px 5px; border: none; cursor: pointer; }}
                .btn-primary {{ background-color: #007bff; color: white; }}
                .btn-secondary {{ background-color: #6c757d; color: white; }}
                .product-info {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            </style>
        </head>
        <body>
            <h2>商品カテゴリー設定</h2>
            
            <div class="product-info">
                <h3>商品情報</h3>
                <p><strong>JANコード:</strong> {product.get('jancode', '')}</p>
                <p><strong>商品名:</strong> {product.get('name_jp', '')}</p>
                <p><strong>現在のカテゴリー:</strong> {product.get('category', '未設定')}</p>
            </div>
            
            <form id="categoryForm">
                <div class="form-group">
                    <label for="category">新しいカテゴリー:</label>
                    <select id="category" name="category">
                        <option value="">カテゴリーを選択してください</option>
        """

    for cat in categories:
        selected = "selected" if cat == product.get('category') else ""
        html += f'<option value="{cat}" {selected}>{cat}</option>'

    html += f"""
                    </select>
                </div>
                
                <div class="form-group">
                    <label for="custom_category">または新しいカテゴリーを入力:</label>
                    <input type="text" id="custom_category" name="custom_category" placeholder="新しいカテゴリー名">
                </div>
                
                <button type="submit" class="btn btn-primary">保存</button>
                <button type="button" class="btn btn-secondary" onclick="history.back()">キャンセル</button>
            </form>
            
            <script>
                document.getElementById('categoryForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    const category = document.getElementById('category').value || document.getElementById('custom_category').value;
                    if (!category) {{
                        alert('カテゴリーを選択または入力してください');
                        return;
                    }}
                    
                    // 自然言語コマンドとして送信
                    const command = `JANコード{product.get('jancode')}の商品のカテゴリーを${{category}}に設定してください`;
                    alert('コマンド送信: ' + command);
                    // 実際の実装では、ここでエージェントにコマンドを送信
                }});
            </script>
        </body>
        </html>
        """

    return html

def _generate_stock_form_html(data: Dict[str, Any]) -> str:
    product = data.get("product", {})

    html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>在庫管理 - {product.get('name_jp', '')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .form-group {{ margin: 15px 0; }}
                .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                .form-group input {{ width: 200px; padding: 8px; }}
                .btn {{ padding: 10px 20px; margin: 10px 5px; border: none; cursor: pointer; }}
                .btn-primary {{ background-color: #007bff; color: white; }}
                .btn-success {{ background-color: #28a745; color: white; }}
                .btn-secondary {{ background-color: #6c757d; color: white; }}
                .product-info {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .quick-actions {{ margin: 20px 0; }}
                .quick-actions button {{ margin: 5px; }}
            </style>
        </head>
        <body>
            <h2>商品在庫管理</h2>
            
            <div class="product-info">
                <h3>商品情報</h3>
                <p><strong>JANコード:</strong> {product.get('jancode', '')}</p>
                <p><strong>商品名:</strong> {product.get('name_jp', '')}</p>
                <p><strong>現在の在庫:</strong> {product.get('stock', 0)}</p>
            </div>
            
            <form id="stockForm">
                <div class="form-group">
                    <label for="stock">新しい在庫数:</label>
                    <input type="number" id="stock" name="stock" min="0" value="{product.get('stock', 0)}">
                </div>
                
                <button type="submit" class="btn btn-primary">在庫更新</button>
                <button type="button" class="btn btn-secondary" onclick="history.back()">キャンセル</button>
            </form>
            
            <div class="quick-actions">
                <h4>クイックアクション:</h4>
                <button class="btn btn-success" onclick="setStock(50)">50に設定</button>
                <button class="btn btn-success" onclick="setStock(100)">100に設定</button>
                <button class="btn btn-success" onclick="addStock(10)">+10追加</button>
                <button class="btn btn-success" onclick="addStock(50)">+50追加</button>
            </div>
            
            <script>
                function setStock(amount) {{
                    document.getElementById('stock').value = amount;
                }}
                
                function addStock(amount) {{
                    const current = parseInt(document.getElementById('stock').value) || 0;
                    document.getElementById('stock').value = current + amount;
                }}
                
                document.getElementById('stockForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    const stock = document.getElementById('stock').value;
                    if (!stock || stock < 0) {{
                        alert('有効な在庫数を入力してください');
                        return;
                    }}
                    
                    // 自然言語コマンドとして送信
                    const command = `JANコード{product.get('jancode')}の商品の在庫を${{stock}}に設定してください`;
                    alert('コマンド送信: ' + command);
                    // 実際の実装では、ここでエージェントにコマンドを送信
                }});
            </script>
        </body>
        </html>
        """

    return html

def _generate_error_page_html(data: Dict[str, Any]) -> str:
    error_message = data.get("error", "エラーが発生しました")
    suggestions = data.get("suggestions", [])

    html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>エラー - 商品管理</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .error-container {{ background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 20px; border-radius: 5px; }}
                .error-message {{ color: #721c24; font-size: 18px; margin-bottom: 15px; }}
                .suggestions {{ margin-top: 20px; }}
                .suggestions ul {{ list-style-type: disc; margin-left: 20px; }}
                .btn {{ padding: 10px 20px; margin: 5px; border: none; cursor: pointer; background-color: #007bff; color: white; }}
            </style>
        </head>
        <body>
            <div class="error-container">
                <div class="error-message">⚠️ {error_message}</div>
                
                <div class="suggestions">
                    <h4>解決方法:</h4>
                    <ul>
        """

    for suggestion in suggestions:
        html += f"<li>{suggestion}</li>"

    html += """
                    </ul>
                </div>
                
                <button class="btn" onclick="history.back()">戻る</button>
            </div>
        </body>
        </html>
        """

    return html

@router.get("/management-interface", response_class=HTMLResponse)
async def get_management_interface():
    """商品管理メインインターフェース"""
    html = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EC商品管理システム</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .chat-interface { background: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .chat-input { width: 70%; padding: 10px; font-size: 16px; }
            .chat-submit { padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; }
            .result-area { min-height: 400px; border: 1px solid #ddd; padding: 20px; background: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>EC商品管理システム</h1>
            
            <div class="chat-interface">
                <h3>自然言語コマンド入力</h3>
                <input type="text" id="commandInput" class="chat-input" placeholder="例: コーヒー商品を検索して棚上げ可能か確認してください">
                <button class="chat-submit" onclick="executeCommand()">実行</button>
                
                <div style="margin-top: 10px; font-size: 14px; color: #666;">
                    <strong>使用例:</strong><br>
                    • "コーヒー商品を検索してください"<br>
                    • "在庫が少ない商品を棚上げしてください"<br>
                    • "JANコード123の商品のカテゴリーを設定してください"
                </div>
            </div>
            
            <div id="resultArea" class="result-area">
                <p>コマンドを入力してください。システムが自動的に適切な操作画面を生成します。</p>
            </div>
        </div>
        
        <script>
            async function executeCommand() {
                const command = document.getElementById('commandInput').value;
                if (!command.trim()) {
                    alert('コマンドを入力してください');
                    return;
                }
                
                try {
                    const response = await fetch('/api/agent/chat', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ message: command })
                    });
                    
                    const result = await response.json();
                    
                    // HTMLコンテンツがある場合は表示、そうでなければテキスト応答を表示
                    if (result.html_content) {
                        document.getElementById('resultArea').innerHTML = result.html_content;
                    } else {
                        document.getElementById('resultArea').innerHTML = '<pre>' + result.response + '</pre>';
                    }
                    
                    document.getElementById('commandInput').value = '';
                    
                } catch (error) {
                    console.error('Error:', error);
                    alert('エラーが発生しました: ' + error.message);
                }
            }
            
            // Enterキーでコマンド実行
            document.getElementById('commandInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    executeCommand();
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)