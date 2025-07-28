"""
並列処理設定
基本処理設定、並列処理、Stage別並列化、パイプライン設定を管理
"""
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


class ProcessingSettings(BaseModel):
    """並列処理設定クラス"""
    
    # ===== 基本処理設定 =====
    processing_chunk_size: int = int(os.getenv("PROCESSING_CHUNK_SIZE", 3))  # Stage 4での分割処理サイズ
    rate_limit_sleep: float = float(os.getenv("RATE_LIMIT_SLEEP", 1.0))  # API呼び出し間隔
    retry_base_delay: int = 2  # 指数バックオフの基本遅延時間
    
    # ===== 並列処理設定（詳細説明生成用） =====
    concurrent_chunk_limit: int = int(os.getenv("CONCURRENT_CHUNK_LIMIT", 10))  # 同時実行チャンク数
    enable_category_parallel: bool = os.getenv("ENABLE_CATEGORY_PARALLEL", "true").lower() == "true"  # カテゴリレベル並列処理
    
    # ===== 画像生成並列処理設定 =====
    image_concurrent_chunk_limit: int = int(os.getenv("IMAGE_CONCURRENT_CHUNK_LIMIT", 3))  # 画像生成同時実行チャンク数
    enable_image_category_parallel: bool = os.getenv("ENABLE_IMAGE_CATEGORY_PARALLEL", "true").lower() == "true"  # 画像生成カテゴリレベル並列処理
    image_processing_chunk_size: int = int(os.getenv("IMAGE_PROCESSING_CHUNK_SIZE", 3))  # 画像生成チャンクサイズ
    
    # ===== Stage 1 OCR並列化設定 =====
    enable_parallel_ocr: bool = os.getenv("ENABLE_PARALLEL_OCR", "true").lower() == "true"  # 並列OCRの有効化
    parallel_ocr_timeout: int = int(os.getenv("PARALLEL_OCR_TIMEOUT", "90"))  # 並列OCRのタイムアウト時間（秒）
    
    # ===== Stage 2 カテゴライズ並列化設定 =====
    enable_parallel_categorization: bool = os.getenv("ENABLE_PARALLEL_CATEGORIZATION", "true").lower() == "true"  # 並列カテゴライズの有効化
    categorization_parallel_limit: int = int(os.getenv("CATEGORIZATION_PARALLEL_LIMIT", "4"))  # 並列カテゴライズの最大同時実行数
    
    # ===== Stage 3翻訳並列化設定 =====
    enable_parallel_translation: bool = os.getenv("ENABLE_PARALLEL_TRANSLATION", "true").lower() == "true"  # 並列翻訳の有効化
    parallel_translation_limit: int = int(os.getenv("PARALLEL_TRANSLATION_LIMIT", "6"))  # 並列翻訳の最大同時実行数
    parallel_category_threshold: int = int(os.getenv("PARALLEL_CATEGORY_THRESHOLD", "2"))  # 並列処理を使用する最小カテゴリ数
    translation_timeout_per_category: int = int(os.getenv("TRANSLATION_TIMEOUT_PER_CATEGORY", "30"))  # カテゴリあたりのタイムアウト時間（秒）
    
    # ===== Stage 4詳細説明並列化設定 =====
    enable_parallel_description: bool = os.getenv("ENABLE_PARALLEL_DESCRIPTION", "true").lower() == "true"  # 並列詳細説明の有効化
    
    # ===== 完全パイプライン並列化設定 (Stage 1-5全体) =====
    enable_full_pipeline_parallel: bool = os.getenv("ENABLE_FULL_PIPELINE_PARALLEL", "true").lower() == "true"  # 完全パイプライン並列化の有効化
    pipeline_parallel_mode: str = os.getenv("PIPELINE_PARALLEL_MODE", "smart")  # パイプライン並列化モード: smart, aggressive, conservative
    
    # ===== パイプライン並列処理制御 =====
    enable_early_stage5_start: bool = os.getenv("ENABLE_EARLY_STAGE5_START", "true").lower() == "true"  # Stage 3完了後にStage 5を開始
    enable_category_pipelining: bool = os.getenv("ENABLE_CATEGORY_PIPELINING", "true").lower() == "true"  # カテゴリレベルパイプライン処理
    enable_streaming_results: bool = os.getenv("ENABLE_STREAMING_RESULTS", "true").lower() == "true"  # 段階的結果ストリーミング
    
    # ===== パイプライン性能制御 =====
    max_pipeline_workers: int = int(os.getenv("MAX_PIPELINE_WORKERS", "12"))  # パイプライン並列ワーカー最大数
    pipeline_category_threshold: int = int(os.getenv("PIPELINE_CATEGORY_THRESHOLD", "3"))  # パイプライン処理を使用する最小カテゴリ数
    pipeline_item_threshold: int = int(os.getenv("PIPELINE_ITEM_THRESHOLD", "10"))  # パイプライン処理を使用する最小アイテム数
    pipeline_total_timeout: int = int(os.getenv("PIPELINE_TOTAL_TIMEOUT", "600"))  # パイプライン全体のタイムアウト（10分）
    
    class Config:
        env_file = ".env"
    
    def get_basic_processing_config(self) -> dict:
        """基本処理設定辞書を取得"""
        return {
            "chunk_size": self.processing_chunk_size,
            "rate_limit_sleep": self.rate_limit_sleep,
            "retry_base_delay": self.retry_base_delay
        }
    
    def get_parallel_config(self) -> dict:
        """並列処理設定辞書を取得"""
        return {
            "concurrent_chunk_limit": self.concurrent_chunk_limit,
            "enable_category_parallel": self.enable_category_parallel,
            "image_concurrent_chunk_limit": self.image_concurrent_chunk_limit,
            "enable_image_category_parallel": self.enable_image_category_parallel,
            "image_processing_chunk_size": self.image_processing_chunk_size
        }
    
    def get_stage_parallel_config(self) -> dict:
        """Stage別並列処理設定辞書を取得"""
        return {
            "ocr": {
                "enabled": self.enable_parallel_ocr,
                "timeout": self.parallel_ocr_timeout
            },
            "categorization": {
                "enabled": self.enable_parallel_categorization,
                "parallel_limit": self.categorization_parallel_limit
            },
            "translation": {
                "enabled": self.enable_parallel_translation,
                "parallel_limit": self.parallel_translation_limit,
                "category_threshold": self.parallel_category_threshold,
                "timeout_per_category": self.translation_timeout_per_category
            },
            "description": {
                "enabled": self.enable_parallel_description
            }
        }
    
    def get_pipeline_config(self) -> dict:
        """パイプライン設定辞書を取得"""
        return {
            "enabled": self.enable_full_pipeline_parallel,
            "mode": self.pipeline_parallel_mode,
            "early_stage5_start": self.enable_early_stage5_start,
            "category_pipelining": self.enable_category_pipelining,
            "streaming_results": self.enable_streaming_results,
            "max_workers": self.max_pipeline_workers,
            "category_threshold": self.pipeline_category_threshold,
            "item_threshold": self.pipeline_item_threshold,
            "total_timeout": self.pipeline_total_timeout
        }
    
    def is_parallel_enabled(self, stage: str) -> bool:
        """指定されたStageで並列処理が有効かチェック"""
        stage_map = {
            "ocr": self.enable_parallel_ocr,
            "categorization": self.enable_parallel_categorization,
            "translation": self.enable_parallel_translation,
            "description": self.enable_parallel_description,
            "pipeline": self.enable_full_pipeline_parallel
        }
        return stage_map.get(stage.lower(), False)
    
    def get_parallel_limits(self) -> dict:
        """各Stageの並列処理制限を取得"""
        return {
            "concurrent_chunk_limit": self.concurrent_chunk_limit,
            "image_concurrent_chunk_limit": self.image_concurrent_chunk_limit,
            "categorization_parallel_limit": self.categorization_parallel_limit,
            "translation_parallel_limit": self.parallel_translation_limit,
            "max_pipeline_workers": self.max_pipeline_workers
        }
    
    def validate_configuration(self) -> list:
        """並列処理設定の妥当性を検証"""
        issues = []
        
        # 基本設定の検証
        if self.processing_chunk_size <= 0:
            issues.append("PROCESSING_CHUNK_SIZE must be positive")
        
        if self.rate_limit_sleep < 0:
            issues.append("RATE_LIMIT_SLEEP must be non-negative")
        
        if self.retry_base_delay <= 0:
            issues.append("RETRY_BASE_DELAY must be positive")
        
        # 並列処理制限の検証
        if self.concurrent_chunk_limit <= 0:
            issues.append("CONCURRENT_CHUNK_LIMIT must be positive")
        
        if self.image_concurrent_chunk_limit <= 0:
            issues.append("IMAGE_CONCURRENT_CHUNK_LIMIT must be positive")
        
        if self.categorization_parallel_limit <= 0:
            issues.append("CATEGORIZATION_PARALLEL_LIMIT must be positive")
        
        if self.parallel_translation_limit <= 0:
            issues.append("PARALLEL_TRANSLATION_LIMIT must be positive")
        
        if self.max_pipeline_workers <= 0:
            issues.append("MAX_PIPELINE_WORKERS must be positive")
        
        # タイムアウト値の検証
        if self.parallel_ocr_timeout <= 0:
            issues.append("PARALLEL_OCR_TIMEOUT must be positive")
        
        if self.translation_timeout_per_category <= 0:
            issues.append("TRANSLATION_TIMEOUT_PER_CATEGORY must be positive")
        
        if self.pipeline_total_timeout <= 0:
            issues.append("PIPELINE_TOTAL_TIMEOUT must be positive")
        
        # しきい値の検証
        if self.parallel_category_threshold <= 0:
            issues.append("PARALLEL_CATEGORY_THRESHOLD must be positive")
        
        if self.pipeline_category_threshold <= 0:
            issues.append("PIPELINE_CATEGORY_THRESHOLD must be positive")
        
        if self.pipeline_item_threshold <= 0:
            issues.append("PIPELINE_ITEM_THRESHOLD must be positive")
        
        # パイプライン並列化モードの検証
        valid_modes = ["smart", "aggressive", "conservative"]
        if self.pipeline_parallel_mode not in valid_modes:
            issues.append(f"PIPELINE_PARALLEL_MODE must be one of {valid_modes}")
        
        return issues


# グローバルインスタンス
processing_settings = ProcessingSettings()


# 後方互換性のための関数（移行期間中のみ使用）
def get_processing_settings():
    """並列処理設定を取得（後方互換性用）"""
    return processing_settings 