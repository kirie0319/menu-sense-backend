"""
Background処理（メニュー処理ワークフロー）専用のハンドラー
"""
import os
import asyncio

# 必要な関数を取得する関数群
def get_stage_functions():
    """Stage処理関数を取得"""
    try:
        from app.workflows.stages import (
            stage1_ocr_gemini_exclusive,
            stage2_categorize_openai_exclusive,
            stage3_translate_with_fallback,
            stage4_add_descriptions,
            stage5_generate_images,
        )
        from app.services.realtime import send_progress
        
        return {
            "stage1_ocr": stage1_ocr_gemini_exclusive,
            "stage2_categorize": stage2_categorize_openai_exclusive,
            "stage3_translate": stage3_translate_with_fallback,
            "stage4_descriptions": stage4_add_descriptions,
            "stage5_images": stage5_generate_images,
            "send_progress": send_progress
        }
    except ImportError as e:
        print(f"⚠️ Stage functions import error: {e}")
        return {}

def get_progress_state():
    """進行状況管理の状態を取得"""
    try:
        from app.services.realtime import get_ping_pong_sessions
        return {
            "ping_pong_sessions": get_ping_pong_sessions()
        }
    except ImportError as e:
        print(f"⚠️ Progress state import error: {e}")
        return {
            "ping_pong_sessions": {}
        }

def get_image_functions():
    """画像関連の関数を取得"""
    try:
        from app.services.image import combine_menu_with_images
        return {
            "combine_menu_with_images": combine_menu_with_images
        }
    except ImportError as e:
        print(f"⚠️ Image functions import error: {e}")
        return {
            "combine_menu_with_images": None
        }

async def process_menu_background(session_id: str, file_path: str):
    """バックグラウンドでメニュー処理を実行"""
    
    # 必要な関数を取得
    stage_functions = get_stage_functions()
    progress_state = get_progress_state()
    image_functions = get_image_functions()
    
    # 関数の取得
    stage1_ocr = stage_functions.get("stage1_ocr")
    stage2_categorize = stage_functions.get("stage2_categorize")
    stage3_translate = stage_functions.get("stage3_translate")
    stage4_descriptions = stage_functions.get("stage4_descriptions")
    stage5_images = stage_functions.get("stage5_images")
    send_progress = stage_functions.get("send_progress")
    
    ping_pong_sessions = progress_state.get("ping_pong_sessions", {})
    combine_menu_with_images = image_functions.get("combine_menu_with_images")
    
    # 必要な関数が利用できない場合のチェック
    if not all([stage1_ocr, stage2_categorize, stage3_translate, stage4_descriptions, stage5_images, send_progress]):
        print(f"❌ Required functions not available for session {session_id}")
        return
    
    try:
        # Stage 1: OCR with Gemini 2.0 Flash (Gemini専用モード)
        await send_progress(session_id, 1, "active", "🎯 Gemini 2.0 Flashで画像からテキストを抽出中...")
        
        # Gemini専用OCRサービスを使用
        stage1_result = await stage1_ocr(file_path, session_id)
        
        if not stage1_result["success"]:
            await send_progress(session_id, 1, "error", f"OCRエラー: {stage1_result['error']}")
            return

        # Stage 1完了通知（重要: フロントエンドのステージ遷移に必須）
        await send_progress(session_id, 1, "completed", "✅ テキスト抽出完了", {
            "extracted_text": stage1_result["extracted_text"],
            "extracted_length": len(stage1_result["extracted_text"])
        })

        # Stage 2: 日本語カテゴリ分類（OpenAI専用モード）
        await send_progress(session_id, 2, "active", "🏷️ OpenAI Function Callingでメニューを分析中...")
        stage2_result = await stage2_categorize(stage1_result["extracted_text"], session_id)
        
        if not stage2_result["success"]:
            await send_progress(session_id, 2, "error", f"分析エラー: {stage2_result['error']}")
            return
            
        await send_progress(session_id, 2, "completed", "🏷️ カテゴリ分析完了！メニューを分類しました", {
            "categories": stage2_result["categories"],
            "total_categories": len(stage2_result["categories"]),
            "total_items": sum(len(items) for items in stage2_result["categories"].values()),
            "show_categories": True,  # フロントエンドにカテゴリ表示を指示
            "stage_completed": True   # ステージ完了フラグ
        })
        
        # Stage 3: 翻訳（Google Translate + OpenAI フォールバック）
        total_categories_to_translate = len(stage2_result["categories"])
        total_items_to_translate = sum(len(items) for items in stage2_result["categories"].values())
        
        await send_progress(session_id, 3, "active", f"🌍 翻訳開始: {total_categories_to_translate}カテゴリ、{total_items_to_translate}アイテムを翻訳中...", {
            "categories_to_translate": total_categories_to_translate,
            "items_to_translate": total_items_to_translate,
            "translation_method": "google_translate_with_openai_fallback",
            "stage_starting": True
        })
        
        stage3_result = await stage3_translate(stage2_result["categories"], session_id)
        
        if not stage3_result["success"]:
            await send_progress(session_id, 3, "error", f"翻訳エラー: {stage3_result['error']}")
            return
            
        # Stage3完了時に詳細な翻訳結果を送信（フロントエンド表示用）
        translated_summary = {}
        total_translated_items = 0
        for category, items in stage3_result["translated_categories"].items():
            translated_summary[category] = len(items)
            total_translated_items += len(items)
            
        await send_progress(session_id, 3, "completed", "✅ 翻訳完了！英語メニューをご確認ください", {
            "translated_categories": stage3_result["translated_categories"],
            "translation_summary": translated_summary,
            "total_translated_items": total_translated_items,
            "translation_method": stage3_result.get("translation_method", "google_translate"),
            "show_translated_menu": True  # フロントエンドに翻訳メニュー表示を指示
        })
        
        # Stage 4: 詳細説明追加（安定性強化版）
        await send_progress(session_id, 4, "active", "詳細説明を生成中...")
        stage4_result = await stage4_descriptions(stage3_result["translated_categories"], session_id)
        
        # Stage 4の結果処理を改善
        final_menu_for_images = None
        if not stage4_result["success"]:
            # 部分結果がある場合は、それを使用して完了とする
            if stage4_result.get("final_menu") and len(stage4_result["final_menu"]) > 0:
                print(f"⚠️ Stage 4 had errors but partial results available for session {session_id}")
                final_menu_for_images = stage4_result["final_menu"]
                await send_progress(session_id, 4, "completed", "詳細説明完了（一部制限あり）", {
                    "final_menu": stage4_result["final_menu"],
                    "partial_completion": True,
                    "warning": "Some descriptions may be incomplete due to processing limitations"
                })
            else:
                # 部分結果もない場合はStage 3の結果で代替完了
                print(f"⚠️ Stage 4 failed completely, using Stage 3 results for session {session_id}")
                
                # Stage 3の結果を基に基本的な最終メニューを作成
                fallback_menu = {}
                for category, items in stage3_result["translated_categories"].items():
                    fallback_items = []
                    for item in items:
                        fallback_items.append({
                            "japanese_name": item.get("japanese_name", "N/A"),
                            "english_name": item.get("english_name", "N/A"),
                            "description": "Traditional Japanese dish with authentic flavors. Description generation was incomplete.",
                            "price": item.get("price", "")
                        })
                    fallback_menu[category] = fallback_items
                
                final_menu_for_images = fallback_menu
                await send_progress(session_id, 4, "completed", "基本翻訳完了（詳細説明は制限されています）", {
                    "final_menu": fallback_menu,
                    "fallback_completion": True,
                    "warning": "Detailed descriptions could not be generated, but translation is complete"
                })
        else:
            # 正常完了
            final_menu_for_images = stage4_result["final_menu"]
            await send_progress(session_id, 4, "completed", "詳細説明完了", {
                "final_menu": stage4_result["final_menu"],
                "total_items": stage4_result.get("total_items", 0),
                "categories_processed": stage4_result.get("categories_processed", 0)
            })
        
        # Stage 5: 画像生成（Imagen 3）
        await send_progress(session_id, 5, "active", "🎨 メニュー画像を生成中...")
        stage5_result = await stage5_images(final_menu_for_images, session_id)
        
        if stage5_result["success"]:
            if stage5_result.get("skipped_reason"):
                # Imagen 3が利用できない場合
                await send_progress(session_id, 5, "completed", "画像生成をスキップしました", {
                    "skipped_reason": stage5_result["skipped_reason"],
                    "final_menu": final_menu_for_images
                })
            else:
                # 画像生成成功
                total_generated = stage5_result.get("total_images", 0)
                total_items = stage5_result.get("total_items", 0)
                
                # 画像と最終メニューの結合
                if combine_menu_with_images:
                    final_menu_with_images = combine_menu_with_images(final_menu_for_images, stage5_result["images_generated"])
                else:
                    final_menu_with_images = final_menu_for_images
                
                await send_progress(session_id, 5, "completed", f"🎨 画像生成完了！{total_generated}/{total_items}枚の画像を生成しました", {
                    "images_generated": stage5_result["images_generated"],
                    "total_images": total_generated,
                    "final_menu_with_images": final_menu_with_images
                })
        else:
            # 画像生成エラー
            await send_progress(session_id, 5, "completed", "画像生成でエラーが発生しました", {
                "error": stage5_result.get("error", "Unknown error"),
                "final_menu": final_menu_for_images
            })
        
        # Stage 6: 完了通知（stage4_resultとstage5_resultの状態に関わらず送信）
        await send_progress(session_id, 6, "completed", "全ての処理が完了しました！", {
            "processing_summary": {
                "ocr_success": stage1_result["success"],
                "categorization_success": stage2_result["success"], 
                "translation_success": stage3_result["success"],
                "description_success": stage4_result["success"],
                "image_generation_success": stage5_result["success"],
                "completion_type": "full" if all([stage4_result["success"], stage5_result["success"]]) else "partial",
                "total_images_generated": stage5_result.get("total_images", 0)
            }
        })
        
    except Exception as e:
        if send_progress:
            await send_progress(session_id, 0, "error", f"処理エラー: {str(e)}")
    finally:
        # Ping/Pong機能の停止
        if session_id in ping_pong_sessions:
            ping_pong_sessions[session_id]["active"] = False
            print(f"🏓 Ping/Pong stopped for session {session_id}")
        
        # クリーンアップ
        if os.path.exists(file_path):
            os.remove(file_path) 