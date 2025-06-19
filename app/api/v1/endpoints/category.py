from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

from app.services.category import categorize_menu, get_category_service_status, get_default_categories

router = APIRouter()

class CategorizationRequest(BaseModel):
    """カテゴリ分類リクエストモデル"""
    extracted_text: str
    session_id: Optional[str] = None

class CategorizationResponse(BaseModel):
    """カテゴリ分類レスポンスモデル"""
    success: bool
    categories: dict = {}
    uncategorized: list = []
    metadata: dict = {}
    error: Optional[str] = None

@router.post("/categorize")
async def categorize_menu_text(request: CategorizationRequest):
    """
    OpenAIでメニューテキストをカテゴリ分類するエンドポイント（OpenAI専用モード）
    
    Args:
        request: 分類リクエスト（extracted_text, session_id）
        
    Returns:
        OpenAIによるカテゴリ分類結果
    """
    # 入力検証
    if not request.extracted_text or not request.extracted_text.strip():
        raise HTTPException(
            status_code=400, 
            detail="Extracted text is required and cannot be empty"
        )
    
    if len(request.extracted_text.strip()) < 5:
        raise HTTPException(
            status_code=400, 
            detail="Extracted text must be at least 5 characters long"
        )
    
    try:
        # OpenAI カテゴリ分類を実行
        result = await categorize_menu(request.extracted_text, request.session_id)
        
        # 結果を辞書形式に変換
        response_data = result.to_dict()
        
        # OpenAI専用の追加情報
        response_data["categorization_engine"] = "openai-function-calling"
        response_data["mode"] = "openai_exclusive"
        
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
            detail=f"OpenAI categorization processing error: {str(e)}"
        )

@router.get("/status")
async def get_categorization_status():
    """
    OpenAIカテゴリ分類サービスの状態を取得するエンドポイント（OpenAI専用モード）
    
    Returns:
        OpenAIカテゴリ分類サービスの利用可能性と詳細ステータス
    """
    try:
        status = get_category_service_status()
        
        # OpenAIサービスの状態を確認
        openai_status = status.get("openai", {"available": False})
        is_healthy = openai_status["available"]
        
        response = {
            "status": "healthy" if is_healthy else "degraded",
            "categorization_engine": "openai-function-calling",
            "mode": "openai_exclusive",
            "openai_available": is_healthy,
            "service_details": openai_status,
            "features": [
                "japanese_menu_categorization",
                "function_calling_support", 
                "structured_output",
                "menu_item_extraction",
                "price_detection"
            ] if is_healthy else [],
            "default_categories": get_default_categories(),
            "recommendations": []
        }
        
        # 推奨事項を追加
        if not is_healthy:
            response["recommendations"] = [
                "Set OPENAI_API_KEY environment variable",
                "Install openai package: pip install openai",
                "Verify OpenAI API key has proper permissions",
                "Check OpenAI service status and quotas"
            ]
        else:
            response["recommendations"] = [
                "OpenAI categorization is ready for Japanese menu text analysis",
                "Provide clear, well-structured menu text for best results",
                "Ensure text contains recognizable menu items and prices"
            ]
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"OpenAI categorization status check error: {str(e)}"
        )

# カテゴライズ 情報取得系エンドポイントは削除されました（パイプライン統合により不要）
# - /categories: パイプライン設定で統合

# カテゴライズ テストエンドポイントは削除されました（パイプライン統合により不要）
