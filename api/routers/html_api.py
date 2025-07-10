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

    html = """<!DOCTYPE html>
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
        .btn-edit-category { background-color: #FF9800; color: white; }
        .btn-edit-inventory { background-color: #9C27B0; color: white; }
        .btn-edit-price { background-color: #2196F3; color: white; }
        .btn-edit-description { background-color: #607D8B; color: white; }
        .status-published { color: #4CAF50; font-weight: bold; }
        .status-unpublished { color: #f44336; font-weight: bold; }
        .error { color: #f44336; font-size: 12px; }
        .price { font-weight: bold; color: #007bff; }
        .description { max-width: 200px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        
        /* Modal styles */
        .modal {
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.4);
        }
        .modal-content {
            background-color: #fefefe;
            margin: 15% auto;
            padding: 20px;
            border: 1px solid #888;
            border-radius: 5px;
            width: 400px;
            max-width: 90%;
        }
        .modal-header {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
            color: #333;
        }
        .modal-input {
            width: 100%;
            padding: 8px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 14px;
        }
        .modal-textarea {
            width: 100%;
            padding: 8px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 3px;
            font-size: 14px;
            min-height: 80px;
            resize: vertical;
        }
        .modal-buttons {
            text-align: right;
            margin-top: 15px;
        }
        .modal-btn {
            padding: 8px 16px;
            margin-left: 10px;
            border: none;
            border-radius: 3px;
            cursor: pointer;
            font-size: 14px;
        }
        .modal-btn-primary {
            background-color: #007bff;
            color: white;
        }
        .modal-btn-secondary {
            background-color: #6c757d;
            color: white;
        }
        .modal-btn:hover {
            opacity: 0.8;
        }
        .modal-label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
    </style>
    <script>
        // Define executeCommand function globally in head to ensure it's available before buttons
        window.executeCommand = function(command) {
            try {
                // トップページの対話框にコマンドをコピー
                let targetWindow = null;

                // 親ウィンドウ（iframe内の場合）
                if (window.parent && window.parent !== window) {
                    targetWindow = window.parent;
                }
                // 開いたウィンドウ（別ウィンドウの場合）
                else if (window.opener) {
                    targetWindow = window.opener;
                }
                // 同じウィンドウの場合
                else {
                    targetWindow = window;
                }

                // commandInputテキストエリアを探してコマンドを設定
                const commandInput = targetWindow.document.getElementById('commandInput');
                if (commandInput) {
                    commandInput.value = command;
                    commandInput.focus();

                    // 可能であれば親ウィンドウにフォーカス
                    if (targetWindow !== window) {
                        targetWindow.focus();
                    }
                } else {
                    // フォールバック: クリップボードにコピー
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(command).then(() => {
                            alert('コマンドをクリップボードにコピーしました:\\n' + command);
                        }).catch(() => {
                            alert('コマンド: ' + command + '\\n\\n手動でトップページの対話框にコピーしてください。');
                        });
                    } else {
                        alert('コマンド: ' + command + '\\n\\n手動でトップページの対話框にコピーしてください。');
                    }
                }
            } catch (error) {
                console.error('executeCommand error:', error);
                // エラー時のフォールバック
                try {
                    if (navigator.clipboard && navigator.clipboard.writeText) {
                        navigator.clipboard.writeText(command).then(() => {
                            alert('コマンドをクリップボードにコピーしました:\\n' + command);
                        }).catch(() => {
                            alert('コマンド: ' + command + '\\n\\n手動でトップページの対話框にコピーしてください。');
                        });
                    } else {
                        alert('コマンド: ' + command + '\\n\\n手動でトップページの対話框にコピーしてください。');
                    }
                } catch (clipboardError) {
                    console.error('Clipboard error:', clipboardError);
                    alert('コマンド: ' + command + '\\n\\n手動でトップページの対話框にコピーしてください。');
                }
            }
        };

        // Show modal dialog for input
        function showInputModal(title, fieldName, currentValue, promptTemplate, isTextarea = false) {
            // Create modal if it doesn't exist
            let modal = document.getElementById('inputModal');
            if (!modal) {
                modal = document.createElement('div');
                modal.id = 'inputModal';
                modal.className = 'modal';
                document.body.appendChild(modal);
            }

            const inputType = isTextarea ? 'textarea' : 'input';
            const inputClass = isTextarea ? 'modal-textarea' : 'modal-input';
            
            modal.innerHTML = `
                <div class="modal-content">
                    <div class="modal-header">${title}</div>
                    <label class="modal-label">${fieldName}:</label>
                    ${isTextarea ? 
                        `<textarea id="modalInput" class="${inputClass}" placeholder="内容を入力してください...">${currentValue || ''}</textarea>` :
                        `<input type="text" id="modalInput" class="${inputClass}" value="${currentValue || ''}" placeholder="値を入力してください...">`
                    }
                    <div class="modal-buttons">
                        <button class="modal-btn modal-btn-secondary" onclick="closeModal()">キャンセル</button>
                        <button class="modal-btn modal-btn-primary" onclick="confirmInput('${promptTemplate}')">確定</button>
                    </div>
                </div>
            `;

            modal.style.display = 'block';
            
            // Focus on input and select text
            setTimeout(() => {
                const input = document.getElementById('modalInput');
                input.focus();
                if (!isTextarea) {
                    input.select();
                }
            }, 100);

            // Close modal when clicking outside
            modal.onclick = function(event) {
                if (event.target === modal) {
                    closeModal();
                }
            };

            // Handle Enter key for input (not textarea)
            if (!isTextarea) {
                document.getElementById('modalInput').onkeypress = function(event) {
                    if (event.key === 'Enter') {
                        confirmInput(promptTemplate);
                    }
                };
            }

            // Handle Escape key
            document.onkeydown = function(event) {
                if (event.key === 'Escape') {
                    closeModal();
                }
            };
        }

        function closeModal() {
            const modal = document.getElementById('inputModal');
            if (modal) {
                modal.style.display = 'none';
            }
            document.onkeydown = null;
        }

        function confirmInput(promptTemplate) {
            const input = document.getElementById('modalInput');
            const value = input.value.trim();
            
            if (!value) {
                alert('値を入力してください');
                input.focus();
                return;
            }

            // Replace placeholder in prompt template with user input
            const command = promptTemplate.replace('{VALUE}', value);
            
            closeModal();
            executeCommand(command);
        }

        // Edit functions for different fields
        function editCategory(jancode, currentValue) {
            showInputModal(
                'カテゴリー変更',
                'カテゴリー名',
                currentValue,
                `JANコード${jancode}の商品のカテゴリーを{VALUE}に設定してください`
            );
        }

        function editInventory(jancode, currentValue) {
            showInputModal(
                '在庫変更',
                '在庫数',
                currentValue,
                `JANコード${jancode}の商品の在庫を{VALUE}に更新してください`
            );
        }

        function editPrice(jancode, currentValue) {
            showInputModal(
                '価格変更',
                '価格（円）',
                currentValue,
                `JANコード${jancode}の商品の価格を{VALUE}円に設定してください`
            );
        }

        function editDescription(jancode, currentValue) {
            showInputModal(
                '商品説明変更',
                '商品説明',
                currentValue,
                `JANコード${jancode}の商品の説明を「{VALUE}」に設定してください`,
                true // Use textarea
            );
        }

        // Also define as global function for compatibility
        function executeCommand(command) {
            return window.executeCommand(command);
        }
    </script>
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
        <tbody>"""

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

        jancode = product.get('jancode', '')
        category = product.get('category', '')
        stock = product.get('stock', 0)
        description_for_js = description.replace('"', '&quot;').replace("'", "&#39;")
        
        html += f"""
                <tr>
                    <td>{jancode}</td>
                    <td>{product.get('name_jp', '')}</td>
                    <td>{category or '未設定'}</td>
                    <td class="price">{price_display}</td>
                    <td>{stock}</td>
                    <td class="description" title="{description}">{description_display or '未設定'}</td>
                    <td class="{status_class}">{status_text}{error_html}</td>
                    <td>
                        <button class="btn btn-publish" {publish_disabled} onclick="executeCommand('JANコード{jancode}の商品を棚上げしてください')">上架</button>
                        <button class="btn btn-unpublish" onclick="executeCommand('JANコード{jancode}の商品を棚下げしてください')">下架</button>
                        <button class="btn btn-edit-category" onclick="editCategory('{jancode}', '{category}')">カテゴリー</button>
                        <button class="btn btn-edit-inventory" onclick="editInventory('{jancode}', '{stock}')">在庫</button>
                        <button class="btn btn-edit-price" onclick="editPrice('{jancode}', '{price}')">価格</button>
                        <button class="btn btn-edit-description" onclick="editDescription('{jancode}', '{description_for_js}')">説明</button>
                    </td>
                </tr>
        """

    html += """
        </tbody>
    </table>
</body>
</html>"""

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
