from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import aiofiles
import os
from typing import Optional

from app.core.config import settings
from app.services.ocr import extract_text, get_ocr_service_status, OCRProvider

router = APIRouter()

@router.post("/extract")
async def extract_text_from_image(file: UploadFile = File(...)):
    """
    Gemini OCRで画像からテキストを抽出するエンドポイント（Gemini専用モード）
    
    Args:
        file: アップロードされた画像ファイル
        
    Returns:
        Gemini OCRによる抽出結果
    """
    # ファイル形式チェック
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # 一時ファイル保存
    file_path = f"{settings.UPLOAD_DIR}/temp_gemini_ocr_{file.filename}"
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Gemini OCR実行
        result = await extract_text(image_path=file_path)
        
        # 結果を辞書形式に変換
        response_data = result.to_dict()
        
        # Gemini専用の追加情報
        response_data["ocr_engine"] = "gemini-2.0-flash"
        response_data["mode"] = "gemini_exclusive"
        
        if result.success:
            return JSONResponse(content=response_data)
        else:
            raise HTTPException(
                status_code=500, 
                detail=response_data
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini OCR processing error: {str(e)}")
    finally:
        # 一時ファイル削除
        if os.path.exists(file_path):
            os.remove(file_path)

@router.get("/status")
async def get_ocr_status():
    """
    Gemini OCRサービスの状態を取得するエンドポイント（Gemini専用モード）
    
    Returns:
        Gemini OCRの利用可能性と詳細ステータス
    """
    try:
        status = get_ocr_service_status()
        
        # Geminiサービスの状態を確認
        gemini_status = status.get("gemini", {"available": False})
        is_healthy = gemini_status["available"]
        
        response = {
            "status": "healthy" if is_healthy else "degraded",
            "ocr_engine": "gemini-2.0-flash",
            "mode": "gemini_exclusive",
            "gemini_available": is_healthy,
            "service_details": gemini_status,
            "features": [
                "japanese_menu_optimized",
                "high_precision_ocr", 
                "context_aware_extraction",
                "multimodal_understanding"
            ] if is_healthy else [],
            "recommendations": []
        }
        
        # 推奨事項を追加
        if not is_healthy:
            response["recommendations"] = [
                "Set GEMINI_API_KEY environment variable",
                "Install google-generativeai package: pip install google-generativeai",
                "Verify Gemini API key is valid and has proper permissions",
                "Check internet connectivity for Gemini API access"
            ]
        else:
            response["recommendations"] = [
                "Gemini OCR is ready for high-precision Japanese menu text extraction",
                "Upload clear, well-lit menu images for best results"
            ]
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini OCR status check error: {str(e)}")

# OCR プロバイダー情報エンドポイントは削除されました（パイプライン統合により不要）
# - /providers: パイプライン設定で統合

# OCR テストエンドポイントは削除されました（パイプライン統合により不要）
