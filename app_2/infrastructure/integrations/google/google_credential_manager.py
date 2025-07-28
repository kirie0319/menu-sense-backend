"""
Google Credential Manager - Minimal Implementation
"""

from functools import lru_cache
from google.cloud import vision, translate_v2 as translate
from googleapiclient.discovery import build

from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("google_credential")


class GoogleCredentialManager:
    def __init__(self):
        # 実際の設定構造に合わせて修正
        self.api_key = settings.ai.gemini_api_key  # Google Cloud APIキーはGemini APIキーを使用
        self.search_engine_id = settings.ai.google_search_engine_id
        self._vision_client = None
        self._translate_client = None
        self._search_service = None

    def get_vision_client(self):
        if self._vision_client is None:
            logger.info("Creating new Google Vision API client")
            self._vision_client = vision.ImageAnnotatorClient()
        return self._vision_client
    
    def reset_vision_client(self):
        """
        Vision APIクライアントを再作成
        
        GOAWAYエラーやセッションタイムアウト時に使用
        """
        logger.info("Resetting Google Vision API client due to connection issue")
        if self._vision_client:
            try:
                # 既存クライアントのクリーンアップ（可能であれば）
                self._vision_client.close()
            except Exception as e:
                logger.warning(f"Failed to close existing Vision client: {e}")
        
        self._vision_client = None
        # 次回のget_vision_client()呼び出し時に新しいクライアントが作成される

    def get_translate_client(self):
        if self._translate_client is None:
            self._translate_client = translate.Client()
        return self._translate_client

    def get_search_service(self):
        if self._search_service is None:
            self._search_service = build("customsearch", "v1", developerKey=self.api_key)
        return self._search_service

    def get_search_engine_id(self):
        return self.search_engine_id


@lru_cache(maxsize=1)
def get_google_credential_manager():
    return GoogleCredentialManager() 