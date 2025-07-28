"""
Logger Utility - Menu Processor v2
Minimal and efficient logging system

最小限のログシステム:
- 統一フォーマット
- 環境別ログレベル
- 簡潔なAPI
"""

import logging
import sys
import os
from typing import Optional

# ==========================================
# Logger Configuration
# ==========================================

def setup_logger(
    name: Optional[str] = None,
    level: Optional[str] = None,
    format_style: str = "simple"
) -> logging.Logger:
    """
    ロガーを設定
    
    Args:
        name: ロガー名（デフォルト: "menu_processor_v2"）
        level: ログレベル（デフォルト: 環境変数 LOG_LEVEL または INFO）
        format_style: フォーマットスタイル（"simple" または "detailed"）
    
    Returns:
        logging.Logger: 設定済みロガー
    """
    
    # ロガー名
    logger_name = name or "menu_processor_v2"
    logger = logging.getLogger(logger_name)
    
    # 重複ハンドラー防止
    if logger.handlers:
        return logger
    
    # ログレベル設定
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    
    # フォーマット設定
    if format_style == "detailed":
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
        )
    else:  # simple
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 本番環境での設定
    if os.getenv("ENVIRONMENT", "development").lower() == "production":
        logger.setLevel(logging.WARNING)
    
    return logger


# ==========================================
# Default Logger Instance
# ==========================================

# デフォルトロガー
logger = setup_logger()


# ==========================================
# Convenience Functions
# ==========================================

def get_logger(name: str) -> logging.Logger:
    """名前付きロガーを取得"""
    return setup_logger(name)


def set_log_level(level: str):
    """ログレベルを動的に変更"""
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))


# ==========================================
# Export
# ==========================================

__all__ = [
    "setup_logger",
    "get_logger", 
    "set_log_level",
    "logger"
] 