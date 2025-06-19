"""
メニュー処理ワークフローの各Stage関数

各Stageの責務：
- Stage 1: OCR（画像からテキスト抽出）
- Stage 2: カテゴリ分類（日本語メニューの分類）
- Stage 3: 翻訳（日本語→英語）
- Stage 4: 詳細説明追加
- Stage 5: 画像生成
"""
import asyncio

# サービス層のインポート
from app.services.ocr import extract_text as ocr_extract_text
from app.services.category import categorize_menu as category_categorize_menu
from app.services.translation import translate_menu as translation_translate_menu
from app.services.description import add_descriptions as description_add_descriptions
from app.services.image import generate_images as image_generate_images

# 依存関数の取得（循環インポート回避）
def get_progress_function():
    """send_progress関数を取得（循環インポート回避）"""
    try:
        from app.services.realtime import send_progress
        return send_progress
    except ImportError:
        return None

# Stage 1: OCR - 文字認識 (Gemini専用版)
async def stage1_ocr_gemini_exclusive(image_path: str, session_id: str = None) -> dict:
    """Stage 1: Gemini 2.0 Flash OCRを使って画像からテキストを抽出（Gemini専用モード）"""
    print("🎯 Stage 1: Starting OCR with Gemini 2.0 Flash (Exclusive Mode)...")
    
    send_progress = get_progress_function()
    
    try:
        # Gemini専用OCRサービスを使用
        result = await ocr_extract_text(image_path, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 1,
            "success": result.success,
            "extracted_text": result.extracted_text,
            "ocr_engine": "gemini-2.0-flash",
            "mode": "gemini_exclusive"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            legacy_result.update({
                "text_length": len(result.extracted_text),
                "ocr_service": "Gemini 2.0 Flash",
                "features": ["menu_optimized", "japanese_text", "high_precision"],
                "file_size": result.metadata.get("file_size", 0)
            })
            
            # 進行状況通知は process_menu_background で統一管理
            # if session_id:
            #     await send_progress(session_id, 1, "completed", "🎯 Gemini OCR完了", {
            #         "extracted_text": result.extracted_text,
            #         "text_preview": result.extracted_text[:100] + "..." if len(result.extracted_text) > 100 else result.extracted_text,
            #         "ocr_service": "Gemini 2.0 Flash",
            #         "ocr_engine": "gemini-2.0-flash"
            #     })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            # 進行状況通知
            if session_id and send_progress:
                await send_progress(session_id, 1, "error", f"🎯 Gemini OCRエラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 1 Gemini OCR Failed: {e}")
        
        error_result = {
            "stage": 1,
            "success": False,
            "error": f"Gemini OCRサービスでエラーが発生しました: {str(e)}",
            "ocr_engine": "gemini-2.0-flash",
            "mode": "gemini_exclusive", 
            "detailed_error": {
                "error_type": "gemini_ocr_error",
                "original_error": str(e),
                "suggestions": [
                    "GEMINI_API_KEYが正しく設定されているか確認してください",
                    "Gemini APIの利用状況・クォータを確認してください",
                    "google-generativeaiパッケージがインストールされているか確認してください"
                ]
            },
            "extracted_text": ""
        }
        
        if session_id and send_progress:
            await send_progress(session_id, 1, "error", f"🎯 Gemini OCRエラー: {str(e)}", error_result["detailed_error"])
        
        return error_result

# Stage 2: 日本語のままカテゴリ分類・枠組み作成 (OpenAI専用版)
async def stage2_categorize_openai_exclusive(extracted_text: str, session_id: str = None) -> dict:
    """Stage 2: OpenAI Function Callingを使って抽出されたテキストを日本語のままカテゴリ分類（OpenAI専用モード）"""
    print("🏷️ Stage 2: Starting Japanese categorization with OpenAI Function Calling (Exclusive Mode)...")
    
    send_progress = get_progress_function()
    
    try:
        # 新しいカテゴリサービスを使用
        result = await category_categorize_menu(extracted_text, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 2,
            "success": result.success,
            "categories": result.categories,
            "uncategorized": result.uncategorized,
            "categorization_engine": "openai-function-calling",
            "mode": "openai_exclusive"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.categories.values())
            legacy_result.update({
                "total_items": total_items,
                "total_categories": len(result.categories),
                "uncategorized_count": len(result.uncategorized),
                "categorization_service": "OpenAI Function Calling"
            })
            
            # 進行状況通知は process_menu_background で統一管理
            # if session_id:
            #     await send_progress(session_id, 2, "completed", "🏷️ OpenAI カテゴリ分類完了", {
            #         "categories": result.categories,
            #         "uncategorized": result.uncategorized,
            #         "total_items": total_items,
            #         "categorization_engine": "openai-function-calling"
            #     })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            # 進行状況通知
            if session_id and send_progress:
                await send_progress(session_id, 2, "error", f"🏷️ OpenAI カテゴリ分類エラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 2 OpenAI Categorization Failed: {e}")
        
        error_result = {
            "stage": 2,
            "success": False,
            "error": f"OpenAI カテゴリ分類サービスでエラーが発生しました: {str(e)}",
            "categorization_engine": "openai-function-calling",
            "mode": "openai_exclusive",
            "detailed_error": {
                "error_type": "openai_categorization_error",
                "original_error": str(e),
                "suggestions": [
                    "OPENAI_API_KEYが正しく設定されているか確認してください",
                    "OpenAI APIの利用状況・クォータを確認してください",
                    "openaiパッケージがインストールされているか確認してください"
                ]
            },
            "categories": {}
        }
        
        if session_id and send_progress:
            await send_progress(session_id, 2, "error", f"🏷️ OpenAI カテゴリ分類エラー: {str(e)}", error_result["detailed_error"])
        
        return error_result

# Stage 3: 翻訳 (Google Translate + OpenAI フォールバック版)
async def stage3_translate_with_fallback(categorized_data: dict, session_id: str = None) -> dict:
    """Stage 3: Google Translate + OpenAI フォールバックで翻訳（新サービス層使用）"""
    print("🌍 Stage 3: Starting translation with Google Translate + OpenAI fallback...")
    
    send_progress = get_progress_function()
    
    try:
        # 新しい翻訳サービスを使用
        result = await translation_translate_menu(categorized_data, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 3,
            "success": result.success,
            "translated_categories": result.translated_categories,
            "translation_method": result.translation_method,
            "translation_architecture": "google_translate_with_openai_fallback"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.translated_categories.values())
            legacy_result.update({
                "total_items": total_items,
                "total_categories": len(result.translated_categories),
                "translation_service": result.metadata.get("successful_service", "unknown"),
                "fallback_used": result.metadata.get("fallback_used", False)
            })
            
            # 進行状況通知は process_menu_background で統一管理
            # if session_id:
            #     await send_progress(session_id, 3, "completed", "🌍 翻訳完了", {
            #         "translatedCategories": result.translated_categories,
            #         "translation_method": result.translation_method,
            #         "total_items": total_items,
            #         "fallback_used": result.metadata.get("fallback_used", False)
            #     })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            # 進行状況通知
            if session_id and send_progress:
                await send_progress(session_id, 3, "error", f"🌍 翻訳エラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 3 Translation Service Failed: {e}")
        
        error_result = {
            "stage": 3,
            "success": False,
            "error": f"翻訳サービスでエラーが発生しました: {str(e)}",
            "translation_architecture": "google_translate_with_openai_fallback",
            "detailed_error": {
                "error_type": "translation_service_error",
                "original_error": str(e),
                "suggestions": [
                    "GOOGLE_CREDENTIALS_JSONまたはOPENAI_API_KEYが正しく設定されているか確認してください",
                    "Google Translate APIまたはOpenAI APIの利用状況・クォータを確認してください",
                    "必要なパッケージがインストールされているか確認してください"
                ]
            },
            "translated_categories": {}
        }
        
        if session_id and send_progress:
            await send_progress(session_id, 3, "error", f"🌍 翻訳エラー: {str(e)}", error_result["detailed_error"])
        
        return error_result

# Stage 4: 詳細説明追加 (新サービス層使用)
async def stage4_add_descriptions(translated_data: dict, session_id: str = None) -> dict:
    """Stage 4: OpenAI詳細説明サービスで詳細説明を追加（新サービス層使用）"""
    print("📝 Stage 4: Adding detailed descriptions with OpenAI service...")
    
    try:
        # 新しい詳細説明サービスを使用
        result = await description_add_descriptions(translated_data, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 4,
            "success": result.success,
            "final_menu": result.final_menu,
            "description_method": result.description_method,
            "description_architecture": "openai_chunked_processing"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.final_menu.values())
            legacy_result.update({
                "total_items": total_items,
                "categories_processed": len(result.final_menu),
                "description_service": result.metadata.get("provider", "OpenAI API"),
                "features": result.metadata.get("features", [])
            })
            
            print(f"✅ OpenAI Description Generation successful - {total_items} items processed")
            
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            print(f"❌ OpenAI Description Generation failed: {result.error}")
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 4 Description Service Failed: {e}")
        
        error_result = {
            "stage": 4,
            "success": False,
            "error": f"詳細説明サービスでエラーが発生しました: {str(e)}",
            "description_architecture": "openai_chunked_processing",
            "detailed_error": {
                "error_type": "description_service_error",
                "original_error": str(e),
                "suggestions": [
                    "OPENAI_API_KEYが正しく設定されているか確認してください",
                    "OpenAI APIの利用状況・クォータを確認してください",
                    "openaiパッケージがインストールされているか確認してください",
                    "入力データの形式が正しいか確認してください"
                ]
            },
            "final_menu": {}
        }
        
        return error_result

# Stage 5: 画像生成 (Celery + Redis 非同期処理版)
async def stage5_generate_images(final_menu: dict, session_id: str = None) -> dict:
    """Stage 5: Celery + Redis非同期処理でImagen 3画像を生成"""
    print("🎨 Stage 5: Starting async image generation with Celery + Redis...")
    
    try:
        from app.services.image.async_manager import get_async_manager
        
        # AsyncImageManagerを取得
        async_manager = get_async_manager()
        
        # 非同期画像生成を開始
        success, message, job_id = async_manager.start_async_generation(final_menu, session_id)
        
        if not success or not job_id:
            # 非同期処理開始に失敗した場合は従来の同期処理にフォールバック
            print(f"⚠️ Async generation failed ({message}), falling back to sync processing...")
            result = await image_generate_images(final_menu, session_id)
            
            return {
                "stage": 5,
                "success": result.success,
                "images_generated": result.images_generated,
                "total_images": result.total_images,
                "total_items": result.total_items,
                "image_method": result.image_method + "_sync_fallback",
                "image_architecture": "imagen3_food_photography_sync",
                "fallback_reason": message
            }
        
        print(f"🚀 Async image generation started: job_id={job_id}")
        
        # ジョブ完了まで監視
        return await monitor_async_image_job(job_id, session_id, final_menu)
        
    except Exception as e:
        print(f"❌ Stage 5 Async Image Generation Failed: {e}")
        
        # 例外が発生した場合も同期処理にフォールバック
        try:
            print("⚠️ Exception occurred, attempting sync fallback...")
            result = await image_generate_images(final_menu, session_id)
            
            return {
                "stage": 5,
                "success": result.success,
                "images_generated": result.images_generated,
                "total_images": result.total_images,
                "total_items": result.total_items,
                "image_method": result.image_method + "_exception_fallback",
                "image_architecture": "imagen3_food_photography_sync",
                "fallback_reason": f"Exception in async processing: {str(e)}"
            }
        except Exception as sync_error:
            # 同期処理も失敗した場合はエラーレスポンス
            error_result = {
                "stage": 5,
                "success": False,
                "error": f"画像生成サービスでエラーが発生しました: {str(e)}",
                "image_architecture": "imagen3_async_with_sync_fallback",
                "detailed_error": {
                    "error_type": "both_async_and_sync_failed",
                    "async_error": str(e),
                    "sync_error": str(sync_error),
                    "suggestions": [
                        "Redisサーバーが起動しているか確認してください",
                        "Celeryワーカーが起動しているか確認してください",
                        "GEMINI_API_KEYが正しく設定されているか確認してください",
                        "IMAGE_GENERATION_ENABLEDが有効になっているか確認してください"
                    ]
                },
                "images_generated": {}
            }
            
            return error_result

async def monitor_async_image_job(job_id: str, session_id: str = None, final_menu: dict = None) -> dict:
    """非同期画像生成ジョブを監視し、完了まで待機"""
    from app.services.image.async_manager import get_async_manager
    
    send_progress = get_progress_function()
    async_manager = get_async_manager()
    start_time = asyncio.get_event_loop().time()
    last_progress = -1
    monitoring_interval = 2.0  # 2秒間隔でチェック
    max_wait_time = 300  # 最大5分待機
    
    print(f"📊 Starting job monitoring: job_id={job_id}")
    
    try:
        while asyncio.get_event_loop().time() - start_time < max_wait_time:
            # ジョブステータスを取得
            status_info = async_manager.get_job_status(job_id)
            
            if not status_info.get("found", False):
                print(f"❌ Job not found: {job_id}")
                break
            
            current_status = status_info.get("status", "unknown")
            current_progress = status_info.get("progress_percent", 0)
            
            # 進行状況が変化した場合のみ通知
            if current_progress != last_progress:
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                
                # 進行状況をクライアントに通知
                if session_id and send_progress:
                    processing_info = status_info.get("processing_info", {})
                    await send_progress(
                        session_id, 5, "active",
                        f"🎨 非同期画像生成中: {current_progress}% (経過時間: {elapsed}秒)",
                        {
                            "job_id": job_id,
                            "progress_percent": current_progress,
                            "status": current_status,
                            "async_processing": True,
                            "processing_info": {
                                "completed_chunks": status_info.get("completed_chunks", 0),
                                "total_chunks": status_info.get("total_chunks", 0),
                                "total_items": status_info.get("total_items", 0),
                                "elapsed_time": elapsed
                            }
                        }
                    )
                
                print(f"📊 [{elapsed}s] Job {job_id}: {current_status} - {current_progress}%")
                last_progress = current_progress
            
            # 完了チェック
            if current_status in ["completed", "partial_completed", "failed"]:
                print(f"✅ Job completed: {job_id} - Status: {current_status}")
                
                # 結果を構築
                if current_status in ["completed", "partial_completed"]:
                    images_generated = status_info.get("images_generated", {})
                    total_images = status_info.get("total_images", 0)
                    total_items = sum(len(items) for items in final_menu.values()) if final_menu else status_info.get("total_items", 0)
                    
                    # 成功率計算
                    success_rate = (total_images / total_items * 100) if total_items > 0 else 0
                    
                    return {
                        "stage": 5,
                        "success": True,
                        "images_generated": images_generated,
                        "total_images": total_images,
                        "total_items": total_items,
                        "image_method": "celery_async_imagen3",
                        "image_architecture": "imagen3_async_food_photography",
                        "job_id": job_id,
                        "processing_time": int(asyncio.get_event_loop().time() - start_time),
                        "success_rate": round(success_rate, 2),
                        "async_processing_completed": True
                    }
                else:
                    # 失敗
                    return {
                        "stage": 5,
                        "success": False,
                        "error": f"Async image generation failed: {current_status}",
                        "job_id": job_id,
                        "image_architecture": "imagen3_async_food_photography",
                        "processing_time": int(asyncio.get_event_loop().time() - start_time),
                        "images_generated": {}
                    }
            
            # 次のチェックまで待機
            await asyncio.sleep(monitoring_interval)
        
        # タイムアウト
        print(f"⏰ Job monitoring timeout: {job_id}")
        return {
            "stage": 5,
            "success": False,
            "error": f"Image generation timeout after {max_wait_time} seconds",
            "job_id": job_id,
            "image_architecture": "imagen3_async_food_photography",
            "timeout": True,
            "images_generated": {}
        }
        
    except Exception as e:
        print(f"❌ Job monitoring error: {e}")
        return {
            "stage": 5,
            "success": False,
            "error": f"Job monitoring failed: {str(e)}",
            "job_id": job_id,
            "image_architecture": "imagen3_async_food_photography",
            "monitoring_error": True,
            "images_generated": {}
        } 