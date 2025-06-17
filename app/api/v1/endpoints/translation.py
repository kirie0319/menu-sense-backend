from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List

from app.services.translation import translate_menu, get_translation_service_status, get_supported_languages, get_category_mapping

router = APIRouter()

class TranslationRequest(BaseModel):
    """翻訳リクエストモデル"""
    categorized_data: Dict[str, List[Dict]]
    session_id: Optional[str] = None

class TranslationResponse(BaseModel):
    """翻訳レスポンスモデル"""
    success: bool
    translated_categories: Dict[str, List[Dict]] = {}
    translation_method: str = ""
    metadata: Dict = {}
    error: Optional[str] = None

@router.post("/translate")
async def translate_categorized_menu(request: TranslationRequest):
    """
    Google Translateメイン、OpenAIフォールバックでメニューを翻訳するエンドポイント
    
    Args:
        request: 翻訳リクエスト（categorized_data, session_id）
        
    Returns:
        Google Translate + OpenAI フォールバック翻訳結果
    """
    # 入力検証
    if not request.categorized_data or not isinstance(request.categorized_data, dict):
        raise HTTPException(
            status_code=400, 
            detail="Categorized data is required and must be a dictionary"
        )
    
    # カテゴリデータの妥当性チェック
    has_items = any(
        isinstance(items, list) and len(items) > 0 
        for items in request.categorized_data.values()
    )
    
    if not has_items:
        raise HTTPException(
            status_code=400, 
            detail="At least one category must contain menu items"
        )
    
    try:
        # Google Translate + OpenAI フォールバック翻訳を実行
        result = await translate_menu(request.categorized_data, request.session_id)
        
        # 結果を辞書形式に変換
        response_data = result.to_dict()
        
        # 翻訳エンジンの追加情報
        response_data["translation_architecture"] = "google_translate_with_openai_fallback"
        
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
        raise HTTPException(
            status_code=500, 
            detail=f"Translation processing error: {str(e)}"
        )

@router.get("/status")
async def get_translation_status():
    """
    翻訳サービスの状態を取得するエンドポイント
    
    Returns:
        Google Translate + OpenAI 翻訳サービスの利用可能性と詳細ステータス
    """
    try:
        status = get_translation_service_status()
        
        # 各サービスの状態を確認
        google_status = status.get("google_translate", {"available": False})
        openai_status = status.get("openai", {"available": False})
        
        # 全体の健康状態を判定
        is_healthy = google_status["available"] or openai_status["available"]
        
        response = {
            "status": "healthy" if is_healthy else "degraded",
            "translation_architecture": "google_translate_with_openai_fallback",
            "primary_service": {
                "name": "Google Translate API",
                "available": google_status["available"],
                "details": google_status
            },
            "fallback_service": {
                "name": "OpenAI Function Calling",
                "available": openai_status["available"],
                "details": openai_status
            },
            "service_details": status,
            "features": [],
            "supported_languages": get_supported_languages(),
            "recommendations": []
        }
        
        # 機能リストを構築
        if google_status["available"]:
            response["features"].extend([
                "google_translate_primary_engine",
                "real_time_translation",
                "category_mapping",
                "html_entity_cleanup"
            ])
        
        if openai_status["available"]:
            response["features"].extend([
                "openai_fallback_engine",
                "function_calling_support",
                "japanese_cuisine_terminology",
                "batch_translation"
            ])
        
        # 推奨事項を追加
        if not google_status["available"] and not openai_status["available"]:
            response["recommendations"] = [
                "Set GOOGLE_CREDENTIALS_JSON environment variable",
                "Set OPENAI_API_KEY environment variable",
                "Install required packages: google-cloud-translate, openai",
                "Check API access permissions and quotas"
            ]
        elif not google_status["available"]:
            response["recommendations"] = [
                "Google Translate API not available - using OpenAI fallback only",
                "Configure Google Cloud credentials for optimal translation performance",
                "Check Google Cloud Translate API permissions"
            ]
        elif not openai_status["available"]:
            response["recommendations"] = [
                "OpenAI fallback not available - primary Google Translate only",
                "Configure OpenAI API key for redundancy",
                "Primary service should handle most requests successfully"
            ]
        else:
            response["recommendations"] = [
                "Translation services are fully operational",
                "Google Translate handles primary translation with OpenAI fallback",
                "Provide well-structured categorized menu data for best results"
            ]
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Translation status check error: {str(e)}"
        )

@router.get("/languages")
async def get_translation_languages():
    """
    サポートされている翻訳言語を取得
    
    Returns:
        サポートされている言語情報
    """
    try:
        languages = get_supported_languages()
        
        response = {
            "supported_languages": languages,
            "translation_architecture": "google_translate_with_openai_fallback",
            "language_features": {
                "primary_translation": "Google Translate API supports 100+ languages",
                "fallback_translation": "OpenAI supports major world languages",
                "specialty": "Optimized for Japanese menu translation to English"
            },
            "translation_quality": {
                "google_translate": "High accuracy for general translation",
                "openai_fallback": "Better understanding of Japanese cuisine terminology",
                "combined": "Best of both translation approaches"
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Language information error: {str(e)}"
        )

@router.get("/categories")
async def get_translation_categories():
    """
    翻訳で使用されるカテゴリマッピングを取得
    
    Returns:
        日本語→英語カテゴリマッピング情報
    """
    try:
        category_mapping = get_category_mapping()
        
        # カテゴリマッピングの詳細情報
        detailed_mapping = {}
        for japanese, english in category_mapping.items():
            detailed_mapping[japanese] = {
                "english": english,
                "translation_method": "predefined_mapping",
                "confidence": "high"
            }
        
        response = {
            "category_mapping": category_mapping,
            "detailed_mapping": detailed_mapping,
            "translation_architecture": "google_translate_with_openai_fallback",
            "mapping_strategy": {
                "primary": "Predefined category mappings for common Japanese menu categories",
                "fallback": "Google Translate API for unknown categories",
                "optimization": "Optimized for Japanese restaurant terminology"
            },
            "supported_categories": list(category_mapping.keys()),
            "features": {
                "predefined_mapping": True,
                "dynamic_translation": True,
                "cuisine_specialization": "Japanese",
                "accuracy_optimization": True
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Category mapping error: {str(e)}"
        )

@router.post("/test")
async def test_translation(request: TranslationRequest):
    """
    翻訳サービスのテスト用エンドポイント
    
    Args:
        request: テスト用翻訳リクエスト
        
    Returns:
        詳細なテスト結果と翻訳分析
    """
    # 入力検証
    if not request.categorized_data or not isinstance(request.categorized_data, dict):
        raise HTTPException(
            status_code=400, 
            detail="Test data is required and must be a dictionary"
        )
    
    try:
        # テスト開始時刻
        import time
        start_time = time.time()
        
        # 翻訳実行
        result = await translate_menu(request.categorized_data, request.session_id)
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        # 入力分析
        input_analysis = {
            "total_categories": len(request.categorized_data),
            "categories": list(request.categorized_data.keys()),
            "total_items": sum(len(items) for items in request.categorized_data.values()),
            "items_per_category": {
                category: len(items) 
                for category, items in request.categorized_data.items()
            }
        }
        
        # テスト結果を構築
        test_result = {
            "success": result.success,
            "translation_architecture": "google_translate_with_openai_fallback",
            "processing_time_seconds": processing_time,
            "input_analysis": input_analysis,
            "translated_categories": result.translated_categories,
            "translation_method": result.translation_method,
            "metadata": result.metadata,
            "performance": {}
        }
        
        if result.success:
            # 成功時の詳細分析
            output_analysis = {
                "categories_translated": len(result.translated_categories),
                "total_items_translated": sum(len(items) for items in result.translated_categories.values()),
                "translation_completeness": "complete" if len(result.translated_categories) == len(request.categorized_data) else "partial"
            }
            
            test_result["output_analysis"] = output_analysis
            test_result["performance"] = {
                "processing_speed": "fast" if processing_time < 10 else "medium" if processing_time < 30 else "slow",
                "translation_service": result.metadata.get("successful_service", "unknown"),
                "fallback_used": result.metadata.get("fallback_used", False),
                "translation_features": result.metadata.get("features", [])
            }
            
            # 翻訳品質評価
            if result.translation_method == "google_translate":
                test_result["evaluation"] = "excellent - primary Google Translate service used"
            elif result.translation_method == "openai_fallback":
                test_result["evaluation"] = "good - OpenAI fallback service used successfully"
            else:
                test_result["evaluation"] = "unknown - check translation method"
            
            # カテゴリマッピング分析
            category_mapping = get_category_mapping()
            mapped_categories = sum(1 for cat in request.categorized_data.keys() if cat in category_mapping)
            test_result["category_analysis"] = {
                "predefined_mappings_used": mapped_categories,
                "dynamic_translations": len(request.categorized_data) - mapped_categories,
                "mapping_efficiency": f"{mapped_categories}/{len(request.categorized_data)} categories pre-mapped"
            }
            
        else:
            # 失敗時の分析
            test_result["evaluation"] = "failed - translation could not be completed"
            test_result["error"] = result.error
            test_result["troubleshooting"] = result.metadata.get("suggestions", [])
            test_result["performance"] = {
                "processing_speed": "failed",
                "services_attempted": result.metadata.get("services_checked", []),
                "error_type": result.metadata.get("error_type", "unknown")
            }
        
        return JSONResponse(content=test_result)
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Translation test execution error: {str(e)}",
                "translation_architecture": "google_translate_with_openai_fallback",
                "evaluation": "error - test execution failed",
                "processing_time_seconds": 0
            }
        )
