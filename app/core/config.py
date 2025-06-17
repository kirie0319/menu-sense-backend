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
    
    # Google Cloud認証情報
    GOOGLE_CREDENTIALS_JSON: Optional[str] = os.getenv("GOOGLE_CREDENTIALS_JSON")
    
    # API設定
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY")
    
    # OpenAI設定
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_TIMEOUT: float = 120.0
    OPENAI_MAX_RETRIES: int = 3
    
    # Gemini設定
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    
    # Imagen設定
    IMAGEN_MODEL: str = "imagen-3.0-generate-002"
    IMAGEN_ASPECT_RATIO: str = "1:1"
    IMAGEN_NUMBER_OF_IMAGES: int = 1
    
    # 処理設定
    PROCESSING_CHUNK_SIZE: int = 3  # Stage 4での分割処理サイズ
    RATE_LIMIT_SLEEP: float = 1.0  # API呼び出し間隔
    RETRY_BASE_DELAY: int = 2  # 指数バックオフの基本遅延時間
    
    # SSE設定（リアルタイム進行状況）
    SSE_HEARTBEAT_INTERVAL: int = 5  # ハートビート間隔（秒）
    SSE_PING_INTERVAL: int = 15  # Ping間隔（秒）
    SSE_MAX_NO_PONG_TIME: int = 60  # Pongタイムアウト（秒）
    
    # 画像生成設定
    IMAGE_GENERATION_ENABLED: bool = True
    IMAGE_RATE_LIMIT_SLEEP: float = 2.0  # Imagen 3のレート制限対策
    
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
        "google_credentials": bool(settings.GOOGLE_CREDENTIALS_JSON)
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
        
    if not settings.GOOGLE_CREDENTIALS_JSON:
        issues.append("GOOGLE_CREDENTIALS_JSON not set")
    
    return issues