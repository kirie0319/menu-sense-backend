"""
Google Translate Client - Minimal Implementation
"""

from functools import lru_cache
from typing import List

from app_2.infrastructure.integrations.google.google_credential_manager import get_google_credential_manager


class GoogleTranslateClient:
    def __init__(self):
        credential_manager = get_google_credential_manager()
        self.client = credential_manager.get_translate_client()

    async def translate(self, text: str, target_language: str = "ja") -> str:
        if not text or not text.strip():
            return text
        
        result = self.client.translate(text, target_language=target_language)
        return result['translatedText']

    async def translate_list(self, texts: List[str], target_language: str = "ja") -> List[str]:
        return [await self.translate(text, target_language) for text in texts]


@lru_cache(maxsize=1)
def get_google_translate_client():
    return GoogleTranslateClient() 