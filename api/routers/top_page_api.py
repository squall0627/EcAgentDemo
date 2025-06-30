from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from config.llm_config_loader import llm_config

router = APIRouter()

@router.get("", response_class=HTMLResponse)
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
            .session-info {{ background: #e9ecef; padding: 10px 20px; border-radius: 6px; margin-bottom: 15px; font-size: 12px; color: #666; display: flex; justify-content: space-between; align-items: center; }}
            .clear-history-btn {{ background: #dc3545; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 12px; }}
            .clear-history-btn:hover {{ background: #c82333; }}
            .chat-interface {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .input-row {{ display: flex; gap: 10px; align-items: center; margin-bottom: 15px; }}
            .config-row {{ display: flex; gap: 15px; align-items: center; margin-bottom: 20px; padding: 15px; background: #f8f9fa; border-radius: 6px; border: 1px solid #e9ecef; }}
            .chat-input {{ flex: 1; padding: 12px; font-size: 16px; border: 2px solid #e1e5e9; border-radius: 6px; transition: border-color 0.3s; }}
            .chat-input:focus {{ outline: none; border-color: #007bff; }}
            .llm-select {{ padding: 12px; font-size: 14px; background: white; border: 2px solid #e1e5e9; border-radius: 6px; min-width: 300px; cursor: pointer; }}
            .llm-select:focus {{ outline: none; border-color: #007bff; }}
            .agent-mode-select {{ padding: 12px; font-size: 14px; background: white; border: 2px solid #e1e5e9; border-radius: 6px; min-width: 200px; cursor: pointer; }}
            .agent-mode-select:focus {{ outline: none; border-color: #007bff; }}
            .chat-submit {{ padding: 12px 24px; background: #007bff; color: white; border: none; cursor: pointer; border-radius: 6px; font-weight: 600; transition: background-color 0.3s; }}
            .chat-submit:hover {{ background: #0056b3; }}
            .chat-submit:disabled {{ background: #6c757d; cursor: not-allowed; }}
            .result-area {{ min-height: 500px; border: 2px solid #e1e5e9; padding: 20px; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            .llm-status {{ display: flex; align-items: center; gap: 8px; font-size: 13px; color: #666; margin-top: 8px; padding: 8px 12px; background: #f8f9fa; border-radius: 4px; }}
            .llm-indicator {{ width: 10px; height: 10px; border-radius: 50%; }}
            .agent-mode-status {{ display: flex; align-items: center; gap: 8px; font-size: 13px; color: #666; padding: 8px 12px; background: #f8f9fa; border-radius: 4px; }}
            .agent-mode-indicator {{ width: 10px; height: 10px; border-radius: 50%; }}
            .single-agent {{ background-color: #28a745; }}
            .multi-agent {{ background-color: #ffc107; }}
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
            .config-label {{ font-size: 14px; font-weight: 600; color: #495057; min-width: 120px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; color: #343a40;">🤖 EC商品管理システム</h1>
                <p style="margin: 10px 0 0 0; color: #6c757d;">自然言語でAIエージェントと対話して商品を管理できます</p>
            </div>
            
            <!-- セッション情報と履歴クリアボタン -->
            <div class="session-info">
                <span>📝 セッションID: <span id="sessionId"></span></span>
                <button class="clear-history-btn" onclick="clearHistory()">New Chat</button>
            </div>
            
            <div class="chat-interface">
                <h3 style="margin-top: 0; color: #495057;">💬 自然言語コマンド入力</h3>
                
                <div class="config-row">
                    <div class="config-label">🧠 エージェントモード:</div>
                    <select id="agentModeSelect" class="agent-mode-select" title="使用するエージェントモードを選択">
                        <option value="single" selected>🔧 単一エージェント - 専門的な処理に集中</option>
                        <option value="multi">🌐 マルチエージェント - 複合的な処理を自動判断</option>
                    </select>
                    <div class="agent-mode-status">
                        <span class="agent-mode-indicator single-agent" id="agentModeIndicator"></span>
                        <span id="agentModeStatus">現在のモード: 単一エージェント</span>
                    </div>
                </div>
                
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
            
            // セッションID管理
            let currentSessionId = localStorage.getItem('productManagementSessionId');
            if (!currentSessionId) {{
                currentSessionId = generateSessionId();
                localStorage.setItem('productManagementSessionId', currentSessionId);
            }}
            document.getElementById('sessionId').textContent = currentSessionId;

            // セッションID生成関数
            function generateSessionId() {{
                return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            }}

            // 会話履歴クリア機能
            async function clearHistory() {{
                if (!confirm('会話履歴をクリアしますが、よろしいでしょうか？')) {{
                    return;
                }}

                try {{
                    const response = await fetch(`/api/chat/history/${{currentSessionId}}`, {{
                        method: 'DELETE'
                    }});

                    if (response.ok) {{
                        const result = await response.json();
                        
                        // 新しいセッションIDを生成
                        currentSessionId = generateSessionId();
                        localStorage.setItem('productManagementSessionId', currentSessionId);
                        document.getElementById('sessionId').textContent = currentSessionId;
                        
                        // 結果エリアをリセット
                        document.getElementById('resultArea').innerHTML = `
                            <div style="text-align: center; padding: 40px; color: #6c757d;">
                                <h4>✅ 会話履歴がクリアされました</h4>
                                <p>新しいセッションが開始されました。<br>
                                上記の入力欄にコマンドを入力してください。</p>
                            </div>
                        `;
                        
                        alert(`会話履歴をクリアしました（${{result.deleted_count}}件削除）`);
                    }} else {{
                        const error = await response.json();
                        alert('履歴クリアに失敗しました: ' + (error.detail || 'Unknown error'));
                    }}
                }} catch (error) {{
                    alert('通信エラーが発生しました: ' + error.message);
                }}
            }}
            
            // LLM選択時の状態更新
            document.getElementById('llmSelect').addEventListener('change', function() {{
                updateLLMStatus();
            }});
            
            // エージェントモード選択時の状態更新
            document.getElementById('agentModeSelect').addEventListener('change', function() {{
                updateAgentModeStatus();
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
            
            function updateAgentModeStatus() {{
                const selectedValue = document.getElementById('agentModeSelect').value;
                const selectedOption = document.getElementById('agentModeSelect').options[document.getElementById('agentModeSelect').selectedIndex];
                
                const indicator = document.getElementById('agentModeIndicator');
                const status = document.getElementById('agentModeStatus');
                
                if (selectedValue === 'single') {{
                    indicator.className = 'agent-mode-indicator single-agent';
                    status.textContent = '現在のモード: 単一エージェント';
                }} else {{
                    indicator.className = 'agent-mode-indicator multi-agent';
                    status.textContent = '現在のモード: マルチエージェント';
                }}
            }}
            
            async function executeCommand() {{
                const command = document.getElementById('commandInput').value;
                const selectedLLM = document.getElementById('llmSelect').value;
                const selectedAgentMode = document.getElementById('agentModeSelect').value;
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
                
                // エージェントモードに応じたAPIエンドポイントを選択
                const apiEndpoint = selectedAgentMode === 'single' ? '/api/agent/single-agent/chat' : '/api/agent/multi-agent/chat';
                const agentModeText = selectedAgentMode === 'single' ? '単一エージェント' : 'マルチエージェント';
                
                // 実行中の状態を表示
                document.getElementById('resultArea').innerHTML = `
                    <div class="loading">
                        <h4 style="margin-bottom: 15px;">🔄 処理中...</h4>
                        <div style="font-size: 16px; color: #495057; margin-bottom: 8px;">セッション: ${{currentSessionId}}</div>
                        <div style="font-size: 16px; color: #495057; margin-bottom: 8px;">モード: ${{agentModeText}}</div>
                        <div style="font-size: 16px; color: #495057; margin-bottom: 8px;">LLM: ${{selectedOption.textContent}}</div>
                        <div style="font-size: 14px; color: #6c757d; margin-bottom: 30px;">コマンド: "${{command}}"</div>
                        <div class="spinner"></div>
                        <div style="margin-top: 20px; font-size: 14px; color: #999;">
                            AIが応答を生成中です...
                        </div>
                    </div>
                `;
                
                try {{
                    const response = await fetch(apiEndpoint, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ 
                            message: command,
                            llm_type: selectedLLM,
                            session_id: currentSessionId,  // セッションIDを追加
                            user_id: 'default_user'      // 必要に応じて変更
                        }})
                    }});
                    
                    if (!response.ok) {{
                        throw new Error(`HTTP error! status: ${{response.status}}`);
                    }}
                    
                    const result = await response.json();
                    
                    // 結果を表示
                    let resultHTML = '';
                    
                    // セッション情報を表示
                    resultHTML += `<div class="llm-info">
                        <strong>📝 セッション情報:</strong> ${{currentSessionId}}
                        <br><small>会話履歴が自動的に管理されています</small>
                    </div>`;
                    
                    // エージェントモード情報を表示
                    resultHTML += `<div class="llm-info">
                        <strong>🧠 エージェントモード:</strong> ${{agentModeText}}
                        ${{selectedAgentMode === 'multi' && result.routing_decision ? 
                            `<br><small>選択されたエージェント: ${{result.routing_decision.selected_agent}}</small>` : ''}}
                    </div>`;
                    
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
            updateAgentModeStatus();
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