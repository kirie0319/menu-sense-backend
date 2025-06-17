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
from .base import BaseCategoryService, CategoryResult

class OpenAICategoryService(BaseCategoryService):
    """OpenAI Function Callingを使用したカテゴリ分類サービス"""
    
    def __init__(self):
        super().__init__()
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
                print("🔧 OpenAI Category Service initialized successfully")
            else:
                print("⚠️ OPENAI_API_KEY not set")
                
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI Category Service: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        return self.client is not None and bool(settings.OPENAI_API_KEY)
    
    def get_categorize_function_schema(self) -> dict:
        """カテゴリ分類用のFunction Callingスキーマを取得"""
        return {
            "name": "categorize_menu_items",
            "description": "日本語のメニューテキストを分析してカテゴリ別に分類する",
            "parameters": {
                "type": "object",
                "properties": {
                    "categories": {
                        "type": "object",
                        "properties": {
                            "前菜": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "料理名"},
                                        "price": {"type": "string", "description": "価格"},
                                        "description": {"type": "string", "description": "簡潔な説明"}
                                    },
                                    "required": ["name"]
                                }
                            },
                            "メイン": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "料理名"},
                                        "price": {"type": "string", "description": "価格"},
                                        "description": {"type": "string", "description": "簡潔な説明"}
                                    },
                                    "required": ["name"]
                                }
                            },
                            "ドリンク": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "料理名"},
                                        "price": {"type": "string", "description": "価格"},
                                        "description": {"type": "string", "description": "簡潔な説明"}
                                    },
                                    "required": ["name"]
                                }
                            },
                            "デザート": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "料理名"},
                                        "price": {"type": "string", "description": "価格"},
                                        "description": {"type": "string", "description": "簡潔な説明"}
                                    },
                                    "required": ["name"]
                                }
                            }
                        },
                        "required": ["前菜", "メイン", "ドリンク", "デザート"]
                    },
                    "uncategorized": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "分類できなかった項目"
                    }
                },
                "required": ["categories", "uncategorized"]
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
    
    async def categorize_menu(
        self, 
        extracted_text: str, 
        session_id: Optional[str] = None
    ) -> CategoryResult:
        """
        OpenAI Function Callingを使ってメニューテキストをカテゴリ分類
        
        Args:
            extracted_text: OCRで抽出されたメニューテキスト
            session_id: セッションID（進行状況通知用）
            
        Returns:
            CategoryResult: 分類結果
        """
        print("📋 Starting Japanese menu categorization with OpenAI Function Calling...")
        
        # サービス利用可能性チェック
        if not self.is_available():
            return CategoryResult(
                success=False,
                error="OpenAI API is not available",
                metadata={
                    "error_type": "service_unavailable",
                    "suggestions": [
                        "Set OPENAI_API_KEY environment variable",
                        "Install openai package: pip install openai",
                        "Check internet connectivity"
                    ]
                }
            )
        
        # 入力テキストの妥当性チェック
        if not self.validate_text_input(extracted_text):
            return CategoryResult(
                success=False,
                error="Invalid input text",
                metadata={
                    "error_type": "invalid_input",
                    "text_length": len(extracted_text),
                    "suggestions": [
                        "Provide menu text with at least 5 characters",
                        "Ensure text is not empty",
                        "Check OCR extraction results"
                    ]
                }
            )
        
        try:
            # Function Calling用のメッセージを作成
            messages = [
                {
                    "role": "user",
                    "content": f"""以下の日本語レストランメニューテキストを分析し、料理をカテゴリ別に整理してください。

テキスト:
{extracted_text}

要件:
1. 料理名を抽出
2. 適切なカテゴリに分類（前菜、メイン、ドリンク、デザートなど）
3. 価格があれば抽出
4. 日本語のまま処理（翻訳はしない）
5. 料理名が明確でない場合は、uncategorizedに含めてください
"""
                }
            ]
            
            # OpenAI Function Callingを実行
            response = await self.call_openai_with_retry(
                messages=messages,
                functions=[self.get_categorize_function_schema()],
                function_call={"name": "categorize_menu_items"}
            )
            
            # レスポンスを解析
            function_call = response.choices[0].message.function_call
            if function_call and function_call.name == "categorize_menu_items":
                result = json.loads(function_call.arguments)
                
                categories = result.get("categories", {})
                uncategorized = result.get("uncategorized", [])
                
                # 成功ログ
                total_items = sum(len(items) for items in categories.values())
                print(f"✅ OpenAI Categorization Complete: {total_items} items in {len(categories)} categories")
                
                return CategoryResult(
                    success=True,
                    categories=categories,
                    uncategorized=uncategorized,
                    metadata={
                        "total_items": total_items,
                        "total_categories": len(categories),
                        "uncategorized_count": len(uncategorized),
                        "categorization_method": "openai_function_calling",
                        "model": settings.OPENAI_MODEL,
                        "text_length": len(extracted_text)
                    }
                )
            else:
                raise ValueError("Function call not found in response")
                
        except Exception as e:
            print(f"❌ OpenAI Categorization Failed: {e}")
            
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
                    "Try with shorter text input"
                ]
            else:
                suggestions = [
                    "Check OPENAI_API_KEY is valid",
                    "Verify model access permissions",
                    "Check OpenAI service status"
                ]
            
            return CategoryResult(
                success=False,
                error=f"OpenAI categorization error: {str(e)}",
                metadata={
                    "error_type": error_type,
                    "original_error": str(e),
                    "suggestions": suggestions,
                    "categorization_method": "openai_function_calling",
                    "model": settings.OPENAI_MODEL,
                    "text_length": len(extracted_text)
                }
            )
