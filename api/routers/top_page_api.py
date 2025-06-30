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
            body {{ 
                font-family: Arial, sans-serif; 
                margin: 0; 
                padding: 20px; 
                background-color: #f5f5f5; 
                height: 100vh; 
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
            }}
            
            .container {{ 
                max-width: 1200px; 
                margin: 0 auto; 
                flex: 1;
                display: flex;
                flex-direction: column;
                min-height: 0; /* フレックスサブアイテムの縮小を許可 */
            }}
            
            .header {{ 
                background: white; 
                padding: 20px; 
                border-radius: 8px; 
                margin-bottom: 15px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                flex-shrink: 0; /* ヘッダーは縮小しない */
            }}
            
            .session-info {{ 
                background: #e9ecef; 
                padding: 10px 20px; 
                border-radius: 6px; 
                margin-bottom: 15px; 
                font-size: 12px; 
                color: #666; 
                display: flex; 
                justify-content: space-between; 
                align-items: center;
                flex-shrink: 0; /* セッション情報は縮小しない */
            }}
            
            .session-actions {{
                display: flex;
                gap: 10px;
                align-items: center;
            }}
            
            .new-chat-btn {{ 
                background: #28a745; 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 4px; 
                cursor: pointer; 
                font-size: 12px; 
            }}
            .new-chat-btn:hover {{ background: #218838; }}
            
            .history-btn {{ 
                background: #007bff; 
                color: white; 
                border: none; 
                padding: 8px 16px; 
                border-radius: 4px; 
                cursor: pointer; 
                font-size: 12px; 
            }}
            .history-btn:hover {{ background: #0056b3; }}
            
            /* 履歴サイドバーのスタイル */
            .history-sidebar {{
                position: fixed;
                top: 0;
                right: -400px; /* 初期状態では画面外に隠す */
                width: 400px;
                height: 100vh;
                background: white;
                box-shadow: -2px 0 5px rgba(0,0,0,0.1);
                transition: right 0.3s ease;
                z-index: 1000;
                display: flex;
                flex-direction: column;
            }}
            
            .history-sidebar.open {{
                right: 0; /* 開いた状態では画面内に表示 */
            }}
            
            .history-header {{
                padding: 20px;
                border-bottom: 1px solid #e9ecef;
                display: flex;
                justify-content: space-between;
                align-items: center;
                background: #f8f9fa;
            }}
            
            .history-close-btn {{
                background: #6c757d;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
            }}
            .history-close-btn:hover {{ background: #5a6268; }}
            
            .history-content {{
                flex: 1;
                overflow-y: auto;
                padding: 20px;
            }}
            
            .user-sessions {{
                margin-bottom: 30px;
            }}
            
            .user-header {{
                font-size: 16px;
                font-weight: bold;
                color: #495057;
                margin-bottom: 15px;
                padding-bottom: 5px;
                border-bottom: 2px solid #007bff;
            }}
            
            .session-item {{
                background: #f8f9fa;
                border: 1px solid #e9ecef;
                border-radius: 6px;
                padding: 12px;
                margin-bottom: 10px;
                cursor: pointer;
                transition: background-color 0.2s;
            }}
            
            .session-item:hover {{
                background: #e9ecef;
            }}
            
            .session-item.current {{
                background: #d1ecf1;
                border-color: #bee5eb;
            }}
            
            .session-id {{
                font-family: monospace;
                font-size: 12px;
                color: #6c757d;
                margin-bottom: 5px;
            }}
            
            .session-time {{
                font-size: 11px;
                color: #999;
                margin-bottom: 5px;
            }}
            
            .session-preview {{
                font-size: 13px;
                color: #495057;
                line-height: 1.4;
                overflow: hidden;
                text-overflow: ellipsis;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
            }}
            
            .no-history {{
                text-align: center;
                color: #6c757d;
                padding: 40px 20px;
            }}
            
            /* オーバーレイ背景 */
            .history-overlay {{
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.3);
                z-index: 999;
                opacity: 0;
                visibility: hidden;
                transition: opacity 0.3s ease, visibility 0.3s ease;
            }}
            
            .history-overlay.open {{
                opacity: 1;
                visibility: visible;
            }}
            
            /* スクリーン高さに適応するチャットコンテナ */
            .chat-container {{ 
                background: white; 
                border-radius: 8px; 
                box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                display: flex; 
                flex-direction: column; 
                flex: 1; /* 残りのスペースを占有 */
                min-height: 0; /* 縮小を許可 */
            }}
            
            .chat-header {{ 
                padding: 20px; 
                border-bottom: 1px solid #e9ecef; 
                background: #f8f9fa; 
                border-radius: 8px 8px 0 0;
                flex-shrink: 0; /* ヘッダーは縮小しない */
            }}
            
            .config-row {{ 
                display: flex; 
                gap: 15px; 
                align-items: center; 
                margin-bottom: 15px; 
                flex-wrap: wrap;
            }}
            
            .chat-messages {{ 
                flex: 1; 
                overflow-y: auto; 
                padding: 20px; 
                background: #fafafa;
                min-height: 0; /* 縮小を許可 */
            }}
            
            .message {{ 
                margin-bottom: 20px; 
                display: flex; 
                align-items: flex-start; 
                gap: 12px;
            }}
            
            .message.user {{ flex-direction: row-reverse; }}
            
            .message-avatar {{ 
                width: 40px; 
                height: 40px; 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                font-size: 18px; 
                flex-shrink: 0;
            }}
            
            .user .message-avatar {{ 
                background: #007bff; 
                color: white; 
            }}
            
            .assistant .message-avatar {{ 
                background: #28a745; 
                color: white; 
            }}
            
            .message-content {{ 
                max-width: 70%; 
                padding: 12px 16px; 
                border-radius: 18px; 
                position: relative;
                word-wrap: break-word;
                overflow-wrap: break-word;
            }}
            
            .user .message-content {{ 
                background: #007bff; 
                color: white; 
                border-bottom-right-radius: 4px;
            }}
            
            .assistant .message-content {{ 
                background: white; 
                color: #333; 
                border: 1px solid #e9ecef; 
                border-bottom-left-radius: 4px;
            }}
            
            .message-time {{ 
                font-size: 11px; 
                opacity: 0.7; 
                margin-top: 4px; 
                text-align: right;
            }}
            
            .user .message-time {{ color: rgba(255,255,255,0.8); }}
            .assistant .message-time {{ color: #666; }}
            
            .message-html-content {{ 
                margin-top: 10px; 
                border: 1px solid #ddd; 
                border-radius: 6px; 
                overflow: hidden;
                background: #f8f9fa;
                max-width: 100%;
            }}
            
            /* 複数行入力フィールドのスタイル */
            .chat-input-area {{ 
                padding: 20px; 
                border-top: 1px solid #e9ecef; 
                background: white; 
                border-radius: 0 0 8px 8px;
                flex-shrink: 0; /* 入力エリアは縮小しない */
            }}
            
            .input-container {{ 
                display: flex; 
                gap: 10px; 
                align-items: flex-end; 
            }}
            
            .input-wrapper {{ 
                flex: 1;
                position: relative;
            }}
            
            .chat-input {{ 
                width: 100%; 
                min-height: 40px;
                max-height: 120px; /* 最大高さ制限 */
                padding: 12px 45px 12px 16px; /* 右側に送信ボタンのスペースを空ける */
                font-size: 16px; 
                border: 2px solid #e1e5e9; 
                border-radius: 20px; 
                outline: none; 
                resize: none;
                font-family: inherit;
                line-height: 1.4;
                box-sizing: border-box;
                transition: border-color 0.3s;
                overflow-y: auto; /* 垂直スクロールを許可 */
            }}
            
            .chat-input:focus {{ 
                border-color: #007bff; 
            }}
            
            .chat-input::placeholder {{
                color: #999;
                font-style: italic;
            }}
            
            .send-button {{ 
                position: absolute;
                right: 8px;
                bottom: 8px;
                width: 32px;
                height: 32px;
                background: #007bff; 
                color: white; 
                border: none; 
                border-radius: 50%; 
                cursor: pointer; 
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                transition: background-color 0.3s;
            }}
            
            .send-button:hover {{ 
                background: #0056b3; 
            }}
            
            .send-button:disabled {{ 
                background: #6c757d; 
                cursor: not-allowed; 
            }}
            
            .input-hint {{
                font-size: 11px;
                color: #999;
                margin-top: 5px;
                text-align: center;
            }}
            
            .llm-select {{ 
                padding: 8px 12px; 
                font-size: 12px; 
                background: white; 
                border: 1px solid #e1e5e9; 
                border-radius: 4px; 
                cursor: pointer;
            }}
            
            .agent-mode-select {{ 
                padding: 8px 12px; 
                font-size: 12px; 
                background: white; 
                border: 1px solid #e1e5e9; 
                border-radius: 4px; 
                cursor: pointer;
            }}
            
            .config-label {{ 
                font-size: 12px; 
                font-weight: 600; 
                color: #495057; 
                white-space: nowrap;
            }}
            
            .llm-status {{ 
                font-size: 11px; 
                color: #666; 
                display: flex; 
                align-items: center; 
                gap: 6px;
            }}
            
            .llm-indicator {{ 
                width: 8px; 
                height: 8px; 
                border-radius: 50%; 
            }}
            
            .agent-mode-indicator {{ 
                width: 8px; 
                height: 8px; 
                border-radius: 50%; 
            }}
            
            .single-agent {{ background-color: #28a745; }}
            .multi-agent {{ background-color: #ffc107; }}
            .ollama {{ background-color: #10b981; }}
            .openai {{ background-color: #3b82f6; }}
            .anthropic {{ background-color: #8b5cf6; }}
            
            .typing-indicator {{ 
                display: flex; 
                align-items: center; 
                gap: 12px; 
                margin-bottom: 20px;
            }}
            
            .typing-indicator .message-avatar {{ 
                background: #28a745; 
                color: white; 
            }}
            
            .typing-dots {{ 
                background: white; 
                border: 1px solid #e9ecef; 
                border-radius: 18px; 
                padding: 12px 16px; 
                display: flex; 
                gap: 4px;
            }}
            
            .typing-dot {{ 
                width: 8px; 
                height: 8px; 
                background: #999; 
                border-radius: 50%; 
                animation: typing 1.4s infinite;
            }}
            
            .typing-dot:nth-child(2) {{ animation-delay: 0.2s; }}
            .typing-dot:nth-child(3) {{ animation-delay: 0.4s; }}
            
            @keyframes typing {{
                0%, 60%, 100% {{ transform: translateY(0); opacity: 0.5; }}
                30% {{ transform: translateY(-10px); opacity: 1; }}
            }}
            
            .welcome-message {{ 
                text-align: center; 
                padding: 60px 20px; 
                color: #6c757d; 
            }}
            
            .examples {{ 
                background: #f8f9fa; 
                padding: 15px; 
                border-radius: 6px; 
                margin-top: 15px; 
                font-size: 12px;
            }}
            
            .examples ul {{ 
                margin: 8px 0; 
                padding-left: 20px; 
            }}
            
            .examples li {{ 
                margin: 4px 0; 
                color: #6c757d; 
            }}
            
            /* カスタムスクロールバー */
            .chat-messages::-webkit-scrollbar {{ width: 6px; }}
            .chat-messages::-webkit-scrollbar-track {{ background: #f1f1f1; }}
            .chat-messages::-webkit-scrollbar-thumb {{ background: #c1c1c1; border-radius: 3px; }}
            .chat-messages::-webkit-scrollbar-thumb:hover {{ background: #a8a8a8; }}
            
            .history-content::-webkit-scrollbar {{ width: 6px; }}
            .history-content::-webkit-scrollbar-track {{ background: #f1f1f1; }}
            .history-content::-webkit-scrollbar-thumb {{ background: #c1c1c1; border-radius: 3px; }}
            .history-content::-webkit-scrollbar-thumb:hover {{ background: #a8a8a8; }}
            
            .chat-input::-webkit-scrollbar {{ width: 4px; }}
            .chat-input::-webkit-scrollbar-track {{ background: #f1f1f1; }}
            .chat-input::-webkit-scrollbar-thumb {{ background: #c1c1c1; border-radius: 2px; }}
            
            /* レスポンシブデザイン */
            @media (max-width: 768px) {{
                body {{ padding: 10px; }}
                .config-row {{ flex-direction: column; gap: 10px; }}
                .message-content {{ max-width: 85%; }}
                .chat-input {{ font-size: 16px; /* iOSの拡大を防ぐ */ }}
                .header {{ padding: 15px; }}
                .chat-header {{ padding: 15px; }}
                .chat-input-area {{ padding: 15px; }}
                
                .history-sidebar {{
                    width: 100%;
                    right: -100%;
                }}
                
                .session-actions {{
                    flex-direction: column;
                    gap: 5px;
                }}
            }}
            
            @media (max-height: 600px) {{
                .header {{ padding: 10px; margin-bottom: 10px; }}
                .session-info {{ padding: 8px 15px; margin-bottom: 10px; }}
                .chat-header {{ padding: 15px; }}
                .examples {{ display: none; }} /* 小さいスクリーン高さ時に例を非表示 */
            }}
        </style>
    </head>
    <body>
        <!-- 履歴サイドバー用オーバーレイ -->
        <div class="history-overlay" id="historyOverlay" onclick="closeHistorySidebar()"></div>
        
        <!-- 履歴サイドバー -->
        <div class="history-sidebar" id="historySidebar">
            <div class="history-header">
                <h3 style="margin: 0;">📖 チャット履歴</h3>
                <button class="history-close-btn" onclick="closeHistorySidebar()">×</button>
            </div>
            <div class="history-content" id="historyContent">
                <div class="no-history">履歴を読み込み中...</div>
            </div>
        </div>
        
        <div class="container">
            <div class="header">
                <h1 style="margin: 0; color: #343a40;">🤖 EC商品管理システム</h1>
                <p style="margin: 10px 0 0 0; color: #6c757d;">自然言語でAIエージェントと対話して商品を管理できます</p>
            </div>
            
            <!-- セッション情報と履歴クリアボタン -->
            <div class="session-info">
                <span>📝 セッションID: <span id="sessionId"></span></span>
                <div class="session-actions">
                    <button class="history-btn" onclick="openHistorySidebar()">履歴表示</button>
                    <button class="new-chat-btn" onclick="startNewChat()">新しいチャット</button>
                </div>
            </div>
            
            <!-- チャットコンテナ -->
            <div class="chat-container">
                <!-- チャットヘッダー（設定エリア） -->
                <div class="chat-header">
                    <div class="config-row">
                        <div class="config-label">🧠 エージェント:</div>
                        <select id="agentModeSelect" class="agent-mode-select">
                            <option value="single" selected>単一エージェント</option>
                            <option value="multi">マルチエージェント</option>
                        </select>
                        
                        <div class="config-label">🤖 LLM:</div>
                        <select id="llmSelect" class="llm-select">
                            {llm_options}
                        </select>
                        
                        <div class="llm-status">
                            <span class="llm-indicator" id="llmIndicator"></span>
                            <span id="llmStatus">読み込み中...</span>
                        </div>
                    </div>
                    
                    <div class="examples">
                        <strong>💡 使用例:</strong>
                        <ul>
                            <li>"コーヒー商品を検索してください"</li>
                            <li>"在庫が少ない商品を棚上げしてください"</li>
                            <li>"JANコード123の商品のカテゴリーを設定してください"</li>
                        </ul>
                    </div>
                </div>
                
                <!-- チャットメッセージエリア -->
                <div id="chatMessages" class="chat-messages">
                    <div class="welcome-message">
                        <h4>👋 ようこそ！</h4>
                        <p>下の入力欄にコマンドを入力して会話を始めてください。<br>
                        システムが自動的に適切な操作画面を生成します。</p>
                    </div>
                </div>
                
                <!-- チャット入力エリア -->
                <div class="chat-input-area">
                    <div class="input-container">
                        <div class="input-wrapper">
                            <textarea 
                                id="commandInput" 
                                class="chat-input" 
                                placeholder="メッセージを入力してください..."
                                maxlength="2000"
                                rows="1"></textarea>
                            <button id="sendBtn" class="send-button" onclick="sendMessage()" title="送信 (Enter)">
                                ➤
                            </button>
                        </div>
                    </div>
                    <div class="input-hint">
                        Shift+Enter: 改行 | Enter: 送信 | 最大2000文字
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // LLM設定（設定ファイルから読み込み）
            const llmConfigs = {llm_js_config};
            
            // ユーザーID（実際のシステムでは認証から取得）
            const currentUserId = 'default_user';
            
            // セッションID管理
            let currentSessionId = localStorage.getItem('productManagementSessionId');
            if (!currentSessionId) {{
                currentSessionId = generateSessionId();
                localStorage.setItem('productManagementSessionId', currentSessionId);
            }}
            document.getElementById('sessionId').textContent = currentSessionId;

            // Mac系统专用的IME处理
            // IME合成状態の管理変数
            let isComposingText = false;
            let pendingSubmit = false;
            let lastCompositionValue = '';
            
            // 检测Mac系统
            const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0;
            console.log('Detected platform:', navigator.platform, 'isMac:', isMac);

            // セッションID生成関数
            function generateSessionId() {{
                return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
            }}

            // テキストエリアの自動リサイズ機能
            function autoResize(textarea) {{
                textarea.style.height = 'auto';
                const newHeight = Math.min(textarea.scrollHeight, 120); // 最大120px
                textarea.style.height = newHeight + 'px';
            }}

            // 履歴サイドバーの開閉機能
            function openHistorySidebar() {{
                const sidebar = document.getElementById('historySidebar');
                const overlay = document.getElementById('historyOverlay');
                
                sidebar.classList.add('open');
                overlay.classList.add('open');
                
                // 履歴を読み込み
                loadAllHistory();
            }}
            
            function closeHistorySidebar() {{
                const sidebar = document.getElementById('historySidebar');
                const overlay = document.getElementById('historyOverlay');
                
                sidebar.classList.remove('open');
                overlay.classList.remove('open');
            }}

            // 新しいチャットを開始する関数
            function startNewChat() {{
                // 新しいセッションIDを生成
                currentSessionId = generateSessionId();
                localStorage.setItem('productManagementSessionId', currentSessionId);
                document.getElementById('sessionId').textContent = currentSessionId;
                
                // チャットメッセージエリアをクリア
                const chatMessages = document.getElementById('chatMessages');
                chatMessages.innerHTML = `
                    <div class="welcome-message">
                        <h4>✨ 新しいチャットが開始されました</h4>
                        <p>下の入力欄にコマンドを入力してください。<br>
                        システムが自動的に適切な操作画面を生成します。</p>
                    </div>
                `;
                
                // 入力フィールドをクリア
                const commandInput = document.getElementById('commandInput');
                commandInput.value = '';
                autoResize(commandInput);
                commandInput.focus();
            }}
            
            // 全ユーザーの履歴を読み込む関数
            async function loadAllHistory() {{
                try {{
                    const response = await fetch('/api/chat/history/users/all?limit=100');
                    if (response.ok) {{
                        const data = await response.json();
                        displayHistory(data.user_sessions || []);
                    }} else {{
                        const historyContent = document.getElementById('historyContent');
                        historyContent.innerHTML = `
                            <div class="no-history">
                                履歴の読み込みに失敗しました
                            </div>
                        `;
                    }}
                }} catch (error) {{
                    console.error('履歴読み込みエラー:', error);
                    const historyContent = document.getElementById('historyContent');
                    historyContent.innerHTML = `
                        <div class="no-history">
                            通信エラーが発生しました
                        </div>
                    `;
                }}
            }}
            
            // 履歴を表示する関数
            function displayHistory(userSessions) {{
                const historyContent = document.getElementById('historyContent');
                
                if (!userSessions || userSessions.length === 0) {{
                    historyContent.innerHTML = `
                        <div class="no-history">
                            <h4>📭 履歴がありません</h4>
                            <p>まだチャット履歴がありません。<br>
                            新しい会話を始めてみましょう！</p>
                        </div>
                    `;
                    return;
                }}
                
                let historyHtml = '';
                
                userSessions.forEach(userSession => {{
                    historyHtml += `
                        <div class="user-sessions">
                            <div class="user-header">👤 ユーザー: ${{userSession.user_id}}</div>
                    `;
                    
                    userSession.sessions.forEach(session => {{
                        const isCurrentSession = session.session_id === currentSessionId;
                        const sessionClass = isCurrentSession ? 'session-item current' : 'session-item';
                        
                        // 最新のメッセージプレビューを作成
                        const latestMessage = session.latest_message;
                        const previewText = latestMessage ? 
                            latestMessage.substring(0, 100) + (latestMessage.length > 100 ? '...' : '') :
                            '新しいセッション';
                        
                        historyHtml += `
                            <div class="${{sessionClass}}" onclick="loadSession('${{session.session_id}}')">
                                <div class="session-id">${{session.session_id}}</div>
                                <div class="session-time">${{formatTimestamp(session.last_activity)}}</div>
                                <div class="session-preview">${{previewText}}</div>
                                <div style="font-size: 11px; color: #999; margin-top: 5px;">
                                    💬 ${{session.message_count}}件のメッセージ
                                </div>
                            </div>
                        `;
                    }});
                    
                    historyHtml += '</div>';
                }});
                
                historyContent.innerHTML = historyHtml;
            }}
            
            // セッションを読み込む関数
            async function loadSession(sessionId) {{
                if (sessionId === currentSessionId) {{
                    // 現在のセッションの場合はサイドバーを閉じるだけ
                    closeHistorySidebar();
                    return;
                }}
                
                try {{
                    // セッションIDを切り替え
                    currentSessionId = sessionId;
                    localStorage.setItem('productManagementSessionId', currentSessionId);
                    document.getElementById('sessionId').textContent = currentSessionId;
                    
                    // 会話履歴を読み込み
                    await loadConversationHistory();
                    
                    // サイドバーを閉じる
                    closeHistorySidebar();
                    
                    // 入力フィールドにフォーカス
                    document.getElementById('commandInput').focus();
                    
                }} catch (error) {{
                    console.error('セッション読み込みエラー:', error);
                    alert('セッションの読み込みに失敗しました');
                }}
            }}
            
            // タイムスタンプをフォーマットする関数
            function formatTimestamp(timestamp) {{
                const date = new Date(timestamp);
                const now = new Date();
                const diffMs = now - date;
                const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
                
                if (diffDays === 0) {{
                    return '今日 ' + date.toLocaleTimeString('ja-JP', {{hour: '2-digit', minute: '2-digit'}});
                }} else if (diffDays === 1) {{
                    return '昨日 ' + date.toLocaleTimeString('ja-JP', {{hour: '2-digit', minute: '2-digit'}});
                }} else if (diffDays < 7) {{
                    return `${{diffDays}}日前`;
                }} else {{
                    return date.toLocaleDateString('ja-JP');
                }}
            }}

            // チャットメッセージを追加する関数
            function addMessage(content, isUser = false, timestamp = null, hasHtml = false, htmlContent = '') {{
                const chatMessages = document.getElementById('chatMessages');
                const messageTime = timestamp ? new Date(timestamp).toLocaleString('ja-JP') : new Date().toLocaleString('ja-JP');
                
                // ウェルカムメッセージを削除
                const welcomeMessage = chatMessages.querySelector('.welcome-message');
                if (welcomeMessage) {{
                    welcomeMessage.remove();
                }}
                
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${{isUser ? 'user' : 'assistant'}}`;
                
                const avatarDiv = document.createElement('div');
                avatarDiv.className = 'message-avatar';
                avatarDiv.textContent = isUser ? '👤' : '🤖';
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                
                const textDiv = document.createElement('div');
                textDiv.style.whiteSpace = 'pre-wrap';
                textDiv.textContent = content;
                contentDiv.appendChild(textDiv);
                
                if (hasHtml && htmlContent) {{
                    const htmlDiv = document.createElement('div');
                    htmlDiv.className = 'message-html-content';
                    htmlDiv.innerHTML = htmlContent;
                    contentDiv.appendChild(htmlDiv);
                }}
                
                const timeDiv = document.createElement('div');
                timeDiv.className = 'message-time';
                timeDiv.textContent = messageTime;
                contentDiv.appendChild(timeDiv);
                
                messageDiv.appendChild(avatarDiv);
                messageDiv.appendChild(contentDiv);
                
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }}

            // タイピングインジケーターを表示
            function showTypingIndicator() {{
                const chatMessages = document.getElementById('chatMessages');
                
                const typingDiv = document.createElement('div');
                typingDiv.id = 'typingIndicator';
                typingDiv.className = 'typing-indicator';
                
                const avatarDiv = document.createElement('div');
                avatarDiv.className = 'message-avatar';
                avatarDiv.textContent = '🤖';
                
                const dotsDiv = document.createElement('div');
                dotsDiv.className = 'typing-dots';
                for (let i = 0; i < 3; i++) {{
                    const dot = document.createElement('div');
                    dot.className = 'typing-dot';
                    dotsDiv.appendChild(dot);
                }}
                
                typingDiv.appendChild(avatarDiv);
                typingDiv.appendChild(dotsDiv);
                
                chatMessages.appendChild(typingDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }}

            // タイピングインジケーターを非表示
            function hideTypingIndicator() {{
                const typingIndicator = document.getElementById('typingIndicator');
                if (typingIndicator) {{
                    typingIndicator.remove();
                }}
            }}

            // 会話履歴を読み込む関数
            async function loadConversationHistory() {{
                try {{
                    const response = await fetch(`/api/chat/history/${{currentSessionId}}?limit=50`);
                    if (response.ok) {{
                        const data = await response.json();
                        const chatMessages = document.getElementById('chatMessages');
                        chatMessages.innerHTML = '';
                        
                        if (data.conversations && data.conversations.length > 0) {{
                            // 履歴を時間順（古い順）にソート
                            const sortedConversations = data.conversations.sort((a, b) => 
                                new Date(a.created_at) - new Date(b.created_at)
                            );
                            
                            sortedConversations.forEach(conv => {{
                                // ユーザーメッセージを追加
                                addMessage(conv.user_message, true, conv.created_at);
                                
                                // エージェントレスポンスを追加
                                const hasHtml = conv.html_content && conv.html_content.trim() !== '';
                                addMessage(conv.agent_response, false, conv.created_at, hasHtml, conv.html_content);
                            }});
                        }} else {{
                            chatMessages.innerHTML = `
                                <div class="welcome-message">
                                    <h4>👋 ようこそ！</h4>
                                    <p>下の入力欄にコマンドを入力して会話を始めてください。<br>
                                    システムが自動的に適切な操作画面を生成します。</p>
                                </div>
                            `;
                        }}
                    }}
                }} catch (error) {{
                    console.error('会話履歴の取得エラー:', error);
                }}
            }}

            // メッセージを送信する関数
            async function sendMessage() {{
                const commandInput = document.getElementById('commandInput');
                const command = commandInput.value.trim();
                const selectedLLM = document.getElementById('llmSelect').value;
                const selectedAgentMode = document.getElementById('agentModeSelect').value;
                
                if (!command) {{
                    alert('メッセージを入力してください');
                    return;
                }}
                
                // ボタンを無効化
                const sendBtn = document.getElementById('sendBtn');
                sendBtn.disabled = true;
                sendBtn.textContent = '...';
                
                // ユーザーメッセージを表示
                addMessage(command, true);
                
                // 入力欄をクリア・リセット
                commandInput.value = '';
                autoResize(commandInput);
                
                // タイピングインジケーターを表示
                showTypingIndicator();
                
                try {{
                    const apiEndpoint = selectedAgentMode === 'single' ? 
                        '/api/agent/single-agent/chat' : '/api/agent/multi-agent/chat';
                    
                    const response = await fetch(apiEndpoint, {{
                        method: 'POST',
                        headers: {{ 'Content-Type': 'application/json' }},
                        body: JSON.stringify({{ 
                            message: command,
                            llm_type: selectedLLM,
                            session_id: currentSessionId,
                            user_id: currentUserId
                        }})
                    }});
                    
                    if (!response.ok) {{
                        throw new Error(`HTTP error! status: ${{response.status}}`);
                    }}
                    
                    const result = await response.json();
                    
                    // タイピングインジケーターを非表示
                    hideTypingIndicator();
                    
                    // エージェントレスポンスを表示
                    let responseText = result.response || result.message || 'レスポンスを受信しました';
                    const hasHtml = result.html_content && result.html_content.trim() !== '';
                    
                    addMessage(responseText, false, null, hasHtml, result.html_content);
                    
                }} catch (error) {{
                    console.error('Error:', error);
                    hideTypingIndicator();
                    addMessage(`❌ エラーが発生しました: ${{error.message}}`, false);
                }} finally {{
                    // ボタンを再有効化
                    sendBtn.disabled = false;
                    sendBtn.textContent = '➤';
                    commandInput.focus(); // 入力欄にフォーカスを戻す
                }}
            }}
            
            // LLM選択時の状態更新
            function updateLLMStatus() {{
                const selectedValue = document.getElementById('llmSelect').value;
                const selectedOption = document.getElementById('llmSelect').options[document.getElementById('llmSelect').selectedIndex];
                
                const provider = selectedOption.getAttribute('data-provider');
                const color = selectedOption.getAttribute('data-color');
                
                const indicator = document.getElementById('llmIndicator');
                const status = document.getElementById('llmStatus');
                
                indicator.className = `llm-indicator ${{color}}`;
                status.textContent = selectedOption.textContent.replace(/^[🦙🤖🧠]\\s*/, '');
            }}
            
            // Mac系统专用的IME处理函数
            function handleCompositionStart(e) {{
                console.log('🎌 Mac Composition start:', e.type, e.data);
                isComposingText = true;
                pendingSubmit = false;
                lastCompositionValue = e.target.value;
            }}
            
            function handleCompositionUpdate(e) {{
                console.log('🎌 Mac Composition update:', e.type, e.data);
                isComposingText = true;
                lastCompositionValue = e.target.value;
            }}
            
            function handleCompositionEnd(e) {{
                console.log('🎌 Mac Composition end:', e.type, e.data);
                isComposingText = false;
                
                // Mac需要更长的延迟来确保合成完全结束
                setTimeout(() => {{
                    if (pendingSubmit && !isComposingText) {{
                        console.log('🎌 Mac Executing deferred submit');
                        pendingSubmit = false;
                        if (!document.getElementById('sendBtn').disabled) {{
                            sendMessage();
                        }}
                    }}
                }}, isMac ? 100 : 50); // Mac使用更长延迟
            }}
            
            function handleInput(e) {{
                autoResize(e.target);
                
                // Mac系统额外的输入法检测
                if (isMac && e.inputType) {{
                    if (e.inputType.includes('composition') || 
                        e.inputType === 'insertCompositionText' ||
                        e.inputType === 'deleteCompositionText') {{
                        console.log('🎌 Mac IME detected via inputType:', e.inputType);
                        isComposingText = true;
                    }}
                }}
            }}
            
            function handleKeyDown(e) {{
                const isEnter = e.key === 'Enter' || e.keyCode === 13 || e.which === 13;
                
                if (isEnter) {{
                    if (e.shiftKey) {{
                        // Shift+Enter: 换行
                        return;
                    }}
                    
                    // 执行发送
                    e.preventDefault();
                    if (!document.getElementById('sendBtn').disabled) {{
                        sendMessage();
                    }}
                }}
            }}
            
            // イベントリスナー
            document.getElementById('llmSelect').addEventListener('change', updateLLMStatus);
            
            // テキストエリアのイベントリスナー設定
            const commandInput = document.getElementById('commandInput');
            
            // 基本事件监听
            // 额外的input事件监听，用于检测输入状态
            commandInput.addEventListener('input', handleInput);
            commandInput.addEventListener('keypress', handleKeyDown);
            
            // IME事件监听（Mac优化）
            commandInput.addEventListener('compositionstart', handleCompositionStart);
            commandInput.addEventListener('compositionupdate', handleCompositionUpdate);
            commandInput.addEventListener('compositionend', handleCompositionEnd);
            
            // フォーカス事件
            // フォーカス時にプレースホルダーを更新
            commandInput.addEventListener('focus', function() {{
                this.placeholder = 'メッセージを入力してください...';
            }});
            
            commandInput.addEventListener('blur', function() {{
                this.placeholder = 'メッセージを入力してください...';
            }});
            
            // ESCキーでサイドバーを閉じる
            document.addEventListener('keydown', function(e) {{
                if (e.key === 'Escape') {{
                    closeHistorySidebar();
                }}
            }});
            
            // 初期化
            updateLLMStatus();
            
            // ページ読み込み時に会話履歴を読み込み
            window.addEventListener('load', function() {{
                loadConversationHistory();
                commandInput.focus(); // 入力欄にフォーカス
            }});
            
            // ウィンドウリサイズ時の処理
            window.addEventListener('resize', function() {{
                autoResize(commandInput);
            }});
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