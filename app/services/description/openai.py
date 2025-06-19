import json
import asyncio
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

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
        # 並列処理用セマフォ（同時実行数を制限）
        self.semaphore = asyncio.Semaphore(settings.CONCURRENT_CHUNK_LIMIT)
    
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
            from app.services.realtime import send_progress
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
    
    async def process_chunk_with_semaphore(
        self, 
        category: str, 
        chunk: list, 
        chunk_number: int, 
        total_chunks: int,
        session_id: Optional[str] = None
    ) -> tuple:
        """セマフォを使用してチャンクを並列処理"""
        async with self.semaphore:
            print(f"  🚀 Starting parallel chunk {chunk_number}/{total_chunks} ({len(chunk)} items)")
            
            # 進行状況通知（チャンク開始）
            if session_id:
                from app.services.realtime import send_progress
                await send_progress(
                    session_id, 4, "active", 
                    f"🔄 Starting parallel processing for {category} (chunk {chunk_number}/{total_chunks})",
                    {
                        "chunk_progress": f"{chunk_number}/{total_chunks}",
                        "parallel_processing": True,
                        "chunk_started": chunk_number
                    }
                )
            
            try:
                # チャンク処理を実行
                result = await self.process_chunk(category, chunk, chunk_number, total_chunks, session_id)
                
                print(f"  ✅ Completed parallel chunk {chunk_number}/{total_chunks}")
                return (chunk_number, result, None)  # (chunk_number, result, error)
                
            except Exception as e:
                print(f"  ❌ Error in parallel chunk {chunk_number}/{total_chunks}: {e}")
                return (chunk_number, None, str(e))

    async def process_category_parallel(
        self,
        category: str,
        items: list,
        session_id: Optional[str] = None
    ) -> list:
        """カテゴリ内のアイテムを並列チャンク処理"""
        if not items:
            return []
            
        print(f"🔄 Processing category: {category} ({len(items)} items) - PARALLEL MODE")
        
        # 進行状況通知（カテゴリ開始）
        if session_id:
            from app.services.realtime import send_progress
            await send_progress(
                session_id, 4, "active", 
                f"🍽️ Adding descriptions for {category} (parallel processing)...",
                {
                    "processing_category": category,
                    "parallel_mode": True,
                    "total_items": len(items)
                }
            )
        
        # チャンクに分割
        chunk_size = settings.PROCESSING_CHUNK_SIZE
        chunks = []
        
        for i in range(0, len(items), chunk_size):
            chunk = items[i:i + chunk_size]
            chunk_number = (i // chunk_size) + 1
            total_chunks = (len(items) + chunk_size - 1) // chunk_size
            chunks.append((chunk, chunk_number, total_chunks))
        
        print(f"  📦 Created {len(chunks)} chunks for parallel processing")
        
        # 全チャンクを並列で処理
        tasks = []
        for chunk, chunk_number, total_chunks in chunks:
            task = self.process_chunk_with_semaphore(
                category, chunk, chunk_number, total_chunks, session_id
            )
            tasks.append(task)
        
        # 並列実行開始
        print(f"  🚀 Starting {len(tasks)} parallel chunk tasks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を処理
        category_results = []
        successful_chunks = 0
        failed_chunks = 0
        
        # チャンク番号でソート（元の順序を維持）
        sorted_results = []
        for result in results:
            if isinstance(result, tuple):
                sorted_results.append(result)
            else:
                # 例外が発生した場合
                print(f"  ⚠️ Exception in parallel processing: {result}")
                failed_chunks += 1
        
        sorted_results.sort(key=lambda x: x[0])  # chunk_numberでソート
        
        for chunk_number, chunk_result, error in sorted_results:
            if error:
                print(f"  ⚠️ Chunk {chunk_number} failed: {error}")
                failed_chunks += 1
                # フォールバック処理（対応するチャンクのデータが必要）
                # この場合は空のリストを追加（エラーハンドリングの改善が必要）
            elif chunk_result:
                category_results.extend(chunk_result)
                successful_chunks += 1
                
                # チャンク完了の進捗送信
                if session_id:
                    await send_progress(
                        session_id, 4, "active", 
                        f"🍽️ {category}: Chunk {chunk_number} completed ({len(chunk_result)} items)",
                        {
                            "processing_category": category,
                            "chunk_completed": chunk_number,
                            "chunk_result": chunk_result,
                            "parallel_processing": True,
                            "successful_chunks": successful_chunks,
                            "failed_chunks": failed_chunks
                        }
                    )
        
        print(f"  ✅ Parallel processing complete: {successful_chunks} successful, {failed_chunks} failed chunks")
        
        # カテゴリ完了通知
        if session_id:
            await send_progress(
                session_id, 4, "active", 
                f"✅ {category}カテゴリ完了！{len(category_results)}アイテムの詳細説明を並列処理で追加しました",
                {
                    "category_completed": category,
                    "category_items": len(category_results),
                    "parallel_processing_stats": {
                        "successful_chunks": successful_chunks,
                        "failed_chunks": failed_chunks,
                        "total_chunks": len(chunks),
                        "processing_mode": "parallel"
                    },
                    "completed_category_items": category_results
                }
            )
        
        return category_results

    async def add_descriptions(
        self, 
        translated_data: dict, 
        session_id: Optional[str] = None
    ) -> DescriptionResult:
        """
        翻訳されたメニューに詳細説明を追加（並列チャンク処理版）
        
        Args:
            translated_data: 翻訳されたメニューデータ
            session_id: セッションID（進行状況通知用）
            
        Returns:
            DescriptionResult: 詳細説明生成結果
        """
        print("📝 Starting detailed description generation with OpenAI (Parallel Chunked Processing)...")
        
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
            
            print(f"🔢 Total items to process: {total_items}")
            print(f"🚀 Parallel processing enabled with max {settings.CONCURRENT_CHUNK_LIMIT} concurrent chunks")
            
            # カテゴリの並列処理も可能にする（オプション）
            if settings.ENABLE_CATEGORY_PARALLEL and len(translated_data) > 1:
                print("🌟 Category-level parallel processing enabled")
                
                # カテゴリごとの処理タスクを作成
                category_tasks = []
                for category, items in translated_data.items():
                    if items:  # 空でないカテゴリのみ処理
                        task = self.process_category_parallel(category, items, session_id)
                        category_tasks.append((category, task))
                
                # カテゴリを並列で処理
                category_results = await asyncio.gather(
                    *[task for _, task in category_tasks], 
                    return_exceptions=True
                )
                
                # 結果をマッピング
                for i, (category, _) in enumerate(category_tasks):
                    if i < len(category_results) and not isinstance(category_results[i], Exception):
                        final_menu[category] = category_results[i]
                    else:
                        print(f"⚠️ Category {category} processing failed")
                        final_menu[category] = []
                
                # 空のカテゴリを追加
                for category, items in translated_data.items():
                    if not items:
                        final_menu[category] = []
                        
            else:
                # カテゴリごとに順次処理（但しチャンク内は並列）
                for category, items in translated_data.items():
                    if not items:
                        final_menu[category] = []
                        continue
                    
                    # カテゴリ内並列処理を実行
                    category_results = await self.process_category_parallel(category, items, session_id)
                    final_menu[category] = category_results
            
            print(f"🎉 OpenAI Parallel Description Generation Complete: Added descriptions to {len(final_menu)} categories, {total_items} total items")
            
            # 処理統計を生成
            statistics = self.extract_processing_statistics(translated_data, final_menu)
            statistics["processing_mode"] = "parallel_chunked"
            statistics["concurrent_chunk_limit"] = settings.CONCURRENT_CHUNK_LIMIT
            
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
                        "parallel_chunked_processing",
                        "detailed_descriptions",
                        "cultural_context",
                        "tourist_friendly_language",
                        "real_time_progress",
                        "concurrent_execution"
                    ],
                    "processing_statistics": statistics
                }
            )
            
        except Exception as e:
            print(f"❌ OpenAI Parallel Description Generation Failed: {e}")
            
            # エラータイプの判定
            error_type = "unknown_error"
            suggestions = []
            
            if "rate limit" in str(e).lower():
                error_type = "rate_limit_exceeded"
                suggestions = [
                    "Reduce concurrent chunk limit",
                    "Wait before retrying",
                    "Check OpenAI API usage limits",
                    "Consider upgrading your OpenAI plan"
                ]
            elif "timeout" in str(e).lower():
                error_type = "api_timeout"
                suggestions = [
                    "Retry the request",
                    "Check internet connectivity",
                    "Reduce parallel processing load",
                    "Increase timeout settings"
                ]
            else:
                suggestions = [
                    "Check OPENAI_API_KEY is valid",
                    "Verify model access permissions", 
                    "Check OpenAI service status",
                    "Try reducing concurrent chunk limit"
                ]
            
            return DescriptionResult(
                success=False,
                description_method="openai",
                error=f"OpenAI parallel description generation error: {str(e)}",
                metadata={
                    "error_type": error_type,
                    "original_error": str(e),
                    "suggestions": suggestions,
                    "provider": "OpenAI API",
                    "model": settings.OPENAI_MODEL,
                    "processing_mode": "parallel_chunked"
                }
            )

def get_progress_function():
    """send_progress関数を動的にインポート（循環インポート回避）"""
    try:
        from app.services.realtime import send_progress
        return send_progress
    except ImportError:
        return None

def get_progress_function_stage4():
    """Stage4用のsend_progress関数を動的にインポート（循環インポート回避）"""
    try:
        from app.services.realtime import send_progress
        return send_progress
    except ImportError:
        return None

async def get_description_progress_function():
    """詳細説明用のsend_progress関数を動的にインポート（循環インポート回避）"""
    try:
        from app.services.realtime import send_progress
        return send_progress
    except ImportError:
        return None
