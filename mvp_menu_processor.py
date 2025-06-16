from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv
import aiofiles
import io
import json
import asyncio
import uuid
from typing import Dict, AsyncGenerator

# 環境変数の読み込み
load_dotenv()

app = FastAPI(title="Menu Processor MVP", version="1.0.0")

# CORS設定（モバイル対応版）
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "https://menu-sense-frontend.vercel.app",
        "https://speeches-plastic-excitement-reproduced.trycloudflare.com",  # 全てのVercelドメインを許可
        "https://menu-sense-frontend-*.vercel.app",  # ブランチデプロイ対応
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # モバイル対応
)

# 静的ファイルとアップロードディレクトリの設定
os.makedirs("uploads", exist_ok=True)

# 進行状況を管理するための辞書
progress_store = {}

# Google Cloud認証情報の設定
google_credentials = None
google_credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")

if google_credentials_json:
    try:
        import json
        from google.oauth2 import service_account
        
        # 改行文字やエスケープシーケンスを正規
        
        # JSON文字列をパース
        credentials_info = json.loads(google_credentials_json)
        google_credentials = service_account.Credentials.from_service_account_info(credentials_info)
        print("✅ Google Cloud credentials loaded from environment variable")
    except json.JSONDecodeError as e:
        print(f"⚠️ Failed to parse Google credentials JSON: {e}")
        print(f"   First 100 chars: {google_credentials_json[:100]}...")
        google_credentials = None
    except Exception as e:
        print(f"⚠️ Failed to load Google credentials: {e}")
        google_credentials = None
else:
    print("⚠️ GOOGLE_CREDENTIALS_JSON not found in environment variables")

# Google Vision APIのインポートとエラーハンドリング
try:
    from google.cloud import vision
    
    if google_credentials:
        vision_client = vision.ImageAnnotatorClient(credentials=google_credentials)
    else:
        vision_client = vision.ImageAnnotatorClient()  # デフォルト認証を試行
    
    VISION_AVAILABLE = True
    print("✅ Google Vision API client initialized successfully")
except Exception as e:
    VISION_AVAILABLE = False
    print(f"❌ Google Vision API initialization failed: {e}")
    vision_client = None

# Google Translate APIのインポートとエラーハンドリング
try:
    from google.cloud import translate_v2 as translate
    
    if google_credentials:
        translate_client = translate.Client(credentials=google_credentials)
    else:
        translate_client = translate.Client()  # デフォルト認証を試行
    
    TRANSLATE_AVAILABLE = True
    print("✅ Google Translate API client initialized successfully")
except Exception as e:
    TRANSLATE_AVAILABLE = False
    translate_client = None
    print(f"❌ Google Translate API initialization failed: {e}")
    print("   Note: Install with 'pip install google-cloud-translate' and set up authentication")

# OpenAI APIの設定
try:
    import openai
    from openai import AsyncOpenAI
    import time
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    OPENAI_AVAILABLE = bool(openai_api_key)
    
    if OPENAI_AVAILABLE:
        # AsyncOpenAIクライアントを初期化（タイムアウトとリトライ設定付き）
        openai_client = AsyncOpenAI(
            api_key=openai_api_key,
            timeout=120.0,  # 120秒タイムアウト
            max_retries=3   # 最大3回リトライ
        )
    
    print(f"{'✅' if OPENAI_AVAILABLE else '❌'} OpenAI API {'configured' if OPENAI_AVAILABLE else 'not configured'}")
except Exception as e:
    OPENAI_AVAILABLE = False
    openai_client = None
    print(f"❌ OpenAI API initialization failed: {e}")

# Gemini APIの設定
try:
    import google.generativeai as genai
    import base64
    
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    GEMINI_AVAILABLE = bool(gemini_api_key)
    
    if GEMINI_AVAILABLE:
        genai.configure(api_key=gemini_api_key)
        # Gemini 2.0 Flash modelを使用
        gemini_model = genai.GenerativeModel('gemini-2.0-flash-exp')
        print("✅ Gemini 2.0 Flash API configured successfully")
    else:
        gemini_model = None
        print("⚠️ GEMINI_API_KEY not found in environment variables")
    
except ImportError:
    GEMINI_AVAILABLE = False
    gemini_model = None
    print("❌ google-generativeai package not installed. Install with: pip install google-generativeai")
except Exception as e:
    GEMINI_AVAILABLE = False
    gemini_model = None
    print(f"❌ Gemini API initialization failed: {e}")

# Function calling用のスキーマ定義
CATEGORIZE_FUNCTION = {
    "name": "categorize_menu_items",
    "description": "日本語のメニューテキストを分析してカテゴリ別に分類する",
    "parameters": {
        "type": "object",
        "properties": {
            "categories": {
                "type": "object",
                "properties": {
                    "前菜": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "料理名"},
                                "price": {"type": "string", "description": "価格"},
                                "description": {"type": "string", "description": "簡潔な説明"}
                            },
                            "required": ["name"]
                        }
                    },
                    "メイン": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "料理名"},
                                "price": {"type": "string", "description": "価格"},
                                "description": {"type": "string", "description": "簡潔な説明"}
                            },
                            "required": ["name"]
                        }
                    },
                    "ドリンク": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "料理名"},
                                "price": {"type": "string", "description": "価格"},
                                "description": {"type": "string", "description": "簡潔な説明"}
                            },
                            "required": ["name"]
                        }
                    },
                    "デザート": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "料理名"},
                                "price": {"type": "string", "description": "価格"},
                                "description": {"type": "string", "description": "簡潔な説明"}
                            },
                            "required": ["name"]
                        }
                    }
                },
                "required": ["前菜", "メイン", "ドリンク", "デザート"]
            },
            "uncategorized": {
                "type": "array",
                "items": {"type": "string"},
                "description": "分類できなかった項目"
            }
        },
        "required": ["categories", "uncategorized"]
    }
}

TRANSLATE_FUNCTION = {
    "name": "translate_menu_categories",
    "description": "日本語でカテゴリ分類されたメニューを英語に翻訳する",
    "parameters": {
        "type": "object",
        "properties": {
            "translated_categories": {
                "type": "object",
                "properties": {
                    "Appetizers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "japanese_name": {"type": "string", "description": "元の日本語名"},
                                "english_name": {"type": "string", "description": "英語名"},
                                "price": {"type": "string", "description": "価格"}
                            },
                            "required": ["japanese_name", "english_name"]
                        }
                    },
                    "Main Dishes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "japanese_name": {"type": "string", "description": "元の日本語名"},
                                "english_name": {"type": "string", "description": "英語名"},
                                "price": {"type": "string", "description": "価格"}
                            },
                            "required": ["japanese_name", "english_name"]
                        }
                    },
                    "Drinks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "japanese_name": {"type": "string", "description": "元の日本語名"},
                                "english_name": {"type": "string", "description": "英語名"},
                                "price": {"type": "string", "description": "価格"}
                            },
                            "required": ["japanese_name", "english_name"]
                        }
                    },
                    "Desserts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "japanese_name": {"type": "string", "description": "元の日本語名"},
                                "english_name": {"type": "string", "description": "英語名"},
                                "price": {"type": "string", "description": "価格"}
                            },
                            "required": ["japanese_name", "english_name"]
                        }
                    }
                },
                "required": ["Appetizers", "Main Dishes", "Drinks", "Desserts"]
            }
        },
        "required": ["translated_categories"]
    }
}

ADD_DESCRIPTIONS_FUNCTION = {
    "name": "add_detailed_descriptions",
    "description": "翻訳されたメニューに外国人観光客向けの詳細説明を追加する",
    "parameters": {
        "type": "object",
        "properties": {
            "final_menu": {
                "type": "object",
                "properties": {
                    "Appetizers": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "japanese_name": {"type": "string", "description": "日本語名"},
                                "english_name": {"type": "string", "description": "英語名"},
                                "description": {"type": "string", "description": "詳細な英語説明"},
                                "price": {"type": "string", "description": "価格"}
                            },
                            "required": ["japanese_name", "english_name", "description"]
                        }
                    },
                    "Main Dishes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "japanese_name": {"type": "string", "description": "日本語名"},
                                "english_name": {"type": "string", "description": "英語名"},
                                "description": {"type": "string", "description": "詳細な英語説明"},
                                "price": {"type": "string", "description": "価格"}
                            },
                            "required": ["japanese_name", "english_name", "description"]
                        }
                    },
                    "Drinks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "japanese_name": {"type": "string", "description": "日本語名"},
                                "english_name": {"type": "string", "description": "英語名"},
                                "description": {"type": "string", "description": "詳細な英語説明"},
                                "price": {"type": "string", "description": "価格"}
                            },
                            "required": ["japanese_name", "english_name", "description"]
                        }
                    },
                    "Desserts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "japanese_name": {"type": "string", "description": "日本語名"},
                                "english_name": {"type": "string", "description": "英語名"},
                                "description": {"type": "string", "description": "詳細な英語説明"},
                                "price": {"type": "string", "description": "価格"}
                            },
                            "required": ["japanese_name", "english_name", "description"]
                        }
                    }
                },
                "required": ["Appetizers", "Main Dishes", "Drinks", "Desserts"]
            }
        },
        "required": ["final_menu"]
    }
}

# OpenAI API 呼び出し用のリトライ関数（指数バックオフ付き）
async def call_openai_with_retry(messages, functions=None, function_call=None, max_retries=3):
    """指数バックオフ付きでOpenAI APIを呼び出すリトライ関数"""
    if not OPENAI_AVAILABLE or not openai_client:
        raise Exception("OpenAI API is not available")
    
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                "model": "gpt-4.1-nano",
                "messages": messages
            }
            
            if functions:
                kwargs["functions"] = functions
            if function_call:
                kwargs["function_call"] = function_call
            
            response = await openai_client.chat.completions.create(**kwargs)
            return response
            
        except openai.RateLimitError as e:
            if attempt == max_retries:
                raise Exception(f"Rate limit exceeded after {max_retries + 1} attempts: {str(e)}")
            
            # 指数バックオフ（2^attempt秒待機）
            wait_time = 2 ** attempt
            print(f"⏳ Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(wait_time)
            
        except openai.APITimeoutError as e:
            if attempt == max_retries:
                raise Exception(f"API timeout after {max_retries + 1} attempts: {str(e)}")
            
            wait_time = 2 ** attempt
            print(f"⏳ API timeout, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(wait_time)
            
        except openai.APIConnectionError as e:
            if attempt == max_retries:
                raise Exception(f"API connection error after {max_retries + 1} attempts: {str(e)}")
            
            wait_time = 2 ** attempt
            print(f"⏳ Connection error, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            # その他のエラーは即座に失敗
            raise Exception(f"OpenAI API error: {str(e)}")

# 進行状況を送信する関数（Ping/Pong対応版 + リアルタイム反映強化）
async def send_progress(session_id: str, stage: int, status: str, message: str, data: dict = None):
    """進行状況をクライアントに送信（Ping/Pong対応 + リアルタイム反映強化）"""
    progress_data = {
        "stage": stage,
        "status": status,
        "message": message,
        "timestamp": asyncio.get_event_loop().time()
    }
    if data:
        progress_data.update(data)
    
    if session_id in progress_store:
        progress_store[session_id].append(progress_data)
        
        # 送信データの詳細ログ（デバッグ用）
        data_keys = list(data.keys()) if data else []
        data_summary = {}
        if data:
            for key in ['translatedCategories', 'translated_categories', 'partial_results', 'partial_menu', 'processing_category']:
                if key in data:
                    if isinstance(data[key], dict):
                        data_summary[key] = f"{len(data[key])} categories"
                    else:
                        data_summary[key] = str(data[key])
        
        print(f"📤 SSE Data sent for {session_id}: Stage {stage} - {status}")
        print(f"   📋 Message: {message}")
        print(f"   🔑 Data keys: {data_keys}")
        print(f"   📊 Data summary: {data_summary}")
        
        # Stage別の詳細ログ
        if stage == 3:
            if data and ('translatedCategories' in data or 'translated_categories' in data):
                translated_data = data.get('translatedCategories') or data.get('translated_categories')
                if translated_data and isinstance(translated_data, dict):
                    print(f"   🌍 Stage 3 translation data: {len(translated_data)} categories")
                    for cat_name, items in translated_data.items():
                        if isinstance(items, list):
                            print(f"      - {cat_name}: {len(items)} items")
        
        elif stage == 4:
            if data:
                if "processing_category" in data:
                    print(f"   🍽️ Processing: {data['processing_category']}")
                if "category_completed" in data:
                    print(f"   ✅ Completed: {data['category_completed']}")
                if "progress_percent" in data:
                    print(f"   📊 Progress: {data['progress_percent']}%")
                if "partial_results" in data and isinstance(data['partial_results'], dict):
                    print(f"   🔄 Partial results: {len(data['partial_results'])} categories")
                if "partial_menu" in data and isinstance(data['partial_menu'], dict):
                    print(f"   🔄 Partial menu: {len(data['partial_menu'])} categories")
            
            # Stage 4でのPing/Pong開始（重複回避）
            if status == "active" and not hasattr(send_progress, f'ping_scheduled_{session_id}'):
                setattr(send_progress, f'ping_scheduled_{session_id}', True)
                asyncio.create_task(start_ping_pong(session_id))

# Ping送信関数
async def send_ping(session_id: str):
    """クライアントにPingを送信"""
    if session_id in progress_store:
        ping_data = {
            "type": "ping",
            "timestamp": asyncio.get_event_loop().time(),
            "session_id": session_id
        }
        progress_store[session_id].append(ping_data)
        print(f"🏓 Ping sent to {session_id}")

# Ping/Pong管理
ping_pong_sessions = {}  # session_id -> {"last_pong": timestamp, "ping_count": int}

async def start_ping_pong(session_id: str):
    """Ping/Pong機能を開始"""
    print(f"🏓 Starting Ping/Pong for session {session_id}")
    
    ping_pong_sessions[session_id] = {
        "last_pong": asyncio.get_event_loop().time(),
        "ping_count": 0,
        "active": True
    }
    
    ping_interval = 15  # 15秒間隔でPing送信
    max_no_pong_time = 60  # 60秒Pongなしでタイムアウト
    
    try:
        while session_id in progress_store and ping_pong_sessions.get(session_id, {}).get("active", False):
            # Ping送信
            await send_ping(session_id)
            ping_pong_sessions[session_id]["ping_count"] += 1
            
            # Pongチェック
            current_time = asyncio.get_event_loop().time()
            last_pong = ping_pong_sessions[session_id]["last_pong"]
            
            if current_time - last_pong > max_no_pong_time:
                print(f"⚠️ No Pong received from {session_id} for {max_no_pong_time}s, connection may be lost")
                # 接続切断を検知（ただし処理は継続）
                await send_progress(session_id, 0, "warning", 
                                  f"Connection unstable (no response for {max_no_pong_time}s)", 
                                  {"connection_warning": True})
            
            await asyncio.sleep(ping_interval)
            
    except asyncio.CancelledError:
        print(f"🏓 Ping/Pong cancelled for session {session_id}")
    except Exception as e:
        print(f"⚠️ Ping/Pong error for session {session_id}: {e}")
    finally:
        # クリーンアップ
        if session_id in ping_pong_sessions:
            del ping_pong_sessions[session_id]
        if hasattr(send_progress, f'ping_scheduled_{session_id}'):
            delattr(send_progress, f'ping_scheduled_{session_id}')
        print(f"🏓 Ping/Pong cleanup completed for {session_id}")

# Pong受信処理
async def handle_pong(session_id: str):
    """クライアントからのPongを処理"""
    if session_id in ping_pong_sessions:
        ping_pong_sessions[session_id]["last_pong"] = asyncio.get_event_loop().time()
        print(f"🏓 Pong received from {session_id}")
        return True
    return False

# 注意: この関数は廃止されました。Ping/Pong機能を使用してください。
# Stage 4専用のハートビート機能（廃止済み - Ping/Pongに置き換え）
async def stage4_heartbeat(session_id: str, initial_message: str):
    """Stage 4専用のハートビート機能（廃止済み - Ping/Pongに置き換え）"""
    print(f"💓 Legacy heartbeat function called for {session_id}, but Ping/Pong is now used instead")
    # この関数は何もしない（Ping/Pong機能が置き換え）
    pass

# Stage 1: OCR - 文字認識
async def stage1_ocr(image_path: str, session_id: str = None) -> dict:
    """Stage 1: Google Vision APIを使って画像からテキストを抽出"""
    print("🔍 Stage 1: Starting OCR...")
    
    # Vision API利用可能性チェック
    if not VISION_AVAILABLE:
        error_message = "Google Vision APIが利用できません。管理者に問い合わせてください。"
        detailed_error = {
            "error_type": "api_unavailable",
            "service": "Google Vision API",
            "troubleshooting": [
                "GOOGLE_CREDENTIALS_JSON環境変数が設定されているか確認してください",
                "Google Cloud Vision APIが有効化されているか確認してください",
                "サービスアカウントキーが正しく設定されているか確認してください"
            ]
        }
        
        error_result = {
            "stage": 1,
            "success": False,
            "error": error_message,
            "detailed_error": detailed_error,
            "extracted_text": ""
        }
        
        if session_id:
            await send_progress(session_id, 1, "error", error_message, detailed_error)
        return error_result
    
    # 画像ファイル存在チェック
    if not os.path.exists(image_path):
        error_message = "画像ファイルが見つかりません"
        error_result = {
            "stage": 1,
            "success": False,
            "error": error_message,
            "detailed_error": {"error_type": "file_not_found", "file_path": image_path},
            "extracted_text": ""
        }
        
        if session_id:
            await send_progress(session_id, 1, "error", error_message)
        return error_result
    
    try:
        # 画像ファイル読み込み
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()

        # ファイルサイズチェック
        if len(content) == 0:
            raise Exception("画像ファイルが空です")
        
        if len(content) > 20 * 1024 * 1024:  # 20MB制限
            raise Exception("画像ファイルが大きすぎます（20MB以下にしてください）")

        # Vision API呼び出し
        image = vision.Image(content=content)
        response = vision_client.text_detection(image=image)
        
        # エラーレスポンスチェック
        if response.error.message:
            raise Exception(f'Vision API Error: {response.error.message}')
        
        # テキスト抽出
        texts = response.text_annotations
        extracted_text = texts[0].description if texts else ""
        
        print(f"✅ Stage 1 Complete: Extracted {len(extracted_text)} characters")
        
        # 結果が空の場合の処理
        if not extracted_text.strip():
            warning_message = "画像からテキストを検出できませんでした。より鮮明な画像をお試しください。"
            result = {
                "stage": 1,
                "success": False,
                "error": warning_message,
                "detailed_error": {
                    "error_type": "no_text_detected",
                    "suggestions": [
                        "より鮮明な画像を使用してください",
                        "文字が大きく写っている画像を選んでください",
                        "照明が良い環境で撮影した画像を使用してください",
                        "メニューテキストが中央に写っている画像を選んでください"
                    ]
                },
                "extracted_text": ""
            }
            
            if session_id:
                await send_progress(session_id, 1, "error", warning_message, result["detailed_error"])
            
            return result
        
        # 成功結果
        result = {
            "stage": 1,
            "success": True,
            "extracted_text": extracted_text,
            "total_detections": len(texts),
            "file_size": len(content),
            "text_length": len(extracted_text)
        }
        
        if session_id:
            await send_progress(session_id, 1, "completed", "OCR完了", {
                "extracted_text": extracted_text,
                "total_detections": len(texts),
                "text_preview": extracted_text[:100] + "..." if len(extracted_text) > 100 else extracted_text
            })
        
        return result
            
    except Exception as e:
        print(f"❌ Stage 1 Failed: {e}")
        
        # エラータイプの判定
        error_type = "unknown_error"
        suggestions = []
        
        if "permission" in str(e).lower() or "forbidden" in str(e).lower():
            error_type = "permission_error"
            suggestions = [
                "Google Cloud認証が正しく設定されているか確認してください",
                "サービスアカウントにVision API権限があるか確認してください"
            ]
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_type = "quota_exceeded"
            suggestions = [
                "Vision APIクォータを確認してください",
                "しばらく時間をおいてから再試行してください"
            ]
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            error_type = "network_error"
            suggestions = [
                "インターネット接続を確認してください",
                "しばらく時間をおいてから再試行してください"
            ]
        else:
            suggestions = [
                "画像ファイルが破損していないか確認してください",
                "サポートされている画像形式（JPG、PNG、GIF）を使用してください",
                "しばらく時間をおいてから再試行してください"
            ]
        
        detailed_error = {
            "error_type": error_type,
            "original_error": str(e),
            "suggestions": suggestions
        }
        
        error_result = {
            "stage": 1,
            "success": False,
            "error": f"OCR処理中にエラーが発生しました: {str(e)}",
            "detailed_error": detailed_error,
            "extracted_text": ""
        }
        
        if session_id:
            await send_progress(session_id, 1, "error", f"OCRエラー: {str(e)}", detailed_error)
        
        return error_result

# Stage 1: OCR with Gemini 2.0 Flash - 高精度版
async def stage1_ocr_gemini(image_path: str, session_id: str = None) -> dict:
    """Stage 1: Gemini 2.0 Flashを使って画像からテキストを抽出（高精度版）"""
    print("🔍 Stage 1: Starting OCR with Gemini 2.0 Flash...")
    
    # Gemini API利用可能性チェック
    if not GEMINI_AVAILABLE or not gemini_model:
        error_message = "Gemini APIが利用できません。GEMINI_API_KEYが設定されているか確認してください。"
        detailed_error = {
            "error_type": "api_unavailable",
            "service": "Gemini 2.0 Flash API",
            "troubleshooting": [
                "GEMINI_API_KEY環境変数が設定されているか確認してください",
                "google-generativeaiパッケージがインストールされているか確認してください",
                "Gemini APIが有効化されているか確認してください"
            ]
        }
        
        error_result = {
            "stage": 1,
            "success": False,
            "error": error_message,
            "detailed_error": detailed_error,
            "extracted_text": ""
        }
        
        if session_id:
            await send_progress(session_id, 1, "error", error_message, detailed_error)
        return error_result
    
    # 画像ファイル存在チェック
    if not os.path.exists(image_path):
        error_message = "画像ファイルが見つかりません"
        error_result = {
            "stage": 1,
            "success": False,
            "error": error_message,
            "detailed_error": {"error_type": "file_not_found", "file_path": image_path},
            "extracted_text": ""
        }
        
        if session_id:
            await send_progress(session_id, 1, "error", error_message)
        return error_result
    
    try:
        # 画像ファイル読み込み
        with open(image_path, 'rb') as image_file:
            image_data = image_file.read()

        # ファイルサイズチェック
        if len(image_data) == 0:
            raise Exception("画像ファイルが空です")
        
        if len(image_data) > 20 * 1024 * 1024:  # 20MB制限
            raise Exception("画像ファイルが大きすぎます（20MB以下にしてください）")

        # 画像をbase64エンコード
        import base64
        import mimetypes
        
        # ファイルタイプの検出
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type or not mime_type.startswith('image/'):
            mime_type = 'image/jpeg'  # デフォルト
        
        # Gemini用の画像データ準備
        image_parts = [
            {
                "mime_type": mime_type,
                "data": image_data
            }
        ]

        # メニュー画像OCR用のプロンプト（飲食店特化）
        prompt = """
この画像は日本の飲食店のメニューです。以下の要件に従ってテキストを抽出してください：

1. 料理名、価格、説明を正確に読み取る
2. メニューの視覚的構造（セクション、カテゴリ）を保持する
3. 「ドリンク」「メイン」「前菜」「デザート」などの基本カテゴリを推測して分類
4. 文字が不鮮明な場合は可能な限り推測
5. 価格表記（円、¥など）を正確に抽出
6. テキストの読み取り順序を視覚的な配置に合わせる

抽出形式:
- カテゴリごとに整理
- 各料理について： 料理名 価格（ある場合）
- セクション間に空行を入れる
- 推測したカテゴリ名は [カテゴリ名] の形式で記載

画像から読み取れる全てのテキストを丁寧に抽出してください。
        """

        # Gemini APIに画像とプロンプトを送信
        response = gemini_model.generate_content([prompt] + image_parts)
        
        # レスポンスからテキストを抽出
        if response.text:
            extracted_text = response.text.strip()
        else:
            extracted_text = ""
        
        print(f"✅ Stage 1 (Gemini) Complete: Extracted {len(extracted_text)} characters")
        
        # 結果が空の場合の処理
        if not extracted_text.strip():
            warning_message = "画像からテキストを検出できませんでした。より鮮明な画像をお試しください。"
            result = {
                "stage": 1,
                "success": False,
                "error": warning_message,
                "detailed_error": {
                    "error_type": "no_text_detected",
                    "suggestions": [
                        "より鮮明な画像を使用してください",
                        "文字が大きく写っている画像を選んでください",
                        "照明が良い環境で撮影した画像を使用してください",
                        "メニューテキストが中央に写っている画像を選んでください"
                    ]
                },
                "extracted_text": ""
            }
            
            if session_id:
                await send_progress(session_id, 1, "error", warning_message, result["detailed_error"])
            
            return result
        
        # 成功結果
        result = {
            "stage": 1,
            "success": True,
            "extracted_text": extracted_text,
            "file_size": len(image_data),
            "text_length": len(extracted_text),
            "ocr_method": "gemini_2.0_flash"
        }
        
        if session_id:
            await send_progress(session_id, 1, "completed", "OCR完了 (Gemini 2.0 Flash)", {
                "extracted_text": extracted_text,
                "text_preview": extracted_text[:100] + "..." if len(extracted_text) > 100 else extracted_text,
                "ocr_method": "gemini_2.0_flash"
            })
        
        return result
            
    except Exception as e:
        print(f"❌ Stage 1 (Gemini) Failed: {e}")
        
        # エラータイプの判定
        error_type = "unknown_error"
        suggestions = []
        
        if "api" in str(e).lower() and "key" in str(e).lower():
            error_type = "api_key_error"
            suggestions = [
                "GEMINI_API_KEYが正しく設定されているか確認してください",
                "Gemini APIキーが有効であることを確認してください"
            ]
        elif "quota" in str(e).lower() or "limit" in str(e).lower():
            error_type = "quota_exceeded"
            suggestions = [
                "Gemini APIクォータを確認してください",
                "しばらく時間をおいてから再試行してください"
            ]
        elif "permission" in str(e).lower() or "forbidden" in str(e).lower():
            error_type = "permission_error"
            suggestions = [
                "Gemini API権限を確認してください",
                "APIキーが正しく設定されているか確認してください"
            ]
        elif "network" in str(e).lower() or "connection" in str(e).lower():
            error_type = "network_error"
            suggestions = [
                "インターネット接続を確認してください",
                "しばらく時間をおいてから再試行してください"
            ]
        else:
            suggestions = [
                "画像ファイルが破損していないか確認してください",
                "サポートされている画像形式（JPG、PNG、GIF、WEBP）を使用してください",
                "しばらく時間をおいてから再試行してください"
            ]
        
        detailed_error = {
            "error_type": error_type,
            "original_error": str(e),
            "suggestions": suggestions,
            "ocr_method": "gemini_2.0_flash"
        }
        
        error_result = {
            "stage": 1,
            "success": False,
            "error": f"Gemini OCR処理中にエラーが発生しました: {str(e)}",
            "detailed_error": detailed_error,
            "extracted_text": ""
        }
        
        if session_id:
            await send_progress(session_id, 1, "error", f"Gemini OCRエラー: {str(e)}", detailed_error)
        
        return error_result

# Stage 2: 日本語のままカテゴリ分類・枠組み作成 (Function Calling版)
async def stage2_categorize(extracted_text: str, session_id: str = None) -> dict:
    """Stage 2: Function Callingを使って抽出されたテキストを日本語のままカテゴリ分類"""
    print("📋 Stage 2: Starting Japanese categorization with Function Calling...")
    
    if not OPENAI_AVAILABLE:
        error_result = {
            "stage": 2,
            "success": False,
            "error": "OpenAI API not available",
            "categories": {}
        }
        if session_id:
            await send_progress(session_id, 2, "error", "OpenAI API not available")
        return error_result
    
    try:
        messages = [
            {
                "role": "user",
                "content": f"""以下の日本語レストランメニューテキストを分析し、料理をカテゴリ別に整理してください。

テキスト:
{extracted_text}

要件:
1. 料理名を抽出
2. 適切なカテゴリに分類（前菜、メイン、ドリンク、デザートなど）
3. 価格があれば抽出
4. 日本語のまま処理（翻訳はしない）
5. 料理名が明確でない場合は、uncategorizedに含めてください
"""
            }
        ]
        
        response = await call_openai_with_retry(
            messages=messages,
            functions=[CATEGORIZE_FUNCTION],
            function_call={"name": "categorize_menu_items"}
        )
        
        function_call = response.choices[0].message.function_call
        if function_call and function_call.name == "categorize_menu_items":
            result = json.loads(function_call.arguments)
            
            print(f"✅ Stage 2 Complete: Categorized into {len(result.get('categories', {}))} categories")
            
            return {
                "stage": 2,
                "success": True,
                "categories": result.get("categories", {}),
                "uncategorized": result.get("uncategorized", [])
            }
        else:
            raise ValueError("Function call not found in response")
            
    except Exception as e:
        print(f"❌ Stage 2 Failed: {e}")
        return {
            "stage": 2,
            "success": False,
            "error": str(e),
            "categories": {}
        }

# Stage 3: 翻訳 (Google Translate版) - リアルタイム反映強化
async def stage3_translate(categorized_data: dict, session_id: str = None) -> dict:
    """Stage 3: Google Translate APIを使ってカテゴリ分類された料理を英語に翻訳（リアルタイム反映強化）"""
    print("🌍 Stage 3: Starting translation with Google Translate API...")
    
    if not TRANSLATE_AVAILABLE:
        print("⚠️ Google Translate API not available, falling back to OpenAI...")
        return await stage3_translate_openai_fallback(categorized_data, session_id)
    
    try:
        # カテゴリ名のマッピング（日本語→英語）
        category_mapping = {
            "前菜": "Appetizers",
            "メイン": "Main Dishes", 
            "ドリンク": "Drinks",
            "デザート": "Desserts",
            "飲み物": "Beverages",
            "お酒": "Alcoholic Beverages",
            "サラダ": "Salads",
            "スープ": "Soups",
            "パスタ": "Pasta",
            "ピザ": "Pizza",
            "肉料理": "Meat Dishes",
            "魚料理": "Seafood",
            "鍋料理": "Hot Pot",
            "揚げ物": "Fried Foods",
            "焼き物": "Grilled Foods",
            "その他": "Others"
        }
        
        translated_categories = {}
        total_items = sum(len(items) for items in categorized_data.values())
        processed_items = 0
        
        print(f"🔢 Total items to translate: {total_items}")
        
        for japanese_category, items in categorized_data.items():
            if not items:
                continue
                
            # カテゴリ名を翻訳（マッピングにない場合はGoogle Translateを使用）
            if japanese_category in category_mapping:
                english_category = category_mapping[japanese_category]
                print(f"📋 Using predefined mapping: {japanese_category} → {english_category}")
            else:
                try:
                    category_result = translate_client.translate(
                        japanese_category,
                        source_language='ja',
                        target_language='en'
                    )
                    english_category = category_result['translatedText']
                    print(f"📋 Google Translate: {japanese_category} → {english_category}")
                except Exception as e:
                    print(f"⚠️ Category translation failed for '{japanese_category}': {e}")
                    english_category = japanese_category  # フォールバック
            
            # 進行状況を送信（カテゴリー開始）
            if session_id:
                await send_progress(
                    session_id, 3, "active", 
                    f"🌍 Translating {japanese_category}...",
                    {
                        "processing_category": japanese_category,
                        "total_categories": len(categorized_data),
                        "translatedCategories": translated_categories  # リアルタイム反映用
                    }
                )
            
            translated_items = []
            
            # 各料理を翻訳
            for item_index, item in enumerate(items):
                # uncategorizedリストの文字列要素を適切に処理
                if isinstance(item, str):
                    item_name = item
                    item_price = ""
                elif isinstance(item, dict):
                    item_name = item.get("name", "")
                    item_price = item.get("price", "")
                else:
                    print(f"⚠️ Unexpected item type in {japanese_category}: {type(item)} - {item}")
                    continue
                
                if not item_name.strip():
                    continue
                
                try:
                    # Google Translate APIで料理名を翻訳
                    translation_result = translate_client.translate(
                        item_name,
                        source_language='ja',
                        target_language='en'
                    )
                    
                    english_name = translation_result['translatedText']
                    
                    # 翻訳結果をクリーンアップ（HTMLエンティティなど）
                    import html
                    english_name = html.unescape(english_name)
                    
                    translated_items.append({
                        "japanese_name": item_name,
                        "english_name": english_name,
                        "price": item_price
                    })
                    
                    processed_items += 1
                    
                    print(f"  ✅ {item_name} → {english_name}")
                    
                    # アイテム単位でのリアルタイム更新（3つごと、またはカテゴリー完了時）
                    if (len(translated_items) % 3 == 0) or (item_index == len(items) - 1):
                        # 現在のカテゴリーの部分的な翻訳結果を送信
                        current_translated = translated_categories.copy()
                        current_translated[english_category] = translated_items.copy()
                        
                        progress_percent = int((processed_items / total_items) * 100) if total_items > 0 else 100
                        
                        if session_id:
                            await send_progress(
                                session_id, 3, "active", 
                                f"🌍 {japanese_category}: {len(translated_items)}/{len(items)} items translated",
                                {
                                    "progress_percent": progress_percent,
                                    "processing_category": japanese_category,
                                    "translatedCategories": current_translated,  # リアルタイム更新
                                    "category_progress": f"{len(translated_items)}/{len(items)}"
                                }
                            )
                    
                    # レート制限対策
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    print(f"  ⚠️ Translation failed for '{item_name}': {e}")
                    # 翻訳失敗時はオリジナルの日本語名を英語名としても使用
                    translated_items.append({
                        "japanese_name": item_name,
                        "english_name": item_name,  # フォールバック
                        "price": item_price
                    })
                    processed_items += 1
            
            if translated_items:
                translated_categories[english_category] = translated_items
                
                # カテゴリー完了通知（リアルタイム反映）
                if session_id:
                    progress_percent = int((processed_items / total_items) * 100) if total_items > 0 else 100
                    await send_progress(
                        session_id, 3, "active", 
                        f"✅ Completed {japanese_category} ({len(translated_items)} items)",
                        {
                            "progress_percent": progress_percent,
                            "translatedCategories": translated_categories,  # 完全な翻訳結果
                            "category_completed": japanese_category,
                            "category_items": len(translated_items)
                        }
                    )
        
        print(f"✅ Stage 3 Complete: Translated {len(translated_categories)} categories with Google Translate")
        
        return {
            "stage": 3,
            "success": True,
            "translated_categories": translated_categories,
            "translation_method": "google_translate"
        }
            
    except Exception as e:
        print(f"❌ Stage 3 Failed with Google Translate: {e}")
        print("🔄 Attempting OpenAI fallback...")
        return await stage3_translate_openai_fallback(categorized_data, session_id)

# OpenAIフォールバック関数
async def stage3_translate_openai_fallback(categorized_data: dict, session_id: str = None) -> dict:
    """Stage 3: Google Translate失敗時のOpenAI Function Callingフォールバック"""
    print("🔄 Stage 3: Using OpenAI fallback for translation...")
    
    if not OPENAI_AVAILABLE:
        return {
            "stage": 3,
            "success": False,
            "error": "Both Google Translate and OpenAI API are not available",
            "translated_categories": {}
        }
    
    try:
        messages = [
            {
                "role": "user",
                "content": f"""以下の日本語でカテゴリ分類されたメニューを英語に翻訳してください。

データ:
{json.dumps(categorized_data, ensure_ascii=False, indent=2)}

要件:
1. カテゴリ名を英語に翻訳（前菜→Appetizers, メイン→Main Dishes など）
2. 料理名を英語に翻訳
3. 価格はそのまま保持
4. 基本的な翻訳のみ（詳細説明は次の段階で追加）
"""
            }
        ]
        
        response = await call_openai_with_retry(
            messages=messages,
            functions=[TRANSLATE_FUNCTION],
            function_call={"name": "translate_menu_categories"}
        )
        
        function_call = response.choices[0].message.function_call
        if function_call and function_call.name == "translate_menu_categories":
            result = json.loads(function_call.arguments)
            
            print(f"✅ Stage 3 OpenAI Fallback Complete: Translated {len(result.get('translated_categories', {}))} categories")
            
            return {
                "stage": 3,
                "success": True,
                "translated_categories": result.get("translated_categories", {}),
                "translation_method": "openai_fallback"
            }
        else:
            raise ValueError("Function call not found in response")
            
    except Exception as e:
        print(f"❌ Stage 3 OpenAI Fallback Failed: {e}")
        return {
            "stage": 3,
            "success": False,
            "error": str(e),
            "translated_categories": {}
        }

# Stage 4: 詳細説明追加 (分割処理版)
async def stage4_add_descriptions(translated_data: dict, session_id: str = None) -> dict:
    """Stage 4: 分割処理で翻訳された料理に詳細説明を追加（安定性重視）"""
    print("📝 Stage 4: Adding detailed descriptions with chunked processing...")
    
    if not OPENAI_AVAILABLE:
        return {
            "stage": 4,
            "success": False,
            "error": "OpenAI API not available",
            "final_menu": {}
        }
    
    try:
        final_menu = {}
        total_items = sum(len(items) for items in translated_data.values())
        processed_items = 0
        
        print(f"🔢 Total items to process: {total_items}")
        
        # カテゴリごとに処理
        for category, items in translated_data.items():
            if not items:
                final_menu[category] = []
                continue
                
            print(f"🔄 Processing category: {category} ({len(items)} items)")
            
            # ハートビート送信
            if session_id:
                await send_progress(
                    session_id, 4, "active", 
                    f"🍽️ Adding descriptions for {category}...",
                    {"processing_category": category, "total_categories": len(translated_data)}
                )
            
            # 大きなカテゴリは分割処理（一度に最大3つずつ）
            chunk_size = 3
            category_results = []
            
            for i in range(0, len(items), chunk_size):
                chunk = items[i:i + chunk_size]
                chunk_number = (i // chunk_size) + 1
                total_chunks = (len(items) + chunk_size - 1) // chunk_size
                
                print(f"  📦 Processing chunk {chunk_number}/{total_chunks} ({len(chunk)} items)")
                
                # ハートビート（チャンク処理中）
                if session_id:
                    await send_progress(
                        session_id, 4, "active", 
                        f"🔄 Processing {category} (part {chunk_number}/{total_chunks})",
                        {"chunk_progress": f"{chunk_number}/{total_chunks}"}
                    )
                
                try:
                    # チャンク用のメッセージ作成
                    chunk_data = {category: chunk}
                    messages = [
                        {
                            "role": "user",
                            "content": f"""以下の翻訳済みメニュー項目に、外国人観光客向けの詳細説明を追加してください。

カテゴリ: {category}
項目数: {len(chunk)}

データ:
{json.dumps(chunk_data, ensure_ascii=False, indent=2)}

要件:
1. 各料理に詳細な英語説明を追加
2. 調理法、使用食材、味の特徴を含める  
3. 外国人が理解しやすい表現を使用
4. 文化的背景も簡潔に説明

必ずJSON形式で返答してください:
{{
  "final_menu": {{
    "{category}": [
      {{
        "japanese_name": "日本語名",
        "english_name": "英語名", 
        "description": "詳細な英語説明",
        "price": "価格（あれば）"
      }}
    ]
  }}
}}

例の説明:
- "Yakitori" → "Traditional Japanese grilled chicken skewers, marinated in savory tare sauce and grilled over charcoal for a smoky flavor"
- "Tempura" → "Light and crispy battered and deep-fried seafood and vegetables, served with tentsuyu dipping sauce"
"""
                        }
                    ]
                    
                    # より短いタイムアウトでリトライ（分割処理なので）
                    response = await call_openai_with_retry(
                        messages=messages,
                        max_retries=2  # 分割処理なので少なめのリトライ
                    )
                    
                    # レスポンスからJSONを抽出
                    content = response.choices[0].message.content
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    
                    if json_start != -1 and json_end != -1:
                        json_str = content[json_start:json_end]
                        chunk_result = json.loads(json_str)
                        
                        if 'final_menu' in chunk_result and category in chunk_result['final_menu']:
                            new_items = chunk_result['final_menu'][category]
                            category_results.extend(new_items)
                            print(f"    ✅ Successfully processed {len(new_items)} items in chunk")
                        else:
                            raise ValueError("Invalid response format")
                    else:
                        raise ValueError("No JSON found in response")
                    
                    # 進捗更新（リアルタイムストリーミング強化）
                    processed_items += len(chunk)
                    progress_percent = int((processed_items / total_items) * 100)
                    
                    if session_id:
                        # 現在のチャンクで処理されたアイテム詳細
                        newly_processed_items = new_items
                        
                        await send_progress(
                            session_id, 4, "active", 
                            f"🍽️ {category}: チャンク{chunk_number}/{total_chunks}完了 ({len(newly_processed_items)}アイテム追加)",
                            {
                                "progress_percent": progress_percent,
                                "processing_category": category,
                                "partial_results": {category: category_results},  # 累積結果
                                "newly_processed_items": newly_processed_items,   # 新しく処理されたアイテム
                                "chunk_completed": f"{chunk_number}/{total_chunks}",
                                "chunk_size": len(chunk),
                                "items_in_category": len(category_results),
                                "streaming_update": True  # ストリーミング更新フラグ
                            }
                        )
                    
                    # レート制限対策として少し待機
                    await asyncio.sleep(1.0)
                    
                except Exception as chunk_error:
                    print(f"⚠️ Chunk processing error: {chunk_error}")
                    print(f"    🔄 Using fallback descriptions for chunk {chunk_number}")
                    
                    # エラー時はシンプルな説明で代替
                    for item in chunk:
                        fallback_description = f"Traditional Japanese dish. {item.get('english_name', 'This dish')} is a popular menu item with authentic Japanese flavors."
                        category_results.append({
                            "japanese_name": item.get("japanese_name", "N/A"),
                            "english_name": item.get("english_name", "N/A"),
                            "description": fallback_description,
                            "price": item.get("price", "")
                        })
                        processed_items += 1
            
            final_menu[category] = category_results
            
            # カテゴリ完了通知（ストリーミング強化）
            if session_id:
                await send_progress(
                    session_id, 4, "active", 
                    f"✅ {category}カテゴリ完了！{len(category_results)}アイテムの詳細説明を追加しました",
                    {
                        "category_completed": category,
                        "category_items": len(category_results),
                        "partial_menu": final_menu,  # 全体の累積結果
                        "completed_category_items": category_results,  # 完了したカテゴリのアイテム詳細
                        "category_completion": True,  # カテゴリ完了フラグ
                        "remaining_categories": [cat for cat in translated_data.keys() if cat not in final_menu]
                    }
                )
            
            print(f"✅ Category '{category}' completed: {len(category_results)} items")
        
        print(f"🎉 Stage 4 Complete: Added descriptions to {len(final_menu)} categories, {total_items} total items")
        
        return {
            "stage": 4,
            "success": True,
            "final_menu": final_menu,
            "total_items": total_items,
            "categories_processed": len(final_menu)
        }
        
    except Exception as e:
        print(f"❌ Stage 4 Failed: {e}")
        return {
            "stage": 4,
            "success": False,
            "error": str(e),
            "final_menu": {}
        }

@app.get("/api/", response_class=HTMLResponse)
async def read_root():
    """4段階処理のメインページ（MVP版）"""
    vision_status = "✅ Ready" if VISION_AVAILABLE else "❌ Not Configured"
    translate_status = "✅ Ready" if TRANSLATE_AVAILABLE else "❌ Not Configured"
    openai_status = "✅ Ready" if OPENAI_AVAILABLE else "❌ Not Configured"
    gemini_status = "✅ Ready (Gemini 2.0 Flash)" if GEMINI_AVAILABLE else "❌ Not Configured"
    
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Menu Processor MVP - Production Ready</title>
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
                    grid-template-columns: repeat(4, 1fr);
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
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin: 30px 0;
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
                <div class="version-badge">MVP - Production Ready</div>
                <h1 class="title">🍜 Menu Processor</h1>
                <p class="subtitle">Transform Japanese restaurant menus into detailed English descriptions for international visitors</p>
            </div>
            
            <div class="status-grid">
                <div class="status-card {'ready' if GEMINI_AVAILABLE else 'error'}">
                    <strong>🎯 Gemini 2.0 Flash</strong><br>
                    {gemini_status}
                    {'<div class="success-badge">High-Precision OCR</div>' if GEMINI_AVAILABLE else ''}
                </div>
                <div class="status-card {'ready' if VISION_AVAILABLE else 'error'}">
                    <strong>🔍 Google Vision API</strong><br>
                    {vision_status}
                    {'<div class="success-badge">OCR Fallback</div>' if VISION_AVAILABLE else ''}
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
            </div>
            
            <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                <div class="upload-icon">📷</div>
                <h3>Upload Japanese Menu Image</h3>
                <p>Click here or drag & drop your menu image to start processing</p>
                <small>Supports JPG, PNG, WEBP formats</small>
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
                    const response = await fetch('/process-menu', {{
                        method: 'POST',
                        body: formData
                    }});

                    const data = await response.json();
                    const sessionId = data.session_id;
                    
                    // Server-Sent Eventsで進行状況を監視
                    const eventSource = new EventSource(`/progress/${{sessionId}}`);
                    
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
                if (stage === 5 && status === 'completed') {{
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
                for (let i = 1; i <= 4; i++) {{
                    const stage = document.getElementById(`stage${{i}}`);
                    stage.className = 'stage';
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

            async function showStage1and2(stage1Data, stage2Data) {{
                updateProgressStage(1, 'completed');
                updateProgressStage(2, 'active');
                updateProgressMessage('日本語メニューを分析中...');
                
                await sleep(800); // 少し間を置く
                
                updateProgressStage(2, 'completed');
                
                const stage1Html = `
                    <div class="stage-result show">
                        <h3><div class="stage-icon">🔍</div>OCR & カテゴリ分析完了</h3>
                        <p><strong>抽出されたテキスト:</strong></p>
                        <div class="extracted-text">${{stage1Data.extracted_text}}</div>
                        
                        <p><strong>カテゴリ分類結果:</strong></p>
                        <div class="categorized-menu">
                            ${{Object.entries(stage2Data.categories).map(([category, items]) => `
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
                
                appendToResults(stage1Html);
                await sleep(1000);
            }}

            async function showStage3(stage3Data) {{
                updateProgressStage(3, 'active');
                updateProgressMessage('英語に翻訳中...');
                
                await sleep(1000);
                
                updateProgressStage(3, 'completed');
                updateProgressStage(4, 'active');
                updateProgressMessage('詳細説明を生成中... (翻訳されたメニューをご確認ください)');
                
                const translatedMenuHtml = `
                    <div class="stage-result show">
                        <h3><div class="stage-icon">🌍</div>英語翻訳完了</h3>
                        <p>詳細説明を追加中です。翻訳されたメニューをご確認ください...</p>
                        <div id="translatedMenu"></div>
                    </div>
                `;
                
                appendToResults(translatedMenuHtml);
                
                // 翻訳されたメニューを表示（詳細説明なし）
                const translatedMenu = stage3Data.translated_categories;
                displayTranslatedMenu(translatedMenu);
                
                await sleep(800);
            }}

            async function showStage4(stage4Data) {{
                if (!stage4Data.success) {{
                    updateProgressStage(4, 'error');
                    updateProgressMessage('詳細説明の生成に失敗しました');
                    return;
                }}
                
                updateProgressStage(4, 'completed');
                updateProgressMessage('詳細説明を各料理に追加中...');
                
                // 詳細説明を段階的に追加
                await addDescriptionsProgressively(stage4Data.final_menu);
                
                // 完了メッセージを表示
                const completionHtml = `
                    <div class="completion-message show">
                        ✅ メニュー処理が完了しました！詳細な英語説明付きのメニューをお楽しみください。
                    </div>
                `;
                appendToResults(completionHtml);
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

            // Legacy function - kept for compatibility
            function displayFinalMenu(menu) {{
                const finalMenuDiv = document.getElementById('finalMenu');
                if (!finalMenuDiv) return;

                let menuHtml = '';
                
                for (const [category, items] of Object.entries(menu)) {{
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
                                    <div class="description">${{item.description || 'No description available'}}</div>
                                    ${{item.price ? `<div class="price">${{item.price}}</div>` : ''}}
                                </div>
                            `;
                        }}
                        
                        menuHtml += '</div>';
                    }}
                }}
                
                if (menuHtml === '') {{
                    menuHtml = '<p style="text-align: center; color: #666; font-style: italic;">No menu items found</p>';
                }}
                
                finalMenuDiv.innerHTML = menuHtml;
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

@app.post("/api/process-menu")
async def process_menu_start(file: UploadFile = File(...)):
    """メニュー処理を開始してセッションIDを返す"""
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # セッションIDを生成
    session_id = str(uuid.uuid4())
    progress_store[session_id] = []
    
    # ファイル保存
    file_path = f"uploads/{session_id}_{file.filename}"
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # バックグラウンドでメニュー処理を開始
    asyncio.create_task(process_menu_background(session_id, file_path))
    
    return JSONResponse(content={"session_id": session_id})

async def process_menu_background(session_id: str, file_path: str):
    """バックグラウンドでメニュー処理を実行"""
    try:
        # Stage 1: OCR with Gemini 2.0 Flash (優先) / Google Vision API (フォールバック)
        await send_progress(session_id, 1, "active", "画像からテキストを抽出中...")
        
        # Gemini 2.0 Flashを優先して使用
        if GEMINI_AVAILABLE:
            stage1_result = await stage1_ocr_gemini(file_path, session_id)
            # Geminiで失敗した場合はGoogle Vision APIをフォールバック
            if not stage1_result["success"] and VISION_AVAILABLE:
                print("⚠️ Gemini OCR failed, falling back to Google Vision API...")
                await send_progress(session_id, 1, "active", "Gemini OCRが失敗したため、Google Vision APIで再試行中...")
                stage1_result = await stage1_ocr(file_path, session_id)
        else:
            # Geminiが利用できない場合はGoogle Vision APIを使用
            stage1_result = await stage1_ocr(file_path, session_id)
        
        if not stage1_result["success"]:
            await send_progress(session_id, 1, "error", f"OCRエラー: {stage1_result['error']}")
            return
        
        # Stage 2: 日本語カテゴリ分類
        await send_progress(session_id, 2, "active", "日本語メニューを分析中...")
        stage2_result = await stage2_categorize(stage1_result["extracted_text"], session_id)
        
        if not stage2_result["success"]:
            await send_progress(session_id, 2, "error", f"分析エラー: {stage2_result['error']}")
            return
            
        await send_progress(session_id, 2, "completed", "カテゴリ分析完了", {
            "categories": stage2_result["categories"]
        })
        
        # Stage 3: 翻訳
        await send_progress(session_id, 3, "active", "英語に翻訳中...")
        stage3_result = await stage3_translate(stage2_result["categories"], session_id)
        
        if not stage3_result["success"]:
            await send_progress(session_id, 3, "error", f"翻訳エラー: {stage3_result['error']}")
            return
            
        # Stage3完了時に詳細な翻訳結果を送信（フロントエンド表示用）
        translated_summary = {}
        total_translated_items = 0
        for category, items in stage3_result["translated_categories"].items():
            translated_summary[category] = len(items)
            total_translated_items += len(items)
            
        await send_progress(session_id, 3, "completed", "✅ 翻訳完了！英語メニューをご確認ください", {
            "translated_categories": stage3_result["translated_categories"],
            "translation_summary": translated_summary,
            "total_translated_items": total_translated_items,
            "translation_method": stage3_result.get("translation_method", "google_translate"),
            "show_translated_menu": True  # フロントエンドに翻訳メニュー表示を指示
        })
        
        # Stage 4: 詳細説明追加（安定性強化版）
        await send_progress(session_id, 4, "active", "詳細説明を生成中...")
        stage4_result = await stage4_add_descriptions(stage3_result["translated_categories"], session_id)
        
        # Stage 4の結果処理を改善
        if not stage4_result["success"]:
            # 部分結果がある場合は、それを使用して完了とする
            if stage4_result.get("final_menu") and len(stage4_result["final_menu"]) > 0:
                print(f"⚠️ Stage 4 had errors but partial results available for session {session_id}")
                await send_progress(session_id, 4, "completed", "詳細説明完了（一部制限あり）", {
                    "final_menu": stage4_result["final_menu"],
                    "partial_completion": True,
                    "warning": "Some descriptions may be incomplete due to processing limitations"
                })
            else:
                # 部分結果もない場合はStage 3の結果で代替完了
                print(f"⚠️ Stage 4 failed completely, using Stage 3 results for session {session_id}")
                
                # Stage 3の結果を基に基本的な最終メニューを作成
                fallback_menu = {}
                for category, items in stage3_result["translated_categories"].items():
                    fallback_items = []
                    for item in items:
                        fallback_items.append({
                            "japanese_name": item.get("japanese_name", "N/A"),
                            "english_name": item.get("english_name", "N/A"),
                            "description": "Traditional Japanese dish with authentic flavors. Description generation was incomplete.",
                            "price": item.get("price", "")
                        })
                    fallback_menu[category] = fallback_items
                
                await send_progress(session_id, 4, "completed", "基本翻訳完了（詳細説明は制限されています）", {
                    "final_menu": fallback_menu,
                    "fallback_completion": True,
                    "warning": "Detailed descriptions could not be generated, but translation is complete"
                })
        else:
            # 正常完了
            await send_progress(session_id, 4, "completed", "詳細説明完了", {
                "final_menu": stage4_result["final_menu"],
                "total_items": stage4_result.get("total_items", 0),
                "categories_processed": stage4_result.get("categories_processed", 0)
            })
        
        # 完了通知（stage4_resultの状態に関わらず送信）
        await send_progress(session_id, 5, "completed", "全ての処理が完了しました！", {
            "processing_summary": {
                "ocr_success": stage1_result["success"],
                "categorization_success": stage2_result["success"], 
                "translation_success": stage3_result["success"],
                "description_success": stage4_result["success"],
                "completion_type": "full" if stage4_result["success"] else "partial"
            }
        })
        
    except Exception as e:
        await send_progress(session_id, 0, "error", f"処理エラー: {str(e)}")
    finally:
        # Ping/Pong機能の停止
        if session_id in ping_pong_sessions:
            ping_pong_sessions[session_id]["active"] = False
            print(f"🏓 Ping/Pong stopped for session {session_id}")
        
        # クリーンアップ
        if os.path.exists(file_path):
            os.remove(file_path)

@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    """Server-Sent Eventsで進行状況を送信（モバイル対応版）"""
    async def event_generator():
        completed = False
        last_heartbeat = asyncio.get_event_loop().time()
        heartbeat_interval = 5  # 5秒ごとにハートビート（モバイル向け）
        
        while not completed and session_id in progress_store:
            current_time = asyncio.get_event_loop().time()
            
            # 新しい進行状況があるか確認
            if progress_store[session_id]:
                progress_data = progress_store[session_id].pop(0)
                yield f"data: {json.dumps(progress_data)}\n\n"
                last_heartbeat = current_time
                
                # 完了チェック
                if progress_data.get("stage") == 5:
                    completed = True
            else:
                # ハートビート送信（モバイル接続維持用）
                if current_time - last_heartbeat > heartbeat_interval:
                    heartbeat_data = {
                        "type": "heartbeat",
                        "timestamp": current_time,
                        "session_id": session_id
                    }
                    yield f"data: {json.dumps(heartbeat_data)}\n\n"
                    last_heartbeat = current_time
                
                await asyncio.sleep(0.2)
        
        # セッション終了とクリーンアップ
        if session_id in progress_store:
            del progress_store[session_id]
            
        # Ping/Pong機能の停止
        if session_id in ping_pong_sessions:
            ping_pong_sessions[session_id]["active"] = False
            print(f"🏓 Ping/Pong stopped for SSE disconnect: {session_id}")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Expose-Headers": "*",
            "X-Accel-Buffering": "no",  # Nginxバッファリング無効
            "Content-Encoding": "identity",  # モバイル圧縮問題回避
            "Transfer-Encoding": "chunked"  # チャンク転送
        }
    )

@app.post("/api/pong/{session_id}")
async def receive_pong(session_id: str):
    """クライアントからのPongを受信"""
    success = await handle_pong(session_id)
    if success:
        return {"status": "pong_received", "session_id": session_id}
    else:
        return {"status": "session_not_found", "session_id": session_id}

@app.get("/api/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    
    # サービス状態の詳細情報
    services_detail = {}
    
    if VISION_AVAILABLE:
        services_detail["vision_api"] = {"status": "available", "client": "initialized"}
    else:
        services_detail["vision_api"] = {"status": "unavailable", "reason": "initialization_failed"}
    
    if TRANSLATE_AVAILABLE:
        services_detail["translate_api"] = {"status": "available", "client": "initialized"}
    else:
        services_detail["translate_api"] = {"status": "unavailable", "reason": "initialization_failed"}
    
    if OPENAI_AVAILABLE:
        services_detail["openai_api"] = {"status": "available", "client": "initialized"}
    else:
        services_detail["openai_api"] = {"status": "unavailable", "reason": "missing_api_key"}
    
    if GEMINI_AVAILABLE:
        services_detail["gemini_api"] = {"status": "available", "model": "gemini-2.0-flash-exp"}
    else:
        services_detail["gemini_api"] = {"status": "unavailable", "reason": "missing_api_key_or_package"}
    
    # アプリケーション全体の状態
    overall_status = "healthy" if any([GEMINI_AVAILABLE, VISION_AVAILABLE, TRANSLATE_AVAILABLE, OPENAI_AVAILABLE]) else "degraded"
    
    return {
        "status": overall_status,
        "version": "1.0.0",
        "timestamp": asyncio.get_event_loop().time(),
        "environment": {
            "port": os.getenv("PORT", "8000"),
            "google_credentials": "loaded" if google_credentials else "not_loaded"
        },
        "services": {
            "vision_api": VISION_AVAILABLE,
            "translate_api": TRANSLATE_AVAILABLE,
            "openai_api": OPENAI_AVAILABLE,
            "gemini_api": GEMINI_AVAILABLE
        },
        "services_detail": services_detail,
        "ping_pong_sessions": len(ping_pong_sessions)
    }

@app.post("/api/translate")
async def translate_menu(file: UploadFile = File(...)):
    """フロントエンド互換のメニュー翻訳エンドポイント"""
    
    # ファイル形式チェック
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    try:
        # ファイルを一時保存
        file_path = f"uploads/{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Stage 1: OCR with Gemini 2.0 Flash (優先) / Google Vision API (フォールバック)
        if GEMINI_AVAILABLE:
            stage1_result = await stage1_ocr_gemini(file_path)
            # Geminiで失敗した場合はGoogle Vision APIをフォールバック
            if not stage1_result["success"] and VISION_AVAILABLE:
                print("⚠️ Gemini OCR failed, falling back to Google Vision API...")
                stage1_result = await stage1_ocr(file_path)
        else:
            # Geminiが利用できない場合はGoogle Vision APIを使用
            stage1_result = await stage1_ocr(file_path)
        
        if not stage1_result["success"]:
            raise HTTPException(status_code=500, detail=f"Text extraction error: {stage1_result['error']}")
        
        extracted_text = stage1_result["extracted_text"]
        
        if not extracted_text.strip():
            return JSONResponse(content={
                "extracted_text": "",
                "menu_items": [],
                "message": "No text could be extracted from the image"
            })
        
        # Stage 2: カテゴリ分類
        stage2_result = await stage2_categorize(extracted_text)
        
        if not stage2_result["success"]:
            raise HTTPException(status_code=500, detail=f"Categorization error: {stage2_result['error']}")
        
        # Stage 3: 翻訳
        stage3_result = await stage3_translate(stage2_result["categories"])
        
        if not stage3_result["success"]:
            raise HTTPException(status_code=500, detail=f"Translation error: {stage3_result['error']}")
        
        # Stage 4: 詳細説明追加
        stage4_result = await stage4_add_descriptions(stage3_result["translated_categories"])
        
        if not stage4_result["success"]:
            raise HTTPException(status_code=500, detail=f"Description error: {stage4_result['error']}")
        
        # フロントエンド互換フォーマットに変換
        menu_items = []
        final_menu = stage4_result["final_menu"]
        
        for category_name, items in final_menu.items():
            for item in items:
                menu_items.append({
                    "japanese_name": item.get("japanese_name", "N/A"),
                    "english_name": item.get("english_name", "N/A"),
                    "description": item.get("description", "No description available"),
                    "price": item.get("price", "")
                })
        
        # 一時ファイルを削除
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # フロントエンドが期待する形式でレスポンス
        response_data = {
            "extracted_text": extracted_text,
            "menu_items": menu_items
        }
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        # HTTPException はそのまま再発生
        raise
    except Exception as e:
        # その他のエラーを一時ファイルを削除してから処理
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

# 診断エンドポイントを追加
@app.get("/api/diagnostic")
async def diagnostic():
    """システム診断情報を返す"""
    diagnostic_info = {
        "vision_api": {
            "available": VISION_AVAILABLE,
            "error": None if VISION_AVAILABLE else "Google Vision API not available"
        },
        "translate_api": {
            "available": TRANSLATE_AVAILABLE,
            "error": None if TRANSLATE_AVAILABLE else "Google Translate API not available"
        },
        "openai_api": {
            "available": OPENAI_AVAILABLE,
            "error": None if OPENAI_AVAILABLE else "OpenAI API not available"
        },
        "environment": {
            "google_credentials_available": google_credentials is not None,
            "google_credentials_json_env": "GOOGLE_CREDENTIALS_JSON" in os.environ,
            "openai_api_key_env": "OPENAI_API_KEY" in os.environ
        }
    }
    
    # Google Vision APIのテスト
    if VISION_AVAILABLE:
        try:
            # テスト用の小さな画像でAPIを確認
            test_response = vision_client.text_detection(vision.Image(content=b''))
            diagnostic_info["vision_api"]["test_status"] = "connection_ok"
        except Exception as e:
            diagnostic_info["vision_api"]["test_status"] = f"connection_failed: {str(e)}"
            diagnostic_info["vision_api"]["available"] = False
    
    return JSONResponse(content=diagnostic_info)

# モバイル専用診断エンドポイント
@app.get("/api/mobile-diagnostic")
async def mobile_diagnostic(request: Request):
    """モバイル専用の詳細診断情報"""
    # リクエスト情報の詳細分析
    headers = dict(request.headers)
    user_agent = headers.get("user-agent", "Unknown")
    is_mobile = any(mobile_indicator in user_agent.lower() for mobile_indicator in [
        "mobile", "android", "iphone", "ipad", "blackberry", "windows phone"
    ])
    
    # ネットワーク情報
    network_info = {
        "client_ip": request.client.host if request.client else "Unknown",
        "user_agent": user_agent,
        "is_mobile_detected": is_mobile,
        "request_headers": headers,
        "forwarded_for": headers.get("x-forwarded-for"),
        "real_ip": headers.get("x-real-ip")
    }
    
    # サービス状態の詳細確認
    services_status = {
        "vision_api": {
            "available": VISION_AVAILABLE,
            "mobile_compatibility": "good" if VISION_AVAILABLE else "unavailable",
            "error": None if VISION_AVAILABLE else "Google Vision API not available"
        },
        "backend_connectivity": {
            "cors_configured": True,
            "sse_support": True,
            "mobile_headers": True
        }
    }
    
    # モバイル特有の問題チェック
    mobile_issues = []
    
    if not VISION_AVAILABLE:
        mobile_issues.append("Vision API unavailable - this will cause Stage 1 failures")
    
    origin = headers.get("origin", "")
    if "vercel.app" not in origin and "localhost" not in origin:
        mobile_issues.append(f"Request from unexpected origin: {origin}")
    
    accept_header = headers.get("accept", "")
    if "text/event-stream" not in accept_header:
        mobile_issues.append("SSE support may be limited")
    
    return JSONResponse(content={
        "mobile_diagnostic": True,
        "timestamp": asyncio.get_event_loop().time(),
        "network_info": network_info,
        "services_status": services_status,
        "mobile_issues": mobile_issues,
        "recommendations": [
            "Use Wi-Fi instead of mobile data for better stability",
            "Ensure latest browser version for SSE support",
            "Clear browser cache if experiencing persistent issues"
        ]
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Railway用のポート設定
    uvicorn.run(app, host="0.0.0.0", port=port) 