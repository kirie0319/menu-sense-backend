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

# Stage 1: OCR並列処理版
async def stage1_ocr_gemini_exclusive(image_path: str, session_id: str = None) -> dict:
    """Stage 1: 並列OCRで高精度・高速化（マルチエンジン + フォールバック）"""
    print("🚀 Stage 1: Starting OCR with PARALLEL processing...")
    
    send_progress = get_progress_function()
    
    try:
        # 並列OCRサービスを使用
        from app.services.ocr.parallel import extract_text_with_parallel
        
        result = await extract_text_with_parallel(image_path, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 1,
            "success": result.success,
            "extracted_text": result.extracted_text,
            "ocr_engine": result.metadata.get("selected_engine", "gemini-2.0-flash"),
            "mode": "parallel_ocr_with_fallback"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            processing_mode = result.metadata.get("processing_mode", "unknown")
            
            legacy_result.update({
                "text_length": len(result.extracted_text),
                "ocr_service": result.metadata.get("provider", "Parallel OCR Service"),
                "processing_mode": processing_mode,
                "parallel_enabled": result.metadata.get("parallel_enabled", False),
                "selected_engine": result.metadata.get("selected_engine", "unknown"),
                "engines_used": result.metadata.get("engines_used", []),
                "all_results": result.metadata.get("all_results", {}),
                "selection_reason": result.metadata.get("selection_reason", ""),
                "processing_time": result.metadata.get("processing_time"),
                "features": result.metadata.get("features", ["menu_optimized", "japanese_text", "high_precision"])
            })
            
            # 性能向上の表示
            if result.metadata.get("parallel_enabled", False):
                print(f"🚀 PARALLEL OCR successful - {len(result.extracted_text)} characters extracted with enhanced accuracy")
            else:
                processing_mode_display = processing_mode.replace("_", " ").title()
                print(f"🔄 {processing_mode_display} used - {len(result.extracted_text)} characters extracted")
            
            # 進行状況通知は process_menu_background で統一管理
            # if session_id:
            #     await send_progress(session_id, 1, "completed", "🚀 並列OCR完了", {
            #         "extracted_text": result.extracted_text,
            #         "text_preview": result.extracted_text[:100] + "..." if len(result.extracted_text) > 100 else result.extracted_text,
            #         "ocr_service": result.metadata.get("provider", "Parallel OCR Service"),
            #         "processing_mode": processing_mode,
            #         "parallel_enabled": result.metadata.get("parallel_enabled", False)
            #     })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            print(f"❌ Parallel OCR failed: {result.error}")
            
            # 進行状況通知
            if session_id and send_progress:
                await send_progress(session_id, 1, "error", f"🚀 並列OCRエラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 1 Parallel OCR Service Failed: {e}")
        
        error_result = {
            "stage": 1,
            "success": False,
            "error": f"並列OCRサービスでエラーが発生しました: {str(e)}",
            "ocr_engine": "parallel_multi_engine",
            "mode": "parallel_ocr_with_fallback",
            "detailed_error": {
                "error_type": "parallel_ocr_service_error",
                "original_error": str(e),
                "suggestions": [
                    "GEMINI_API_KEYが正しく設定されているか確認してください",
                    "Celeryワーカーが起動しているか確認してください",
                    "並列OCRの設定（ENABLE_PARALLEL_OCR）を確認してください",
                    "Google Vision APIまたはGemini APIの利用状況・クォータを確認してください"
                ]
            },
            "extracted_text": ""
        }
        
        if session_id and send_progress:
            await send_progress(session_id, 1, "error", f"🚀 並列OCRエラー: {str(e)}", error_result["detailed_error"])
        
        return error_result

# Stage 2: 日本語のままカテゴリ分類・枠組み作成 (並列化対応版)
async def stage2_categorize_openai_exclusive(extracted_text: str, session_id: str = None) -> dict:
    """Stage 2: OpenAI Function Callingを使って抽出されたテキストを日本語のままカテゴリ分類（並列化対応）"""
    print("🏷️ Stage 2: Starting Japanese categorization with PARALLEL PROCESSING...")
    
    send_progress = get_progress_function()
    
    try:
        # 並列カテゴライズサービスを使用
        from app.services.category.parallel import categorize_menu_with_parallel
        
        result = await categorize_menu_with_parallel(extracted_text, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 2,
            "success": result.success,
            "categories": result.categories,
            "uncategorized": result.uncategorized,
            "categorization_engine": "openai-function-calling-parallel",
            "mode": "parallel_categorization"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.categories.values())
            legacy_result.update({
                "total_items": total_items,
                "total_categories": len(result.categories),
                "uncategorized_count": len(result.uncategorized),
                "categorization_service": "Parallel Categorization Service",
                "parallel_processing": True,
                "processing_time": result.metadata.get('processing_time', 0),
                "parallel_strategy": result.metadata.get('parallel_strategy', 'unknown')
            })
            
            print(f"✅ Stage 2 PARALLEL Categorization Complete: {total_items} items in {len(result.categories)} categories")
            
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            # 進行状況通知
            if session_id and send_progress:
                await send_progress(session_id, 2, "error", f"🏷️ 並列カテゴリ分類エラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 2 Parallel Categorization Failed: {e}")
        
        error_result = {
            "stage": 2,
            "success": False,
            "error": f"並列カテゴリ分類サービスでエラーが発生しました: {str(e)}",
            "categorization_engine": "openai-function-calling-parallel",
            "mode": "parallel_categorization",
            "detailed_error": {
                "error_type": "parallel_categorization_error",
                "original_error": str(e),
                "suggestions": [
                    "Celeryワーカーが起動しているか確認してください",
                    "OPENAI_API_KEYが正しく設定されているか確認してください", 
                    "並列処理設定を確認してください（ENABLE_PARALLEL_CATEGORIZATION）"
                ]
            },
            "categories": {}
        }
        
        if session_id and send_progress:
            await send_progress(session_id, 2, "error", f"🏷️ 並列カテゴリ分類エラー: {str(e)}", error_result["detailed_error"])
        
        return error_result

# Stage 2: 日本語のままカテゴリ分類・枠組み作成 (従来版・フォールバック用)
async def stage2_categorize_openai_exclusive_legacy(extracted_text: str, session_id: str = None) -> dict:
    """Stage 2: OpenAI Function Callingを使って抽出されたテキストを日本語のままカテゴリ分類（従来版）"""
    print("🏷️ Stage 2: Starting Japanese categorization with OpenAI Function Calling (Legacy Mode)...")
    
    send_progress = get_progress_function()
    
    try:
        # 従来のカテゴリサービスを使用
        from app.services.category import category_categorize_menu
        
        result = await category_categorize_menu(extracted_text, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 2,
            "success": result.success,
            "categories": result.categories,
            "uncategorized": result.uncategorized,
            "categorization_engine": "openai-function-calling",
            "mode": "openai_exclusive_legacy"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.categories.values())
            legacy_result.update({
                "total_items": total_items,
                "total_categories": len(result.categories),
                "uncategorized_count": len(result.uncategorized),
                "categorization_service": "OpenAI Function Calling (Legacy)"
            })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
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
            "mode": "openai_exclusive_legacy",
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

# Stage 3: 翻訳 (並列翻訳版)
async def stage3_translate_with_fallback(categorized_data: dict, session_id: str = None) -> dict:
    """Stage 3: 並列翻訳で高速化（Google Translate + OpenAI フォールバック）"""
    print("🚀 Stage 3: Starting PARALLEL translation with enhanced performance...")
    
    send_progress = get_progress_function()
    
    try:
        # 並列翻訳サービスを使用
        from app.services.translation.parallel import translate_menu_with_parallel
        
        result = await translate_menu_with_parallel(categorized_data, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 3,
            "success": result.success,
            "translated_categories": result.translated_categories,
            "translation_method": result.translation_method,
            "translation_architecture": "parallel_translation_with_fallback"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.translated_categories.values())
            processing_mode = result.metadata.get("processing_mode", "unknown")
            
            legacy_result.update({
                "total_items": total_items,
                "total_categories": len(result.translated_categories),
                "translation_service": result.metadata.get("provider", "Parallel Translation Service"),
                "processing_mode": processing_mode,
                "parallel_enabled": processing_mode == "parallel_direct",
                "fallback_used": result.metadata.get("fallback_used", False),
                "failed_categories": result.metadata.get("failed_categories"),
                "processing_time": result.metadata.get("total_processing_time")
            })
            
            # 性能向上の表示
            if processing_mode == "parallel_direct":
                print(f"🚀 PARALLEL Translation successful - {total_items} items processed with enhanced speed")
            else:
                print(f"🔄 Sequential fallback used - {total_items} items processed")
            
            # 進行状況通知は process_menu_background で統一管理
            # if session_id:
            #     await send_progress(session_id, 3, "completed", "🚀 並列翻訳完了", {
            #         "translatedCategories": result.translated_categories,
            #         "translation_method": result.translation_method,
            #         "total_items": total_items,
            #         "processing_mode": processing_mode,
            #         "parallel_enabled": processing_mode == "parallel_direct"
            #     })
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            # 進行状況通知
            if session_id and send_progress:
                await send_progress(session_id, 3, "error", f"🚀 並列翻訳エラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 3 Parallel Translation Service Failed: {e}")
        
        error_result = {
            "stage": 3,
            "success": False,
            "error": f"並列翻訳サービスでエラーが発生しました: {str(e)}",
            "translation_architecture": "parallel_translation_with_fallback",
            "detailed_error": {
                "error_type": "parallel_translation_service_error",
                "original_error": str(e),
                "suggestions": [
                    "GOOGLE_CREDENTIALS_JSONまたはOPENAI_API_KEYが正しく設定されているか確認してください",
                    "Celeryワーカーが起動しているか確認してください",
                    "並列翻訳の設定（ENABLE_PARALLEL_TRANSLATION）を確認してください",
                    "Google Translate APIまたはOpenAI APIの利用状況・クォータを確認してください"
                ]
            },
            "translated_categories": {}
        }
        
        if session_id and send_progress:
            await send_progress(session_id, 3, "error", f"🚀 並列翻訳エラー: {str(e)}", error_result["detailed_error"])
        
        return error_result

# Stage 4: 詳細説明追加 (並列処理版)
async def stage4_add_descriptions(translated_data: dict, session_id: str = None) -> dict:
    """Stage 4: 並列詳細説明で高速化（OpenAI並列ワーカー + フォールバック）"""
    print("🚀 Stage 4: Adding detailed descriptions with PARALLEL processing...")
    
    send_progress = get_progress_function()
    
    try:
        # 並列詳細説明サービスを使用
        from app.services.description.parallel import add_descriptions_with_parallel
        
        result = await add_descriptions_with_parallel(translated_data, session_id)
        
        # レガシー形式に変換
        legacy_result = {
            "stage": 4,
            "success": result.success,
            "final_menu": result.final_menu,
            "description_method": result.description_method,
            "description_architecture": "parallel_description_with_fallback"
        }
        
        if result.success:
            # 成功時のメタデータを追加
            total_items = sum(len(items) for items in result.final_menu.values())
            processing_mode = result.metadata.get("processing_mode", "unknown")
            
            legacy_result.update({
                "total_items": total_items,
                "categories_processed": len(result.final_menu),
                "description_service": result.metadata.get("provider", "OpenAI API (Parallel)"),
                "processing_mode": processing_mode,
                "parallel_enabled": result.metadata.get("parallel_enabled", False),
                "fallback_used": result.metadata.get("fallback_reason") is not None,
                "failed_categories": result.metadata.get("failed_categories"),
                "processing_time": result.metadata.get("processing_time"),
                "features": result.metadata.get("features", [])
            })
            
            # 性能向上の表示
            if result.metadata.get("parallel_enabled", False):
                print(f"🚀 PARALLEL Description successful - {total_items} items processed with enhanced speed")
            else:
                processing_mode_display = processing_mode.replace("_", " ").title()
                print(f"🔄 {processing_mode_display} used - {total_items} items processed")
            
            # 進行状況通知は process_menu_background で統一管理
            # if session_id:
            #     await send_progress(session_id, 4, "completed", "🚀 並列詳細説明完了", {
            #         "finalMenu": result.final_menu,
            #         "description_method": result.description_method,
            #         "total_items": total_items,
            #         "processing_mode": processing_mode,
            #         "parallel_enabled": result.metadata.get("parallel_enabled", False)
            #     })
            
        else:
            # エラー時の詳細情報を追加
            legacy_result.update({
                "error": result.error,
                "detailed_error": result.metadata
            })
            
            print(f"❌ Parallel Description Generation failed: {result.error}")
            
            # 進行状況通知
            if session_id and send_progress:
                await send_progress(session_id, 4, "error", f"🚀 並列詳細説明エラー: {result.error}", result.metadata)
        
        return legacy_result
        
    except Exception as e:
        print(f"❌ Stage 4 Parallel Description Service Failed: {e}")
        
        error_result = {
            "stage": 4,
            "success": False,
            "error": f"並列詳細説明サービスでエラーが発生しました: {str(e)}",
            "description_architecture": "parallel_description_with_fallback",
            "detailed_error": {
                "error_type": "parallel_description_service_error",
                "original_error": str(e),
                "suggestions": [
                    "OPENAI_API_KEYが正しく設定されているか確認してください",
                    "Celeryワーカーが起動しているか確認してください",
                    "並列詳細説明の設定（ENABLE_PARALLEL_DESCRIPTION）を確認してください",
                    "OpenAI APIの利用状況・クォータを確認してください"
                ]
            },
            "final_menu": {}
        }
        
        if session_id and send_progress:
            await send_progress(session_id, 4, "error", f"🚀 並列詳細説明エラー: {str(e)}", error_result["detailed_error"])
        
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