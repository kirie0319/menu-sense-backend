from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def read_root():
    """6段階処理のメインページ（MVP版）- Imagen 3画像生成対応"""
    # API可用性の確認 - 新しいサービス層から取得
    from app.services.auth import get_compatibility_variables
    
    auth_vars = get_compatibility_variables()
    VISION_AVAILABLE = auth_vars["VISION_AVAILABLE"]
    TRANSLATE_AVAILABLE = auth_vars["TRANSLATE_AVAILABLE"]
    OPENAI_AVAILABLE = auth_vars["OPENAI_AVAILABLE"]
    GEMINI_AVAILABLE = auth_vars["GEMINI_AVAILABLE"]
    IMAGEN_AVAILABLE = auth_vars["IMAGEN_AVAILABLE"]
    
    vision_status = "✅ Ready" if VISION_AVAILABLE else "❌ Not Configured"
    translate_status = "✅ Ready" if TRANSLATE_AVAILABLE else "❌ Not Configured"
    openai_status = "✅ Ready" if OPENAI_AVAILABLE else "❌ Not Configured"
    gemini_status = "✅ Ready (Gemini 2.0 Flash - Primary OCR)" if GEMINI_AVAILABLE else "❌ Not Configured"
    imagen_status = "✅ Ready (Imagen 3)" if IMAGEN_AVAILABLE else "❌ Not Configured"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Menu Processor MVP - Gemini OCR Powered</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                line-height: 1.6;
            }}
            .container {{
                background: white;
                border-radius: 15px;
                padding: 30px;
                box-shadow: 0 15px 35px rgba(0,0,0,0.1);
                backdrop-filter: blur(10px);
            }}
            .header {{
                text-align: center;
                margin-bottom: 40px;
            }}
            .version-badge {{
                background: linear-gradient(45deg, #4CAF50, #45a049);
                color: white;
                padding: 8px 20px;
                border-radius: 25px;
                font-size: 14px;
                font-weight: 600;
                display: inline-block;
                margin-bottom: 15px;
                box-shadow: 0 4px 15px rgba(76, 175, 80, 0.3);
            }}
            .title {{
                font-size: 2.5em;
                color: #333;
                margin-bottom: 10px;
                font-weight: 700;
            }}
            .subtitle {{
                color: #666;
                font-size: 1.1em;
                margin-bottom: 30px;
            }}
            .status-grid {{
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                margin-bottom: 40px;
            }}
            
            @media (max-width: 768px) {{
                .status-grid {{
                    grid-template-columns: 1fr;
                    gap: 15px;
                }}
            }}
            
            @media (min-width: 1200px) {{
                .status-grid {{
                    grid-template-columns: repeat(5, 1fr);
                    gap: 20px;
                }}
            }}
            .status-card {{
                padding: 20px;
                border-radius: 12px;
                border: 2px solid #eee;
                text-align: center;
                transition: all 0.3s ease;
            }}
            .status-card:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }}
            .status-card.ready {{ 
                border-color: #4CAF50; 
                background: linear-gradient(135deg, #f8fff8, #e8f5e8);
            }}
            .status-card.error {{ 
                border-color: #f44336; 
                background: linear-gradient(135deg, #fff8f8, #ffebee);
            }}
            .stages {{
                display: grid;
                grid-template-columns: repeat(6, 1fr);
                gap: 15px;
                margin: 30px 0;
            }}
            
            @media (max-width: 768px) {{
                .stages {{
                    grid-template-columns: repeat(2, 1fr);
                    gap: 10px;
                }}
            }}
            
            @media (max-width: 480px) {{
                .stages {{
                    grid-template-columns: 1fr;
                    gap: 10px;
                }}
            }}
            .stage {{
                padding: 20px;
                text-align: center;
                border-radius: 12px;
                background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
                border: 2px solid #ddd;
                font-size: 14px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }}
            .stage::before {{
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
                transition: left 0.5s;
            }}
            .stage:hover::before {{
                left: 100%;
            }}
            .stage.active {{ 
                background: linear-gradient(135deg, #e3f2fd, #bbdefb);
                border-color: #2196F3;
                animation: pulse 2s infinite;
                transform: scale(1.05);
            }}
            .stage.completed {{ 
                background: linear-gradient(135deg, #e8f5e8, #c8e6c9);
                border-color: #4CAF50;
                transform: scale(1.02);
            }}
            .stage.error {{ 
                background: linear-gradient(135deg, #ffebee, #ffcdd2);
                border-color: #f44336;
            }}
            @keyframes pulse {{
                0%, 100% {{ transform: scale(1.05); }}
                50% {{ transform: scale(1.08); }}
            }}
            .upload-area {{
                border: 3px dashed #667eea;
                border-radius: 15px;
                padding: 50px;
                text-align: center;
                margin: 30px 0;
                cursor: pointer;
                transition: all 0.3s ease;
                background: linear-gradient(135deg, #f8f9ff, #e8eaf6);
            }}
            .upload-area:hover {{
                background: linear-gradient(135deg, #e8eaf6, #c5cae9);
                transform: translateY(-3px);
                box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
            }}
            .upload-icon {{
                font-size: 3em;
                margin-bottom: 15px;
                color: #667eea;
            }}
            .result-section {{
                margin-top: 40px;
                display: none;
            }}
            .progress-container {{
                margin: 30px 0;
                padding: 20px;
                background: linear-gradient(135deg, #f8f9ff, #e8eaf6);
                border-radius: 12px;
                border: 1px solid #e0e0e0;
            }}
            .progress-title {{
                font-size: 1.2em;
                font-weight: 600;
                color: #333;
                margin-bottom: 15px;
                text-align: center;
            }}
            .stage-result {{
                margin: 25px 0;
                padding: 25px;
                border-radius: 12px;
                border: 1px solid #e0e0e0;
                background: #fafafa;
                opacity: 0;
                transform: translateY(20px);
                transition: all 0.5s ease;
            }}
            .stage-result.show {{
                opacity: 1;
                transform: translateY(0);
            }}
            .stage-result h3 {{
                margin-top: 0;
                color: #333;
                font-size: 1.3em;
                font-weight: 600;
                display: flex;
                align-items: center;
                gap: 10px;
            }}
            .stage-icon {{
                width: 30px;
                height: 30px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 16px;
                color: white;
                background: #667eea;
            }}
            .extracted-text, .json-result {{
                background: #f8f8f8;
                padding: 20px;
                border-radius: 8px;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                white-space: pre-wrap;
                max-height: 200px;
                overflow-y: auto;
                font-size: 13px;
                border: 1px solid #e0e0e0;
                margin-top: 10px;
            }}
            .categorized-menu {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }}
            .category-card {{
                background: white;
                padding: 15px;
                border-radius: 8px;
                border: 1px solid #e0e0e0;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }}
            .category-title {{
                font-weight: 600;
                color: #667eea;
                margin-bottom: 10px;
                font-size: 16px;
                border-bottom: 2px solid #667eea;
                padding-bottom: 5px;
            }}
            .category-items {{
                list-style: none;
                padding: 0;
                margin: 0;
            }}
            .category-items li {{
                padding: 5px 0;
                color: #555;
                font-size: 14px;
                border-bottom: 1px solid #f0f0f0;
            }}
            .category-items li:last-child {{
                border-bottom: none;
            }}
            .menu-category {{
                margin: 20px 0;
                padding: 20px;
                background: linear-gradient(135deg, #f9f9f9, #f0f0f0);
                border-radius: 12px;
                border-left: 5px solid #667eea;
                opacity: 0;
                transform: translateY(20px);
                transition: all 0.5s ease;
            }}
            .menu-category.show {{
                opacity: 1;
                transform: translateY(0);
            }}
            .menu-item {{
                margin: 15px 0;
                padding: 20px;
                background: white;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
                box-shadow: 0 4px 15px rgba(0,0,0,0.05);
                transition: all 0.3s ease;
                position: relative;
            }}
            .menu-item:hover {{
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            }}
            .menu-item.loading-description {{
                border-left: 4px solid #ffa726;
            }}
            .menu-item.loading-description::after {{
                content: '詳細説明を生成中...';
                position: absolute;
                top: 10px;
                right: 15px;
                background: #ffa726;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            }}
            .japanese-name {{ 
                font-weight: 700; 
                color: #333; 
                margin-bottom: 5px;
                font-size: 18px;
            }}
            .english-name {{ 
                font-weight: 600; 
                color: #667eea; 
                margin-bottom: 10px;
                font-size: 20px;
            }}
            .description {{ 
                color: #555; 
                font-size: 15px;
                line-height: 1.5;
                margin-bottom: 10px;
                opacity: 0;
                transform: translateY(10px);
                transition: all 0.5s ease;
            }}
            .description.show {{
                opacity: 1;
                transform: translateY(0);
            }}
            .price {{ 
                color: #764ba2; 
                font-weight: 700; 
                font-size: 18px;
            }}
            .stage-loading {{
                display: flex;
                align-items: center;
                gap: 10px;
                color: #667eea;
                font-weight: 500;
                margin: 15px 0;
            }}
            .stage-loading .mini-spinner {{
                width: 20px;
                height: 20px;
                border: 2px solid #e0e0e0;
                border-top: 2px solid #667eea;
                border-radius: 50%;
                animation: spin 1s linear infinite;
            }}
            .completion-message {{
                background: linear-gradient(135deg, #e8f5e8, #c8e6c9);
                border: 1px solid #4CAF50;
                border-radius: 8px;
                padding: 15px;
                margin: 20px 0;
                text-align: center;
                color: #2e7d32;
                font-weight: 600;
                opacity: 0;
                transform: translateY(20px);
                transition: all 0.5s ease;
            }}
            .completion-message.show {{
                opacity: 1;
                transform: translateY(0);
            }}
            .loading {{
                display: none;
                text-align: center;
                margin: 30px 0;
                padding: 30px;
                background: linear-gradient(135deg, #f0f4f8, #e2e8f0);
                border-radius: 12px;
            }}
            .spinner {{
                border: 4px solid #f3f3f3;
                border-top: 4px solid #667eea;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }}
            @keyframes spin {{
                0% {{ transform: rotate(0deg); }}
                100% {{ transform: rotate(360deg); }}
            }}
            .error {{
                color: #d32f2f;
                background: linear-gradient(135deg, #ffebee, #ffcdd2);
                padding: 15px;
                border-radius: 8px;
                margin: 15px 0;
                border-left: 4px solid #f44336;
            }}
            .success-badge {{
                background: linear-gradient(45deg, #4CAF50, #45a049);
                color: white;
                padding: 5px 15px;
                border-radius: 15px;
                font-size: 12px;
                font-weight: 600;
                margin-left: 10px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="version-badge">MVP - Gemini OCR Powered</div>
                <h1 class="title">🍜 Menu Processor</h1>
                <p class="subtitle">Transform Japanese restaurant menus into detailed English descriptions using Gemini 2.0 Flash OCR technology</p>
            </div>
            
            <div class="status-grid">
                <div class="status-card {'ready' if GEMINI_AVAILABLE else 'error'}">
                    <strong>🎯 Gemini 2.0 Flash OCR</strong><br>
                    {gemini_status}
                    {'<div class="success-badge">Primary OCR Engine</div>' if GEMINI_AVAILABLE else ''}
                </div>
                <div class="status-card {'ready' if VISION_AVAILABLE else 'error'}" style="opacity: 0.6;">
                    <strong>🔍 Google Vision API</strong><br>
                    Disabled (Gemini Mode)
                    <div class="success-badge" style="background: #9e9e9e;">Not Used</div>
                </div>
                <div class="status-card {'ready' if TRANSLATE_AVAILABLE else 'error'}">
                    <strong>🌍 Google Translate API</strong><br>
                    {translate_status}
                    {'<div class="success-badge">Translation Ready</div>' if TRANSLATE_AVAILABLE else ''}
                </div>
                <div class="status-card {'ready' if OPENAI_AVAILABLE else 'error'}">
                    <strong>🤖 OpenAI API</strong><br>
                    {openai_status}
                    {'<div class="success-badge">AI Ready</div>' if OPENAI_AVAILABLE else ''}
                </div>
                <div class="status-card {'ready' if IMAGEN_AVAILABLE else 'error'}">
                    <strong>🎨 Imagen 3</strong><br>
                    {imagen_status}
                    {'<div class="success-badge">Image Generation</div>' if IMAGEN_AVAILABLE else ''}
                </div>
            </div>
            
            <div class="stages">
                <div class="stage" id="stage1">
                    <strong>Stage 1</strong><br>
                    🔍 <strong>OCR</strong><br>
                    <small>Text Extraction</small>
                </div>
                <div class="stage" id="stage2">
                    <strong>Stage 2</strong><br>
                    📋 <strong>Categorize</strong><br>
                    <small>Japanese Structure</small>
                </div>
                <div class="stage" id="stage3">
                    <strong>Stage 3</strong><br>
                    🌍 <strong>Translate</strong><br>
                    <small>English Names</small>
                </div>
                <div class="stage" id="stage4">
                    <strong>Stage 4</strong><br>
                    📝 <strong>Describe</strong><br>
                    <small>Detailed Descriptions</small>
                </div>
                <div class="stage" id="stage5">
                    <strong>Stage 5</strong><br>
                    🎨 <strong>Generate</strong><br>
                    <small>Menu Images</small>
                </div>
                <div class="stage" id="stage6">
                    <strong>Stage 6</strong><br>
                    ✅ <strong>Complete</strong><br>
                    <small>Finalization</small>
                </div>
            </div>
            
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📷</div>
                <h3>Upload Japanese Menu Image</h3>
                <p>Click here or drag & drop your menu image to start processing with <strong>Gemini 2.0 Flash OCR</strong></p>
                <small>Supports JPG, PNG, WEBP formats • Powered by Gemini AI technology</small>
            </div>
            
            <input type="file" id="fileInput" accept="image/*" style="display: none;">
            
            <div class="result-section" id="resultSection"></div>
        </div>

        <script>
            const fileInput = document.getElementById('fileInput');
            const resultSection = document.getElementById('resultSection');

            // Drag and drop functionality
            const uploadArea = document.querySelector('.upload-area');
            
            ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
                uploadArea.addEventListener(eventName, preventDefaults, false);
                document.body.addEventListener(eventName, preventDefaults, false);
            }});

            ['dragenter', 'dragover'].forEach(eventName => {{
                uploadArea.addEventListener(eventName, highlight, false);
            }});

            ['dragleave', 'drop'].forEach(eventName => {{
                uploadArea.addEventListener(eventName, unhighlight, false);
            }});

            uploadArea.addEventListener('drop', handleDrop, false);

            function preventDefaults(e) {{
                e.preventDefault();
                e.stopPropagation();
            }}

            function highlight(e) {{
                uploadArea.style.background = 'linear-gradient(135deg, #c5cae9, #9fa8da)';
            }}

            function unhighlight(e) {{
                uploadArea.style.background = 'linear-gradient(135deg, #f8f9ff, #e8eaf6)';
            }}

            function handleDrop(e) {{
                const dt = e.dataTransfer;
                const files = dt.files;
                if (files.length > 0) {{
                    handleFile(files[0]);
                }}
            }}

            fileInput.addEventListener('change', (e) => {{
                if (e.target.files.length > 0) {{
                    handleFile(e.target.files[0]);
                }}
            }});

            async function handleFile(file) {{
                if (!file.type.startsWith('image/')) {{
                    alert('Please select an image file');
                    return;
                }}

                resetStages();
                resultSection.style.display = 'block';
                
                // 進行状況コンテナを表示
                resultSection.innerHTML = `
                    <div class="progress-container">
                        <div class="progress-title">🔄 メニュー処理中...</div>
                        <div class="stages">
                            <div class="stage" id="progress-stage1">
                                <strong>Stage 1</strong><br>
                                🔍 <strong>OCR</strong><br>
                                <small>Text Extraction</small>
                            </div>
                            <div class="stage" id="progress-stage2">
                                <strong>Stage 2</strong><br>
                                📋 <strong>Categorize</strong><br>
                                <small>Japanese Structure</small>
                            </div>
                            <div class="stage" id="progress-stage3">
                                <strong>Stage 3</strong><br>
                                🌍 <strong>Translate</strong><br>
                                <small>English Names</small>
                            </div>
                            <div class="stage" id="progress-stage4">
                                <strong>Stage 4</strong><br>
                                📝 <strong>Describe</strong><br>
                                <small>Detailed Descriptions</small>
                            </div>
                            <div class="stage" id="progress-stage5">
                                <strong>Stage 5</strong><br>
                                🎨 <strong>Generate</strong><br>
                                <small>Menu Images</small>
                            </div>
                            <div class="stage" id="progress-stage6">
                                <strong>Stage 6</strong><br>
                                ✅ <strong>Complete</strong><br>
                                <small>Finalization</small>
                            </div>
                        </div>
                        <div class="stage-loading">
                            <div class="mini-spinner"></div>
                            処理を開始しています...
                        </div>
                    </div>
                `;

                const formData = new FormData();
                formData.append('file', file);

                try {{
                    // セッション開始
                    const response = await fetch('/api/process-menu', {{
                        method: 'POST',
                        body: formData
                    }});

                    const data = await response.json();
                    const sessionId = data.session_id;
                    
                    // Server-Sent Eventsで進行状況を監視
                    const eventSource = new EventSource(`/api/progress/${{sessionId}}`);
                    
                    eventSource.onmessage = function(event) {{
                        const progressData = JSON.parse(event.data);
                        handleProgressUpdate(progressData);
                    }};
                    
                    eventSource.onerror = function(event) {{
                        console.error('SSE error:', event);
                        eventSource.close();
                    }};
                    
                }} catch (error) {{
                    displayError('Network error: ' + error.message);
                }}
            }}

            function handleProgressUpdate(progress) {{
                console.log('Progress update:', progress);
                
                const stage = progress.stage;
                const status = progress.status;
                const message = progress.message;
                
                // ステージ状態を更新
                updateProgressStage(stage, status);
                updateProgressMessage(message);
                
                // データがある場合は表示
                if (progress.extracted_text) {{
                    showOCRResult(progress.extracted_text);
                }}
                
                if (progress.categories) {{
                    showCategorizationResult(progress.categories);
                }}
                
                if (progress.translated_categories) {{
                    showTranslationResult(progress.translated_categories);
                }}
                
                if (progress.final_menu) {{
                    showFinalMenu(progress.final_menu);
                }}
                
                // 完了時の処理
                if (stage === 6 && status === 'completed') {{
                    showCompletionMessage();
                }}
            }}

            function showOCRResult(extractedText) {{
                const ocrHtml = `
                    <div class="stage-result show">
                        <h3><div class="stage-icon">🔍</div>OCR完了</h3>
                        <p><strong>抽出されたテキスト:</strong></p>
                        <div class="extracted-text">${{extractedText}}</div>
                    </div>
                `;
                appendToResults(ocrHtml);
            }}

            function showCategorizationResult(categories) {{
                const categoriesHtml = `
                    <div class="stage-result show">
                        <h3><div class="stage-icon">📋</div>カテゴリ分析完了</h3>
                        <p><strong>カテゴリ分類結果:</strong></p>
                        <div class="categorized-menu">
                            ${{Object.entries(categories).map(([category, items]) => `
                                <div class="category-card">
                                    <div class="category-title">${{category}}</div>
                                    <ul class="category-items">
                                        ${{items.map(item => `<li>${{item.name}} ${{item.price || ''}}</li>`).join('')}}
                                    </ul>
                                </div>
                            `).join('')}}
                        </div>
                    </div>
                `;
                appendToResults(categoriesHtml);
            }}

            function showTranslationResult(translatedCategories) {{
                const translationHtml = `
                    <div class="stage-result show">
                        <h3><div class="stage-icon">🌍</div>英語翻訳完了</h3>
                        <p>詳細説明を追加中です。翻訳されたメニューをご確認ください...</p>
                        <div id="translatedMenu"></div>
                    </div>
                `;
                appendToResults(translationHtml);
                
                // 翻訳されたメニューを表示
                setTimeout(() => {{
                    displayTranslatedMenu(translatedCategories);
                }}, 100);
            }}

            function showFinalMenu(finalMenu) {{
                // 詳細説明を段階的に追加
                setTimeout(() => {{
                    addDescriptionsProgressively(finalMenu);
                }}, 500);
            }}

            function showCompletionMessage() {{
                const completionHtml = `
                    <div class="completion-message show">
                        ✅ メニュー処理が完了しました！詳細な英語説明付きのメニューをお楽しみください。
                    </div>
                `;
                appendToResults(completionHtml);
            }}

            function resetStages() {{
                for (let i = 1; i <= 6; i++) {{
                    const stage = document.getElementById(`stage${{i}}`);
                    if (stage) {{
                        stage.className = 'stage';
                    }}
                }}
            }}

            function updateStage(stageNum, status) {{
                const stage = document.getElementById(`stage${{stageNum}}`);
                stage.className = `stage ${{status}}`;
            }}

            async function displayResultsProgressively(data) {{
                // Stage 1 & 2: OCR and Categorization (show together)
                if (data.stage1 && data.stage2) {{
                    await showStage1and2(data.stage1, data.stage2);
                }}
                
                // Stage 3: Translation (show translated menu)
                if (data.stage3) {{
                    await showStage3(data.stage3);
                }}
                
                // Stage 4: Add descriptions progressively
                if (data.stage4) {{
                    await showStage4(data.stage4);
                }}
            }}

            async function addDescriptionsProgressively(finalMenu) {{
                const menuItems = document.querySelectorAll('.menu-item');
                
                for (const [categoryIndex, [category, items]] of Object.entries(finalMenu).entries()) {{
                    for (const [itemIndex, item] of items.entries()) {{
                        const menuItemSelector = `.menu-category:nth-child(${{categoryIndex + 1}}) .menu-item:nth-child(${{itemIndex + 1}})`;
                        const menuItemElement = document.querySelector(menuItemSelector);
                        
                        if (menuItemElement) {{
                            // ローディング状態を表示
                            menuItemElement.classList.add('loading-description');
                            
                            await sleep(300 + Math.random() * 500); // ランダムな間隔で追加
                            
                            // 詳細説明を追加
                            const descriptionElement = menuItemElement.querySelector('.description');
                            if (descriptionElement) {{
                                descriptionElement.textContent = item.description;
                                descriptionElement.classList.add('show');
                                menuItemElement.classList.remove('loading-description');
                            }}
                        }}
                    }}
                }}
            }}

            function displayTranslatedMenu(translatedCategories) {{
                const translatedMenuDiv = document.getElementById('translatedMenu');
                if (!translatedMenuDiv) return;

                let menuHtml = '';
                
                for (const [category, items] of Object.entries(translatedCategories)) {{
                    if (items.length > 0) {{
                        menuHtml += `
                            <div class="menu-category">
                                <h4 style="margin: 0 0 15px 0; color: #333; font-size: 1.3em;">${{category}}</h4>
                        `;
                        
                        for (const item of items) {{
                            menuHtml += `
                                <div class="menu-item">
                                    <div class="japanese-name">${{item.japanese_name || 'N/A'}}</div>
                                    <div class="english-name">${{item.english_name || 'N/A'}}</div>
                                    <div class="description">詳細説明を生成中...</div>
                                    ${{item.price ? `<div class="price">${{item.price}}</div>` : ''}}
                                </div>
                            `;
                        }}
                        
                        menuHtml += '</div>';
                    }}
                }}
                
                translatedMenuDiv.innerHTML = menuHtml;
                
                // アニメーションで表示
                setTimeout(() => {{
                    document.querySelectorAll('.menu-category').forEach((category, index) => {{
                        setTimeout(() => {{
                            category.classList.add('show');
                        }}, index * 200);
                    }});
                }}, 100);
            }}

            function updateProgressStage(stageNum, status) {{
                const stage = document.getElementById(`progress-stage${{stageNum}}`);
                if (stage) {{
                    stage.className = `stage ${{status}}`;
                }}
            }}

            function updateProgressMessage(message) {{
                const loadingElement = document.querySelector('.stage-loading');
                if (loadingElement) {{
                    loadingElement.innerHTML = `
                        <div class="mini-spinner"></div>
                        ${{message}}
                    `;
                }}
            }}

            function appendToResults(html) {{
                const currentContent = resultSection.innerHTML;
                resultSection.innerHTML = currentContent + html;
            }}

            function sleep(ms) {{
                return new Promise(resolve => setTimeout(resolve, ms));
            }}

            function displayError(message) {{
                resultSection.innerHTML = `
                    <h2>❌ Processing Failed</h2>
                    <div class="error">
                        <strong>Error:</strong> ${{message}}
                    </div>
                `;
                resultSection.style.display = 'block';
            }}
        </script>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content) 