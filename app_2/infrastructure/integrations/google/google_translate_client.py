"""
Google Translate Client - AWS Secrets Manager Integration
"""

from functools import lru_cache
from typing import List

from app_2.infrastructure.integrations.google.google_credential_manager import get_google_credential_manager
from app_2.utils.logger import get_logger

logger = get_logger("google_translate_client")


class GoogleTranslateClient:
    def __init__(self):
        self.credential_manager = get_google_credential_manager()
        self.client = None

    async def _ensure_client(self):
        """認証済みクライアントを確保"""
        if self.client is None:
            self.client = await self.credential_manager.get_translate_client_async()
        return self.client

    async def translate(self, text: str, target_language: str = "ja") -> str:
        """
        テキストを翻訳
        
        Args:
            text: 翻訳するテキスト
            target_language: 翻訳先言語コード（デフォルト: 日本語）
            
        Returns:
            str: 翻訳されたテキスト
        """
        if not text or not text.strip():
            return text
        
        try:
            # 認証済みクライアントを確保
            client = await self._ensure_client()
            
            result = client.translate(text, target_language=target_language)
            logger.info(f"Translation successful: '{text[:30]}...' -> '{result['translatedText'][:30]}...'")
            return result['translatedText']
            
        except Exception as e:
            logger.error(f"Translation failed for text '{text[:30]}...': {e}")
            # エラー時は元のテキストを返す
            return text

    async def translate_list(self, texts: List[str], target_language: str = "ja") -> List[str]:
        """
        複数のテキストを翻訳
        
        Args:
            texts: 翻訳するテキストのリスト
            target_language: 翻訳先言語コード（デフォルト: 日本語）
            
        Returns:
            List[str]: 翻訳されたテキストのリスト
        """
        return [await self.translate(text, target_language) for text in texts]


@lru_cache(maxsize=1)
def get_google_translate_client():
    return GoogleTranslateClient() 