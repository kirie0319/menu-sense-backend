#!/usr/bin/env python3
"""
🎯 メニューアイテム並列処理タスク（段階的実装・デバッグ版）

Phase 1: 基本的なタスク構造とRedis連携のテスト
"""

import time
import asyncio
import logging
import json
from typing import Dict, List, Any, Optional

from .celery_app import celery_app
from app.core.config import settings

# Redis接続（既存utilsから）
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
# 🧪 Phase 1: 基本的なテストタスク
# ===============================================

@celery_app.task(bind=True, queue='translate_queue', name="test_translate_menu_item")
def test_translate_menu_item(self, session_id: str, item_id: int, item_text: str):
    """
    Phase 1: 翻訳タスクの基本テスト版
    
    Args:
        session_id: セッションID  
        item_id: アイテムID (0-39)
        item_text: 日本語テキスト
        
    Returns:
        Dict: 翻訳結果
    """
    
    try:
        logger.info(f"🧪 [TEST] Starting translation: session={session_id}, item={item_id}, text='{item_text}'")
        
        # モックの翻訳処理（実際のAPI呼び出しはせずにテスト）
        time.sleep(1)  # 処理時間シミュレート
        english_text = f"[TRANSLATED] {item_text} (English version)"
        
        # Redis保存テスト
        redis_key = f"{session_id}:item{item_id}:translation"
        translation_data = {
            "japanese_text": item_text,
            "english_text": english_text,
            "timestamp": time.time(),
            "provider": "TestTranslationService",
            "test_mode": True
        }
        
        if redis_client:
            redis_client.setex(redis_key, 3600, json.dumps(translation_data))  # 1時間TTL
            logger.info(f"✅ [TEST] Translation saved to Redis: {redis_key}")
            
            # Redis読み取りテスト
            saved_data = redis_client.get(redis_key)
            if saved_data:
                parsed_data = json.loads(saved_data)
                logger.info(f"✅ [TEST] Redis read-back successful: {parsed_data['english_text']}")
            else:
                logger.error(f"❌ [TEST] Redis read-back failed")
        else:
            logger.error(f"❌ [TEST] Redis client not available")
        
        # 依存判定テスト呼び出し
        test_trigger_check(session_id, item_id)
        
        result = {
            "success": True,
            "session_id": session_id,
            "item_id": item_id,
            "japanese_text": item_text,
            "english_text": english_text,
            "processing_time": time.time(),
            "test_mode": True
        }
        
        logger.info(f"✅ [TEST] Translation completed: {item_text} → {english_text}")
        return result
        
    except Exception as e:
        logger.error(f"❌ [TEST] Translation failed: session={session_id}, item={item_id}, error={str(e)}")
        
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e),
            "test_mode": True
        }

@celery_app.task(bind=True, queue='description_queue', name="test_generate_menu_description")
def test_generate_menu_description(self, session_id: str, item_id: int, item_text: str):
    """
    Phase 1: 説明生成タスクの基本テスト版
    
    Args:
        session_id: セッションID
        item_id: アイテムID (0-39)
        item_text: 日本語テキスト
        
    Returns:
        Dict: 説明生成結果
    """
    
    try:
        logger.info(f"🧪 [TEST] Starting description generation: session={session_id}, item={item_id}, text='{item_text}'")
        
        # モックの説明生成処理
        time.sleep(2)  # 処理時間シミュレート（翻訳より少し重い）
        description = f"[DESCRIPTION] This is a delicious {item_text} with authentic Japanese flavors and premium ingredients."
        
        # Redis保存テスト
        redis_key = f"{session_id}:item{item_id}:description"
        description_data = {
            "japanese_text": item_text,
            "description": description,
            "timestamp": time.time(),
            "provider": "TestDescriptionService",
            "test_mode": True
        }
        
        if redis_client:
            redis_client.setex(redis_key, 3600, json.dumps(description_data))  # 1時間TTL
            logger.info(f"✅ [TEST] Description saved to Redis: {redis_key}")
            
            # Redis読み取りテスト
            saved_data = redis_client.get(redis_key)
            if saved_data:
                parsed_data = json.loads(saved_data)
                logger.info(f"✅ [TEST] Redis read-back successful: {parsed_data['description'][:50]}...")
            else:
                logger.error(f"❌ [TEST] Redis read-back failed")
        else:
            logger.error(f"❌ [TEST] Redis client not available")
        
        # 依存判定テスト呼び出し
        test_trigger_check(session_id, item_id)
        
        result = {
            "success": True,
            "session_id": session_id,
            "item_id": item_id,
            "japanese_text": item_text,
            "description": description,
            "processing_time": time.time(),
            "test_mode": True
        }
        
        logger.info(f"✅ [TEST] Description completed: {item_text} → {description[:50]}...")
        return result
        
    except Exception as e:
        logger.error(f"❌ [TEST] Description generation failed: session={session_id}, item={item_id}, error={str(e)}")
        
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e),
            "test_mode": True
        }

@celery_app.task(bind=True, queue='image_queue', name="test_generate_menu_image")
def test_generate_menu_image(self, session_id: str, item_id: int, prompt: str):
    """
    Phase 1: 画像生成タスクの基本テスト版
    
    Args:
        session_id: セッションID
        item_id: アイテムID (0-39)
        prompt: 画像生成プロンプト
        
    Returns:
        Dict: 画像生成結果
    """
    
    try:
        logger.info(f"🧪 [TEST] Starting image generation: session={session_id}, item={item_id}, prompt='{prompt[:50]}...'")
        
        # モックの画像生成処理
        time.sleep(3)  # 処理時間シミュレート（最も重い）
        image_url = f"https://test-images.example.com/{session_id}_{item_id}.jpg"
        
        # Redis保存テスト
        redis_key = f"{session_id}:item{item_id}:image_url"
        image_data = {
            "prompt": prompt,
            "image_url": image_url,
            "timestamp": time.time(),
            "provider": "TestImageService",
            "test_mode": True
        }
        
        if redis_client:
            redis_client.setex(redis_key, 3600, json.dumps(image_data))  # 1時間TTL
            logger.info(f"✅ [TEST] Image URL saved to Redis: {redis_key}")
            
            # Redis読み取りテスト
            saved_data = redis_client.get(redis_key)
            if saved_data:
                parsed_data = json.loads(saved_data)
                logger.info(f"✅ [TEST] Redis read-back successful: {parsed_data['image_url']}")
            else:
                logger.error(f"❌ [TEST] Redis read-back failed")
        else:
            logger.error(f"❌ [TEST] Redis client not available")
        
        result = {
            "success": True,
            "session_id": session_id,
            "item_id": item_id,
            "prompt": prompt,
            "image_url": image_url,
            "processing_time": time.time(),
            "test_mode": True
        }
        
        logger.info(f"✅ [TEST] Image generation completed: {prompt[:30]}... → {image_url}")
        return result
        
    except Exception as e:
        logger.error(f"❌ [TEST] Image generation failed: session={session_id}, item={item_id}, error={str(e)}")
        
        return {
            "success": False,
            "session_id": session_id,
            "item_id": item_id,
            "error": str(e),
            "test_mode": True
        }

# ===============================================
# 🧠 Phase 1: 依存判定テスト機能
# ===============================================

def test_trigger_check(session_id: str, item_id: int):
    """
    Phase 1: 依存判定のテスト版
    
    翻訳と説明が両方完了したら画像生成をトリガー
    """
    
    if not redis_client:
        logger.error("❌ [TEST] Redis not available for dependency check")
        return
    
    try:
        # Redis から翻訳と説明の完了状態をチェック
        translation_key = f"{session_id}:item{item_id}:translation"
        description_key = f"{session_id}:item{item_id}:description"
        
        translation_data = redis_client.get(translation_key)
        description_data = redis_client.get(description_key)
        
        logger.info(f"🔍 [TEST] Dependency check: session={session_id}, item={item_id}")
        logger.info(f"🔍 [TEST] Translation exists: {bool(translation_data)}")
        logger.info(f"🔍 [TEST] Description exists: {bool(description_data)}")
        
        # 両方が完了していたら画像生成プロンプトを作成
        if translation_data and description_data:
            translation_info = json.loads(translation_data)
            description_info = json.loads(description_data)
            
            # プロンプト作成
            prompt = make_test_image_prompt(
                translation_info.get("english_text", ""),
                description_info.get("description", "")
            )
            
            # 画像生成タスクを非同期で投入
            test_generate_menu_image.apply_async(
                args=[session_id, item_id, prompt],
                queue='image_queue'
            )
            
            logger.info(f"🎨 [TEST] Image generation triggered: session={session_id}, item={item_id}")
            logger.info(f"🎨 [TEST] Prompt: {prompt[:100]}...")
            
        else:
            logger.info(f"⏳ [TEST] Waiting for dependencies: translation={bool(translation_data)}, description={bool(description_data)}")
            
    except Exception as e:
        logger.error(f"⚠️ [TEST] Dependency check failed: {str(e)}")

def make_test_image_prompt(english_text: str, description: str) -> str:
    """Phase 1: テスト用画像生成プロンプト作成"""
    return f"[TEST PROMPT] Professional food photography of {english_text}. {description[:100]}. High quality, restaurant style."

# ===============================================
# 🧪 Phase 1: 基本機能テスト用ヘルパー
# ===============================================

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

def get_test_status(session_id: str, item_id: int):
    """特定アイテムのテスト状況を取得"""
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
        image_key = f"{session_id}:item{item_id}:image_url"
        image_data = redis_client.get(image_key)
        status["image"] = {
            "completed": bool(image_data),
            "data": json.loads(image_data) if image_data else None
        }
        
        return status
        
    except Exception as e:
        return {"error": f"Status check failed: {str(e)}"} 