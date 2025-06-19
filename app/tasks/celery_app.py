from celery import Celery
from app.core.config import settings
import os

def create_celery_app():
    """Celeryアプリケーションを作成・設定（最適化版）"""
    
    # Redis URLの設定
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    celery_app = Celery(
        "image_processor",
        broker=redis_url,
        backend=redis_url,
        include=["app.tasks.image_tasks", "app.tasks.translation_tasks", "app.tasks.description_tasks", "app.tasks.ocr_tasks", "app.tasks.pipeline_tasks", "app.tasks.categorization_tasks"]
    )
    
    # Celery最適化設定
    celery_app.conf.update(
        # シリアライザー設定
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        
        # タイムゾーン設定
        timezone="Asia/Tokyo",
        enable_utc=True,
        
        # ワーカー最適化設定
        worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,  # 適切なワーカー同時実行数
        worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,  # パフォーマンス向上のためのプリフェッチ
        worker_max_tasks_per_child=settings.CELERY_WORKER_MAX_TASKS_PER_CHILD,  # メモリリーク対策
        
        # タスク最適化設定
        task_acks_late=True,  # タスク完了後にACK
        worker_disable_rate_limits=False,
        task_compression=settings.CELERY_TASK_COMPRESSION,  # タスクデータ圧縮
        task_ignore_result=False,  # 結果を保持
        
        # 結果バックエンド設定
        result_expires=settings.CELERY_RESULT_EXPIRES,  # 結果の有効期限（2時間）
        result_persistent=True,  # 結果の永続化
        
        # パフォーマンス最適化
        worker_send_task_events=True,  # イベント送信有効化
        task_send_sent_event=True,  # 送信イベント有効化
        worker_pool_restarts=True,  # ワーカープール再起動有効化
        
        # タスクルーティング最適化
        task_routes={
            'app.tasks.image_tasks.hello_world_task': {'queue': 'default'},
            'app.tasks.image_tasks.test_image_chunk_task': {'queue': 'image_queue'},
            'app.tasks.image_tasks.advanced_image_chunk_task': {'queue': 'image_queue'},
            'app.tasks.image_tasks.real_image_chunk_task': {'queue': 'image_queue'},
            # 翻訳タスクルーティング
            'app.tasks.translation_tasks.translate_category_simple': {'queue': 'translation_queue'},
            'app.tasks.translation_tasks.translate_category_with_fallback': {'queue': 'translation_queue'},
            'app.tasks.translation_tasks.translate_menu_parallel': {'queue': 'translation_queue'},
            # 詳細説明タスクルーティング
            'app.tasks.description_tasks.add_descriptions_to_category': {'queue': 'description_queue'},
            'app.tasks.description_tasks.add_descriptions_parallel_menu': {'queue': 'description_queue'},
            # OCRタスクルーティング
            'app.tasks.ocr_tasks.ocr_with_gemini': {'queue': 'ocr_queue'},
            'app.tasks.ocr_tasks.ocr_with_google_vision': {'queue': 'ocr_queue'},
            'app.tasks.ocr_tasks.ocr_parallel_multi_engine': {'queue': 'ocr_queue'},
            # パイプラインタスクルーティング
            'app.tasks.pipeline_tasks.full_pipeline_process': {'queue': 'pipeline_queue'},
            'app.tasks.pipeline_tasks.category_stage45_pipeline': {'queue': 'pipeline_queue'},
            'app.tasks.pipeline_tasks.multiple_images_pipeline': {'queue': 'pipeline_queue'},
            # カテゴライズ並列化タスクルーティング
            'app.tasks.categorization_tasks.categorize_text_chunk': {'queue': 'categorization_queue'},
            'app.tasks.categorization_tasks.categorize_menu_parallel': {'queue': 'categorization_queue'},
        },
        
        # キュー設定
        task_default_queue='default',
        task_default_exchange='default',
        task_default_exchange_type='direct',
        task_default_routing_key='default',
        
        # 接続最適化
        broker_connection_retry_on_startup=True,
        broker_connection_retry=True,
        broker_connection_max_retries=3,
        
        # ログ設定
        worker_log_level='INFO',
        worker_hijack_root_logger=False,
        
        # メモリ最適化
        worker_max_memory_per_child=200000,  # 200MB でワーカー再起動
        
        # 並列処理最適化設定
        task_always_eager=False,  # 非同期実行を強制
        task_eager_propagates=False,  # エラーの即座伝播を無効化
    )
    
    return celery_app

# Celeryアプリのインスタンス化
celery_app = create_celery_app()

# デバッグ用: 接続テスト関数
def test_celery_connection():
    """Celery接続をテストする関数"""
    try:
        # Brokerへの接続確認
        inspector = celery_app.control.inspect()
        ping_result = inspector.ping()
        if ping_result:
            active_workers = len(ping_result)
            return True, f"Celery connection successful - {active_workers} workers active"
        else:
            return False, "Celery connection failed - no workers responding"
    except Exception as e:
        return False, f"Celery connection failed: {str(e)}"

# デバッグ用: 基本情報取得
def get_celery_info():
    """Celery設定情報を取得"""
    return {
        "broker_url": celery_app.conf.broker_url,
        "result_backend": celery_app.conf.result_backend,
        "worker_concurrency": celery_app.conf.worker_concurrency,
        "worker_prefetch_multiplier": celery_app.conf.worker_prefetch_multiplier,
        "worker_max_tasks_per_child": celery_app.conf.worker_max_tasks_per_child,
        "task_serializer": celery_app.conf.task_serializer,
        "timezone": celery_app.conf.timezone,
        "task_compression": celery_app.conf.task_compression,
        "result_expires": celery_app.conf.result_expires
    }

# デバッグ用: ワーカー統計取得
def get_worker_stats():
    """ワーカーの詳細統計情報を取得"""
    try:
        inspector = celery_app.control.inspect()
        stats = inspector.stats()
        active = inspector.active()
        registered = inspector.registered()
        
        return {
            "stats": stats,
            "active_tasks": active,
            "registered_tasks": registered,
            "worker_count": len(stats) if stats else 0
        }
    except Exception as e:
        return {"error": f"Failed to get worker stats: {str(e)}"}
