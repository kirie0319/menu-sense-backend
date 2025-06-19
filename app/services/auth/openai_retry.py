"""
OpenAI API リトライサービス
"""
import asyncio
from typing import Optional, List, Dict, Any
from .clients import get_api_clients_manager

class OpenAIRetryService:
    """OpenAI APIのリトライ機能を提供するサービス"""
    
    def __init__(self):
        self.clients_manager = get_api_clients_manager()
    
    async def call_openai_with_retry(
        self, 
        messages: List[Dict[str, Any]], 
        functions: Optional[List[Dict[str, Any]]] = None, 
        function_call: Optional[Dict[str, Any]] = None, 
        max_retries: int = 3
    ):
        """指数バックオフ付きでOpenAI APIを呼び出すリトライ関数"""
        
        if not self.clients_manager.is_openai_available():
            raise Exception("OpenAI API is not available")
        
        openai_client = self.clients_manager.get_openai_client()
        if not openai_client:
            raise Exception("OpenAI API client is not initialized")
        
        from app.core.config import settings
        
        for attempt in range(max_retries + 1):
            try:
                kwargs = {
                    "model": settings.OPENAI_MODEL,
                    "messages": messages
                }
                
                if functions:
                    kwargs["functions"] = functions
                if function_call:
                    kwargs["function_call"] = function_call
                
                response = await openai_client.chat.completions.create(**kwargs)
                return response
                
            except Exception as e:
                # OpenAIライブラリの例外を動的にインポート
                try:
                    import openai
                    
                    if isinstance(e, openai.RateLimitError):
                        if attempt == max_retries:
                            raise Exception(f"Rate limit exceeded after {max_retries + 1} attempts: {str(e)}")
                        
                        # 指数バックオフ
                        wait_time = settings.RETRY_BASE_DELAY ** attempt
                        print(f"⏳ Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(wait_time)
                        
                    elif isinstance(e, openai.APITimeoutError):
                        if attempt == max_retries:
                            raise Exception(f"API timeout after {max_retries + 1} attempts: {str(e)}")
                        
                        wait_time = settings.RETRY_BASE_DELAY ** attempt
                        print(f"⏳ API timeout, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(wait_time)
                        
                    elif isinstance(e, openai.APIConnectionError):
                        if attempt == max_retries:
                            raise Exception(f"API connection error after {max_retries + 1} attempts: {str(e)}")
                        
                        wait_time = settings.RETRY_BASE_DELAY ** attempt
                        print(f"⏳ Connection error, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                        await asyncio.sleep(wait_time)
                        
                    else:
                        # その他のOpenAIエラーは即座に失敗
                        raise Exception(f"OpenAI API error: {str(e)}")
                        
                except ImportError:
                    # openaiライブラリがインポートできない場合は一般的なエラーとして処理
                    raise Exception(f"OpenAI API error: {str(e)}")

# シングルトンインスタンスを取得する関数
_openai_retry_service: Optional[OpenAIRetryService] = None

def get_openai_retry_service() -> OpenAIRetryService:
    """OpenAIRetryServiceのシングルトンインスタンスを取得"""
    global _openai_retry_service
    if _openai_retry_service is None:
        _openai_retry_service = OpenAIRetryService()
    return _openai_retry_service

# 後方互換性のための関数
async def call_openai_with_retry(
    messages: List[Dict[str, Any]], 
    functions: Optional[List[Dict[str, Any]]] = None, 
    function_call: Optional[Dict[str, Any]] = None, 
    max_retries: int = 3
):
    """後方互換性のためのラッパー関数"""
    service = get_openai_retry_service()
    return await service.call_openai_with_retry(messages, functions, function_call, max_retries) 