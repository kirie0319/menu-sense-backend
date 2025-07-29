"""
Google Credential Manager - AWS Secrets Manager Integration
"""

import json
import tempfile
import os
from functools import lru_cache
from google.cloud import vision, translate_v2 as translate
from google.oauth2 import service_account
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
        self._credentials = None

    async def _get_google_credentials(self):
        """AWS Secrets ManagerからGoogle認証情報を取得"""
        if self._credentials is None:
            try:
                from app_2.infrastructure.integrations.aws.secrets_manager import SecretsManager
                
                secrets_manager = SecretsManager()
                secret_name = settings.aws.secret_name
                
                logger.info(f"Getting Google credentials from AWS Secrets Manager: {secret_name}")
                secret_data = await secrets_manager.get_secret(secret_name)
                
                # Google Service Account の認証情報を作成
                self._credentials = service_account.Credentials.from_service_account_info(secret_data)
                logger.info("✅ Google credentials loaded successfully from AWS Secrets Manager")
                
            except Exception as e:
                logger.error(f"❌ Failed to get Google credentials from AWS Secrets Manager: {e}")
                # フォールバック: Application Default Credentials を試行
                logger.info("Falling back to Application Default Credentials")
                self._credentials = None
                
        return self._credentials

    async def get_vision_client_async(self):
        """非同期でVision Clientを取得"""
        if self._vision_client is None:
            logger.info("Creating new Google Vision API client")
            credentials = await self._get_google_credentials()
            
            if credentials:
                self._vision_client = vision.ImageAnnotatorClient(credentials=credentials)
                logger.info("✅ Vision client created with AWS Secrets Manager credentials")
            else:
                # フォールバック
                self._vision_client = vision.ImageAnnotatorClient()
                logger.warning("⚠️ Vision client created with default credentials")
                
        return self._vision_client

    def get_vision_client(self):
        """同期でVision Clientを取得（後方互換性）"""
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
        self._credentials = None  # 認証情報もリセット
        # 次回のget_vision_client()呼び出し時に新しいクライアントが作成される

    async def get_translate_client_async(self):
        """非同期でTranslate Clientを取得"""
        if self._translate_client is None:
            logger.info("Creating new Google Translate API client")
            credentials = await self._get_google_credentials()
            
            if credentials:
                self._translate_client = translate.Client(credentials=credentials)
                logger.info("✅ Translate client created with AWS Secrets Manager credentials")
            else:
                # フォールバック
                self._translate_client = translate.Client()
                logger.warning("⚠️ Translate client created with default credentials")
                
        return self._translate_client

    def get_translate_client(self):
        """同期でTranslate Clientを取得（後方互換性）"""
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