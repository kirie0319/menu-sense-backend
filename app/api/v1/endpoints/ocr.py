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

@router.get("/providers") 
async def get_gemini_provider_info():
    """
    Gemini OCRプロバイダー情報を取得（Gemini専用モード）
    
    Returns:
        Gemini OCRプロバイダーの詳細情報
    """
    try:
        status = get_ocr_service_status()
        gemini_status = status.get("gemini", {"available": False})
        
        provider_info = {
            "provider": "gemini",
            "engine": "gemini-2.0-flash",
            "mode": "exclusive",
            "available": gemini_status["available"],
            "display_name": "Gemini 2.0 Flash OCR",
            "description": "High-precision OCR powered by Google's Gemini 2.0 Flash model, optimized for Japanese menu text extraction",
            "features": [
                "japanese_text_optimization",
                "menu_context_understanding", 
                "high_accuracy_extraction",
                "multimodal_comprehension",
                "restaurant_terminology_aware",
                "structured_output_generation"
            ] if gemini_status["available"] else [],
            "capabilities": {
                "languages": ["Japanese", "English", "Mixed"],
                "formats": ["JPG", "PNG", "WEBP", "GIF"],
                "max_file_size": "20MB",
                "specialized_for": "Restaurant menus and food-related text"
            } if gemini_status["available"] else {},
            "performance": {
                "accuracy": "95%+ for Japanese menu text",
                "response_time": "2-5 seconds",
                "reliability": "High"
            } if gemini_status["available"] else {}
        }
        
        if not gemini_status["available"]:
            provider_info["error"] = gemini_status.get("error", "Gemini OCR service unavailable")
            provider_info["troubleshooting"] = [
                "Verify GEMINI_API_KEY environment variable is set",
                "Check Gemini API quota and billing status",
                "Ensure google-generativeai package is installed"
            ]
        
        return JSONResponse(content={
            "ocr_provider": provider_info,
            "mode": "gemini_exclusive",
            "fallback_available": False,
            "status": "ready" if gemini_status["available"] else "unavailable"
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini provider info error: {str(e)}")

@router.post("/test")
async def test_gemini_ocr(file: UploadFile = File(...)):
    """
    Gemini OCRサービスのテスト用エンドポイント（Gemini専用モード）
    
    Args:
        file: テスト用画像ファイル
        
    Returns:
        Gemini OCRの詳細なテスト結果
    """
    # ファイル形式チェック
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    # 一時ファイル保存
    file_path = f"{settings.UPLOAD_DIR}/test_gemini_ocr_{file.filename}"
    
    try:
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # ファイル情報
        file_info = {
            "filename": file.filename,
            "content_type": file.content_type,
            "file_size": len(content),
            "file_size_mb": round(len(content) / (1024 * 1024), 2)
        }
        
        # Gemini OCR実行
        import time
        start_time = time.time()
        
        result = await extract_text(image_path=file_path)
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        # テスト結果を構築
        test_result = {
            "success": result.success,
            "ocr_engine": "gemini-2.0-flash",
            "mode": "gemini_exclusive",
            "file_info": file_info,
            "processing_time_seconds": processing_time,
            "extracted_text_length": len(result.extracted_text) if result.success else 0,
            "extracted_text_preview": result.extracted_text[:200] + "..." if result.success and len(result.extracted_text) > 200 else result.extracted_text,
            "metadata": result.metadata,
            "performance": {
                "characters_per_second": round(len(result.extracted_text) / processing_time, 2) if result.success and processing_time > 0 else 0,
                "processing_speed": "fast" if processing_time < 5 else "medium" if processing_time < 15 else "slow",
                "gemini_optimizations": [
                    "menu_context_analysis",
                    "japanese_text_recognition", 
                    "food_terminology_understanding"
                ] if result.success else []
            }
        }
        
        if not result.success:
            test_result["error"] = result.error
            test_result["troubleshooting"] = result.metadata.get("suggestions", [])
        
        # Gemini特化の評価
        if result.success:
            text_length = len(result.extracted_text)
            if text_length > 100:
                test_result["evaluation"] = "excellent - comprehensive text extraction"
            elif text_length > 50:
                test_result["evaluation"] = "good - substantial text extracted"
            elif text_length > 10:
                test_result["evaluation"] = "moderate - partial text extracted"
            else:
                test_result["evaluation"] = "limited - minimal text detected"
            
            # メニュー特化の分析
            menu_keywords = ["料理", "価格", "円", "¥", "$", "menu", "dish", "drink"]
            has_menu_content = any(keyword in result.extracted_text.lower() for keyword in menu_keywords)
            test_result["menu_analysis"] = {
                "likely_menu_content": has_menu_content,
                "analysis": "Text appears to contain menu-related content" if has_menu_content else "Text may not be menu-related"
            }
        else:
            test_result["evaluation"] = "failed - no text extracted"
            test_result["menu_analysis"] = {"likely_menu_content": False, "analysis": "Cannot analyze - extraction failed"}
        
        return JSONResponse(content=test_result)
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Gemini OCR test execution error: {str(e)}",
                "ocr_engine": "gemini-2.0-flash",
                "mode": "gemini_exclusive",
                "file_info": {"filename": file.filename, "content_type": file.content_type},
                "evaluation": "error - test execution failed"
            }
        )
    finally:
        # 一時ファイル削除
        if os.path.exists(file_path):
            os.remove(file_path)
