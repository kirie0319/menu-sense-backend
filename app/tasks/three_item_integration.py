#!/usr/bin/env python3
"""
3つずつ統合処理タスク

目標: 翻訳 → 詳細説明 → 画像生成までを3つのアイテムで同時実行
- 最速のユーザー体験（完了次第配信）
- 統合処理による効率化
- 責任分離アーキテクチャ準拠
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional

from .celery_app import celery_app

logger = logging.getLogger(__name__)

def await_sync(coro):
    """非同期関数を同期的に実行（Celeryワーカー用）"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@celery_app.task(bind=True, name="process_three_items_complete")
def process_three_items_complete(self, items_batch: List[Dict]) -> Dict:
    """
    3つのアイテムを完全処理（翻訳 → 詳細説明 → 画像生成）
    
    Args:
        items_batch: 処理するアイテムリスト（最大3つ）
        
    Returns:
        Dict: 統合処理結果
    """
    batch_id = f"three_batch_{int(time.time())}"
    start_time = time.time()
    
    try:
        logger.info(f"Starting three-item integration processing: {len(items_batch)} items (ID: {batch_id})")
        
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'three_item_integration',
                'batch_id': batch_id,
                'progress': 0,
                'status': 'starting',
                'items_count': len(items_batch),
                'processing_mode': 'three_item_complete'
            }
        )
        
        completed_items = []
        
        # 各アイテムを順次処理（3つまで）
        for i, item in enumerate(items_batch[:3]):  # 最大3つまで
            item_start_time = time.time()
            
            try:
                logger.info(f"Processing item {i+1}/{len(items_batch)}: {item.get('japanese_name', 'Unknown')}")
                
                # Step 1: 翻訳
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': 'three_item_integration',
                        'batch_id': batch_id,
                        'progress': int((i / len(items_batch)) * 100) + 10,
                        'status': f'translating_item_{i+1}',
                        'current_item': item.get('japanese_name', 'Unknown')
                    }
                )
                
                translation_result = await_sync(translate_item_step(item))
                
                if not translation_result.get('success'):
                    logger.warning(f"Translation failed for item {i+1}: {translation_result.get('error', 'Unknown error')}")
                    continue
                
                # Step 2: 詳細説明
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': 'three_item_integration',
                        'batch_id': batch_id,
                        'progress': int((i / len(items_batch)) * 100) + 20,
                        'status': f'describing_item_{i+1}',
                        'current_item': translation_result['english_name']
                    }
                )
                
                description_result = await_sync(describe_item_step(
                    translation_result['japanese_name'],
                    translation_result['english_name'],
                    translation_result.get('category', 'Other')
                ))
                
                if not description_result.get('success'):
                    logger.warning(f"Description failed for item {i+1}: {description_result.get('error', 'Unknown error')}")
                    # 翻訳のみで続行
                    description_result = {
                        'success': True,
                        'description': f"Delicious {translation_result['english_name']} - a traditional Japanese dish."
                    }
                
                # Step 3: 画像生成
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': 'three_item_integration',
                        'batch_id': batch_id,
                        'progress': int((i / len(items_batch)) * 100) + 30,
                        'status': f'generating_image_{i+1}',
                        'current_item': translation_result['english_name']
                    }
                )
                
                image_result = await_sync(generate_image_step(
                    translation_result['japanese_name'],
                    translation_result['english_name'],
                    description_result['description'],
                    translation_result.get('category', 'Other')
                ))
                
                if not image_result.get('success'):
                    logger.warning(f"Image generation failed for item {i+1}: {image_result.get('error', 'Unknown error')}")
                    # 画像なしで続行
                    image_result = {
                        'success': True,
                        'image_url': None
                    }
                
                # 統合結果の作成
                item_processing_time = time.time() - item_start_time
                
                integrated_item = {
                    'item_id': item.get('item_id', f'item_{i+1}'),
                    'japanese_name': translation_result['japanese_name'],
                    'english_name': translation_result['english_name'],
                    'description': description_result['description'],
                    'image_url': image_result.get('image_url'),
                    'price': item.get('price', ''),
                    'category': item.get('category', ''),
                    'processing_time': item_processing_time,
                    'integration_complete': True,
                    'processing_steps': ['translation', 'description', 'image'],
                    'translation_service': translation_result.get('service', 'Unknown'),
                    'description_service': description_result.get('service', 'Unknown'),
                    'image_service': image_result.get('service', 'Unknown')
                }
                
                completed_items.append(integrated_item)
                
                # アイテム完了更新
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': 'three_item_integration',
                        'batch_id': batch_id,
                        'progress': int(((i + 1) / len(items_batch)) * 100),
                        'status': f'completed_item_{i+1}',
                        'completed_items': len(completed_items),
                        'latest_completed': integrated_item
                    }
                )
                
                logger.info(f"✅ Item {i+1} integration completed in {item_processing_time:.2f}s: {translation_result['japanese_name']} → {translation_result['english_name']}")
                
            except Exception as e:
                logger.error(f"❌ Item {i+1} integration failed: {str(e)}")
                # エラーアイテムもログに記録
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'stage': 'three_item_integration',
                        'batch_id': batch_id,
                        'progress': int(((i + 1) / len(items_batch)) * 100),
                        'status': f'failed_item_{i+1}',
                        'error': str(e)
                    }
                )
        
        # 最終完了
        total_processing_time = time.time() - start_time
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'three_item_integration',
                'batch_id': batch_id,
                'progress': 100,
                'status': 'completed',
                'completed_items': len(completed_items),
                'total_processing_time': total_processing_time
            }
        )
        
        result = {
            'success': True,
            'batch_id': batch_id,
            'completed_items': completed_items,
            'total_items': len(items_batch),
            'completed_count': len(completed_items),
            'failed_count': len(items_batch) - len(completed_items),
            'processing_method': 'three_item_complete_integration',
            'total_processing_time': total_processing_time,
            'average_item_time': total_processing_time / len(completed_items) if completed_items else 0,
            'integration_features': [
                'translation',
                'detailed_description', 
                'image_generation',
                'complete_processing'
            ]
        }
        
        logger.info(f"Three-item integration completed: {len(completed_items)}/{len(items_batch)} items successful in {total_processing_time:.2f}s")
        
        return result
        
    except Exception as e:
        total_processing_time = time.time() - start_time
        logger.error(f"Three-item integration failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'three_item_integration',
                'batch_id': batch_id,
                'error': str(e),
                'status': 'failed',
                'total_processing_time': total_processing_time
            }
        )
        
        return {
            'success': False,
            'batch_id': batch_id,
            'error': str(e),
            'processing_method': 'three_item_complete_failed',
            'total_processing_time': total_processing_time
        }

async def translate_item_step(item: Dict) -> Dict:
    """翻訳ステップ"""
    try:
        from app.services.translation.google_translate import GoogleTranslateService
        
        google_service = GoogleTranslateService()
        
        if not google_service.is_available():
            # フォールバック: OpenAI
            from app.services.translation.openai import OpenAITranslationService
            translation_service = OpenAITranslationService()
            if not translation_service.is_available():
                return {'success': False, 'error': 'No translation services available'}
        else:
            translation_service = google_service
        
        japanese_name = item.get('japanese_name', '')
        english_name = await translation_service.translate_menu_item(japanese_name)
        
        return {
            'success': True,
            'japanese_name': japanese_name,
            'english_name': english_name,
            'category': item.get('category', ''),
            'service': type(translation_service).__name__
        }
        
    except Exception as e:
        logger.error(f"Translation step failed: {str(e)}")
        return {'success': False, 'error': str(e)}

async def describe_item_step(japanese_name: str, english_name: str, category: str) -> Dict:
    """詳細説明ステップ"""
    try:
        from app.services.description.openai import OpenAIDescriptionService
        
        description_service = OpenAIDescriptionService()
        
        if not description_service.is_available():
            # フォールバック説明
            fallback_description = f"Traditional Japanese {category.lower()} with authentic flavors and high-quality ingredients."
            return {
                'success': True,
                'description': fallback_description,
                'service': 'Fallback Description'
            }
        
        # 説明生成（同期メソッド呼び出し）
        result = description_service.generate_description(
            japanese_name=japanese_name,
            english_name=english_name,
            category=category
        )
        
        if result and result.get('success'):
            return {
                'success': True,
                'description': result.get('description', f"Delicious {english_name}"),
                'service': 'OpenAI Description'
            }
        else:
            # エラー時のフォールバック
            fallback_description = f"Delicious {english_name} - a traditional {category.lower()} dish."
            return {
                'success': True,
                'description': fallback_description,
                'service': 'Error Fallback Description'
            }
        
    except Exception as e:
        logger.error(f"Description step failed: {str(e)}")
        # エラー時のフォールバック説明
        fallback_description = f"Traditional {category.lower()} dish with authentic Japanese flavors."
        return {
            'success': True,
            'description': fallback_description,
            'service': 'Exception Fallback'
        }

async def generate_image_step(japanese_name: str, english_name: str, description: str, category: str) -> Dict:
    """画像生成ステップ"""
    try:
        from app.services.image.imagen3 import Imagen3Service
        
        image_service = Imagen3Service()
        
        if not image_service.is_available():
            return {
                'success': False,
                'error': 'Imagen 3 service not available',
                'image_url': None,
                'service': 'Imagen 3 (Unavailable)'
            }
        
        # 画像生成実行
        result = await image_service.generate_single_image(
            japanese_name=japanese_name,
            english_name=english_name,
            description=description,
            category=category
        )
        
        if result and result.get('generation_success'):
            return {
                'success': True,
                'image_url': result.get('image_url'),
                'service': 'Imagen 3'
            }
        else:
            return {
                'success': False,
                'error': f"Image generation failed: {result}",
                'image_url': None,
                'service': 'Imagen 3 (Failed)'
            }
        
    except Exception as e:
        logger.error(f"Image generation step failed: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'image_url': None,
            'service': 'Exception'
        }

# エクスポート
__all__ = [
    "process_three_items_complete"
] 