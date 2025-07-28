"""
Celery Application - Menu Processor v2
Minimal Celery configuration for 5-task async pipeline processing
"""

from celery import Celery

from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("celery")

# ==========================================
# Celery Configuration
# ==========================================

def get_celery_config() -> dict:
    """
    8バッチ並列処理用のシンプルなCelery設定
    
    Returns:
        dict: Redis接続を確実にする簡素化された設定
    """
    return {
        # ✅ Broker settings - Redis接続確実化
        "broker_url": settings.celery.redis_url,
        "result_backend": settings.celery.redis_url,
        
        # 🔧 Redis transport 明示的指定
        "broker_transport": "redis",
        "result_backend_transport_options": {
            "retry_on_timeout": True,
            "socket_keepalive": True,
            "socket_keepalive_options": {
                "TCP_KEEPINTVL": 1,
                "TCP_KEEPCNT": 3,
                "TCP_KEEPIDLE": 1,
            },
        },
        
        # ✅ Serialization
        "task_serializer": "json",
        "accept_content": ["json"],
        "result_serializer": "json",
        
        # ✅ Timezone
        "timezone": "UTC",
        "enable_utc": True,
        
        # ⚡ 8バッチ並列処理最適化
        "worker_concurrency": 8,
        "worker_prefetch_multiplier": 4,
        
        # 🚀 Basic performance settings
        "task_compression": "gzip",
        "result_compression": "gzip",
        "worker_max_tasks_per_child": 100,
        
        # ⏱️ Timeouts
        "task_soft_time_limit": 1800,  # 30分
        "task_time_limit": 2100,       # 35分
        
        # 📊 Monitoring
        "worker_send_task_events": True,
        
        # 🔗 Connection retry
        "broker_connection_retry_on_startup": True,
        "broker_connection_retry": True,
        "broker_connection_max_retries": 10,
        
        # 🎯 Redis specific settings
        "visibility_timeout": 3600,  # 1時間
        "result_expires": 3600,      # 1時間
    }


# ==========================================
# Celery Application
# ==========================================

def create_celery_app() -> Celery:
    """
    Create configured Celery application
    
    Returns:
        Celery: Configured Celery instance
    """
    celery_app = Celery("menu_processor_v2")
    celery_app.config_from_object(get_celery_config())
    celery_app.autodiscover_tasks(["app_2.tasks"])
    
    logger.info("✅ Celery application configured for 5 core async tasks")
    return celery_app


# Global Celery instance
celery_app = create_celery_app()


# ==========================================
# Export
# ==========================================

__all__ = ["celery_app"] 