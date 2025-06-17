from fastapi import FastAPI, File, UploadFile, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import aiofiles
import io
import json
import asyncio
import uuid
from datetime import datetime
from typing import Dict, AsyncGenerator

# 設定のインポート
from app.core.config import settings, check_api_availability, validate_settings

# OCRサービスのインポート
from app.services.ocr import extract_text as ocr_extract_text, get_ocr_service_status

# カテゴリサービスのインポート
from app.services.category import categorize_menu as category_categorize_menu, get_category_service_status

# 翻訳サービスのインポート
from app.services.translation import translate_menu as translation_translate_menu, get_translation_service_status

# 詳細説明サービスのインポート
from app.services.description import add_descriptions as description_add_descriptions, get_description_service_status

# 画像生成サービスのインポート
from app.services.image import generate_images as image_generate_images, get_image_service_status, combine_menu_with_images

# APIルーターのインポート
from app.api.v1 import api_router

# 起動時の設定検証
config_issues = validate_settings()
if config_issues:
    print("⚠️ Configuration issues detected:")
    for issue in config_issues:
        print(f"   - {issue}")
    print("   Some features may not be available.")

app = FastAPI(
    title=settings.APP_TITLE, 
    version=settings.APP_VERSION,
    description=settings.APP_DESCRIPTION
)

# APIルーターを統合
app.include_router(api_router, prefix="/api/v1")

# CORS設定（モバイル対応版）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
    expose_headers=settings.CORS_EXPOSE_HEADERS,
)

# 進行状況を管理するための辞書
progress_store = {}

# Google Cloud認証情報の設定
google_credentials = None
google_credentials_json = settings.GOOGLE_CREDENTIALS_JSON

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
    
    OPENAI_AVAILABLE = bool(settings.OPENAI_API_KEY)
    
    if OPENAI_AVAILABLE:
        # AsyncOpenAIクライアントを初期化（タイムアウトとリトライ設定付き）
        openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT,
            max_retries=settings.OPENAI_MAX_RETRIES
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
    
    GEMINI_AVAILABLE = bool(settings.GEMINI_API_KEY)
    
    if GEMINI_AVAILABLE:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        # Gemini 2.0 Flash modelを使用
        gemini_model = genai.GenerativeModel(settings.GEMINI_MODEL)
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

# Imagen 3 (Gemini API) の設定
try:
    from google import genai as imagen_genai
    from google.genai import types
    from PIL import Image
    from io import BytesIO
    
    IMAGEN_AVAILABLE = bool(settings.GEMINI_API_KEY) and settings.IMAGE_GENERATION_ENABLED
    
    if IMAGEN_AVAILABLE:
        imagen_client = imagen_genai.Client(api_key=settings.GEMINI_API_KEY)
        print("✅ Imagen 3 (Gemini API) configured successfully")
    else:
        imagen_client = None
        print("⚠️ Imagen 3 not available - GEMINI_API_KEY required")
    
except ImportError:
    IMAGEN_AVAILABLE = False
    imagen_client = None
    print("❌ google-genai package not installed for Imagen 3. Install with: pip install google-genai")
except Exception as e:
    IMAGEN_AVAILABLE = False
    imagen_client = None
    print(f"❌ Imagen 3 initialization failed: {e}")

# 注意: ADD_DESCRIPTIONS_FUNCTION スキーマは詳細説明サービス層に移動されました
# 詳細説明機能は app/services/description で管理されます

# OpenAI API 呼び出し用のリトライ関数（指数バックオフ付き）
async def call_openai_with_retry(messages, functions=None, function_call=None, max_retries=3):
    """指数バックオフ付きでOpenAI APIを呼び出すリトライ関数"""
    if not OPENAI_AVAILABLE or not openai_client:
        raise Exception("OpenAI API is not available")
    
    for attempt in range(max_retries + 1):
        try:
            kwargs = {
                "model": settings.OPENAI_MODEL,
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
            
            # 指数バックオフ
            wait_time = settings.RETRY_BASE_DELAY ** attempt
            print(f"⏳ Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(wait_time)
            
        except openai.APITimeoutError as e:
            if attempt == max_retries:
                raise Exception(f"API timeout after {max_retries + 1} attempts: {str(e)}")
            
            wait_time = settings.RETRY_BASE_DELAY ** attempt
            print(f"⏳ API timeout, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
            await asyncio.sleep(wait_time)
            
        except openai.APIConnectionError as e:
            if attempt == max_retries:
                raise Exception(f"API connection error after {max_retries + 1} attempts: {str(e)}")
            
            wait_time = settings.RETRY_BASE_DELAY ** attempt
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
    
    ping_interval = settings.SSE_PING_INTERVAL  # Ping間隔
    max_no_pong_time = settings.SSE_MAX_NO_PONG_TIME  # Pongタイムアウト
    
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

# Stage 1: OCR - 文字認識 (Gemini専用版)
async def stage1_ocr_gemini_exclusive(image_path: str, session_id: str = None) -> dict:
    """Stage 1: Gemini 2.0 Flash OCRを使って画像からテキストを抽出（Gemini専用モード）"""
    print("🎯 Stage 1: Starting OCR with Gemini 2.0 Flash (Exclusive Mode)...")
    
    try:
        # Gemini専用OCRサービスを使用
        result = await ocr_extract_text(image_path, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 1,
            "success": result.success,
            "extracted_text": result.extracted_text,
            "ocr_engine": "gemini-2.0-flash",
            "mode": "gemini_exclusive"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            legacy_result.update({
                "text_length": len(result.extracted_text),
                "ocr_service": "Gemini 2.0 Flash",
                "features": ["menu_optimized", "japanese_text", "high_precision"],
                "file_size": result.metadata.get("file_size", 0)
            })
            
            # 進行状況通知
            if session_id:
                await send_progress(session_id, 1, "completed", "🎯 Gemini OCR完了", {
                    "extracted_text": result.extracted_text,
                    "text_preview": result.extracted_text[:100] + "..." if len(result.extracted_text) > 100 else result.extracted_text,
                    "ocr_service": "Gemini 2.0 Flash",
                    "ocr_engine": "gemini-2.0-flash"
                })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            # 進行状況通知
            if session_id:
                await send_progress(session_id, 1, "error", f"🎯 Gemini OCRエラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 1 Gemini OCR Failed: {e}")
        
        error_result = {
            "stage": 1,
            "success": False,
            "error": f"Gemini OCRサービスでエラーが発生しました: {str(e)}",
            "ocr_engine": "gemini-2.0-flash",
            "mode": "gemini_exclusive", 
            "detailed_error": {
                "error_type": "gemini_ocr_error",
                "original_error": str(e),
                "suggestions": [
                    "GEMINI_API_KEYが正しく設定されているか確認してください",
                    "Gemini APIの利用状況・クォータを確認してください",
                    "google-generativeaiパッケージがインストールされているか確認してください"
                ]
            },
            "extracted_text": ""
        }
        
        if session_id:
            await send_progress(session_id, 1, "error", f"🎯 Gemini OCRエラー: {str(e)}", error_result["detailed_error"])
        
        return error_result





# Stage 2: 日本語のままカテゴリ分類・枠組み作成 (OpenAI専用版)
async def stage2_categorize_openai_exclusive(extracted_text: str, session_id: str = None) -> dict:
    """Stage 2: OpenAI Function Callingを使って抽出されたテキストを日本語のままカテゴリ分類（OpenAI専用モード）"""
    print("🏷️ Stage 2: Starting Japanese categorization with OpenAI Function Calling (Exclusive Mode)...")
    
    try:
        # 新しいカテゴリサービスを使用
        result = await category_categorize_menu(extracted_text, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 2,
            "success": result.success,
            "categories": result.categories,
            "uncategorized": result.uncategorized,
            "categorization_engine": "openai-function-calling",
            "mode": "openai_exclusive"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.categories.values())
            legacy_result.update({
                "total_items": total_items,
                "total_categories": len(result.categories),
                "uncategorized_count": len(result.uncategorized),
                "categorization_service": "OpenAI Function Calling"
            })
            
            # 進行状況通知
            if session_id:
                await send_progress(session_id, 2, "completed", "🏷️ OpenAI カテゴリ分類完了", {
                    "categories": result.categories,
                    "uncategorized": result.uncategorized,
                    "total_items": total_items,
                    "categorization_engine": "openai-function-calling"
                })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            # 進行状況通知
            if session_id:
                await send_progress(session_id, 2, "error", f"🏷️ OpenAI カテゴリ分類エラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 2 OpenAI Categorization Failed: {e}")
        
        error_result = {
            "stage": 2,
            "success": False,
            "error": f"OpenAI カテゴリ分類サービスでエラーが発生しました: {str(e)}",
            "categorization_engine": "openai-function-calling",
            "mode": "openai_exclusive",
            "detailed_error": {
                "error_type": "openai_categorization_error",
                "original_error": str(e),
                "suggestions": [
                    "OPENAI_API_KEYが正しく設定されているか確認してください",
                    "OpenAI APIの利用状況・クォータを確認してください",
                    "openaiパッケージがインストールされているか確認してください"
                ]
            },
            "categories": {}
        }
        
        if session_id:
            await send_progress(session_id, 2, "error", f"🏷️ OpenAI カテゴリ分類エラー: {str(e)}", error_result["detailed_error"])
        
        return error_result

# Stage 3: 翻訳 (Google Translate + OpenAI フォールバック版)
async def stage3_translate_with_fallback(categorized_data: dict, session_id: str = None) -> dict:
    """Stage 3: Google Translate + OpenAI フォールバックで翻訳（新サービス層使用）"""
    print("🌍 Stage 3: Starting translation with Google Translate + OpenAI fallback...")
    
    try:
        # 新しい翻訳サービスを使用
        result = await translation_translate_menu(categorized_data, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 3,
            "success": result.success,
            "translated_categories": result.translated_categories,
            "translation_method": result.translation_method,
            "translation_architecture": "google_translate_with_openai_fallback"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.translated_categories.values())
            legacy_result.update({
                "total_items": total_items,
                "total_categories": len(result.translated_categories),
                "translation_service": result.metadata.get("successful_service", "unknown"),
                "fallback_used": result.metadata.get("fallback_used", False)
            })
            
            # 進行状況通知
            if session_id:
                await send_progress(session_id, 3, "completed", "🌍 翻訳完了", {
                    "translatedCategories": result.translated_categories,
                    "translation_method": result.translation_method,
                    "total_items": total_items,
                    "fallback_used": result.metadata.get("fallback_used", False)
                })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            # 進行状況通知
            if session_id:
                await send_progress(session_id, 3, "error", f"🌍 翻訳エラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 3 Translation Service Failed: {e}")
        
        error_result = {
            "stage": 3,
            "success": False,
            "error": f"翻訳サービスでエラーが発生しました: {str(e)}",
            "translation_architecture": "google_translate_with_openai_fallback",
            "detailed_error": {
                "error_type": "translation_service_error",
                "original_error": str(e),
                "suggestions": [
                    "GOOGLE_CREDENTIALS_JSONまたはOPENAI_API_KEYが正しく設定されているか確認してください",
                    "Google Translate APIまたはOpenAI APIの利用状況・クォータを確認してください",
                    "必要なパッケージがインストールされているか確認してください"
                ]
            },
            "translated_categories": {}
        }
        
        if session_id:
            await send_progress(session_id, 3, "error", f"🌍 翻訳エラー: {str(e)}", error_result["detailed_error"])
        
        return error_result

# Stage 4: 詳細説明追加 (新サービス層使用)
async def stage4_add_descriptions(translated_data: dict, session_id: str = None) -> dict:
    """Stage 4: OpenAI詳細説明サービスで詳細説明を追加（新サービス層使用）"""
    print("📝 Stage 4: Adding detailed descriptions with OpenAI service...")
    
    try:
        # 新しい詳細説明サービスを使用
        result = await description_add_descriptions(translated_data, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 4,
            "success": result.success,
            "final_menu": result.final_menu,
            "description_method": result.description_method,
            "description_architecture": "openai_chunked_processing"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.final_menu.values())
            legacy_result.update({
                "total_items": total_items,
                "categories_processed": len(result.final_menu),
                "description_service": result.metadata.get("provider", "OpenAI API"),
                "features": result.metadata.get("features", [])
            })
            
            print(f"✅ OpenAI Description Generation successful - {total_items} items processed")
            
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            print(f"❌ OpenAI Description Generation failed: {result.error}")
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 4 Description Service Failed: {e}")
        
        error_result = {
            "stage": 4,
            "success": False,
            "error": f"詳細説明サービスでエラーが発生しました: {str(e)}",
            "description_architecture": "openai_chunked_processing",
            "detailed_error": {
                "error_type": "description_service_error",
                "original_error": str(e),
                "suggestions": [
                    "OPENAI_API_KEYが正しく設定されているか確認してください",
                    "OpenAI APIの利用状況・クォータを確認してください",
                    "openaiパッケージがインストールされているか確認してください",
                    "入力データの形式が正しいか確認してください"
                ]
            },
            "final_menu": {}
        }
        
        return error_result

# Stage 5: 画像生成 (新サービス層使用)
async def stage5_generate_images(final_menu: dict, session_id: str = None) -> dict:
    """Stage 5: Imagen 3画像生成サービスで画像を生成（新サービス層使用）"""
    print("🎨 Stage 5: Generating images with Imagen 3 service...")
    
    try:
        # 新しい画像生成サービスを使用
        result = await image_generate_images(final_menu, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 5,
            "success": result.success,
            "images_generated": result.images_generated,
            "total_images": result.total_images,
            "total_items": result.total_items,
            "image_method": result.image_method,
            "image_architecture": "imagen3_food_photography"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            legacy_result.update({
                "image_service": result.metadata.get("provider", "Imagen 3"),
                "model": result.metadata.get("model", "imagen-3.0-generate-002"),
                "features": result.metadata.get("features", [])
            })
            
            # スキップされた場合の処理
            if result.metadata.get("skipped_reason"):
                legacy_result["skipped_reason"] = result.metadata["skipped_reason"]
                print(f"⚠️ Imagen 3 image generation skipped: {result.metadata['skipped_reason']}")
            else:
                print(f"✅ Imagen 3 Image Generation successful - {result.total_images} images generated")
            
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            print(f"❌ Imagen 3 Image Generation failed: {result.error}")
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 5 Image Service Failed: {e}")
        
        error_result = {
            "stage": 5,
            "success": False,
            "error": f"画像生成サービスでエラーが発生しました: {str(e)}",
            "image_architecture": "imagen3_food_photography",
            "detailed_error": {
                "error_type": "image_service_error",
                "original_error": str(e),
                "suggestions": [
                    "GEMINI_API_KEYが正しく設定されているか確認してください",
                    "IMAGE_GENERATION_ENABLEDが有効になっているか確認してください",
                    "Imagen 3 APIの利用状況・クォータを確認してください",
                    "google-genai、pillowパッケージがインストールされているか確認してください"
                ]
            },
            "images_generated": {}
        }
        
        return error_result

# 注意: create_image_prompt と combine_menu_with_images 関数は画像生成サービス層に移動されました
# これらの機能は app/services/image で管理されます

# エンドポイント群を app/api/v1/endpoints/ に移動しました:
# - メインページ: app/api/v1/endpoints/ui.py
# - メニュー処理: app/api/v1/endpoints/menu.py  
# - セッション管理: app/api/v1/endpoints/session.py
# - システム診断: app/api/v1/endpoints/system.py

async def process_menu_background(session_id: str, file_path: str):
    """バックグラウンドでメニュー処理を実行"""
    try:
        # Stage 1: OCR with Gemini 2.0 Flash (Gemini専用モード)
        await send_progress(session_id, 1, "active", "🎯 Gemini 2.0 Flashで画像からテキストを抽出中...")
        
        # Gemini専用OCRサービスを使用
        stage1_result = await stage1_ocr_gemini_exclusive(file_path, session_id)
        
        if not stage1_result["success"]:
            await send_progress(session_id, 1, "error", f"OCRエラー: {stage1_result['error']}")
            return
        
        # Stage 2: 日本語カテゴリ分類（OpenAI専用モード）
        await send_progress(session_id, 2, "active", "🏷️ OpenAI Function Callingでメニューを分析中...")
        stage2_result = await stage2_categorize_openai_exclusive(stage1_result["extracted_text"], session_id)
        
        if not stage2_result["success"]:
            await send_progress(session_id, 2, "error", f"分析エラー: {stage2_result['error']}")
            return
            
        await send_progress(session_id, 2, "completed", "カテゴリ分析完了", {
            "categories": stage2_result["categories"]
        })
        
        # Stage 3: 翻訳（Google Translate + OpenAI フォールバック）
        await send_progress(session_id, 3, "active", "🌍 Google Translate + OpenAI フォールバックで翻訳中...")
        stage3_result = await stage3_translate_with_fallback(stage2_result["categories"], session_id)
        
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
        final_menu_for_images = None
        if not stage4_result["success"]:
            # 部分結果がある場合は、それを使用して完了とする
            if stage4_result.get("final_menu") and len(stage4_result["final_menu"]) > 0:
                print(f"⚠️ Stage 4 had errors but partial results available for session {session_id}")
                final_menu_for_images = stage4_result["final_menu"]
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
                
                final_menu_for_images = fallback_menu
                await send_progress(session_id, 4, "completed", "基本翻訳完了（詳細説明は制限されています）", {
                    "final_menu": fallback_menu,
                    "fallback_completion": True,
                    "warning": "Detailed descriptions could not be generated, but translation is complete"
                })
        else:
            # 正常完了
            final_menu_for_images = stage4_result["final_menu"]
            await send_progress(session_id, 4, "completed", "詳細説明完了", {
                "final_menu": stage4_result["final_menu"],
                "total_items": stage4_result.get("total_items", 0),
                "categories_processed": stage4_result.get("categories_processed", 0)
            })
        
        # Stage 5: 画像生成（Imagen 3）
        await send_progress(session_id, 5, "active", "🎨 メニュー画像を生成中...")
        stage5_result = await stage5_generate_images(final_menu_for_images, session_id)
        
        if stage5_result["success"]:
            if stage5_result.get("skipped_reason"):
                # Imagen 3が利用できない場合
                await send_progress(session_id, 5, "completed", "画像生成をスキップしました", {
                    "skipped_reason": stage5_result["skipped_reason"],
                    "final_menu": final_menu_for_images
                })
            else:
                # 画像生成成功
                total_generated = stage5_result.get("total_images", 0)
                total_items = stage5_result.get("total_items", 0)
                await send_progress(session_id, 5, "completed", f"🎨 画像生成完了！{total_generated}/{total_items}枚の画像を生成しました", {
                    "images_generated": stage5_result["images_generated"],
                    "total_images": total_generated,
                    "final_menu_with_images": combine_menu_with_images(final_menu_for_images, stage5_result["images_generated"])
                })
        else:
            # 画像生成エラー
            await send_progress(session_id, 5, "completed", "画像生成でエラーが発生しました", {
                "error": stage5_result.get("error", "Unknown error"),
                "final_menu": final_menu_for_images
            })
        
        # Stage 6: 完了通知（stage4_resultとstage5_resultの状態に関わらず送信）
        await send_progress(session_id, 6, "completed", "全ての処理が完了しました！", {
            "processing_summary": {
                "ocr_success": stage1_result["success"],
                "categorization_success": stage2_result["success"], 
                "translation_success": stage3_result["success"],
                "description_success": stage4_result["success"],
                "image_generation_success": stage5_result["success"],
                "completion_type": "full" if all([stage4_result["success"], stage5_result["success"]]) else "partial",
                "total_images_generated": stage5_result.get("total_images", 0)
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
        heartbeat_interval = settings.SSE_HEARTBEAT_INTERVAL  # ハートビート間隔（モバイル向け）
        
        while not completed and session_id in progress_store:
            current_time = asyncio.get_event_loop().time()
            
            # 新しい進行状況があるか確認
            if progress_store[session_id]:
                progress_data = progress_store[session_id].pop(0)
                yield f"data: {json.dumps(progress_data)}\n\n"
                last_heartbeat = current_time
                
                # 完了チェック
                if progress_data.get("stage") == 6:
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
    
    if IMAGEN_AVAILABLE:
        services_detail["imagen_api"] = {"status": "available", "model": "imagen-3.0-generate-002"}
    else:
        services_detail["imagen_api"] = {"status": "unavailable", "reason": "missing_api_key_or_package"}
    
    # Gemini OCRサービスの状態（Gemini専用モード）
    try:
        ocr_status = get_ocr_service_status()
        gemini_available = ocr_status.get("gemini", {}).get("available", False)
        services_detail["gemini_ocr"] = {
            "status": "available" if gemini_available else "unavailable",
            "mode": "gemini_exclusive",
            "engine": "gemini-2.0-flash",
            "gemini_service": ocr_status.get("gemini", {}),
            "features": [
                "japanese_menu_optimization",
                "high_precision_extraction",
                "contextual_understanding"
            ] if gemini_available else []
        }
    except Exception as e:
        services_detail["gemini_ocr"] = {"status": "error", "error": str(e), "mode": "gemini_exclusive"}
    
    # OpenAI カテゴリ分類サービスの状態（OpenAI専用モード）
    try:
        category_status = get_category_service_status()
        openai_available = category_status.get("openai", {}).get("available", False)
        services_detail["openai_categorization"] = {
            "status": "available" if openai_available else "unavailable",
            "mode": "openai_exclusive",
            "engine": "openai-function-calling",
            "openai_service": category_status.get("openai", {}),
            "features": [
                "japanese_menu_categorization",
                "function_calling_support",
                "structured_output",
                "menu_item_extraction"
            ] if openai_available else []
        }
    except Exception as e:
        services_detail["openai_categorization"] = {"status": "error", "error": str(e), "mode": "openai_exclusive"}
    
    # Google Translate + OpenAI 翻訳サービスの状態
    try:
        translation_status = get_translation_service_status()
        google_translate_available = translation_status.get("google_translate", {}).get("available", False)
        openai_translate_available = translation_status.get("openai", {}).get("available", False)
        
        services_detail["google_translate_translation"] = {
            "status": "available" if google_translate_available else "unavailable",
            "role": "primary",
            "engine": "google-translate-api",
            "google_service": translation_status.get("google_translate", {}),
            "features": [
                "real_time_translation",
                "category_mapping",
                "html_entity_cleanup",
                "rate_limiting"
            ] if google_translate_available else []
        }
        
        services_detail["openai_translation"] = {
            "status": "available" if openai_translate_available else "unavailable",
            "role": "fallback",
            "engine": "openai-function-calling",
            "openai_service": translation_status.get("openai", {}),
            "features": [
                "function_calling_structured_output",
                "japanese_cuisine_terminology",
                "batch_translation",
                "category_mapping"
            ] if openai_translate_available else []
        }
    except Exception as e:
        services_detail["google_translate_translation"] = {"status": "error", "error": str(e), "role": "primary"}
        services_detail["openai_translation"] = {"status": "error", "error": str(e), "role": "fallback"}
    
    # OpenAI 詳細説明サービスの状態
    try:
        description_status = get_description_service_status()
        openai_description_available = description_status.get("openai", {}).get("available", False)
        
        services_detail["openai_description"] = {
            "status": "available" if openai_description_available else "unavailable",
            "role": "primary",
            "engine": "openai-chunked-processing",
            "openai_service": description_status.get("openai", {}),
            "features": [
                "detailed_description_generation",
                "japanese_cuisine_expertise",
                "cultural_context_explanation",
                "tourist_friendly_descriptions",
                "chunked_processing",
                "real_time_progress"
            ] if openai_description_available else []
        }
    except Exception as e:
        services_detail["openai_description"] = {"status": "error", "error": str(e), "role": "primary"}
    
    # Imagen 3 画像生成サービスの状態
    try:
        image_status = get_image_service_status()
        imagen3_available = image_status.get("imagen3", {}).get("available", False)
        
        services_detail["imagen3_image_generation"] = {
            "status": "available" if imagen3_available else "unavailable",
            "role": "primary",
            "engine": "imagen3-food-photography",
            "imagen3_service": image_status.get("imagen3", {}),
            "features": [
                "professional_food_photography",
                "japanese_cuisine_focus",
                "category_specific_styling",
                "high_quality_generation",
                "menu_item_visualization",
                "real_time_progress"
            ] if imagen3_available else []
        }
    except Exception as e:
        services_detail["imagen3_image_generation"] = {"status": "error", "error": str(e), "role": "primary"}
    
    # アプリケーション全体の状態
    overall_status = "healthy" if any([GEMINI_AVAILABLE, VISION_AVAILABLE, TRANSLATE_AVAILABLE, OPENAI_AVAILABLE, IMAGEN_AVAILABLE]) else "degraded"
    
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
            "gemini_api": GEMINI_AVAILABLE,
            "imagen_api": IMAGEN_AVAILABLE
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
        file_path = f"{settings.UPLOAD_DIR}/{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Stage 1: OCR with Gemini 2.0 Flash (Gemini専用モード)
        stage1_result = await stage1_ocr_gemini_exclusive(file_path)
        
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
        stage2_result = await stage2_categorize_openai_exclusive(extracted_text)
        
        if not stage2_result["success"]:
            raise HTTPException(status_code=500, detail=f"Categorization error: {stage2_result['error']}")
        
        # Stage 3: 翻訳
        stage3_result = await stage3_translate_with_fallback(stage2_result["categories"])
        
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
    uvicorn.run(app, host=settings.HOST, port=settings.PORT) 