"""
🤖 OpenAI Provider Service

OpenAI GPTを使用した統合サービス
- Category分類: メニューテキストのカテゴリ分類
- Description生成: 詳細説明の生成

既存のapp.services.category.openai + app.services.description.openaiを統合
"""

import json
import asyncio
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

try:
    import openai
    from openai import AsyncOpenAI
except ImportError:
    openai = None
    AsyncOpenAI = None

from app.core.config.ai import ai_settings
from app.core.config.processing import processing_settings

# CategoryResult class definition (moved from external import)
class CategoryProvider(Enum):
    """カテゴリ分類プロバイダーの列挙型"""
    OPENAI = "openai"
    GOOGLE_TRANSLATE = "google_translate"
    ENHANCED = "enhanced"

class CategoryResult(BaseModel):
    """
    カテゴリ分類結果を格納するクラス
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    categories: Dict[str, List[Dict]] = {}
    uncategorized: List[str] = []
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    total_items: Optional[int] = Field(default=None, description="総アイテム数")
    categorized_items: Optional[int] = Field(default=None, description="分類済みアイテム数")
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    categorization_method: Optional[str] = Field(default=None, description="分類手法")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    coverage_score: Optional[float] = Field(default=None, description="分類カバレッジ")
    balance_score: Optional[float] = Field(default=None, description="カテゴリバランス")
    accuracy_estimate: Optional[float] = Field(default=None, description="精度推定")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "categories": self.categories,
            "uncategorized": self.uncategorized
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result

# DescriptionResult class definition (moved from external import)
class DescriptionProvider(str, Enum):
    """詳細説明プロバイダーの定義"""
    OPENAI = "openai"
    ENHANCED = "enhanced"

class DescriptionResult(BaseModel):
    """
    詳細説明生成結果を格納するクラス
    """
    
    # 既存フィールド（互換性維持）
    success: bool
    final_menu: Dict[str, List[Dict]] = {}
    description_method: str = ""
    error: Optional[str] = None
    metadata: Dict = {}
    
    # Enhanced機能追加フィールド（オプション）
    total_items: Optional[int] = Field(default=None, description="総アイテム数")
    described_items: Optional[int] = Field(default=None, description="説明追加済みアイテム数")
    processing_time: Optional[float] = Field(default=None, description="処理時間（秒）")
    
    # 品質指標（Enhanced機能）
    quality_score: Optional[float] = Field(default=None, description="品質スコア (0-1)")
    confidence: Optional[float] = Field(default=None, description="信頼度 (0-1)")
    description_coverage: Optional[float] = Field(default=None, description="説明カバレッジ")
    description_quality: Optional[float] = Field(default=None, description="説明品質")
    cultural_accuracy: Optional[float] = Field(default=None, description="文化的正確性")
    
    # 統計情報（Enhanced機能）
    failed_descriptions: List[str] = Field(default_factory=list, description="説明生成失敗アイテム")
    description_stats: Dict[str, Any] = Field(default_factory=dict, description="説明統計")
    fallback_used: bool = Field(default=False, description="フォールバック使用フラグ")
    
    def to_dict(self) -> Dict:
        """辞書形式に変換（既存互換性維持）"""
        result = {
            "success": self.success,
            "final_menu": self.final_menu,
            "description_method": self.description_method
        }
        if self.error:
            result["error"] = self.error
        if self.metadata:
            result.update(self.metadata)
        return result


class OpenAIProviderService:
    """OpenAI統合プロバイダーサービス"""
    
    def __init__(self):
        self.service_name = "OpenAIProviderService"
        self.client = None
        self._initialize_client()
        # 並列処理用セマフォ
        self.semaphore = asyncio.Semaphore(processing_settings.concurrent_chunk_limit)
    
    def _initialize_client(self):
        """OpenAI APIクライアントを初期化"""
        try:
            if not openai or not AsyncOpenAI:
                print("❌ openai package not installed. Install with: pip install openai")
                return
                
            if ai_settings.openai_api_key:
                self.client = AsyncOpenAI(
                    api_key=ai_settings.openai_api_key,
                    timeout=ai_settings.openai_timeout,
                    max_retries=ai_settings.openai_max_retries
                )
                print("🔧 OpenAI Provider Service initialized successfully")
            else:
                print("⚠️ OPENAI_API_KEY not set")
                
        except Exception as e:
            print(f"❌ Failed to initialize OpenAI Provider Service: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """サービスが利用可能かチェック"""
        return self.client is not None and bool(ai_settings.openai_api_key)
    
    # ==========================================
    # Category Classification Features
    # ==========================================
    
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
        if not extracted_text or len(extracted_text.strip()) < 5:
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
                        "model": ai_settings.openai_model,
                        "text_length": len(extracted_text)
                    }
                )
            else:
                raise ValueError("Function call not found in response")
                
        except Exception as e:
            print(f"❌ OpenAI Categorization Failed: {e}")
            
            return CategoryResult(
                success=False,
                error=f"OpenAI categorization error: {str(e)}",
                metadata={
                    "error_type": self._get_error_type(e),
                    "original_error": str(e),
                    "suggestions": self._get_error_suggestions(e),
                    "categorization_method": "openai_function_calling",
                    "model": ai_settings.openai_model,
                    "text_length": len(extracted_text)
                }
            )
    
    # ==========================================
    # Description Generation Features
    # ==========================================
    
    def generate_description(
        self,
        japanese_name: str,
        english_name: str,
        category: str = "Other"
    ) -> Dict:
        """
        個別アイテムの詳細説明を生成
        
        Args:
            japanese_name: 日本語名
            english_name: 英語名
            category: カテゴリ
            
        Returns:
            Dict: 説明生成結果
        """
        if not self.is_available():
            # フォールバック説明
            fallback_description = f"Traditional Japanese {category.lower()} with authentic flavors and high-quality ingredients."
            return {
                'success': True,
                'description': fallback_description,
                'service': 'Fallback Description'
            }
        
        try:
            # 個別アイテム用プロンプト作成
            prompt = f"""Please generate a detailed English description for this Japanese dish for foreign tourists:

Japanese Name: {japanese_name}
English Name: {english_name}
Category: {category}

Requirements:
1. Create a detailed description in English (30-80 words)
2. Include cooking method, key ingredients, and flavor profile
3. Add cultural context that tourists would find interesting
4. Use tourist-friendly language that's easy to understand
5. Make it appealing and informative

Please respond with only the description text, no additional formatting or explanation."""

            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # OpenAI API呼び出し（同期版）
            response = self.call_openai_with_retry_sync(messages, max_retries=2)
            description = response.choices[0].message.content.strip()
            
            # 説明をクリーンアップ
            description = self.clean_description_text(description)
            
            return {
                'success': True,
                'description': description,
                'service': 'OpenAI Description'
            }
            
        except Exception as e:
            print(f"❌ Individual description generation failed: {str(e)}")
            # エラー時のフォールバック
            fallback_description = f"Delicious {english_name} - a traditional {category.lower()} dish with authentic Japanese flavors."
            return {
                'success': True,
                'description': fallback_description,
                'service': 'Error Fallback Description'
            }
    
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
            print(f"🚀 Parallel processing enabled with max {processing_settings.concurrent_chunk_limit} concurrent chunks")
            
            # 各カテゴリを並列処理
            for category, items in translated_data.items():
                if items:  # 空でないカテゴリのみ処理
                    category_results = await self.process_category_parallel(category, items, session_id)
                    final_menu[category] = category_results
            
            total_processed = sum(len(items) for items in final_menu.values())
            
            print(f"✅ OpenAI Description Generation Complete: {total_processed} items processed")
            
            return DescriptionResult(
                success=True,
                final_menu=final_menu,
                description_method="openai_parallel_chunked",
                metadata={
                    "total_items": total_processed,
                    "categories_processed": len(final_menu),
                    "processing_mode": "parallel_chunked",
                    "model": ai_settings.openai_model,
                    "concurrent_chunks": processing_settings.concurrent_chunk_limit
                }
            )
            
        except Exception as e:
            print(f"❌ OpenAI Description Generation Failed: {e}")
            
            return DescriptionResult(
                success=False,
                description_method="openai",
                error=f"OpenAI description generation error: {str(e)}",
                metadata={
                    "error_type": self._get_error_type(e),
                    "original_error": str(e),
                    "suggestions": self._get_error_suggestions(e),
                    "model": ai_settings.openai_model
                }
            )
    
    # ==========================================
    # Utility Methods
    # ==========================================
    
    async def call_openai_with_retry(self, messages, functions=None, function_call=None, max_retries=3):
        """指数バックオフ付きでOpenAI APIを呼び出すリトライ関数（非同期版）"""
        if not self.is_available():
            raise Exception("OpenAI API is not available")
        
        for attempt in range(max_retries + 1):
            try:
                kwargs = {
                    "model": ai_settings.openai_model,
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
                
                wait_time = processing_settings.retry_base_delay ** attempt
                print(f"⏳ Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                
            except (openai.APITimeoutError, openai.APIConnectionError) as e:
                if attempt == max_retries:
                    raise Exception(f"API error after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = processing_settings.retry_base_delay ** attempt
                print(f"⏳ API error, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
                
            except Exception as e:
                # その他のエラーは即座に失敗
                raise Exception(f"OpenAI API error: {str(e)}")
    
    def call_openai_with_retry_sync(self, messages, max_retries=2):
        """同期版リトライ関数（generate_description用）"""
        if not self.is_available():
            raise Exception("OpenAI API is not available")
        
        import time
        
        # 同期クライアントを作成
        sync_client = openai.OpenAI(
            api_key=ai_settings.openai_api_key,
            timeout=ai_settings.openai_timeout,
            max_retries=ai_settings.openai_max_retries
        )
        
        for attempt in range(max_retries + 1):
            try:
                response = sync_client.chat.completions.create(
                    model=ai_settings.openai_model,
                    messages=messages
                )
                return response
                
            except openai.RateLimitError as e:
                if attempt == max_retries:
                    raise Exception(f"Rate limit exceeded after {max_retries + 1} attempts: {str(e)}")
                
                wait_time = processing_settings.retry_base_delay ** attempt
                print(f"⏳ Rate limit hit, waiting {wait_time} seconds before retry {attempt + 1}/{max_retries}")
                time.sleep(wait_time)
                
            except Exception as e:
                raise Exception(f"OpenAI API error: {str(e)}")
    
    def validate_translated_data(self, translated_data: Dict) -> bool:
        """翻訳データの妥当性をチェック"""
        if not translated_data or not isinstance(translated_data, dict):
            return False
        
        # 少なくとも1つのカテゴリにアイテムがあることを確認
        has_items = any(
            isinstance(items, list) and len(items) > 0 
            for items in translated_data.values()
        )
        
        return has_items
    
    def clean_description_text(self, description: str) -> str:
        """説明テキストをクリーンアップ"""
        if not description:
            return ""
        
        # 不要な引用符を削除
        description = description.strip().strip('"').strip("'")
        
        # 改行を除去
        description = description.replace('\n', ' ').replace('\r', ' ')
        
        # 複数スペースを単一スペースに
        import re
        description = re.sub(r'\s+', ' ', description)
        
        return description.strip()
    
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
        
        # チャンクに分割
        chunk_size = processing_settings.processing_chunk_size
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
        
        # 並列実行
        print(f"  🚀 Starting {len(tasks)} parallel chunk tasks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 結果を処理
        category_results = []
        successful_chunks = 0
        
        # チャンク番号でソート（元の順序を維持）
        sorted_results = []
        for result in results:
            if isinstance(result, tuple):
                sorted_results.append(result)
            else:
                print(f"  ⚠️ Exception in parallel processing: {result}")
        
        sorted_results.sort(key=lambda x: x[0])  # chunk_numberでソート
        
        for chunk_number, chunk_result, error in sorted_results:
            if error:
                print(f"  ⚠️ Chunk {chunk_number} failed: {error}")
            elif chunk_result:
                category_results.extend(chunk_result)
                successful_chunks += 1
        
        print(f"  ✅ Parallel processing complete: {successful_chunks} successful chunks")
        
        return category_results
    
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
            try:
                # チャンク処理を実行
                result = await self.process_chunk(category, chunk, chunk_number, total_chunks, session_id)
                return (chunk_number, result, None)  # (chunk_number, result, error)
                
            except Exception as e:
                print(f"  ❌ Error in parallel chunk {chunk_number}/{total_chunks}: {e}")
                return (chunk_number, None, str(e))
    
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
    
    def create_description_prompt(self, category: str, chunk: list) -> str:
        """詳細説明生成用のプロンプトを作成"""
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
    
    def create_fallback_description(self, item: dict) -> str:
        """フォールバック説明を作成"""
        english_name = item.get("english_name", "Unknown dish")
        category = item.get("category", "dish")
        
        return f"Traditional Japanese {category.lower()} featuring {english_name} with authentic flavors and quality ingredients."
    
    def _get_error_type(self, error: Exception) -> str:
        """エラータイプを判定"""
        error_str = str(error).lower()
        
        if "rate limit" in error_str:
            return "rate_limit_exceeded"
        elif "timeout" in error_str:
            return "api_timeout"
        elif "function call" in error_str:
            return "function_call_error"
        elif "connection" in error_str:
            return "connection_error"
        else:
            return "unknown_error"
    
    def _get_error_suggestions(self, error: Exception) -> List[str]:
        """エラーに対する改善提案を取得"""
        error_type = self._get_error_type(error)
        
        suggestions_map = {
            "rate_limit_exceeded": [
                "Wait before retrying",
                "Check OpenAI API usage limits",
                "Consider upgrading your OpenAI plan"
            ],
            "api_timeout": [
                "Retry the request",
                "Check internet connectivity",
                "Try with shorter text input"
            ],
            "function_call_error": [
                "Check if the model supports function calling",
                "Verify the function schema is correct",
                "Try with a different model version"
            ],
            "connection_error": [
                "Check internet connectivity",
                "Verify OpenAI service status",
                "Try again in a few moments"
            ],
            "unknown_error": [
                "Check OPENAI_API_KEY is valid",
                "Verify model access permissions",
                "Check OpenAI service status"
            ]
        }
        
        return suggestions_map.get(error_type, suggestions_map["unknown_error"]) 