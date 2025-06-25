from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json

from config.llm_config_loader import llm_config

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
            "price_form": _generate_price_form_html,
            "description_form": _generate_description_form_html,
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
            .price { font-weight: bold; color: #007bff; }
            .description { max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
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
                    <th>価格</th>
                    <th>在庫</th>
                    <th>商品説明</th>
                    <th>ステータス</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
    """

    for product in products:
        status_class = "status-published" if product.get("status") == "published" else "status-unpublished"
        status_text = "公開中" if product.get("status") == "published" else "非公開"
        
        # 価格表示（デフォルト値として0を設定）
        price = product.get("price", 0)
        price_display = f"¥{price:,.0f}" if price is not None else "¥0"
        
        # 商品説明表示（長い場合は省略）
        description = product.get("description", "")
        description_display = description[:50] + "..." if len(description) > 50 else description

        # 棚上げ前提条件チェック
        can_publish = (bool(product.get("category")) and 
                      product.get("stock", 0) > 0 and 
                      product.get("price", 0) > 0)
        publish_disabled = "" if can_publish else "disabled"

        error_messages = []
        if not product.get("category"):
            error_messages.append("カテゴリー未設定")
        if product.get("stock", 0) <= 0:
            error_messages.append("在庫不足")
        if product.get("price", 0) <= 0:
            error_messages.append("価格未設定")

        error_html = f"<br><span class='error'>{', '.join(error_messages)}</span>" if error_messages else ""

        html += f"""
                <tr>
                    <td>{product.get('jancode', '')}</td>
                    <td>{product.get('name_jp', '')}</td>
                    <td>{product.get('category', '未設定')}</td>
                    <td class="price">{price_display}</td>
                    <td>{product.get('stock', 0)}</td>
                    <td class="description" title="{description}">{description_display or '未設定'}</td>
                    <td class="{status_class}">{status_text}{error_html}</td>
                    <td>
                        <button class="btn btn-publish" {publish_disabled} onclick="executeCommand('JANコード{product.get('jancode')}の商品を棚上げしてください')">上架</button>
                        <button class="btn btn-unpublish" onclick="executeCommand('JANコード{product.get('jancode')}の商品を棚下げしてください')">下架</button>
                        <button class="btn btn-edit" onclick="executeCommand('JANコード{product.get('jancode')}の商品のカテゴリーを設定してください')">カテゴリー</button>
                        <button class="btn btn-edit" onclick="executeCommand('JANコード{product.get('jancode')}の商品の在庫を更新してください')">在庫</button>
                        <button class="btn btn-edit" onclick="executeCommand('JANコード{product.get('jancode')}の商品の価格を設定してください')">価格</button>
                        <button class="btn btn-edit" onclick="executeCommand('JANコード{product.get('jancode')}の商品の説明を設定してください')">説明</button>
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

def _generate_price_form_html(data: Dict[str, Any]) -> str:
    product = data.get("product", {})
    current_price = product.get("price", 0)

    html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>価格設定 - {product.get('name_jp', '')}</title>
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
                .price-display {{ font-size: 18px; font-weight: bold; color: #007bff; margin: 10px 0; }}
                .currency {{ color: #666; }}
            </style>
        </head>
        <body>
            <h2>商品価格設定</h2>
            
            <div class="product-info">
                <h3>商品情報</h3>
                <p><strong>JANコード:</strong> {product.get('jancode', '')}</p>
                <p><strong>商品名:</strong> {product.get('name_jp', '')}</p>
                <p><strong>現在の価格:</strong> <span class="price-display">¥{current_price:,.0f}</span></p>
            </div>
            
            <form id="priceForm">
                <div class="form-group">
                    <label for="price">新しい価格 <span class="currency">(円)</span>:</label>
                    <input type="number" id="price" name="price" min="0" step="1" value="{current_price}" placeholder="価格を入力">
                </div>
                
                <button type="submit" class="btn btn-primary">価格更新</button>
                <button type="button" class="btn btn-secondary" onclick="history.back()">キャンセル</button>
            </form>
            
            <div class="quick-actions">
                <h4>クイック価格設定:</h4>
                <button class="btn btn-success" onclick="setPrice(100)">¥100</button>
                <button class="btn btn-success" onclick="setPrice(200)">¥200</button>
                <button class="btn btn-success" onclick="setPrice(300)">¥300</button>
                <button class="btn btn-success" onclick="setPrice(500)">¥500</button>
                <button class="btn btn-success" onclick="setPrice(1000)">¥1,000</button>
                <button class="btn btn-success" onclick="setPrice(2000)">¥2,000</button>
                <button class="btn btn-success" onclick="setPrice(3000)">¥3,000</button>
            </div>
            
            <script>
                function setPrice(amount) {{
                    document.getElementById('price').value = amount;
                    updatePriceDisplay(amount);
                }}
                
                function updatePriceDisplay(price) {{
                    const priceDisplay = document.querySelector('.price-display');
                    if (priceDisplay) {{
                        priceDisplay.textContent = '¥' + price.toLocaleString();
                    }}
                }}
                
                // リアルタイム価格表示更新
                document.getElementById('price').addEventListener('input', function(e) {{
                    const price = parseInt(e.target.value) || 0;
                    updatePriceDisplay(price);
                }});
                
                document.getElementById('priceForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    const price = document.getElementById('price').value;
                    if (!price || price < 0) {{
                        alert('有効な価格を入力してください');
                        return;
                    }}
                    
                    // 自然言語コマンドとして送信
                    const command = `JANコード{product.get('jancode')}の商品の価格を${{price}}円に設定してください`;
                    alert('コマンド送信: ' + command);
                    // 実際の実装では、ここでエージェントにコマンドを送信
                }});
            </script>
        </body>
        </html>
        """

    return html

def _generate_description_form_html(data: Dict[str, Any]) -> str:
    product = data.get("product", {})
    current_description = product.get("description", "")

    html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>商品説明設定 - {product.get('name_jp', '')}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .form-group {{ margin: 15px 0; }}
                .form-group label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
                .form-group textarea {{ width: 100%; max-width: 600px; padding: 8px; }}
                .btn {{ padding: 10px 20px; margin: 10px 5px; border: none; cursor: pointer; }}
                .btn-primary {{ background-color: #007bff; color: white; }}
                .btn-success {{ background-color: #28a745; color: white; }}
                .btn-secondary {{ background-color: #6c757d; color: white; }}
                .product-info {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .template-actions {{ margin: 20px 0; }}
                .template-actions button {{ margin: 5px; }}
                .char-counter {{ font-size: 12px; color: #666; margin-top: 5px; }}
                .current-description {{ background-color: #e7f3ff; padding: 10px; border-radius: 5px; margin: 10px 0; max-height: 100px; overflow-y: auto; }}
            </style>
        </head>
        <body>
            <h2>商品説明設定</h2>
            
            <div class="product-info">
                <h3>商品情報</h3>
                <p><strong>JANコード:</strong> {product.get('jancode', '')}</p>
                <p><strong>商品名:</strong> {product.get('name_jp', '')}</p>
                <p><strong>カテゴリー:</strong> {product.get('category', '未設定')}</p>
                <p><strong>価格:</strong> ¥{product.get('price', 0):,.0f}</p>
            </div>
            
            {'<div class="current-description"><strong>現在の説明:</strong><br>' + current_description + '</div>' if current_description else ''}
            
            <form id="descriptionForm">
                <div class="form-group">
                    <label for="description">商品説明:</label>
                    <textarea id="description" name="description" rows="6" maxlength="1000" placeholder="商品の詳しい説明を入力してください...">{current_description}</textarea>
                    <div class="char-counter">
                        <span id="charCount">{len(current_description)}</span>/1000文字
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary">説明更新</button>
                <button type="button" class="btn btn-secondary" onclick="history.back()">キャンセル</button>
            </form>
            
            <div class="template-actions">
                <h4>テンプレート:</h4>
                <button class="btn btn-success" onclick="setTemplate('basic')">基本テンプレート</button>
                <button class="btn btn-success" onclick="setTemplate('detailed')">詳細テンプレート</button>
                <button class="btn btn-success" onclick="setTemplate('clear')">クリア</button>
            </div>
            
            <script>
                const templates = {{
                    'basic': '高品質な{{商品名}}です。\\n\\n【特徴】\\n- \\n- \\n- \\n\\n【使用方法】\\n\\n\\n【注意事項】\\n',
                    'detailed': '【商品名】\\n{{商品名}}\\n\\n【商品説明】\\n\\n\\n【特徴・魅力】\\n- \\n- \\n- \\n\\n【仕様】\\n- サイズ: \\n- 重量: \\n- 材質: \\n\\n【使用方法】\\n\\n\\n【保存方法・注意事項】\\n\\n\\n【原産国】\\n'
                }};
                
                function setTemplate(type) {{
                    const textarea = document.getElementById('description');
                    if (type === 'clear') {{
                        textarea.value = '';
                    }} else if (templates[type]) {{
                        const productName = '{product.get('name_jp', '')}';
                        let template = templates[type].replace(/{{{{商品名}}}}/g, productName);
                        textarea.value = template;
                    }}
                    updateCharCount();
                }}
                
                function updateCharCount() {{
                    const textarea = document.getElementById('description');
                    const charCount = document.getElementById('charCount');
                    charCount.textContent = textarea.value.length;
                }}
                
                // 文字数カウンターの更新
                document.getElementById('description').addEventListener('input', updateCharCount);
                
                document.getElementById('descriptionForm').addEventListener('submit', function(e) {{
                    e.preventDefault();
                    const description = document.getElementById('description').value.trim();
                    
                    if (description.length > 1000) {{
                        alert('商品説明は1000文字以内で入力してください');
                        return;
                    }}
                    
                    // 自然言語コマンドとして送信
                    const command = `JANコード{product.get('jancode')}の商品の説明を「${{description}}」に設定してください`;
                    
                    if (confirm('商品説明を更新しますか？')) {{
                        alert('コマンド送信: ' + command);
                        // 実際の実装では、ここでエージェントにコマンドを送信
                    }}
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
    """商品管理メインインターフェース - 設定ファイルベース"""
    
    # 設定ファイルからLLM設定を取得
    llm_models = llm_config.get_all_models()
    default_model = llm_config.get_default_model()
    
    # 選択肢の生成
    llm_options = ""
    for model_config in llm_models:
        selected = 'selected' if model_config["value"] == default_model else ''
        llm_options += f'''<option value="{model_config["value"]}" 
                         data-provider="{model_config["provider"]}" 
                         data-model="{model_config["model"]}" 
                         data-color="{model_config["color"]}"
                         data-description="{model_config.get("description", "")}" 
                         {selected}>{model_config["label"]}</option>\n'''
    
    # JavaScript用の設定
    llm_js_config = llm_config.get_frontend_config()
    
    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>EC商品管理システム</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .chat-interface {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .input-row {{ display: flex; gap: 10px; align-items: center; margin-bottom: 15px; }}
            .chat-input {{ flex: 1; padding: 12px; font-size: 16px; border: 2px solid #e1e5e9; border-radius: 6px; transition: border-color 0.3s; }}
            .chat-input:focus {{ outline: none; border-color: #007bff; }}
            .llm-select {{ padding: 12px; font-size: 14px; background: white; border: 2px solid #e1e5e9; border-radius: 6px; min-width: 300px; cursor: pointer; }}
            .llm-select:focus {{ outline: none; border-color: #007bff; }}
            .chat-submit {{ padding: 12px 24px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 6px; font-weight: 600; transition: background-color 0.3s; }}
            .chat-submit:hover {{ background: #0056b3; }}
            .chat-submit:disabled {{ background: #6c757d; cursor: not-allowed; }}
            .result-area {{ min-height: 500px; border: 2px solid #e1e5e9; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .llm-status {{ display: flex; align-items: center; gap: 8px; font-size: 13px; color: #666; margin-top: 8px; padding: 8px 12px; background: #f8f9fa; border-radius: 4px; }}
            .llm-indicator {{ width: 10px; height: 10px; border-radius: 50%; }}
            .ollama {{ background-color: #10b981; }}
            .openai {{ background-color: #3b82f6; }}
            .anthropic {{ background-color: #8b5cf6; }}
            .loading {{ text-align: center; padding: 60px 20px; }}
            .error {{ background: #ffe6e6; border: 2px solid #ff9999; padding: 20px; border-radius: 6px; color: #cc0000; }}
            .llm-info {{ background: #e7f3ff; border: 2px solid #3b82f6; padding: 15px; border-radius: 6px; margin-bottom: 20px; font-size: 14px; }}
            .examples {{ background: #f8f9fa; padding: 15px; border-radius: 6px; margin-top: 15px; }}
            .examples strong {{ color: #495057; }}
            .examples ul {{ margin: 8px 0; padding-left: 20px; }}
            .examples li {{ margin: 4px 0; color: #6c757d; }}
            .spinner {{ width: 40px; height: 40px; border: 4px solid #f3f3f3; border-top: 4px solid #007bff; border-radius: 50%; animation: spin 1s linear infinite; margin: 0 auto; }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .config-info {{ font-size: 12px; color: #999; text-align: right; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; color: #343a40;">🤖 EC商品管理システム</h1>
                <p style="margin: 10px 0 0 0; color: #6c757d;">自然言語でAIエージェントと対話して商品を管理できます</p>
            </div>
            
            <div class="chat-interface">
                <h3 style="margin-top: 0; color: #495057;">💬 自然言語コマンド入力</h3>
                
                <div class="input-row">
                    <select id="llmSelect" class="llm-select" title="使用するLLMモデルを選択">
                        {llm_options}
                    </select>
                    <input type="text" id="commandInput" class="chat-input" 
                           placeholder="例: コーヒー商品を検索して棚上げ可能か確認してください"
                           maxlength="500">
                    <button id="submitBtn" class="chat-submit" onclick="executeCommand()">実行</button>
                </div>
                
                <div class="llm-status">
                    <span class="llm-indicator" id="llmIndicator"></span>
                    <span id="llmStatus">LLM読み込み中...</span>
                    <span id="llmDescription" style="color: #999; font-style: italic;"></span>
                </div>
                
                <div class="examples">
                    <strong>💡 使用例:</strong>
                    <ul>
                        <li>"コーヒー商品を検索してください"</li>
                        <li>"在庫が少ない商品を棚上げしてください"</li>
                        <li>"JANコード123の商品のカテゴリーを設定してください"</li>
                        <li>"未分類の商品をすべて表示してください"</li>
                    </ul>
                </div>
                
                <div class="config-info">
                    ⚙️ LLM設定は config/llm_config.json で管理されています
                </div>
            </div>
            
            <div id="resultArea" class="result-area">
                <div style="text-align: center; padding: 40px; color: #6c757d;">
                    <h4>👋 ようこそ！</h4>
                    <p>上記の入力欄にコマンドを入力してください。<br>
                    システムが自動的に適切な操作画面を生成します。</p>
                </div>
            </div>
        </div>
        
        <script>
            // LLM設定（設定ファイルから読み込み）
            const llmConfigs = {llm_js_config};
            
            // LLM選択時の状態更新
            document.getElementById('llmSelect').addEventListener('change', function() {{
                updateLLMStatus();
            }});
            
            function updateLLMStatus() {{
                const selectedValue = document.getElementById('llmSelect').value;
                const selectedOption = document.getElementById('llmSelect').options[document.getElementById('llmSelect').selectedIndex];
                
                const provider = selectedOption.getAttribute('data-provider');
                const model = selectedOption.getAttribute('data-model');
                const color = selectedOption.getAttribute('data-color');
                const description = selectedOption.getAttribute('data-description');
                
                const indicator = document.getElementById('llmIndicator');
                const status = document.getElementById('llmStatus');
                const descElement = document.getElementById('llmDescription');
                
                indicator.className = `llm-indicator ${{color}}`;
                status.textContent = `現在のLLM: ${{selectedOption.textContent.replace(/^[🦙🤖🧠]\\s*/, '')}}`;
                descElement.textContent = description ? `- ${{description}}` : '';
            }}
            
            async function executeCommand() {{
                const command = document.getElementById('commandInput').value;
                const selectedLLM = document.getElementById('llmSelect').value;
                const selectedOption = document.getElementById('llmSelect').options[document.getElementById('llmSelect').selectedIndex];
                
                if (!command.trim()) {{
                    alert('コマンドを入力してください');
                    return;
                }}
                
                // ボタンを無効化
                const submitBtn = document.getElementById('submitBtn');
                const originalText = submitBtn.textContent;
                submitBtn.disabled = true;
                submitBtn.textContent = '処理中...';
                
                // 実行中の状態を表示
                document.getElementById('resultArea').innerHTML = `
                    <div class="loading">
                        <h4 style="margin-bottom: 15px;">🔄 処理中...</h4>
                        <div style="font-size: 16px; color: #495057; margin-bottom: 8px;">LLM: ${{selectedOption.textContent}}</div>
                        <div style="font-size: 14px; color: #6c757d; margin-bottom: 30px;">コマンド: "${{command}}"</div>
                        <div class="spinner"></div>
                        <div style="margin-top: 20px; font-size: 14px; color: #999;">
                            AIが応答を生成中です...
                        </div>
                    </div>
                `;
                
                try {{
                    const response = await fetch('/api/agent/chat', {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ 
                            message: command,
                            llm_type: selectedLLM
                        }})
                    }});
                    
                    if (!response.ok) {{
                        throw new Error(`HTTP error! status: ${{response.status}}`);
                    }}
                    
                    const result = await response.json();
                    
                    // 結果を表示
                    let resultHTML = '';
                    
                    // LLM使用情報を表示
                    if (result.llm_type_used) {{
                        const usedConfig = llmConfigs.find(config => config.value === result.llm_type_used);
                        const llmInfo = usedConfig ? usedConfig.label : result.llm_type_used;
                        resultHTML += `<div class="llm-info">
                            <strong>🤖 使用されたLLM:</strong> ${{llmInfo}}
                            ${{result.llm_info && result.llm_info.description ? `<br><small>${{result.llm_info.description}}</small>` : ''}}
                        </div>`;
                    }}
                    
                    // HTMLコンテンツがある場合は表示、そうでなければテキスト応答を表示
                    if (result.html_content) {{
                        resultHTML += result.html_content;
                    }} else {{
                        resultHTML += `<div style="padding: 20px; background: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef;">
                            <pre style="white-space: pre-wrap; font-family: inherit; margin: 0; line-height: 1.6;">${{result.response}}</pre>
                        </div>`;
                    }}
                    
                    document.getElementById('resultArea').innerHTML = resultHTML;
                    document.getElementById('commandInput').value = '';
                    
                }} catch (error) {{
                    console.error('Error:', error);
                    document.getElementById('resultArea').innerHTML = `
                        <div class="error">
                            <h4 style="margin-top: 0;">❌ エラーが発生しました</h4>
                            <p><strong>詳細:</strong> ${{error.message}}</p>
                            <p style="margin-bottom: 0; font-size: 14px;">ネットワーク接続やサーバーの状態を確認してください。</p>
                        </div>
                    `;
                }} finally {{
                    // ボタンを再有効化
                    submitBtn.disabled = false;
                    submitBtn.textContent = originalText;
                }}
            }}
            
            // Enterキーでコマンド実行
            document.getElementById('commandInput').addEventListener('keypress', function(e) {{
                if (e.key === 'Enter' && !document.getElementById('submitBtn').disabled) {{
                    executeCommand();
                }}
            }});
            
            // 初期状態の設定
            updateLLMStatus();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)

@router.get("/llm-config")
async def get_llm_config():
    """LLM設定情報を取得するAPI"""
    return {
        "models": llm_config.get_all_models(),
        "default_model": llm_config.get_default_model(),
        "provider_settings": llm_config._config_cache.get("provider_settings", {})
    }

@router.post("/llm-config/reload")
async def reload_llm_config():
    """LLM設定を再読み込み"""
    llm_config.reload_config()
    return {"message": "LLM設定が再読み込みされました"}