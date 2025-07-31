"""
Service Endpoints - Individual Service Testing
各サービスの単体エンドポイント（OCR、Mapping、Categorize）
"""
import time
from typing import Dict, Any, List
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query, Body
from fastapi.responses import JSONResponse

from app_2.services.ocr_service import get_ocr_service
from app_2.services.mapping_service import get_menu_mapping_categorize_service
from app_2.services.categorize_service import get_categorize_service
from app_2.utils.logger import get_logger

logger = get_logger("service_endpoints")

router = APIRouter(prefix="/service", tags=["service"])


@router.post("/ocr", response_model=Dict[str, Any])
async def extract_text_from_image(
    file: UploadFile = File(..., description="画像ファイル (JPEG, PNG, WEBP対応)"),
    level: str = Query("paragraph", description="抽出レベル: 'word' または 'paragraph'")
) -> JSONResponse:
    """
    画像からテキストを抽出（OCR処理）
    """
    start_time = time.time()
    
    try:
        logger.info(f"🔍 OCR processing started: file={file.filename}, level={level}")
        
        # ファイル形式チェック
        if not file.content_type or not file.content_type.startswith('image/'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {file.content_type}. Only image files are supported."
            )
        
        # 画像データ読み込み
        image_data = await file.read()
        
        if not image_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded"
            )
        
        # OCR処理実行
        ocr_service = get_ocr_service()
        ocr_results = await ocr_service.extract_text_with_positions(
            image_data=image_data,
            level=level,
            max_retries=2
        )
        
        processing_time = time.time() - start_time
        
        # 成功レスポンス
        response_data = {
            "status": "success",
            "results": ocr_results,
            "total_elements": len(ocr_results),
            "processing_time": round(processing_time, 3)
        }
        
        logger.info(f"✅ OCR completed: {len(ocr_results)} elements in {processing_time:.3f}s")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        logger.error(f"❌ OCR failed after {processing_time:.3f}s: {e}")
        
        error_response = {
            "status": "error",
            "error_message": str(e),
            "processing_time": round(processing_time, 3)
        }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )


@router.post("/mapping", response_model=Dict[str, Any])
async def format_mapping_data(
    ocr_results: List[Dict[str, Any]] = Body(..., description="OCR結果のリスト")
) -> JSONResponse:
    """
    OCR結果をマッピング用にフォーマット
    
    OCR結果の位置情報を使用してマッピングデータを整形します。
    パイプラインと同じロジックを使用（DB保存・SSE配信なし）
    """
    start_time = time.time()
    
    try:
        logger.info(f"🗺️ Mapping processing started: {len(ocr_results)} elements")
        
        # 入力データ検証
        if not ocr_results:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OCR results are empty"
            )
        
        # OCR結果の形式検証
        for i, result in enumerate(ocr_results):
            if not all(key in result for key in ["text", "x_center", "y_center"]):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid OCR result format at index {i}. Required keys: text, x_center, y_center"
                )
        
        # マッピングサービス実行（パイプラインと同じロジック）
        mapping_service = get_menu_mapping_categorize_service()
        formatted_mapping_data = mapping_service._format_mapping_data(ocr_results)
        
        processing_time = time.time() - start_time
        
        # 成功レスポンス
        response_data = {
            "status": "success",
            "formatted_data": formatted_mapping_data,
            "input_elements": len(ocr_results),
            "formatted_data_length": len(formatted_mapping_data),
            "processing_time": round(processing_time, 3)
        }
        
        logger.info(f"✅ Mapping completed: {len(ocr_results)} elements → {len(formatted_mapping_data)} chars in {processing_time:.3f}s")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        logger.error(f"❌ Mapping failed after {processing_time:.3f}s: {e}")
        
        error_response = {
            "status": "error",
            "error_message": str(e),
            "processing_time": round(processing_time, 3)
        }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )


@router.post("/categorize", response_model=Dict[str, Any])
async def categorize_menu_structure(
    mapping_data: str = Body(..., description="フォーマット済みマッピングデータ"),
    level: str = Body("paragraph", description="データレベル")
) -> JSONResponse:
    """
    マッピングデータをカテゴライズ
    
    OpenAI APIを使用してメニュー構造を分析・カテゴライズします。
    パイプラインと同じロジックを使用（DB保存・SSE配信なし）
    """
    start_time = time.time()
    
    try:
        logger.info(f"🏷️ Categorize processing started: {len(mapping_data)} chars, level={level}")
        
        # 入力データ検証
        if not mapping_data or not mapping_data.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mapping data is empty"
            )
        
        if level not in ["word", "paragraph"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Level must be 'word' or 'paragraph'"
            )
        
        # カテゴライズサービス実行（パイプラインと同じロジック）
        categorize_service = get_categorize_service()
        categorize_results = await categorize_service.categorize_menu_structure(
            mapping_data, level
        )
        
        processing_time = time.time() - start_time
        
        # カテゴリ統計の抽出
        categories_found = []
        total_items = 0
        
        if "menu" in categorize_results and "categories" in categorize_results["menu"]:
            categories_data = categorize_results["menu"]["categories"]
            for cat in categories_data:
                category_info = {
                    "name": cat.get("name", "unknown"),
                    "japanese_name": cat.get("japanese_name", ""),
                    "items_count": len(cat.get("items", []))
                }
                categories_found.append(category_info)
                total_items += category_info["items_count"]
        
        # 成功レスポンス
        response_data = {
            "status": "success",
            "categorize_results": categorize_results,
            "categories_found": categories_found,
            "total_categories": len(categories_found),
            "total_menu_items": total_items,
            "input_data_length": len(mapping_data),
            "processing_time": round(processing_time, 3)
        }
        
        logger.info(f"✅ Categorize completed: {len(categories_found)} categories, {total_items} items in {processing_time:.3f}s")
        return JSONResponse(content=response_data)
        
    except HTTPException:
        raise
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        logger.error(f"❌ Categorize failed after {processing_time:.3f}s: {e}")
        
        error_response = {
            "status": "error",
            "error_message": str(e),
            "processing_time": round(processing_time, 3)
        }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )
