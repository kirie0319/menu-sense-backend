import json
import asyncio
from typing import Optional

try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None
    AsyncOpenAI = None

from app.core.config import settings
from .base import BaseTranslationService, TranslationResult, TranslationProvider

class OpenAITranslationService(BaseTranslationService):
    """OpenAI Function Callingを使用した翻訳サービス（フォールバック）"""
    
    def __init__(self):
        super().__init__()
        self.provider = TranslationProvider.OPENAI
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """OpenAI APIクライアントを初期化"""
        try:
            if not openai or not AsyncOpenAI:
                print("❌ openai package not installed. Install with: pip install openai")
                return
                
            if settings.OPENAI_API_KEY:
                self.client = AsyncOpenAI(
                    api_key=settings.OPENAI_API_KEY,
                    timeout=settings.OPENAI_TIMEOUT,
                    max_retries=settings.OPENAI_MAX_RETRIES
                )
                print("🔧 OpenAI Translation Service initialized successfully")
            else:
                print("⚠️ OPENAI_API_KEY not set")
                
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI Translation Service: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        return self.client is not None and bool(settings.OPENAI_API_KEY)
    
    def get_translate_function_schema(self) -> dict:
        """翻訳用のFunction Callingスキーマを取得"""
        return {
            "name": "translate_menu_categories",
            "description": "日本語でカテゴリ分類されたメニューを英語に翻訳する",
            "parameters": {
                "type": "object",
                "properties": {
                    "translated_categories": {
                        "type": "object",
                        "properties": {
                            "Appetizers": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "japanese_name": {"type": "string", "description": "元の日本語名"},
                                        "english_name": {"type": "string", "description": "英語名"},
                                        "price": {"type": "string", "description": "価格"}
                                    },
                                    "required": ["japanese_name", "english_name"]
                                }
                            },
                            "Main Dishes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "japanese_name": {"type": "string", "description": "元の日本語名"},
                                        "english_name": {"type": "string", "description": "英語名"},
                                        "price": {"type": "string", "description": "価格"}
                                    },
                                    "required": ["japanese_name", "english_name"]
                                }
                            },
                            "Drinks": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "japanese_name": {"type": "string", "description": "元の日本語名"},
                                        "english_name": {"type": "string", "description": "英語名"},
                                        "price": {"type": "string", "description": "価格"}
                                    },
                                    "required": ["japanese_name", "english_name"]
                                }
                            },
                            "Desserts": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "japanese_name": {"type": "string", "description": "元の日本語名"},
                                        "english_name": {"type": "string", "description": "英語名"},
                                        "price": {"type": "string", "description": "価格"}
                                    },
                                    "required": ["japanese_name", "english_name"]
                                }
                            }
                        },
                        "required": ["Appetizers", "Main Dishes", "Drinks", "Desserts"]
                    }
                },
                "required": ["translated_categories"]
            }
        }
    
    async def call_openai_with_retry(self, messages, functions=None, function_call=None, max_retries=3):
        """指数バックオフ付きでOpenAI APIを呼び出すリトライ関数"""
        if not self.is_available():
            raise Exception("OpenAI API is not available")
        
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
                
                response = await self.client.chat.completions.create(**kwargs)
                return response
                
            except openai.RateLimitError as e:
                if attempt == max_retries:
                    raise Exception(f"Rate limit exceeded after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = settings.RETRY_BASE_DELAY ** attempt
                print(f"⏳ Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                
            except openai.APITimeoutError as e:
                if attempt == max_retries:
                    raise Exception(f"API timeout after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = settings.RETRY_BASE_DELAY ** attempt
                print(f"⏳ API timeout, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                
            except openai.APIConnectionError as e:
                if attempt == max_retries:
                    raise Exception(f"API connection error after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = settings.RETRY_BASE_DELAY ** attempt
                print(f"⏳ Connection error, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                # その他のエラーは即座に失敗
                raise Exception(f"OpenAI API error: {str(e)}")
    
    async def translate_menu(
        self, 
        categorized_data: dict, 
        session_id: Optional[str] = None
    ) -> TranslationResult:
        """
        OpenAI Function Callingを使ってカテゴリ分類されたメニューを英語に翻訳
        
        Args:
            categorized_data: カテゴリ分類されたメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            TranslationResult: 翻訳結果
        """
        print("🔄 Starting menu translation with OpenAI Function Calling (Fallback Mode)...")
        
        # サービス利用可能性チェック
        if not self.is_available():
            return TranslationResult(
                success=False,
                translation_method="openai_fallback",
                error="OpenAI API is not available",
                metadata={
                    "error_type": "service_unavailable",
                    "suggestions": [
                        "Set OPENAI_API_KEY environment variable",
                        "Install openai package: pip install openai",
                        "Check OpenAI API access permissions",
                        "Verify internet connectivity"
                    ]
                }
            )
        
        # 入力データの妥当性チェック
        if not self.validate_categorized_data(categorized_data):
            return TranslationResult(
                success=False,
                translation_method="openai_fallback",
                error="Invalid categorized data",
                metadata={
                    "error_type": "invalid_input",
                    "suggestions": [
                        "Provide valid categorized menu data",
                        "Ensure at least one category has menu items",
                        "Check category structure format"
                    ]
                }
            )
        
        try:
            # 進行状況通知
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 3, "active", 
                    f"OpenAI翻訳開始: {len(categorized_data)} カテゴリ",
                    {"openai_translation_started": True, "total_categories": len(categorized_data)}
                )
            
            # Function Calling用のメッセージを作成
            messages = [
                {
                    "role": "user",
                    "content": f"""以下の日本語でカテゴリ分類されたメニューを英語に翻訳してください。

データ:
{json.dumps(categorized_data, ensure_ascii=False, indent=2)}

要件:
1. カテゴリ名を英語に翻訳（前菜→Appetizers, メイン→Main Dishes など）
2. 料理名を英語に翻訳
3. 価格はそのまま保持
4. 基本的な翻訳のみ（詳細説明は次の段階で追加）
5. 日本料理の専門用語は適切に英語化してください
"""
                }
            ]
            
            # OpenAI Function Callingを実行
            response = await self.call_openai_with_retry(
                messages=messages,
                functions=[self.get_translate_function_schema()],
                function_call={"name": "translate_menu_categories"}
            )
            
            # レスポンスを解析
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "translate_menu_categories":
                result = json.loads(function_call.arguments)
                
                translated_categories = result.get("translated_categories", {})
                total_items = sum(len(items) for items in translated_categories.values())
                
                print(f"✅ OpenAI Translation Complete: Translated {len(translated_categories)} categories with {total_items} items")
                
                # 最終進行状況通知
                if session_id:
                    from app.services.realtime import send_progress
                    await send_progress(
                        session_id, 3, "completed", 
                        f"OpenAI翻訳完了: {len(translated_categories)} カテゴリ",
                        {
                            "openai_translation_completed": True,
                            "translated_categories": translated_categories,
                            "total_categories": len(translated_categories)
                        }
                    )
                
                return TranslationResult(
                    success=True,
                    translated_categories=translated_categories,
                    translation_method="openai_fallback",
                    metadata={
                        "total_items": total_items,
                        "total_categories": len(translated_categories),
                        "provider": "OpenAI Function Calling",
                        "model": settings.OPENAI_MODEL,
                        "fallback_mode": True,
                        "features": [
                            "function_calling_structured_output",
                            "japanese_cuisine_terminology",
                            "batch_translation",
                            "category_mapping"
                        ]
                    }
                )
            else:
                raise ValueError("Function call not found in response")
                
        except Exception as e:
            print(f"❌ OpenAI Translation Failed: {e}")
            
            # エラータイプの判定
            error_type = "unknown_error"
            suggestions = []
            
            if "function call" in str(e).lower():
                error_type = "function_call_error"
                suggestions = [
                    "Check if the model supports function calling",
                    "Verify the function schema is correct",
                    "Try with a different model version"
                ]
            elif "rate limit" in str(e).lower():
                error_type = "rate_limit_exceeded"
                suggestions = [
                    "Wait before retrying",
                    "Check OpenAI API usage limits",
                    "Consider upgrading your OpenAI plan"
                ]
            elif "timeout" in str(e).lower():
                error_type = "api_timeout"
                suggestions = [
                    "Retry the request",
                    "Check internet connectivity",
                    "Try with smaller menu data"
                ]
            else:
                suggestions = [
                    "Check OPENAI_API_KEY is valid",
                    "Verify model access permissions",
                    "Check OpenAI service status"
                ]
            
            # 進行状況通知（エラー）
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 3, "error", 
                    f"❌ OpenAI翻訳フォールバック失敗: {str(e)}",
                    {
                        "fallback_failed": True,
                        "primary_service": "google_translate",
                        "fallback_service": "openai_function_calling",
                        "error_type": error_type,
                        "suggestions": suggestions
                    }
                )
            
            return TranslationResult(
                success=False,
                translation_method="openai_fallback",
                error=f"OpenAI translation fallback error: {str(e)}",
                metadata={
                    "error_type": error_type,
                    "original_error": str(e),
                    "suggestions": suggestions,
                    "provider": "OpenAI Function Calling",
                    "model": settings.OPENAI_MODEL,
                    "fallback_mode": True,
                    "fallback_failed": True
                }
            ) 