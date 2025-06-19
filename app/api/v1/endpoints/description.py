from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List

from app.services.description import add_descriptions, get_description_service_status, get_supported_categories, get_description_features, get_example_descriptions

router = APIRouter()

class DescriptionRequest(BaseModel):
    """詳細説明リクエストモデル"""
    translated_data: Dict[str, List[Dict]]
    session_id: Optional[str] = None

class DescriptionResponse(BaseModel):
    """詳細説明レスポンスモデル"""
    success: bool
    final_menu: Dict[str, List[Dict]] = {}
    description_method: str = ""
    metadata: Dict = {}
    error: Optional[str] = None

@router.post("/add")
async def add_detailed_descriptions(request: DescriptionRequest):
    """
    OpenAIで翻訳されたメニューに詳細説明を追加するエンドポイント
    
    Args:
        request: 詳細説明リクエスト（translated_data, session_id）
        
    Returns:
        OpenAI 詳細説明生成結果
    """
    # 入力検証
    if not request.translated_data or not isinstance(request.translated_data, dict):
        raise HTTPException(
            status_code=400, 
            detail="Translated data is required and must be a dictionary"
        )
    
    # 翻訳データの妥当性チェック
    has_items = any(
        isinstance(items, list) and len(items) > 0 
        for items in request.translated_data.values()
    )
    
    if not has_items:
        raise HTTPException(
            status_code=400, 
            detail="At least one category must contain translated menu items"
        )
    
    # メニューアイテムの基本構造チェック
    valid_items = True
    for category, items in request.translated_data.items():
        for item in items:
            if not isinstance(item, dict):
                valid_items = False
                break
            # 必須フィールドのチェック
            required_fields = ["japanese_name", "english_name"]
            if not all(field in item and isinstance(item[field], str) for field in required_fields):
                valid_items = False
                break
        if not valid_items:
            break
    
    if not valid_items:
        raise HTTPException(
            status_code=400, 
            detail="Menu items must contain 'japanese_name' and 'english_name' fields"
        )
    
    try:
        # OpenAI詳細説明生成を実行
        result = await add_descriptions(request.translated_data, request.session_id)
        
        # 結果を辞書形式に変換
        response_data = result.to_dict()
        
        # 詳細説明エンジンの追加情報
        response_data["description_architecture"] = "openai_chunked_processing"
        
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
            detail=f"Description processing error: {str(e)}"
        )

@router.get("/status")
async def get_description_status():
    """
    詳細説明サービスの状態を取得するエンドポイント
    
    Returns:
        OpenAI 詳細説明サービスの利用可能性と詳細ステータス
    """
    try:
        status = get_description_service_status()
        
        # OpenAIサービスの状態を確認
        openai_status = status.get("openai", {"available": False})
        
        # 全体の健康状態を判定
        is_healthy = openai_status["available"]
        
        response = {
            "status": "healthy" if is_healthy else "unavailable",
            "description_architecture": "openai_chunked_processing",
            "primary_service": {
                "name": "OpenAI Description Generation",
                "available": openai_status["available"],
                "details": openai_status
            },
            "service_details": status,
            "features": [],
            "supported_categories": get_supported_categories(),
            "description_features": get_description_features(),
            "recommendations": []
        }
        
        # 機能リストを構築
        if openai_status["available"]:
            response["features"].extend([
                "openai_description_generation",
                "chunked_processing",
                "japanese_cuisine_expertise",
                "cultural_context_explanation",
                "tourist_friendly_descriptions",
                "real_time_progress"
            ])
        
        # 推奨事項を追加
        if not openai_status["available"]:
            response["recommendations"] = [
                "Set OPENAI_API_KEY environment variable",
                "Install required packages: openai",
                "Check OpenAI API access permissions and quotas",
                "Verify internet connectivity"
            ]
        else:
            response["recommendations"] = [
                "Description service is operational",
                "OpenAI handles detailed description generation with chunked processing",
                "Provide well-structured translated menu data for best results",
                "Use appropriate chunk sizes for optimal performance"
            ]
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Description status check error: {str(e)}"
        )

# 詳細説明 情報取得系エンドポイントは削除されました（パイプライン統合により不要）
# - /categories: パイプライン設定で統合
# - /features: パイプライン設定で統合  
# - /examples: パイプライン設定で統合

# 詳細説明 テストエンドポイントは削除されました（パイプライン統合により不要）
