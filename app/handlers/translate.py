"""
翻訳エンドポイント専用のAPIハンドラー
"""
import os
import aiofiles
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter()

# Stage関数の取得
def get_stage_functions():
    """Stage処理関数を取得"""
    try:
        from app.workflows.stages import (
            stage1_ocr_gemini_exclusive,
            stage2_categorize_openai_exclusive,
            stage3_translate_with_fallback,
            stage4_add_descriptions
        )
        return {
            "stage1_ocr": stage1_ocr_gemini_exclusive,
            "stage2_categorize": stage2_categorize_openai_exclusive,
            "stage3_translate": stage3_translate_with_fallback,
            "stage4_descriptions": stage4_add_descriptions
        }
    except ImportError as e:
        print(f"⚠️ Stage functions import error: {e}")
        return {
            "stage1_ocr": None,
            "stage2_categorize": None,
            "stage3_translate": None,
            "stage4_descriptions": None
        }

@router.post("/api/translate")
async def translate_menu(file: UploadFile = File(...)):
    """フロントエンド互換のメニュー翻訳エンドポイント"""
    
    # ファイル形式チェック
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # Stage関数を取得
    stage_functions = get_stage_functions()
    stage1_ocr = stage_functions["stage1_ocr"]
    stage2_categorize = stage_functions["stage2_categorize"]
    stage3_translate = stage_functions["stage3_translate"]
    stage4_descriptions = stage_functions["stage4_descriptions"]
    
    # 必要な関数が利用できない場合
    if not all([stage1_ocr, stage2_categorize, stage3_translate, stage4_descriptions]):
        raise HTTPException(
            status_code=500, 
            detail="Required stage processing functions are not available"
        )
    
    try:
        # ファイルを一時保存
        file_path = f"{settings.UPLOAD_DIR}/{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Stage 1: OCR with Gemini 2.0 Flash (Gemini専用モード)
        stage1_result = await stage1_ocr(file_path)
        
        if not stage1_result["success"]:
            raise HTTPException(status_code=500, detail=f"Text extraction error: {stage1_result['error']}")
        
        extracted_text = stage1_result["extracted_text"]
        
        if not extracted_text.strip():
            return JSONResponse(content={
                "extracted_text": "",
                "menu_items": [],
                "message": "No text could be extracted from the image"
            })
        
        # Stage 2: カテゴリ分類
        stage2_result = await stage2_categorize(extracted_text)
        
        if not stage2_result["success"]:
            raise HTTPException(status_code=500, detail=f"Categorization error: {stage2_result['error']}")
        
        # Stage 3: 翻訳
        stage3_result = await stage3_translate(stage2_result["categories"])
        
        if not stage3_result["success"]:
            raise HTTPException(status_code=500, detail=f"Translation error: {stage3_result['error']}")
        
        # Stage 4: 詳細説明追加
        stage4_result = await stage4_descriptions(stage3_result["translated_categories"])
        
        if not stage4_result["success"]:
            raise HTTPException(status_code=500, detail=f"Description error: {stage4_result['error']}")
        
        # フロントエンド互換フォーマットに変換
        menu_items = []
        final_menu = stage4_result["final_menu"]
        
        for category_name, items in final_menu.items():
            for item in items:
                menu_items.append({
                    "japanese_name": item.get("japanese_name", "N/A"),
                    "english_name": item.get("english_name", "N/A"),
                    "description": item.get("description", "No description available"),
                    "price": item.get("price", "")
                })
        
        # 一時ファイルを削除
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # フロントエンドが期待する形式でレスポンス
        response_data = {
            "extracted_text": extracted_text,
            "menu_items": menu_items
        }
        
        return JSONResponse(content=response_data)
        
    except HTTPException:
        # HTTPException はそのまま再発生
        raise
    except Exception as e:
        # その他のエラーを一時ファイルを削除してから処理
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e)) 