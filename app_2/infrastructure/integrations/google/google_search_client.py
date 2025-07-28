"""
Google Search Client - Minimal Implementation
"""

from functools import lru_cache
from typing import List, Dict

from app_2.infrastructure.integrations.google.google_credential_manager import get_google_credential_manager


class GoogleSearchClient:
    def __init__(self):
        credential_manager = get_google_credential_manager()
        self.service = credential_manager.get_search_service()
        self.search_engine_id = credential_manager.get_search_engine_id()

    async def search_images(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        result = self.service.cse().list(
            q=f"{query} food dish",
            cx=self.search_engine_id,
            searchType='image',
            num=min(num_results, 10),
            safe='active'
        ).execute()
        
        images = []
        if 'items' in result:
            for item in result['items']:
                images.append({
                    'title': item.get('title', ''),
                    'link': item.get('link', ''),
                    'thumbnail': item.get('image', {}).get('thumbnailLink', '')
                })
        
        return images


@lru_cache(maxsize=1)
def get_google_search_client():
    return GoogleSearchClient() 