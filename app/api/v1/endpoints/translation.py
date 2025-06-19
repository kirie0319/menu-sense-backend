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

# 翻訳 情報取得系エンドポイントは削除されました（パイプライン統合により不要）
# - /languages: パイプライン設定で統合  
# - /categories: パイプライン設定で統合

# 翻訳 テストエンドポイントは削除されました（パイプライン統合により不要）
