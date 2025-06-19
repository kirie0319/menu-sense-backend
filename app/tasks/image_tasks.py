from .celery_app import celery_app
import time
import logging
from .utils import save_chunk_result, update_job_progress, get_job_info

# ログ設定
logger = logging.getLogger(__name__)

def create_safe_filename(english_name: str, timestamp: str) -> str:
    """安全なファイル名を作成（元のImagen3Serviceと同じ命名規則）"""
    # ファイル名を安全にする
    safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '' for c in english_name)
    safe_name = safe_name.replace(' ', '_').lower()[:30]  # 30文字に制限
    
    filename = f"menu_image_{safe_name}_{timestamp}.png"
    return filename

@celery_app.task(bind=True, name="hello_world_task")
def hello_world_task(self):
    """Celery動作確認用の基本タスク"""
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={'message': 'Hello World task started', 'progress': 0}
        )
        
        time.sleep(2)  # 2秒待機
        
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={'message': 'Hello World task processing', 'progress': 50}
        )
        
        time.sleep(2)  # さらに2秒待機
        
        # 完了
        return {
            'status': 'completed',
            'message': 'Hello World task completed successfully',
            'task_id': self.request.id,
            'progress': 100
        }
        
    except Exception as e:
        logger.error(f"Hello World task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e)}
        )
        raise e

@celery_app.task(bind=True, name="test_image_chunk")
def test_image_chunk_task(self, chunk_data, chunk_info):
    """画像生成チャンクの基本テスト（モック処理）"""
    try:
        # 進行状況更新
        self.update_state(
            state='PROGRESS',
            meta={
                'message': f'Processing chunk {chunk_info["chunk_id"]}/{chunk_info["total_chunks"]}',
                'progress': 0,
                'chunk_id': chunk_info["chunk_id"]
            }
        )
        
        # モック処理（実際の画像生成の代わりに待機）
        processing_time = len(chunk_data) * 0.5  # アイテム1つあたり0.5秒
        
        for i, item in enumerate(chunk_data):
            time.sleep(0.5)  # 処理時間をシミュレート
            
            progress = int((i + 1) / len(chunk_data) * 100)
            self.update_state(
                state='PROGRESS',
                meta={
                    'message': f'Processing item {i+1}/{len(chunk_data)} in chunk {chunk_info["chunk_id"]}',
                    'progress': progress,
                    'chunk_id': chunk_info["chunk_id"],
                    'current_item': item.get('english_name', 'Unknown')
                }
            )
        
        # チャンク処理完了
        mock_results = []
        for item in chunk_data:
            # 元のImagen3Serviceと同じ命名規則を使用
            english_name = item.get('english_name', 'item')
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_filename = create_safe_filename(english_name, timestamp)
            
            mock_results.append({
                "japanese_name": item.get("japanese_name", "N/A"),
                "english_name": item.get("english_name", "N/A"),
                "image_url": f"/uploads/{safe_filename}",
                "generation_success": True,
                "mock_processing": True
            })
        
        return {
            'status': 'completed',
            'chunk_id': chunk_info["chunk_id"],
            'results': mock_results,
            'items_processed': len(chunk_data),
            'processing_time': processing_time
        }
        
    except Exception as e:
        logger.error(f"Test image chunk task failed: {str(e)}")
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'chunk_id': chunk_info.get("chunk_id", "unknown")}
        )
        raise e

@celery_app.task(bind=True, name="advanced_image_chunk")
def advanced_image_chunk_task(self, chunk_data, chunk_info, job_id=None):
    """Redis進行状況管理統合済みの高度な画像チャンクタスク"""
    chunk_id = chunk_info["chunk_id"]
    
    try:
        logger.info(f"Starting advanced image chunk task: job_id={job_id}, chunk_id={chunk_id}")
        
        # 初期進行状況更新
        progress_data = {
            'message': f'Starting chunk {chunk_id}/{chunk_info["total_chunks"]}',
            'progress': 0,
            'chunk_id': chunk_id,
            'status': 'processing',
            'timestamp': time.time()
        }
        
        # Celeryタスク状態更新
        self.update_state(state='PROGRESS', meta=progress_data)
        
        # Redis進行状況更新
        if job_id:
            update_job_progress(job_id, {
                f"chunk_{chunk_id}": progress_data
            })
        
        # アイテム別処理
        processed_results = []
        total_items = len(chunk_data)
        
        for i, item in enumerate(chunk_data):
            # アイテム処理をシミュレート
            processing_start = time.time()
            time.sleep(0.8)  # より現実的な処理時間
            processing_end = time.time()
            
            # 元のImagen3Serviceと同じ命名規則を使用
            english_name = item.get('english_name', 'item')
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_filename = create_safe_filename(english_name, timestamp)
            
            # 結果生成
            item_result = {
                "japanese_name": item.get("japanese_name", "N/A"),
                "english_name": item.get("english_name", "N/A"),
                "image_url": f"/uploads/{safe_filename}",
                "generation_success": True,
                "processing_time": round(processing_end - processing_start, 2),
                "mock_processing": True,
                "category": chunk_info.get("category", "Unknown")
            }
            
            processed_results.append(item_result)
            
            # 進行状況計算
            item_progress = int((i + 1) / total_items * 100)
            
            # 進行状況データ更新
            progress_data = {
                'message': f'Processed {i+1}/{total_items} items in chunk {chunk_id}',
                'progress': item_progress,
                'chunk_id': chunk_id,
                'current_item': item.get('english_name', 'Unknown'),
                'items_completed': i + 1,
                'items_total': total_items,
                'status': 'processing',
                'timestamp': time.time()
            }
            
            # Celeryタスク状態更新
            self.update_state(state='PROGRESS', meta=progress_data)
            
            # Redis進行状況更新
            if job_id:
                update_job_progress(job_id, {
                    f"chunk_{chunk_id}": progress_data
                })
            
            logger.info(f"Processed item {i+1}/{total_items} in chunk {chunk_id}: {item.get('english_name')}")
        
        # チャンク完了
        final_result = {
            'status': 'completed',
            'chunk_id': chunk_id,
            'category': chunk_info.get("category", "Unknown"),
            'results': processed_results,
            'items_processed': len(processed_results),
            'items_successful': len([r for r in processed_results if r.get("generation_success")]),
            'processing_time': sum(r.get("processing_time", 0) for r in processed_results),
            'completed_at': time.time()
        }
        
        # Redis にチャンク結果を保存
        if job_id:
            save_chunk_result(job_id, chunk_id, final_result)
            
            # 最終進行状況更新
            update_job_progress(job_id, {
                f"chunk_{chunk_id}": {
                    'message': f'Chunk {chunk_id} completed successfully',
                    'progress': 100,
                    'chunk_id': chunk_id,
                    'status': 'completed',
                    'timestamp': time.time(),
                    'items_processed': len(processed_results)
                }
            })
        
        logger.info(f"Advanced image chunk task completed: chunk_id={chunk_id}, items={len(processed_results)}")
        return final_result
        
    except Exception as e:
        logger.error(f"Advanced image chunk task failed: chunk_id={chunk_id}, error={str(e)}")
        
        # エラー情報
        error_result = {
            'status': 'failed',
            'chunk_id': chunk_id,
            'error': str(e),
            'failed_at': time.time()
        }
        
        # Celeryタスク状態更新
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'chunk_id': chunk_id}
        )
        
        # Redis エラー情報保存
        if job_id:
            save_chunk_result(job_id, chunk_id, error_result)
            update_job_progress(job_id, {
                f"chunk_{chunk_id}": {
                    'message': f'Chunk {chunk_id} failed: {str(e)}',
                    'progress': 0,
                    'chunk_id': chunk_id,
                    'status': 'failed',
                    'timestamp': time.time(),
                    'error': str(e)
                }
            })
        
        raise e

@celery_app.task(bind=True, name="real_image_chunk")
def real_image_chunk_task(self, chunk_data, chunk_info, job_id=None):
    """実際の画像生成を行うチャンクタスク"""
    chunk_id = chunk_info["chunk_id"]
    
    try:
        logger.info(f"Starting real image chunk task: job_id={job_id}, chunk_id={chunk_id}")
        
        # 初期進行状況更新
        progress_data = {
            'message': f'Starting real image generation for chunk {chunk_id}/{chunk_info["total_chunks"]}',
            'progress': 0,
            'chunk_id': chunk_id,
            'status': 'processing',
            'timestamp': time.time()
        }
        
        # Celeryタスク状態更新
        self.update_state(state='PROGRESS', meta=progress_data)
        
        # Redis進行状況更新
        if job_id:
            update_job_progress(job_id, {
                f"chunk_{chunk_id}": progress_data
            })
        
        # 実際の画像生成処理
        processed_results = []
        total_items = len(chunk_data)
        
        # Imagen3サービスを初期化
        try:
            from app.services.image.imagen3 import Imagen3Service
            imagen_service = Imagen3Service()
            
            if not imagen_service.is_available():
                # Imagen3が利用できない場合はモック処理にフォールバック
                logger.warning(f"Imagen3 not available, falling back to mock processing for chunk {chunk_id}")
                return advanced_image_chunk_task(self, chunk_data, chunk_info, job_id)
            
        except Exception as e:
            logger.error(f"Failed to initialize Imagen3Service: {e}")
            # 初期化失敗時もモック処理にフォールバック
            return advanced_image_chunk_task(self, chunk_data, chunk_info, job_id)
        
        for i, item in enumerate(chunk_data):
            processing_start = time.time()
            
            # 実際の画像生成を実行
            japanese_name = item.get("japanese_name", "N/A")
            english_name = item.get("english_name", "N/A")
            description = item.get("description", "")
            category = chunk_info.get("category", "Unknown")
            
            try:
                # 同期的に画像生成を実行
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                image_result = loop.run_until_complete(
                    imagen_service.generate_single_image(
                        japanese_name, english_name, description, category
                    )
                )
                
                loop.close()
                
            except Exception as e:
                # 個別アイテムの生成に失敗した場合
                logger.error(f"Failed to generate image for {english_name}: {e}")
                
                # エラー時のファイル名生成
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                safe_filename = create_safe_filename(english_name, timestamp)
                
                image_result = {
                    "japanese_name": japanese_name,
                    "english_name": english_name,
                    "image_url": f"/uploads/{safe_filename}",
                    "generation_success": False,
                    "error": str(e),
                    "mock_fallback": True
                }
            
            processing_end = time.time()
            image_result["processing_time"] = round(processing_end - processing_start, 2)
            image_result["category"] = category
            image_result["real_processing"] = True
            
            processed_results.append(image_result)
            
            # 進行状況計算
            item_progress = int((i + 1) / total_items * 100)
            
            # 進行状況データ更新
            progress_data = {
                'message': f'Generated image {i+1}/{total_items} in chunk {chunk_id}',
                'progress': item_progress,
                'chunk_id': chunk_id,
                'current_item': english_name,
                'items_completed': i + 1,
                'items_total': total_items,
                'status': 'processing',
                'timestamp': time.time()
            }
            
            # Celeryタスク状態更新
            self.update_state(state='PROGRESS', meta=progress_data)
            
            # Redis進行状況更新
            if job_id:
                update_job_progress(job_id, {
                    f"chunk_{chunk_id}": progress_data
                })
            
            logger.info(f"Generated image {i+1}/{total_items} in chunk {chunk_id}: {english_name}")
        
        # チャンク完了
        final_result = {
            'status': 'completed',
            'chunk_id': chunk_id,
            'category': chunk_info.get("category", "Unknown"),
            'results': processed_results,
            'items_processed': len(processed_results),
            'items_successful': len([r for r in processed_results if r.get("generation_success")]),
            'processing_time': sum(r.get("processing_time", 0) for r in processed_results),
            'completed_at': time.time(),
            'real_image_generation': True
        }
        
        # Redis にチャンク結果を保存
        if job_id:
            save_chunk_result(job_id, chunk_id, final_result)
            
            # 最終進行状況更新
            update_job_progress(job_id, {
                f"chunk_{chunk_id}": {
                    'message': f'Real image chunk {chunk_id} completed successfully',
                    'progress': 100,
                    'chunk_id': chunk_id,
                    'status': 'completed',
                    'timestamp': time.time(),
                    'items_processed': len(processed_results)
                }
            })
        
        logger.info(f"Real image chunk task completed: chunk_id={chunk_id}, items={len(processed_results)}")
        return final_result
        
    except Exception as e:
        logger.error(f"Real image chunk task failed: chunk_id={chunk_id}, error={str(e)}")
        
        # エラー情報
        error_result = {
            'status': 'failed',
            'chunk_id': chunk_id,
            'error': str(e),
            'failed_at': time.time()
        }
        
        # Celeryタスク状態更新
        self.update_state(
            state='FAILURE',
            meta={'error': str(e), 'chunk_id': chunk_id}
        )
        
        # Redis エラー情報保存
        if job_id:
            save_chunk_result(job_id, chunk_id, error_result)
            update_job_progress(job_id, {
                f"chunk_{chunk_id}": {
                    'message': f'Real image chunk {chunk_id} failed: {str(e)}',
                    'progress': 0,
                    'chunk_id': chunk_id,
                    'status': 'failed',
                    'timestamp': time.time(),
                    'error': str(e)
                }
            })
        
        raise e

# デバッグ用: タスク情報取得
def get_task_info(task_id):
    """タスクの詳細情報を取得"""
    result = celery_app.AsyncResult(task_id)
    
    return {
        "task_id": task_id,
        "state": result.state,
        "info": result.info,
        "successful": result.successful(),
        "failed": result.failed(),
        "ready": result.ready()
    }
