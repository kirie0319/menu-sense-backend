"""
純粋コンピュート処理タスク

フロー制御なし、データ管理なし、純粋な重い処理のみ
- 翻訳処理
- 説明生成処理
- 画像生成処理
"""

import asyncio
import logging
import time
from typing import Dict, Optional

from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

def await_sync(coroutine):
    """同期的にコルーチンを実行"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coroutine)


@celery_app.task(bind=True, name="translate_item_pure")
def translate_item_pure(
    self,
    japanese_name: str,
    price: str = "",
    category: str = "Other"
) -> Dict:
    """
    純粋翻訳処理（フロー制御なし）
    
    Args:
        japanese_name: 日本語名
        price: 価格
        category: カテゴリ
        
    Returns:
        Dict: 翻訳結果
    """
    start_time = time.time()
    
    try:
        logger.debug(f"Pure translation task: {japanese_name}")
        
        # Google Translate試行
        try:
            from app.services.translation.google_translate import GoogleTranslateService
            
            google_service = GoogleTranslateService()
            
            if google_service.is_available():
                # 単純な翻訳実行
                result = await_sync(google_service.translate_text(japanese_name))
                
                if result and hasattr(result, 'text'):
                    english_name = result.text.strip()
                    
                    return {
                        'success': True,
                        'result': {
                            'japanese_name': japanese_name,
                            'english_name': english_name,
                            'price': price,
                            'category': category
                        },
                        'service': 'Google Translate',
                        'processing_time': time.time() - start_time
                    }
        
        except Exception as google_error:
            logger.warning(f"Google Translate failed: {google_error}")
        
        # OpenAI フォールバック
        try:
            from app.services.translation.openai_translate import OpenAITranslateService
            
            openai_service = OpenAITranslateService()
            
            if openai_service.is_available():
                result = await_sync(openai_service.translate_menu_item(
                    japanese_name, category
                ))
                
                if result and result.get('success'):
                    english_name = result.get('english_name', japanese_name)
                    
                    return {
                        'success': True,
                        'result': {
                            'japanese_name': japanese_name,
                            'english_name': english_name,
                            'price': price,
                            'category': category
                        },
                        'service': 'OpenAI Fallback',
                        'processing_time': time.time() - start_time
                    }
        
        except Exception as openai_error:
            logger.error(f"OpenAI translation failed: {openai_error}")
        
        # 最終フォールバック：そのまま返す
        return {
            'success': True,
            'result': {
                'japanese_name': japanese_name,
                'english_name': japanese_name,  # フォールバック
                'price': price,
                'category': category
            },
            'service': 'Fallback (No Translation)',
            'processing_time': time.time() - start_time,
            'fallback_used': True
        }
        
    except Exception as e:
        logger.error(f"Translation task failed for {japanese_name}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'processing_time': time.time() - start_time
        }


@celery_app.task(bind=True, name="generate_description_pure")
def generate_description_pure(
    self,
    japanese_name: str,
    english_name: str,
    category: str = "Other"
) -> Dict:
    """
    純粋説明生成処理（フロー制御なし）
    
    Args:
        japanese_name: 日本語名
        english_name: 英語名
        category: カテゴリ
        
    Returns:
        Dict: 説明生成結果
    """
    start_time = time.time()
    
    try:
        logger.debug(f"Pure description task: {english_name}")
        
        # OpenAI APIで説明生成
        from app.services.description.openai import OpenAIDescriptionService
        
        description_service = OpenAIDescriptionService()
        
        if not description_service.is_available():
            # フォールバック説明
            fallback_description = f"Traditional Japanese {category.lower()} with authentic flavors and high-quality ingredients."
            
            return {
                'success': True,
                'result': {
                    'japanese_name': japanese_name,
                    'english_name': english_name,
                    'description': fallback_description,
                    'category': category
                },
                'service': 'Fallback Description',
                'processing_time': time.time() - start_time,
                'fallback_used': True
            }
        
        # 実際の説明生成
        result = await_sync(description_service.generate_description(
            japanese_name=japanese_name,
            english_name=english_name,
            category=category
        ))
        
        if result and result.get('success'):
            description = result.get('description', f"Delicious {english_name}")
            
            return {
                'success': True,
                'result': {
                    'japanese_name': japanese_name,
                    'english_name': english_name,
                    'description': description,
                    'category': category
                },
                'service': 'OpenAI Description',
                'processing_time': time.time() - start_time
            }
        else:
            # エラー時のフォールバック
            fallback_description = f"Delicious {english_name} - a traditional {category.lower()} dish."
            
            return {
                'success': True,
                'result': {
                    'japanese_name': japanese_name,
                    'english_name': english_name,
                    'description': fallback_description,
                    'category': category
                },
                'service': 'Error Fallback Description',
                'processing_time': time.time() - start_time,
                'fallback_used': True
            }
        
    except Exception as e:
        logger.error(f"Description task failed for {english_name}: {str(e)}")
        
        # エラー時のフォールバック説明
        fallback_description = f"Traditional {category.lower()} dish with authentic Japanese flavors."
        
        return {
            'success': True,
            'result': {
                'japanese_name': japanese_name,
                'english_name': english_name,
                'description': fallback_description,
                'category': category
            },
            'service': 'Exception Fallback',
            'processing_time': time.time() - start_time,
            'fallback_used': True,
            'error': str(e)
        }


@celery_app.task(bind=True, name="generate_image_pure")
def generate_image_pure(
    self,
    japanese_name: str,
    english_name: str,
    description: str,
    category: str = "Other"
) -> Dict:
    """
    純粋画像生成処理（フロー制御なし）
    
    Args:
        japanese_name: 日本語名
        english_name: 英語名
        description: 説明
        category: カテゴリ
        
    Returns:
        Dict: 画像生成結果
    """
    start_time = time.time()
    
    try:
        logger.debug(f"Pure image generation task: {english_name}")
        
        # Imagen 3画像生成
        from app.services.image.imagen3 import Imagen3Service
        
        image_service = Imagen3Service()
        
        if not image_service.is_available():
            return {
                'success': False,
                'error': 'Imagen 3 service not available',
                'image_url': None,
                'processing_time': time.time() - start_time,
                'service': 'Imagen 3 (Unavailable)'
            }
        
        # 画像生成実行
        result = await_sync(image_service.generate_single_image(
            japanese_name=japanese_name,
            english_name=english_name,
            description=description,
            category=category
        ))
        
        if result and result.get('generation_success'):
            return {
                'success': True,
                'image_url': result.get('image_url'),
                'processing_time': time.time() - start_time,
                'service': 'Imagen 3'
            }
        else:
            return {
                'success': False,
                'error': f"Image generation failed: {result}",
                'image_url': None,
                'processing_time': time.time() - start_time,
                'service': 'Imagen 3 (Failed)'
            }
        
    except Exception as e:
        logger.error(f"Image generation task failed for {english_name}: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'image_url': None,
            'processing_time': time.time() - start_time,
            'service': 'Imagen 3 (Exception)'
        }


@celery_app.task(bind=True, name="hello_world_pure")
def hello_world_pure(self, message: str = "Hello from Pure Compute!") -> Dict:
    """
    テスト用純粋タスク
    
    Args:
        message: テストメッセージ
        
    Returns:
        Dict: テスト結果
    """
    start_time = time.time()
    
    try:
        # 軽い処理時間シミュレーション
        import time as time_module
        time_module.sleep(0.1)
        
        return {
            'success': True,
            'message': message,
            'timestamp': time.time(),
            'processing_time': time.time() - start_time,
            'task_type': 'pure_compute'
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'processing_time': time.time() - start_time
        } 