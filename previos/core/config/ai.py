"""
AI/API設定
OpenAI、Gemini、Imagen、Google Cloud関連の設定を管理
"""
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


class AISettings(BaseModel):
    """AI/API設定クラス"""
    
    # ===== API認証キー =====
    openai_api_key: Optional[str] = os.getenv("OPENAI_API_KEY") # need to set in .env
    gemini_api_key: Optional[str] = os.getenv("GEMINI_API_KEY") # need to set in .env
    
    # ===== OpenAI設定 =====
    openai_model: str = "gpt-4.1-mini"
    openai_timeout: float = float(os.getenv("OPENAI_TIMEOUT", 120.0))
    openai_max_retries: int = int(os.getenv("OPENAI_MAX_RETRIES", 3))
    
    # ===== Gemini設定 =====
    gemini_model: str = "gemini-2.0-flash-exp"
    
    # ===== Imagen設定 =====
    imagen_model: str = "imagen-3.0-generate-002"
    imagen_aspect_ratio: str = "1:1"
    imagen_number_of_images: int = 1
    
    # ===== 画像生成設定 =====
    image_generation_enabled: bool = True  # 一時的に無効化（高速化のため）
    image_rate_limit_sleep: float = float(os.getenv("IMAGE_RATE_LIMIT_SLEEP", 2.0))  # Imagen 3のレート制限対策
    use_real_image_generation: bool = os.getenv("USE_REAL_IMAGE_GENERATION", "true").lower() == "true"
    
    class Config:
        env_file = ".env"
    
    def is_openai_available(self) -> bool:
        """OpenAI APIが利用可能かチェック"""
        return bool(self.openai_api_key)
    
    def is_gemini_available(self) -> bool:
        """Gemini APIが利用可能かチェック"""
        return bool(self.gemini_api_key)
    
    def is_imagen_available(self) -> bool:
        """Imagen APIが利用可能かチェック"""
        return self.is_gemini_available() and self.image_generation_enabled
    
    def get_openai_config(self) -> dict:
        """OpenAI設定辞書を取得"""
        return {
            "api_key": self.openai_api_key,
            "model": self.openai_model,
            "timeout": self.openai_timeout,
            "max_retries": self.openai_max_retries
        }
    
    def get_gemini_config(self) -> dict:
        """Gemini設定辞書を取得"""
        return {
            "api_key": self.gemini_api_key,
            "model": self.gemini_model
        }
    
    def get_imagen_config(self) -> dict:
        """Imagen設定辞書を取得"""
        return {
            "model": self.imagen_model,
            "aspect_ratio": self.imagen_aspect_ratio,
            "number_of_images": self.imagen_number_of_images,
            "enabled": self.image_generation_enabled,
            "rate_limit_sleep": self.image_rate_limit_sleep,
            "use_real_generation": self.use_real_image_generation
        }
    
    def get_availability_status(self) -> dict:
        """すべてのAI APIの可用性ステータスを取得"""
        return {
            "openai": self.is_openai_available(),
            "gemini": self.is_gemini_available(),
            "imagen": self.is_imagen_available()
        }
    
    def validate_configuration(self) -> list:
        """AI設定の妥当性を検証"""
        issues = []
        
        if not self.openai_api_key:
            issues.append("OPENAI_API_KEY not set")
        
        if not self.gemini_api_key:
            issues.append("GEMINI_API_KEY not set")
        
        # タイムアウト値の妥当性チェック
        if self.openai_timeout <= 0:
            issues.append("OPENAI_TIMEOUT must be positive")
        
        if self.openai_max_retries < 0:
            issues.append("OPENAI_MAX_RETRIES must be non-negative")
        
        if self.image_rate_limit_sleep < 0:
            issues.append("IMAGE_RATE_LIMIT_SLEEP must be non-negative")
        
        return issues


# グローバルインスタンス
ai_settings = AISettings()


# 後方互換性のための関数（移行期間中のみ使用）
def get_ai_settings():
    """AI設定を取得（後方互換性用）"""
    return ai_settings 