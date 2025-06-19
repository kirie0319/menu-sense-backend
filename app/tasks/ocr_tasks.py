#!/usr/bin/env python3
"""
OCR処理 Celeryタスク

Stage 1 OCRの並列化を実現するワーカータスク群
- マルチエンジン並列OCR（Gemini + Google Vision）
- 結果品質の自動判定
- エラー時の自動フォールバック
- フロントエンド互換性の完全保持
"""

import time
import asyncio
import logging
from typing import Dict, List, Any, Optional

from .celery_app import celery_app

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

@celery_app.task(bind=True, name="ocr_with_gemini")
def ocr_with_gemini(self, image_path: str, session_id: str = None):
    """
    Gemini 2.0 Flash OCRワーカータスク
    
    Args:
        image_path: 画像ファイルパス
        session_id: セッションID
        
    Returns:
        Dict: OCR結果
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ocr_gemini',
                'progress': 0,
                'status': 'starting',
                'engine': 'gemini-2.0-flash'
            }
        )
        
        logger.info(f"Starting Gemini OCR for: {image_path}")
        
        # Gemini OCRサービスを初期化
        from app.services.ocr.gemini import GeminiOCRService
        
        gemini_service = GeminiOCRService()
        
        if not gemini_service.is_available():
            raise Exception("Gemini OCR service not available")
        
        # OCR実行
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ocr_gemini',
                'progress': 20,
                'status': 'processing'
            }
        )
        
        result = await_sync(gemini_service.extract_text(image_path, session_id))
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ocr_gemini',
                'progress': 100,
                'status': 'completed'
            }
        )
        
        response = {
            'success': result.success,
            'extracted_text': result.extracted_text,
            'error': result.error if not result.success else None,
            'engine': 'gemini-2.0-flash',
            'text_length': len(result.extracted_text) if result.success else 0,
            'processing_time': time.time(),
            'metadata': result.metadata
        }
        
        logger.info(f"Gemini OCR completed: {len(result.extracted_text) if result.success else 0} characters")
        return response
        
    except Exception as e:
        logger.error(f"Gemini OCR failed: {str(e)}")
        
        # エラー状態更新
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'ocr_gemini',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'extracted_text': '',
            'error': str(e),
            'engine': 'gemini-2.0-flash',
            'text_length': 0,
            'processing_time': time.time()
        }

@celery_app.task(bind=True, name="ocr_with_google_vision")
def ocr_with_google_vision(self, image_path: str, session_id: str = None):
    """
    Google Vision API OCRワーカータスク
    
    Args:
        image_path: 画像ファイルパス
        session_id: セッションID
        
    Returns:
        Dict: OCR結果
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ocr_google_vision',
                'progress': 0,
                'status': 'starting',
                'engine': 'google-vision'
            }
        )
        
        logger.info(f"Starting Google Vision OCR for: {image_path}")
        
        # Google Vision OCRサービスを初期化
        from app.services.ocr.google_vision import GoogleVisionOCRService
        
        vision_service = GoogleVisionOCRService()
        
        if not vision_service.is_available():
            raise Exception("Google Vision OCR service not available")
        
        # OCR実行
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ocr_google_vision',
                'progress': 20,
                'status': 'processing'
            }
        )
        
        result = await_sync(vision_service.extract_text(image_path, session_id))
        
        # 完了
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'ocr_google_vision',
                'progress': 100,
                'status': 'completed'
            }
        )
        
        response = {
            'success': result.success,
            'extracted_text': result.extracted_text,
            'error': result.error if not result.success else None,
            'engine': 'google-vision',
            'text_length': len(result.extracted_text) if result.success else 0,
            'processing_time': time.time(),
            'metadata': result.metadata
        }
        
        logger.info(f"Google Vision OCR completed: {len(result.extracted_text) if result.success else 0} characters")
        return response
        
    except Exception as e:
        logger.error(f"Google Vision OCR failed: {str(e)}")
        
        # エラー状態更新
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'ocr_google_vision',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'extracted_text': '',
            'error': str(e),
            'engine': 'google-vision',
            'text_length': 0,
            'processing_time': time.time()
        }

@celery_app.task(bind=True, name="ocr_parallel_multi_engine")
def ocr_parallel_multi_engine(self, image_path: str, session_id: str = None):
    """
    マルチエンジン並列OCRワーカータスク
    
    Args:
        image_path: 画像ファイルパス
        session_id: セッションID
        
    Returns:
        Dict: 最適OCR結果
    """
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'parallel_ocr',
                'progress': 0,
                'status': 'starting',
                'engines': ['gemini-2.0-flash', 'google-vision']
            }
        )
        
        logger.info(f"Starting parallel multi-engine OCR for: {image_path}")
        
        # 並列OCRタスクを作成
        gemini_task = ocr_with_gemini.delay(image_path, session_id)
        vision_task = ocr_with_google_vision.delay(image_path, session_id)
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'parallel_ocr',
                'progress': 10,
                'status': 'engines_started',
                'tasks_created': 2
            }
        )
        
        # 両タスクの完了を待機
        results = []
        tasks = [
            ('gemini', gemini_task),
            ('google_vision', vision_task)
        ]
        
        for engine_name, task in tasks:
            try:
                # タスク完了を待機（タイムアウト60秒）
                result = task.get(timeout=60)
                results.append((engine_name, result))
                logger.info(f"{engine_name} OCR completed")
            except Exception as e:
                logger.warning(f"{engine_name} OCR failed: {str(e)}")
                results.append((engine_name, {
                    'success': False,
                    'extracted_text': '',
                    'error': str(e),
                    'engine': engine_name,
                    'text_length': 0
                }))
        
        # 結果を評価して最適な結果を選択
        best_result = _select_best_ocr_result(results)
        
        self.update_state(
            state='PROGRESS',
            meta={
                'stage': 'parallel_ocr',
                'progress': 100,
                'status': 'completed',
                'selected_engine': best_result.get('engine', 'unknown')
            }
        )
        
        # 並列処理メタデータを追加
        best_result.update({
            'parallel_processing': True,
            'engines_used': ['gemini-2.0-flash', 'google-vision'],
            'all_results': {
                result[0]: {
                    'success': result[1]['success'],
                    'text_length': result[1]['text_length'],
                    'error': result[1].get('error')
                } for result in results
            }
        })
        
        logger.info(f"Parallel OCR completed. Selected: {best_result.get('engine')} ({best_result.get('text_length', 0)} characters)")
        return best_result
        
    except Exception as e:
        logger.error(f"Parallel OCR failed: {str(e)}")
        
        self.update_state(
            state='FAILURE',
            meta={
                'stage': 'parallel_ocr',
                'error': str(e),
                'status': 'failed',
                'exc_type': type(e).__name__,
                'exc_module': type(e).__module__
            }
        )
        
        return {
            'success': False,
            'extracted_text': '',
            'error': f"Parallel OCR error: {str(e)}",
            'engine': 'parallel_multi_engine',
            'text_length': 0,
            'parallel_processing': True
        }

def _select_best_ocr_result(results):
    """複数OCR結果から最適な結果を選択"""
    successful_results = [r for r in results if r[1]['success']]
    
    if not successful_results:
        # 全てが失敗した場合は最初の結果を返す
        return results[0][1] if results else {
            'success': False,
            'extracted_text': '',
            'error': 'All OCR engines failed',
            'engine': 'none',
            'text_length': 0
        }
    
    # 文字数が最も多い結果を選択
    best_result = max(successful_results, key=lambda x: x[1]['text_length'])
    
    # 選択理由をメタデータに追加
    best_result[1]['selection_reason'] = f"Most text extracted ({best_result[1]['text_length']} characters)"
    
    return best_result[1] 