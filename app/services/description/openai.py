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
from .base import BaseDescriptionService, DescriptionResult, DescriptionProvider

class OpenAIDescriptionService(BaseDescriptionService):
    """OpenAI APIを使用した詳細説明生成サービス"""
    
    def __init__(self):
        super().__init__()
        self.provider = DescriptionProvider.OPENAI
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
                print("🔧 OpenAI Description Service initialized successfully")
            else:
                print("⚠️ OPENAI_API_KEY not set")
                
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI Description Service: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        return self.client is not None and bool(settings.OPENAI_API_KEY)
    
    async def call_openai_with_retry(self, messages, max_retries=2):
        """指数バックオフ付きでOpenAI APIを呼び出すリトライ関数（チャンク処理用）"""
        if not self.is_available():
            raise Exception("OpenAI API is not available")
        
        for attempt in range(max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages
                )
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
    
    def create_description_prompt(self, category: str, chunk: list) -> str:
        """詳細説明生成用のプロンプトを作成"""
        example_descriptions = self.get_example_descriptions()
        examples_text = "\n".join([
            f"- \"{dish}\" → \"{desc}\""
            for dish, desc in list(example_descriptions.items())[:3]
        ])
        
        return f"""以下の翻訳済みメニュー項目に、外国人観光客向けの詳細説明を追加してください。

カテゴリ: {category}
項目数: {len(chunk)}

データ:
{json.dumps({category: chunk}, ensure_ascii=False, indent=2)}

要件:
1. 各料理に詳細な英語説明を追加
2. 調理法、使用食材、味の特徴を含める  
3. 外国人が理解しやすい表現を使用
4. 文化的背景も簡潔に説明
5. 観光客向けに魅力的で分かりやすい表現にする

必ずJSON形式で返答してください:
{{
  "final_menu": {{
    "{category}": [
      {{
        "japanese_name": "日本語名",
        "english_name": "英語名", 
        "description": "詳細な英語説明",
        "price": "価格（あれば）"
      }}
    ]
  }}
}}

例の説明:
{examples_text}

各説明は30-80語程度で、料理の特徴と魅力を伝えてください。"""
    
    def extract_json_from_response(self, content: str) -> dict:
        """レスポンスからJSONを抽出"""
        # JSONの開始と終了を探す
        json_start = content.find('{')
        json_end = content.rfind('}') + 1
        
        if json_start == -1 or json_end == -1:
            raise ValueError("No JSON found in response")
        
        json_str = content[json_start:json_end]
        return json.loads(json_str)
    
    async def process_chunk(
        self, 
        category: str, 
        chunk: list, 
        chunk_number: int, 
        total_chunks: int,
        session_id: Optional[str] = None
    ) -> list:
        """チャンクを処理して詳細説明を追加"""
        print(f"  📦 Processing chunk {chunk_number}/{total_chunks} ({len(chunk)} items)")
        
        # 進行状況通知（チャンク処理中）
        if session_id:
            from app.main import send_progress
            await send_progress(
                session_id, 4, "active", 
                f"🔄 Processing {category} (part {chunk_number}/{total_chunks})",
                {"chunk_progress": f"{chunk_number}/{total_chunks}"}
            )
        
        try:
            # プロンプト作成
            messages = [
                {
                    "role": "user",
                    "content": self.create_description_prompt(category, chunk)
                }
            ]
            
            # OpenAI API呼び出し
            response = await self.call_openai_with_retry(messages, max_retries=2)
            
            # レスポンスからJSONを抽出
            content = response.choices[0].message.content
            chunk_result = self.extract_json_from_response(content)
            
            if 'final_menu' in chunk_result and category in chunk_result['final_menu']:
                new_items = chunk_result['final_menu'][category]
                
                # 説明をクリーンアップ
                for item in new_items:
                    if item.get("description"):
                        item["description"] = self.clean_description_text(item["description"])
                
                print(f"    ✅ Successfully processed {len(new_items)} items in chunk")
                return new_items
            else:
                raise ValueError("Invalid response format")
                
        except Exception as chunk_error:
            print(f"⚠️ Chunk processing error: {chunk_error}")
            print(f"    🔄 Using fallback descriptions for chunk {chunk_number}")
            
            # エラー時はフォールバック説明を生成
            fallback_items = []
            for item in chunk:
                fallback_description = self.create_fallback_description(item)
                fallback_items.append({
                    "japanese_name": item.get("japanese_name", "N/A"),
                    "english_name": item.get("english_name", "N/A"),
                    "description": fallback_description,
                    "price": item.get("price", "")
                })
            
            return fallback_items
    
    async def add_descriptions(
        self, 
        translated_data: dict, 
        session_id: Optional[str] = None
    ) -> DescriptionResult:
        """
        翻訳されたメニューに詳細説明を追加（分割処理版）
        
        Args:
            translated_data: 翻訳されたメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            DescriptionResult: 詳細説明生成結果
        """
        print("📝 Starting detailed description generation with OpenAI (Chunked Processing)...")
        
        # サービス利用可能性チェック
        if not self.is_available():
            return DescriptionResult(
                success=False,
                description_method="openai",
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
        if not self.validate_translated_data(translated_data):
            return DescriptionResult(
                success=False,
                description_method="openai",
                error="Invalid translated data",
                metadata={
                    "error_type": "invalid_input",
                    "suggestions": [
                        "Provide valid translated menu data",
                        "Ensure at least one category has menu items",
                        "Check translated data structure format"
                    ]
                }
            )
        
        try:
            final_menu = {}
            total_items = sum(len(items) for items in translated_data.values())
            processed_items = 0
            
            print(f"🔢 Total items to process: {total_items}")
            
            # カテゴリごとに処理
            for category, items in translated_data.items():
                if not items:
                    final_menu[category] = []
                    continue
                    
                print(f"🔄 Processing category: {category} ({len(items)} items)")
                
                # 進行状況通知（カテゴリ開始）
                if session_id:
                    from app.main import send_progress
                    await send_progress(
                        session_id, 4, "active", 
                        f"🍽️ Adding descriptions for {category}...",
                        {"processing_category": category, "total_categories": len(translated_data)}
                    )
                
                # 大きなカテゴリは分割処理
                chunk_size = settings.PROCESSING_CHUNK_SIZE
                category_results = []
                
                for i in range(0, len(items), chunk_size):
                    chunk = items[i:i + chunk_size]
                    chunk_number = (i // chunk_size) + 1
                    total_chunks = (len(items) + chunk_size - 1) // chunk_size
                    
                    # チャンクを処理
                    new_items = await self.process_chunk(
                        category, chunk, chunk_number, total_chunks, session_id
                    )
                    
                    category_results.extend(new_items)
                    processed_items += len(chunk)
                    
                    # 進捗更新（リアルタイムストリーミング）
                    if session_id:
                        progress_percent = int((processed_items / total_items) * 100)
                        
                        await send_progress(
                            session_id, 4, "active", 
                            f"🍽️ {category}: チャンク{chunk_number}/{total_chunks}完了 ({len(new_items)}アイテム追加)",
                            {
                                "progress_percent": progress_percent,
                                "processing_category": category,
                                "partial_results": {category: category_results},  # 累積結果
                                "newly_processed_items": new_items,   # 新しく処理されたアイテム
                                "chunk_completed": f"{chunk_number}/{total_chunks}",
                                "chunk_size": len(chunk),
                                "items_in_category": len(category_results),
                                "streaming_update": True  # ストリーミング更新フラグ
                            }
                        )
                    
                    # レート制限対策として少し待機
                    await asyncio.sleep(settings.RATE_LIMIT_SLEEP)
                
                final_menu[category] = category_results
                
                # カテゴリ完了通知（ストリーミング強化）
                if session_id:
                    await send_progress(
                        session_id, 4, "active", 
                        f"✅ {category}カテゴリ完了！{len(category_results)}アイテムの詳細説明を追加しました",
                        {
                            "category_completed": category,
                            "category_items": len(category_results),
                            "partial_menu": final_menu,  # 全体の累積結果
                            "completed_category_items": category_results,  # 完了したカテゴリのアイテム詳細
                            "category_completion": True,  # カテゴリ完了フラグ
                            "remaining_categories": [cat for cat in translated_data.keys() if cat not in final_menu]
                        }
                    )
                
                print(f"✅ Category '{category}' completed: {len(category_results)} items")
            
            print(f"🎉 OpenAI Description Generation Complete: Added descriptions to {len(final_menu)} categories, {total_items} total items")
            
            # 処理統計を生成
            statistics = self.extract_processing_statistics(translated_data, final_menu)
            
            return DescriptionResult(
                success=True,
                final_menu=final_menu,
                description_method="openai",
                metadata={
                    "total_items": total_items,
                    "categories_processed": len(final_menu),
                    "provider": "OpenAI API",
                    "model": settings.OPENAI_MODEL,
                    "features": [
                        "chunked_processing",
                        "detailed_descriptions",
                        "cultural_context",
                        "tourist_friendly_language",
                        "real_time_progress"
                    ],
                    "processing_statistics": statistics
                }
            )
            
        except Exception as e:
            print(f"❌ OpenAI Description Generation Failed: {e}")
            
            # エラータイプの判定
            error_type = "unknown_error"
            suggestions = []
            
            if "rate limit" in str(e).lower():
                error_type = "rate_limit_exceeded"
                suggestions = [
                    "Wait before retrying",
                    "Check OpenAI API usage limits",
                    "Consider upgrading your OpenAI plan",
                    "Try processing smaller chunks"
                ]
            elif "timeout" in str(e).lower():
                error_type = "api_timeout"
                suggestions = [
                    "Retry the request",
                    "Check internet connectivity",
                    "Try with smaller menu chunks",
                    "Increase timeout settings"
                ]
            elif "json" in str(e).lower() or "parse" in str(e).lower():
                error_type = "response_parsing_error"
                suggestions = [
                    "OpenAI response format was unexpected",
                    "Try with different model settings",
                    "Check if the model supports the request format"
                ]
            else:
                suggestions = [
                    "Check OPENAI_API_KEY is valid",
                    "Verify model access permissions",
                    "Check OpenAI service status",
                    "Ensure input data is properly formatted"
                ]
            
            return DescriptionResult(
                success=False,
                description_method="openai",
                error=f"OpenAI description generation error: {str(e)}",
                metadata={
                    "error_type": error_type,
                    "original_error": str(e),
                    "suggestions": suggestions,
                    "provider": "OpenAI API",
                    "model": settings.OPENAI_MODEL,
                    "processed_items": processed_items if 'processed_items' in locals() else 0,
                    "total_items": sum(len(items) for items in translated_data.values())
                }
            )
