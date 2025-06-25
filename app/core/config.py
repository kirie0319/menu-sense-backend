# config.py
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

class Settings(BaseModel):
    # アプリケーション基本設定
    APP_TITLE: str = "Menu Processor MVP"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "Transform Japanese restaurant menus into detailed English descriptions for international visitors"
    
    # サーバー設定
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", 8000))
    
    # CORS設定
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "https://menu-sense-frontend.vercel.app",
        "https://speeches-plastic-excitement-reproduced.trycloudflare.com",
        "https://menu-sense-frontend-*.vercel.app",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    CORS_EXPOSE_HEADERS: List[str] = ["*"]
    
    # ファイル設定
    UPLOAD_DIR: str = "uploads"
    MAX_FILE_SIZE: int = 20 * 1024 * 1024  # 20MB
    ALLOWED_FILE_TYPES: List[str] = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    # S3設定（画像保存用）
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "menu-sense")
    S3_REGION: str = os.getenv("S3_REGION", "ap-northeast-1")
    S3_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    S3_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    S3_IMAGE_PREFIX: str = os.getenv("S3_IMAGE_PREFIX", "generated-images")
    USE_S3_STORAGE: bool = os.getenv("USE_S3_STORAGE", "true").lower() == "true"
    S3_PUBLIC_URL_TEMPLATE: str = os.getenv("S3_PUBLIC_URL_TEMPLATE", "https://{bucket}.s3.{region}.amazonaws.com/{key}")
    
    # Google Cloud認証情報
    GOOGLE_CREDENTIALS_JSON: Optional[str] = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    # AWS Secrets Manager設定
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_SECRET_NAME: str = os.getenv("AWS_SECRET_NAME", "prod/menu-sense/google-credentials")
    USE_AWS_SECRETS_MANAGER: bool = os.getenv("USE_AWS_SECRETS_MANAGER", "false").lower() == "true"
    
    # AWS認証情報（プロダクション環境用）
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_SESSION_TOKEN: Optional[str] = os.getenv("AWS_SESSION_TOKEN")  # IAM Role使用時に必要
    
    # API設定
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # OpenAI設定
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_TIMEOUT: float = float(os.getenv("OPENAI_TIMEOUT", 120.0))
    OPENAI_MAX_RETRIES: int = int(os.getenv("OPENAI_MAX_RETRIES", 3))
    
    # Gemini設定
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    
    # Imagen設定
    IMAGEN_MODEL: str = "imagen-3.0-generate-002"
    IMAGEN_ASPECT_RATIO: str = "1:1"
    IMAGEN_NUMBER_OF_IMAGES: int = 1
    
    # 処理設定
    PROCESSING_CHUNK_SIZE: int = int(os.getenv("PROCESSING_CHUNK_SIZE", 3))  # Stage 4での分割処理サイズ
    RATE_LIMIT_SLEEP: float = float(os.getenv("RATE_LIMIT_SLEEP", 1.0))  # API呼び出し間隔
    RETRY_BASE_DELAY: int = 2  # 指数バックオフの基本遅延時間
    
    # 並列処理設定（詳細説明生成用）
    CONCURRENT_CHUNK_LIMIT: int = int(os.getenv("CONCURRENT_CHUNK_LIMIT", 10))  # 同時実行チャンク数
    ENABLE_CATEGORY_PARALLEL: bool = os.getenv("ENABLE_CATEGORY_PARALLEL", "true").lower() == "true"  # カテゴリレベル並列処理
    
    # 画像生成並列処理設定
    IMAGE_CONCURRENT_CHUNK_LIMIT: int = int(os.getenv("IMAGE_CONCURRENT_CHUNK_LIMIT", 3))  # 画像生成同時実行チャンク数
    ENABLE_IMAGE_CATEGORY_PARALLEL: bool = os.getenv("ENABLE_IMAGE_CATEGORY_PARALLEL", "true").lower() == "true"  # 画像生成カテゴリレベル並列処理
    IMAGE_PROCESSING_CHUNK_SIZE: int = int(os.getenv("IMAGE_PROCESSING_CHUNK_SIZE", 3))  # 画像生成チャンクサイズ
    
    # SSE設定（リアルタイム進行状況）
    SSE_HEARTBEAT_INTERVAL: int = 5  # ハートビート間隔（秒）
    SSE_PING_INTERVAL: int = 15  # Ping間隔（秒）
    SSE_MAX_NO_PONG_TIME: int = 60  # Pongタイムアウト（秒）
    
    # 画像生成設定
    IMAGE_GENERATION_ENABLED: bool = True  # 一時的に無効化（高速化のため）
    IMAGE_RATE_LIMIT_SLEEP: float = float(os.getenv("IMAGE_RATE_LIMIT_SLEEP", 2.0))  # Imagen 3のレート制限対策
    
    # Celery/Redis設定
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = REDIS_URL
    CELERY_RESULT_BACKEND: str = REDIS_URL
    
    # Celeryワーカー最適化設定
    CELERY_WORKER_CONCURRENCY: int = int(os.getenv("CELERY_WORKER_CONCURRENCY", 8))  # ワーカーの同時実行数
    CELERY_WORKER_PREFETCH_MULTIPLIER: int = int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", 2))  # プリフェッチ数
    CELERY_WORKER_MAX_TASKS_PER_CHILD: int = int(os.getenv("CELERY_WORKER_MAX_TASKS_PER_CHILD", 100))  # 子プロセスあたり最大タスク数
    CELERY_TASK_COMPRESSION: str = os.getenv("CELERY_TASK_COMPRESSION", "gzip")  # タスク圧縮
    CELERY_RESULT_EXPIRES: int = int(os.getenv("CELERY_RESULT_EXPIRES", 7200))  # 結果の有効期限（秒）
    
    # 非同期画像生成設定
    ASYNC_IMAGE_ENABLED: bool = os.getenv("ASYNC_IMAGE_ENABLED", "true").lower() == "true"
    MAX_IMAGE_WORKERS: int = int(os.getenv("MAX_IMAGE_WORKERS", 8))
    IMAGE_JOB_TIMEOUT: int = int(os.getenv("IMAGE_JOB_TIMEOUT", 1800))  # 30分
    USE_REAL_IMAGE_GENERATION: bool = os.getenv("USE_REAL_IMAGE_GENERATION", "true").lower() == "true"
    
    # 画像生成処理制限設定
    MAX_ITEMS_PER_JOB: int = int(os.getenv("MAX_ITEMS_PER_JOB", 100))  # ジョブあたりの最大アイテム数（デフォルト: 100）
    UNLIMITED_PROCESSING: bool = os.getenv("UNLIMITED_PROCESSING", "true").lower() == "true"  # 無制限処理モード
    SCALE_WITH_WORKERS: bool = os.getenv("SCALE_WITH_WORKERS", "true").lower() == "true"  # ワーカー数に応じた自動スケーリング
    ITEMS_PER_WORKER_RATIO: int = int(os.getenv("ITEMS_PER_WORKER_RATIO", 20))  # ワーカーあたりのアイテム数倍率
    
    # ワーカー均等活用設定
    FORCE_WORKER_UTILIZATION: bool = os.getenv("FORCE_WORKER_UTILIZATION", "true").lower() == "true"  # 強制的にワーカーを均等活用
    MIN_CHUNKS_PER_WORKER: float = float(os.getenv("MIN_CHUNKS_PER_WORKER", "0.8"))  # ワーカーあたりの最小チャンク数
    DYNAMIC_CHUNK_SIZING: bool = os.getenv("DYNAMIC_CHUNK_SIZING", "true").lower() == "true"  # 動的チャンクサイズ調整
    
    # ===== Stage 3翻訳並列化設定 =====
    ENABLE_PARALLEL_TRANSLATION: bool = os.getenv("ENABLE_PARALLEL_TRANSLATION", "true").lower() == "true"  # 並列翻訳の有効化
    PARALLEL_TRANSLATION_LIMIT: int = int(os.getenv("PARALLEL_TRANSLATION_LIMIT", "6"))  # 並列翻訳の最大同時実行数
    PARALLEL_CATEGORY_THRESHOLD: int = int(os.getenv("PARALLEL_CATEGORY_THRESHOLD", "2"))  # 並列処理を使用する最小カテゴリ数
    TRANSLATION_TIMEOUT_PER_CATEGORY: int = int(os.getenv("TRANSLATION_TIMEOUT_PER_CATEGORY", "30"))  # カテゴリあたりのタイムアウト時間（秒）
    
    # 段階的テスト用フラグ
    FORCE_SEQUENTIAL_TRANSLATION: bool = os.getenv("FORCE_SEQUENTIAL_TRANSLATION", "false").lower() == "true"  # 逐次処理を強制（テスト用）
    TRANSLATION_FALLBACK_ENABLED: bool = os.getenv("TRANSLATION_FALLBACK_ENABLED", "true").lower() == "true"  # フォールバック機能の有効化
    LOG_TRANSLATION_PERFORMANCE: bool = os.getenv("LOG_TRANSLATION_PERFORMANCE", "true").lower() == "true"  # 翻訳パフォーマンスログの有効化
    
    # ===== Stage 4詳細説明並列化設定 =====
    ENABLE_PARALLEL_DESCRIPTION: bool = os.getenv("ENABLE_PARALLEL_DESCRIPTION", "true").lower() == "true"  # 並列詳細説明の有効化
    PARALLEL_DESCRIPTION_CATEGORY_THRESHOLD: int = int(os.getenv("PARALLEL_DESCRIPTION_CATEGORY_THRESHOLD", "2"))  # 並列処理を使用する最小カテゴリ数
    PARALLEL_DESCRIPTION_ITEM_THRESHOLD: int = int(os.getenv("PARALLEL_DESCRIPTION_ITEM_THRESHOLD", "5"))  # 並列処理を使用する最小アイテム数
    PARALLEL_DESCRIPTION_TIMEOUT: int = int(os.getenv("PARALLEL_DESCRIPTION_TIMEOUT", "300"))  # 並列詳細説明のタイムアウト時間（秒）
    
    # 詳細説明段階的テスト用フラグ
    FORCE_SEQUENTIAL_DESCRIPTION: bool = os.getenv("FORCE_SEQUENTIAL_DESCRIPTION", "false").lower() == "true"  # 逐次処理を強制（テスト用）
    DESCRIPTION_FALLBACK_ENABLED: bool = os.getenv("DESCRIPTION_FALLBACK_ENABLED", "true").lower() == "true"  # フォールバック機能の有効化
    LOG_DESCRIPTION_PERFORMANCE: bool = os.getenv("LOG_DESCRIPTION_PERFORMANCE", "true").lower() == "true"  # 詳細説明パフォーマンスログの有効化
    
    # ===== Stage 1 OCR並列化設定 =====
    ENABLE_PARALLEL_OCR: bool = os.getenv("ENABLE_PARALLEL_OCR", "true").lower() == "true"  # 並列OCRの有効化
    PARALLEL_OCR_TIMEOUT: int = int(os.getenv("PARALLEL_OCR_TIMEOUT", "90"))  # 並列OCRのタイムアウト時間（秒）
    
    # OCR段階的テスト用フラグ
    FORCE_SEQUENTIAL_OCR: bool = os.getenv("FORCE_SEQUENTIAL_OCR", "false").lower() == "true"  # 逐次処理を強制（テスト用）
    OCR_FALLBACK_ENABLED: bool = os.getenv("OCR_FALLBACK_ENABLED", "true").lower() == "true"  # フォールバック機能の有効化
    LOG_OCR_PERFORMANCE: bool = os.getenv("LOG_OCR_PERFORMANCE", "true").lower() == "true"  # OCRパフォーマンスログの有効化
    
    # ===== Stage 2 カテゴライズ並列化設定 =====
    ENABLE_PARALLEL_CATEGORIZATION: bool = os.getenv("ENABLE_PARALLEL_CATEGORIZATION", "true").lower() == "true"  # 並列カテゴライズの有効化
    PARALLEL_CATEGORIZATION_MODE: str = os.getenv("PARALLEL_CATEGORIZATION_MODE", "smart")  # カテゴライズ並列化モード: smart, hierarchical, chunk
    CATEGORIZATION_CHUNK_SIZE: int = int(os.getenv("CATEGORIZATION_CHUNK_SIZE", "3"))  # カテゴライズチャンクサイズ（最適化単位）
    CATEGORIZATION_PARALLEL_LIMIT: int = int(os.getenv("CATEGORIZATION_PARALLEL_LIMIT", "4"))  # 並列カテゴライズの最大同時実行数
    
    # カテゴライズ並列処理制御
    ENABLE_TEXT_CHUNKING: bool = os.getenv("ENABLE_TEXT_CHUNKING", "true").lower() == "true"  # テキスト分割並列処理
    ENABLE_HIERARCHICAL_CATEGORIZATION: bool = os.getenv("ENABLE_HIERARCHICAL_CATEGORIZATION", "true").lower() == "true"  # 階層的カテゴライズ
    TEXT_CHUNK_OVERLAP: int = int(os.getenv("TEXT_CHUNK_OVERLAP", "50"))  # テキストチャンク重複文字数
    CATEGORIZATION_TEXT_THRESHOLD: int = int(os.getenv("CATEGORIZATION_TEXT_THRESHOLD", "1000"))  # 並列処理を使用する最小テキスト長
    
    # カテゴライズ性能制御
    CATEGORIZATION_TIMEOUT: int = int(os.getenv("CATEGORIZATION_TIMEOUT", "120"))  # カテゴライズタイムアウト時間（秒）
    MAX_CATEGORIZATION_WORKERS: int = int(os.getenv("MAX_CATEGORIZATION_WORKERS", "4"))  # カテゴライズワーカー最大数
    
    # 段階的テスト・デバッグ用フラグ
    FORCE_SEQUENTIAL_CATEGORIZATION: bool = os.getenv("FORCE_SEQUENTIAL_CATEGORIZATION", "false").lower() == "true"  # 逐次処理を強制（テスト用）
    CATEGORIZATION_FALLBACK_ENABLED: bool = os.getenv("CATEGORIZATION_FALLBACK_ENABLED", "true").lower() == "true"  # フォールバック機能の有効化
    LOG_CATEGORIZATION_PERFORMANCE: bool = os.getenv("LOG_CATEGORIZATION_PERFORMANCE", "true").lower() == "true"  # カテゴライズパフォーマンスログ
    
    # ===== 完全パイプライン並列化設定 (Stage 1-5全体) =====
    ENABLE_FULL_PIPELINE_PARALLEL: bool = os.getenv("ENABLE_FULL_PIPELINE_PARALLEL", "true").lower() == "true"  # 完全パイプライン並列化の有効化
    PIPELINE_PARALLEL_MODE: str = os.getenv("PIPELINE_PARALLEL_MODE", "smart")  # パイプライン並列化モード: smart, aggressive, conservative
    
    # パイプライン並列処理制御
    ENABLE_EARLY_STAGE5_START: bool = os.getenv("ENABLE_EARLY_STAGE5_START", "true").lower() == "true"  # Stage 3完了後にStage 5を開始
    ENABLE_CATEGORY_PIPELINING: bool = os.getenv("ENABLE_CATEGORY_PIPELINING", "true").lower() == "true"  # カテゴリレベルパイプライン処理
    ENABLE_STREAMING_RESULTS: bool = os.getenv("ENABLE_STREAMING_RESULTS", "true").lower() == "true"  # 段階的結果ストリーミング
    ENABLE_MULTIPLE_IMAGE_PIPELINE: bool = os.getenv("ENABLE_MULTIPLE_IMAGE_PIPELINE", "false").lower() == "true"  # 複数画像並列パイプライン
    
    # パイプライン性能制御
    MAX_PIPELINE_WORKERS: int = int(os.getenv("MAX_PIPELINE_WORKERS", "12"))  # パイプライン並列ワーカー最大数
    PIPELINE_CATEGORY_THRESHOLD: int = int(os.getenv("PIPELINE_CATEGORY_THRESHOLD", "3"))  # パイプライン処理を使用する最小カテゴリ数
    PIPELINE_ITEM_THRESHOLD: int = int(os.getenv("PIPELINE_ITEM_THRESHOLD", "10"))  # パイプライン処理を使用する最小アイテム数
    PIPELINE_TOTAL_TIMEOUT: int = int(os.getenv("PIPELINE_TOTAL_TIMEOUT", "600"))  # パイプライン全体のタイムアウト（10分）
    
    # Stage間オーバーラップ設定
    STAGE3_TO_STAGE5_OVERLAP: bool = os.getenv("STAGE3_TO_STAGE5_OVERLAP", "true").lower() == "true"  # Stage 3→5 重複実行
    CATEGORY_LEVEL_OVERLAP: bool = os.getenv("CATEGORY_LEVEL_OVERLAP", "true").lower() == "true"  # カテゴリレベル重複実行
    MIN_CATEGORIES_FOR_OVERLAP: int = int(os.getenv("MIN_CATEGORIES_FOR_OVERLAP", "2"))  # 重複実行の最小カテゴリ数
    
    # パイプライン最適化フラグ
    ADAPTIVE_PIPELINE_SIZING: bool = os.getenv("ADAPTIVE_PIPELINE_SIZING", "true").lower() == "true"  # データサイズに応じた適応的パイプライン調整
    SMART_RESOURCE_ALLOCATION: bool = os.getenv("SMART_RESOURCE_ALLOCATION", "true").lower() == "true"  # スマートリソース配分
    PIPELINE_LOAD_BALANCING: bool = os.getenv("PIPELINE_LOAD_BALANCING", "true").lower() == "true"  # パイプライン負荷分散
    
    # 段階的テスト・デバッグ用フラグ
    FORCE_SEQUENTIAL_PIPELINE: bool = os.getenv("FORCE_SEQUENTIAL_PIPELINE", "false").lower() == "true"  # 完全逐次処理を強制（テスト用）
    LOG_PIPELINE_PERFORMANCE: bool = os.getenv("LOG_PIPELINE_PERFORMANCE", "true").lower() == "true"  # パイプラインパフォーマンスログ
    ENABLE_PIPELINE_MONITORING: bool = os.getenv("ENABLE_PIPELINE_MONITORING", "true").lower() == "true"  # パイプライン監視機能
    
    class Config:
        env_file = ".env"

# 設定のインスタンス化
settings = Settings()

# アップロードディレクトリの作成
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# API可用性チェック関数
def check_api_availability():
    """各APIの利用可能性をチェック"""
    availability = {
        "openai": bool(settings.OPENAI_API_KEY),
        "gemini": bool(settings.GEMINI_API_KEY),
        "google_credentials": bool(settings.GOOGLE_CREDENTIALS_JSON) if not settings.USE_AWS_SECRETS_MANAGER else True,
        "aws_secrets_manager": settings.USE_AWS_SECRETS_MANAGER
    }
    return availability

# 設定値の検証
def validate_settings():
    """設定値の妥当性を検証"""
    issues = []
    
    if not settings.OPENAI_API_KEY:
        issues.append("OPENAI_API_KEY not set")
    
    if not settings.GEMINI_API_KEY:
        issues.append("GEMINI_API_KEY not set")
        
    # Google認証情報の検証
    if settings.USE_AWS_SECRETS_MANAGER:
        if not settings.AWS_SECRET_NAME:
            issues.append("AWS_SECRET_NAME not set (required when USE_AWS_SECRETS_MANAGER=true)")
        if not settings.AWS_REGION:
            issues.append("AWS_REGION not set (required when USE_AWS_SECRETS_MANAGER=true)")
    else:
        if not settings.GOOGLE_CREDENTIALS_JSON:
            issues.append("GOOGLE_CREDENTIALS_JSON not set (required when USE_AWS_SECRETS_MANAGER=false)")
    
    return issues