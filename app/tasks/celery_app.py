from celery import Celery
from app.core.config import settings
import os

def create_celery_app():
    """Celeryアプリケーションを作成・設定"""
    
    # Redis URLの設定
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    celery_app = Celery(
        "image_processor",
        broker=redis_url,
        backend=redis_url,
        include=["app.tasks.image_tasks"]
    )
    
    # Celery設定
    celery_app.conf.update(
        # シリアライザー設定
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        
        # タイムゾーン設定
        timezone="Asia/Tokyo",
        enable_utc=True,
        
        # ワーカー設定
        worker_concurrency=settings.IMAGE_CONCURRENT_CHUNK_LIMIT,
        worker_prefetch_multiplier=1,  # 一度に1つのタスクのみ処理
        
        # タスク設定
        task_acks_late=True,  # タスク完了後にACK
        worker_disable_rate_limits=False,
        task_compression='gzip',
        
        # 結果の有効期限
        result_expires=3600,  # 1時間
        
        # タスクルーティング
        task_routes={
            'app.tasks.image_tasks.*': {'queue': 'image_queue'}
        },
        
        # ログレベル
        worker_log_level='INFO'
    )
    
    return celery_app

# Celeryアプリのインスタンス化
celery_app = create_celery_app()

# デバッグ用: 接続テスト関数
def test_celery_connection():
    """Celery接続をテストする関数"""
    try:
        # Brokerへの接続確認
        celery_app.control.inspect().ping()
        return True, "Celery connection successful"
    except Exception as e:
        return False, f"Celery connection failed: {str(e)}"

# デバッグ用: 基本情報取得
def get_celery_info():
    """Celery設定情報を取得"""
    return {
        "broker_url": celery_app.conf.broker_url,
        "result_backend": celery_app.conf.result_backend,
        "worker_concurrency": celery_app.conf.worker_concurrency,
        "task_serializer": celery_app.conf.task_serializer,
        "timezone": celery_app.conf.timezone
    }
