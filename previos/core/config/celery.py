"""
Celery/Redis設定
Redis接続、Celeryワーカー最適化、非同期処理、処理制限設定を管理
"""
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


class CelerySettings(BaseModel):
    """Celery/Redis設定クラス"""
    
    # ===== Redis接続設定 =====
    redis_url: str = os.getenv("REDIS_URL") # need to set in .env
    celery_broker_url: str = os.getenv("CELERY_BROKER_URL", None)  # 明示的に設定されていない場合はNone
    celery_result_backend: str = os.getenv("CELERY_RESULT_BACKEND", None)  # 明示的に設定されていない場合はNone
    
    # ===== Celeryワーカー最適化設定 =====
    celery_worker_concurrency: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", 8))  # ワーカーの同時実行数
    celery_worker_prefetch_multiplier: int = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", 2))  # プリフェッチ数
    celery_worker_max_tasks_per_child: int = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", 100))  # 子プロセスあたり最大タスク数
    celery_task_compression: str = os.getenv("CELERY_TASK_COMPRESSION", "gzip")  # タスク圧縮
    celery_result_expires: int = int(os.getenv("CELERY_RESULT_EXPIRES", 7200))  # 結果の有効期限（秒）
    
    # ===== 非同期画像生成設定 =====
    async_image_enabled: bool = os.getenv("ASYNC_IMAGE_ENABLED", "true").lower() == "true"
    max_image_workers: int = int(os.getenv("MAX_IMAGE_WORKERS", 8))
    image_job_timeout: int = int(os.getenv("IMAGE_JOB_TIMEOUT", 1800))  # 30分
    
    # ===== 画像生成処理制限設定 =====
    max_items_per_job: int = int(os.getenv("MAX_ITEMS_PER_JOB", 100))  # ジョブあたりの最大アイテム数（デフォルト: 100）
    unlimited_processing: bool = os.getenv("UNLIMITED_PROCESSING", "true").lower() == "true"  # 無制限処理モード
    scale_with_workers: bool = os.getenv("SCALE_WITH_WORKERS", "true").lower() == "true"  # ワーカー数に応じた自動スケーリング
    items_per_worker_ratio: int = int(os.getenv("ITEMS_PER_WORKER_RATIO", 20))  # ワーカーあたりのアイテム数倍率
    
    # ===== ワーカー均等活用設定 =====
    force_worker_utilization: bool = os.getenv("FORCE_WORKER_UTILIZATION", "true").lower() == "true"  # 強制的にワーカーを均等活用
    min_chunks_per_worker: float = float(os.getenv("MIN_CHUNKS_PER_WORKER", "0.8"))  # ワーカーあたりの最小チャンク数
    dynamic_chunk_sizing: bool = os.getenv("DYNAMIC_CHUNK_SIZING", "true").lower() == "true"  # 動的チャンクサイズ調整
    
    class Config:
        env_file = ".env"
    
    @property
    def effective_broker_url(self) -> str:
        """有効なブローカーURLを取得"""
        return self.celery_broker_url or self.redis_url
    
    @property
    def effective_result_backend(self) -> str:
        """有効な結果バックエンドURLを取得"""
        return self.celery_result_backend or self.redis_url
    
    def get_redis_config(self) -> dict:
        """Redis設定辞書を取得"""
        return {
            "redis_url": self.redis_url,
            "broker_url": self.effective_broker_url,
            "result_backend": self.effective_result_backend
        }
    
    def get_worker_config(self) -> dict:
        """Celeryワーカー設定辞書を取得"""
        return {
            "concurrency": self.celery_worker_concurrency,
            "prefetch_multiplier": self.celery_worker_prefetch_multiplier,
            "max_tasks_per_child": self.celery_worker_max_tasks_per_child,
            "task_compression": self.celery_task_compression,
            "result_expires": self.celery_result_expires
        }
    
    def get_image_processing_config(self) -> dict:
        """画像処理設定辞書を取得"""
        return {
            "async_enabled": self.async_image_enabled,
            "max_workers": self.max_image_workers,
            "job_timeout": self.image_job_timeout,
            "max_items_per_job": self.max_items_per_job,
            "unlimited_processing": self.unlimited_processing,
            "scale_with_workers": self.scale_with_workers,
            "items_per_worker_ratio": self.items_per_worker_ratio
        }
    
    def get_worker_utilization_config(self) -> dict:
        """ワーカー活用設定辞書を取得"""
        return {
            "force_utilization": self.force_worker_utilization,
            "min_chunks_per_worker": self.min_chunks_per_worker,
            "dynamic_chunk_sizing": self.dynamic_chunk_sizing
        }
    
    def calculate_max_items(self) -> int:
        """動的に最大アイテム数を計算"""
        if self.unlimited_processing:
            return float('inf')  # 無制限
        
        if self.scale_with_workers:
            # ワーカー数に応じたスケーリング
            return self.max_image_workers * self.items_per_worker_ratio
        else:
            # 固定制限
            return self.max_items_per_job
    
    def is_redis_available(self) -> bool:
        """Redis接続の可用性をチェック"""
        try:
            import redis
            client = redis.from_url(self.redis_url)
            client.ping()
            return True
        except Exception:
            return False
    
    def is_celery_configured(self) -> bool:
        """Celery設定の妥当性をチェック"""
        try:
            # 基本的な設定チェック
            if not self.effective_broker_url or not self.effective_result_backend:
                return False
            
            # Redis接続チェック
            if not self.is_redis_available():
                return False
            
            return True
        except Exception:
            return False
    
    def get_celery_app_config(self) -> dict:
        """Celeryアプリケーション設定を取得"""
        return {
            "broker_url": self.effective_broker_url,
            "result_backend": self.effective_result_backend,
            "task_serializer": "json",
            "accept_content": ["json"],
            "result_serializer": "json",
            "timezone": "UTC",
            "enable_utc": True,
            "task_compression": self.celery_task_compression,
            "result_expires": self.celery_result_expires,
            "worker_prefetch_multiplier": self.celery_worker_prefetch_multiplier,
            "worker_max_tasks_per_child": self.celery_worker_max_tasks_per_child,
            "worker_concurrency": self.celery_worker_concurrency,
            "task_routes": {
                "app.tasks.image_tasks.*": {"queue": "image_queue"},
                "app.tasks.ocr_tasks.*": {"queue": "ocr_queue"},
                "app.tasks.categorization_tasks.*": {"queue": "categorization_queue"},
                "app.tasks.translation_tasks.*": {"queue": "translation_queue"},
                "app.tasks.description_tasks.*": {"queue": "description_queue"},
                "app.tasks.menu_item_parallel_tasks.*": {"queue": "pipeline_queue"},
            },
            "task_default_queue": "default",
            "task_default_exchange": "default",
            "task_default_exchange_type": "direct",
            "task_default_routing_key": "default"
        }
    
    def validate_configuration(self) -> list:
        """Celery設定の妥当性を検証"""
        issues = []
        
        # Redis URL検証
        if not self.redis_url:
            issues.append("REDIS_URL is required")
        elif not self.redis_url.startswith(("redis://", "rediss://")):
            issues.append("REDIS_URL must start with redis:// or rediss://")
        
        # ワーカー設定検証
        if self.celery_worker_concurrency <= 0:
            issues.append("CELERY_WORKER_CONCURRENCY must be positive")
        
        if self.celery_worker_prefetch_multiplier <= 0:
            issues.append("CELERY_WORKER_PREFETCH_MULTIPLIER must be positive")
        
        if self.celery_worker_max_tasks_per_child <= 0:
            issues.append("CELERY_WORKER_MAX_TASKS_PER_CHILD must be positive")
        
        if self.celery_result_expires <= 0:
            issues.append("CELERY_RESULT_EXPIRES must be positive")
        
        # 画像処理設定検証
        if self.max_image_workers <= 0:
            issues.append("MAX_IMAGE_WORKERS must be positive")
        
        if self.image_job_timeout <= 0:
            issues.append("IMAGE_JOB_TIMEOUT must be positive")
        
        if self.max_items_per_job <= 0:
            issues.append("MAX_ITEMS_PER_JOB must be positive")
        
        if self.items_per_worker_ratio <= 0:
            issues.append("ITEMS_PER_WORKER_RATIO must be positive")
        
        # ワーカー活用設定検証
        if self.min_chunks_per_worker <= 0:
            issues.append("MIN_CHUNKS_PER_WORKER must be positive")
        
        # タスク圧縮設定検証
        valid_compression = ["gzip", "bzip2", "lzma", "zlib"]
        if self.celery_task_compression not in valid_compression:
            issues.append(f"CELERY_TASK_COMPRESSION must be one of {valid_compression}")
        
        # Redis接続テスト
        if not self.is_redis_available():
            issues.append("Redis connection failed - check REDIS_URL and Redis server status")
        
        return issues
    
    def get_performance_recommendations(self) -> list:
        """パフォーマンス改善の推奨事項を取得"""
        recommendations = []
        
        # ワーカー数の推奨
        if self.celery_worker_concurrency < 4:
            recommendations.append("Consider increasing CELERY_WORKER_CONCURRENCY for better parallel processing")
        
        # プリフェッチ数の推奨
        if self.celery_worker_prefetch_multiplier > 4:
            recommendations.append("Consider reducing CELERY_WORKER_PREFETCH_MULTIPLIER to avoid memory issues")
        
        # 画像ワーカー数の推奨
        if self.max_image_workers < self.celery_worker_concurrency:
            recommendations.append("Consider increasing MAX_IMAGE_WORKERS to match CELERY_WORKER_CONCURRENCY")
        
        # 無制限処理の推奨
        if not self.unlimited_processing and self.max_items_per_job < 50:
            recommendations.append("Consider increasing MAX_ITEMS_PER_JOB or enabling UNLIMITED_PROCESSING")
        
        # ワーカー活用の推奨
        if not self.force_worker_utilization:
            recommendations.append("Consider enabling FORCE_WORKER_UTILIZATION for better resource usage")
        
        return recommendations
    
    def get_status_summary(self) -> dict:
        """Celery設定の状態サマリーを取得"""
        return {
            "redis_available": self.is_redis_available(),
            "celery_configured": self.is_celery_configured(),
            "worker_count": self.celery_worker_concurrency,
            "image_workers": self.max_image_workers,
            "unlimited_processing": self.unlimited_processing,
            "force_utilization": self.force_worker_utilization,
            "max_items_calculated": self.calculate_max_items(),
            "configuration_issues": len(self.validate_configuration()),
            "performance_recommendations": len(self.get_performance_recommendations())
        }


# グローバルインスタンス
celery_settings = CelerySettings()


# 後方互換性のための関数（移行期間中のみ使用）
def get_celery_settings():
    """Celery設定を取得（後方互換性用）"""
    return celery_settings 