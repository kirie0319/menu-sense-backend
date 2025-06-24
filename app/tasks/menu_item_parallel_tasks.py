#!/usr/bin/env python3
"""
🎯 実API統合メニューアイテム並列処理タスク

Google Translate + OpenAI GPT-4.1-mini + Google Imagen 3
"""

import time
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional

from .celery_app import celery_app
from app.core.config import settings

# Redis接続
from .utils import redis_client

# ログ設定
logger = logging.getLogger(__name__)

def await_sync(coro):
    """非同期関数を同期的に実行（Celeryワーカー用）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

# ===============================================
# 🚀 実API統合タスク
# ===============================================

@celery_app.task(bind=True, queue='real_translate_queue', name="real_translate_menu_item")
def real_translate_menu_item(self, session_id: str, item_id: int, item_text: str, category: str = "Other"):
    """
    Google Translate APIを使った実際の翻訳タスク
    
    Args:
        session_id: セッションID  
        item_id: アイテムID
        item_text: 日本語テキスト
        category: カテゴリ名
        
    Returns:
        Dict: 翻訳結果
    """
    
    try:
        logger.info(f"🌍 [REAL] Starting Google Translate: session={session_id}, item={item_id}, text='{item_text}'")
        
        # Google Translateサービスをインポート
        from app.services.translation.google_translate import GoogleTranslateService
        
        translate_service = GoogleTranslateService()
        
        if not translate_service.is_available():
            # フォールバックでOpenAI翻訳を試行
            try:
                from app.services.translation.openai import OpenAITranslationService
                openai_service = OpenAITranslationService()
                
                if openai_service.is_available():
                    logger.info(f"🔄 [REAL] Fallback to OpenAI translation")
                    english_text = await_sync(openai_service.translate_menu_item(item_text))
                    provider = "OpenAI Translation (Fallback)"
                else:
                    raise Exception("Both Google Translate and OpenAI translation are unavailable")
            except Exception as fallback_error:
                logger.error(f"❌ [REAL] Fallback translation failed: {fallback_error}")
                raise Exception("All translation services unavailable")
        else:
            # Google Translate API で翻訳
            english_text = await_sync(translate_service.translate_menu_item(item_text))
            provider = "Google Translate API"
        
        # Redis保存
        redis_key = f"{session_id}:item{item_id}:translation"
        translation_data = {
            "japanese_text": item_text,
            "english_text": english_text,
            "category": category,
            "timestamp": time.time(),
            "provider": provider,
            "test_mode": False
        }
        
        if redis_client:
            redis_client.setex(redis_key, 3600, json.dumps(translation_data))  # 1時間TTL
            logger.info(f"✅ [REAL] Translation saved to Redis: {redis_key}")
        else:
            logger.error(f"❌ [REAL] Redis client not available")
        
        # 依存判定チェック（翻訳と説明が完了したら画像生成トリガー）
        check_dependencies_and_trigger_image(session_id, item_id)
        
        result = {
            "success": True,
            "session_id": session_id,
            "item_id": item_id,
            "japanese_text": item_text,
            "english_text": english_text,
            "category": category,
            "provider": provider,
            "processing_time": time.time(),
            "test_mode": False
        }
        
        logger.info(f"✅ [REAL] Translation completed: {item_text} → {english_text}")
        return result
        
    except Exception as e:
        logger.error(f"❌ [REAL] Translation failed: session={session_id}, item={item_id}, error={str(e)}")
        
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e),
            "test_mode": False
        }

@celery_app.task(bind=True, queue='real_description_queue', name="real_generate_menu_description")
def real_generate_menu_description(self, session_id: str, item_id: int, japanese_text: str, english_text: str = "", category: str = "Other"):
    """
    OpenAI GPT-4.1-mini を使った実際の詳細説明生成タスク
    
    Args:
        session_id: セッションID
        item_id: アイテムID
        japanese_text: 日本語テキスト
        english_text: 英語翻訳（あれば）
        category: カテゴリ
        
    Returns:
        Dict: 説明生成結果
    """
    
    try:
        logger.info(f"📝 [REAL] Starting OpenAI description: session={session_id}, item={item_id}, text='{japanese_text}'")
        
        # OpenAI説明サービスをインポート
        from app.services.description.openai import OpenAIDescriptionService
        
        description_service = OpenAIDescriptionService()
        
        if not description_service.is_available():
            # フォールバック説明を生成
            fallback_description = f"Traditional Japanese {category.lower()} with authentic flavors and high-quality ingredients."
            description = fallback_description
            provider = "Fallback Description Service"
            logger.info(f"⚠️ [REAL] Using fallback description")
        else:
            # 英語名がない場合は日本語名を使用
            if not english_text:
                english_text = japanese_text
            
            # OpenAI API で詳細説明を生成
            result = description_service.generate_description(japanese_text, english_text, category)
            
            if result.get('success'):
                description = result.get('description', '')
                provider = "OpenAI GPT-4.1-mini"
            else:
                # エラー時のフォールバック
                description = f"Delicious {category.lower()} with traditional Japanese preparation and premium ingredients."
                provider = "Fallback Description (API Error)"
        
        # Redis保存
        redis_key = f"{session_id}:item{item_id}:description"
        description_data = {
            "japanese_text": japanese_text,
            "english_text": english_text,
            "description": description,
            "category": category,
            "timestamp": time.time(),
            "provider": provider,
            "test_mode": False
        }
        
        if redis_client:
            redis_client.setex(redis_key, 3600, json.dumps(description_data))  # 1時間TTL
            logger.info(f"✅ [REAL] Description saved to Redis: {redis_key}")
        else:
            logger.error(f"❌ [REAL] Redis client not available")
        
        # 依存判定チェック
        check_dependencies_and_trigger_image(session_id, item_id)
        
        result = {
            "success": True,
            "session_id": session_id,
            "item_id": item_id,
            "japanese_text": japanese_text,
            "english_text": english_text,
            "description": description,
            "category": category,
            "provider": provider,
            "processing_time": time.time(),
            "test_mode": False
        }
        
        logger.info(f"✅ [REAL] Description completed: {japanese_text} → {description[:50]}...")
        return result
        
    except Exception as e:
        logger.error(f"❌ [REAL] Description generation failed: session={session_id}, item={item_id}, error={str(e)}")
        
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e),
            "test_mode": False
        }

@celery_app.task(bind=True, queue='real_image_queue', name="real_generate_menu_image")
def real_generate_menu_image(self, session_id: str, item_id: int, english_text: str, description: str, category: str = "Other"):
    """
    Google Imagen 3 を使った実際の画像生成タスク
    
    Args:
        session_id: セッションID
        item_id: アイテムID  
        english_text: 英語料理名
        description: 詳細説明
        category: カテゴリ
        
    Returns:
        Dict: 画像生成結果
    """
    
    try:
        logger.info(f"🎨 [REAL] Starting Imagen 3 generation: session={session_id}, item={item_id}, dish='{english_text}'")
        
        # Imagen 3サービスをインポート
        from app.services.image.imagen3 import Imagen3Service
        
        image_service = Imagen3Service()
        
        # プロンプト作成
        prompt = create_image_prompt(english_text, description, category)
        
        if not image_service.is_available():
            # フォールバック画像URL
            image_url = f"https://placeholder-images.example.com/food/{category.lower()}/{session_id}_{item_id}.jpg"
            provider = "Fallback Image Service"
            fallback_used = True
            logger.info(f"⚠️ [REAL] Using fallback image URL")
        else:
            # Imagen 3 API で画像生成
            result = await_sync(image_service.generate_single_image(
                japanese_name="",  # 既に英語名がある
                english_name=english_text,
                description=description,
                category=category
            ))
            
            if result.get('generation_success'):
                image_url = result.get('image_url', '')
                provider = "Google Imagen 3"
                fallback_used = False
            else:
                # エラー時のフォールバック
                image_url = f"https://placeholder-images.example.com/food/{category.lower()}/{session_id}_{item_id}.jpg"
                provider = "Fallback Image (API Error)"
                fallback_used = True
        
        # Redis保存
        redis_key = f"{session_id}:item{item_id}:image"
        image_data = {
            "english_text": english_text,
            "description": description,
            "category": category,
            "prompt": prompt,
            "image_url": image_url,
            "provider": provider,
            "fallback_used": fallback_used,
            "timestamp": time.time(),
            "test_mode": False
        }
        
        if redis_client:
            redis_client.setex(redis_key, 3600, json.dumps(image_data))  # 1時間TTL
            logger.info(f"✅ [REAL] Image URL saved to Redis: {redis_key}")
        else:
            logger.error(f"❌ [REAL] Redis client not available")
        
        result = {
            "success": True,
            "session_id": session_id,
            "item_id": item_id,
            "english_text": english_text,
            "description": description,
            "category": category,
            "image_url": image_url,
            "provider": provider,
            "fallback_used": fallback_used,
            "processing_time": time.time(),
            "test_mode": False
        }
        
        logger.info(f"✅ [REAL] Image generation completed: {english_text} → {image_url}")
        return result
        
    except Exception as e:
        logger.error(f"❌ [REAL] Image generation failed: session={session_id}, item={item_id}, error={str(e)}")
        
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e),
            "test_mode": False
        }

# ===============================================
# 🧠 依存判定機能
# ===============================================

def check_dependencies_and_trigger_image(session_id: str, item_id: int):
    """
    実際のAPI統合での依存判定
    
    翻訳と説明が両方完了したら画像生成をトリガー
    """
    
    if not redis_client:
        logger.error("❌ [REAL] Redis not available for dependency check")
        return
    
    try:
        # Redis から翻訳と説明の完了状態をチェック
        translation_key = f"{session_id}:item{item_id}:translation"
        description_key = f"{session_id}:item{item_id}:description"
        
        translation_data = redis_client.get(translation_key)
        description_data = redis_client.get(description_key)
        
        logger.info(f"🔍 [REAL] Dependency check: session={session_id}, item={item_id}")
        logger.info(f"🔍 [REAL] Translation exists: {bool(translation_data)}")
        logger.info(f"🔍 [REAL] Description exists: {bool(description_data)}")
        
        # 両方が完了していたら画像生成をトリガー
        if translation_data and description_data:
            translation_info = json.loads(translation_data)
            description_info = json.loads(description_data)
            
            # 画像生成タスクを非同期で投入
            real_generate_menu_image.apply_async(
                args=[
                    session_id, 
                    item_id, 
                    translation_info.get("english_text", ""),
                    description_info.get("description", ""),
                    translation_info.get("category", "Other")
                ],
                queue='real_image_queue'
            )
            
            logger.info(f"🎨 [REAL] Image generation triggered: session={session_id}, item={item_id}")
            
        else:
            logger.info(f"⏳ [REAL] Waiting for dependencies: translation={bool(translation_data)}, description={bool(description_data)}")
            
    except Exception as e:
        logger.error(f"⚠️ [REAL] Dependency check failed: {str(e)}")

def create_image_prompt(english_text: str, description: str, category: str) -> str:
    """実際の画像生成プロンプト作成"""
    
    # カテゴリ別のスタイル調整
    category_styles = {
        "Appetizers": "elegant appetizer presentation on fine dining plate",
        "Main Dishes": "beautiful main course plating with garnishes",
        "Desserts": "artistic dessert presentation with elegant styling",
        "Beverages": "professional beverage photography with appropriate glassware",
        "Soups": "warm soup presentation in traditional bowl",
        "Salads": "fresh salad with vibrant colors and textures"
    }
    
    style = category_styles.get(category, "professional food photography")
    
    return f"Professional food photography of {english_text}. {description[:150]}. {style}, restaurant quality, high resolution, appetizing, Japanese cuisine."

# ===============================================
# 🔍 状況確認機能
# ===============================================

def get_real_status(session_id: str, item_id: int):
    """実際のAPI統合での状況取得"""
    if not redis_client:
        return {"error": "Redis not available"}
    
    try:
        status = {}
        
        # 翻訳状況
        translation_key = f"{session_id}:item{item_id}:translation"
        translation_data = redis_client.get(translation_key)
        status["translation"] = {
            "completed": bool(translation_data),
            "data": json.loads(translation_data) if translation_data else None
        }
        
        # 説明生成状況
        description_key = f"{session_id}:item{item_id}:description"
        description_data = redis_client.get(description_key)
        status["description"] = {
            "completed": bool(description_data),
            "data": json.loads(description_data) if description_data else None
        }
        
        # 画像生成状況
        image_key = f"{session_id}:item{item_id}:image"
        image_data = redis_client.get(image_key)
        status["image"] = {
            "completed": bool(image_data),
            "data": json.loads(image_data) if image_data else None
        }
        
        return status
        
    except Exception as e:
        return {"error": f"Status check failed: {str(e)}"}

def test_redis_connection():
    """Redis接続テスト"""
    if not redis_client:
        return {"success": False, "message": "Redis client not available"}
    
    try:
        # 基本的な読み書きテスト
        test_key = "test:connection"
        test_value = {"test": "data", "timestamp": time.time()}
        
        redis_client.setex(test_key, 60, json.dumps(test_value))
        retrieved_value = redis_client.get(test_key)
        
        if retrieved_value:
            parsed_value = json.loads(retrieved_value)
            redis_client.delete(test_key)  # クリーンアップ
            
            return {
                "success": True,
                "message": "Redis connection test successful",
                "test_data": parsed_value
            }
        else:
            return {"success": False, "message": "Redis write/read test failed"}
            
    except Exception as e:
        return {"success": False, "message": f"Redis test error: {str(e)}"}

# 後方互換性のためのエイリアス
get_test_status = get_real_status
test_translate_menu_item = real_translate_menu_item
test_generate_menu_description = real_generate_menu_description
test_generate_menu_image = real_generate_menu_image 