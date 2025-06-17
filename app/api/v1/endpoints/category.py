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

@router.get("/categories")
async def get_supported_categories():
    """
    サポートされているカテゴリリストを取得
    
    Returns:
        デフォルトのカテゴリ情報
    """
    try:
        default_categories = get_default_categories()
        
        # カテゴリの詳細情報
        category_details = {
            "前菜": {
                "english": "Appetizers",
                "description": "小皿料理、前菜、おつまみ",
                "examples": ["サラダ", "刺身", "冷奴", "枝豆"]
            },
            "メイン": {
                "english": "Main Dishes", 
                "description": "主菜、メイン料理",
                "examples": ["ステーキ", "パスタ", "カレー", "定食"]
            },
            "ドリンク": {
                "english": "Drinks",
                "description": "飲み物、アルコール・ノンアルコール",
                "examples": ["ビール", "ワイン", "ソフトドリンク", "コーヒー"]
            },
            "デザート": {
                "english": "Desserts",
                "description": "デザート、甘味",
                "examples": ["ケーキ", "アイス", "プリン", "和菓子"]
            }
        }
        
        response = {
            "default_categories": default_categories,
            "category_details": category_details,
            "categorization_engine": "openai-function-calling",
            "mode": "openai_exclusive",
            "features": {
                "automatic_detection": True,
                "price_extraction": True,
                "flexible_categorization": True,
                "uncategorized_handling": True
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Category information error: {str(e)}"
        )

@router.post("/test")
async def test_categorization(request: CategorizationRequest):
    """
    OpenAIカテゴリ分類のテスト用エンドポイント（OpenAI専用モード）
    
    Args:
        request: テスト用分類リクエスト
        
    Returns:
        OpenAIカテゴリ分類の詳細なテスト結果
    """
    # 入力検証
    if not request.extracted_text or not request.extracted_text.strip():
        raise HTTPException(
            status_code=400, 
            detail="Test text is required and cannot be empty"
        )
    
    try:
        # テスト開始時刻
        import time
        start_time = time.time()
        
        # OpenAI カテゴリ分類を実行
        result = await categorize_menu(request.extracted_text, request.session_id)
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        # テスト結果を構築
        test_result = {
            "success": result.success,
            "categorization_engine": "openai-function-calling",
            "mode": "openai_exclusive",
            "processing_time_seconds": processing_time,
            "input_text_length": len(request.extracted_text),
            "categories": result.categories,
            "uncategorized": result.uncategorized,
            "metadata": result.metadata,
            "performance": {
                "categories_found": len(result.categories) if result.success else 0,
                "total_items": sum(len(items) for items in result.categories.values()) if result.success else 0,
                "uncategorized_items": len(result.uncategorized) if result.success else 0,
                "processing_speed": "fast" if processing_time < 5 else "medium" if processing_time < 15 else "slow",
                "openai_optimizations": [
                    "function_calling_structured_output",
                    "japanese_menu_understanding", 
                    "price_extraction",
                    "category_intelligence"
                ] if result.success else []
            }
        }
        
        if not result.success:
            test_result["error"] = result.error
            test_result["troubleshooting"] = result.metadata.get("suggestions", [])
        
        # OpenAI特化の評価
        if result.success:
            total_items = sum(len(items) for items in result.categories.values())
            categories_count = len(result.categories)
            
            if total_items > 10 and categories_count >= 3:
                test_result["evaluation"] = "excellent - comprehensive categorization"
            elif total_items > 5 and categories_count >= 2:
                test_result["evaluation"] = "good - substantial categorization"
            elif total_items > 0:
                test_result["evaluation"] = "moderate - partial categorization"
            else:
                test_result["evaluation"] = "limited - minimal categorization"
            
            # メニュー特化の分析
            menu_indicators = ["円", "¥", "価格", "料理", "飲み物", "ドリンク"]
            has_menu_indicators = any(indicator in request.extracted_text for indicator in menu_indicators)
            test_result["menu_analysis"] = {
                "likely_menu_content": has_menu_indicators,
                "analysis": "Text appears to contain menu-related content" if has_menu_indicators else "Text may not be menu-related",
                "price_detection": any("price" in str(item).lower() for category_items in result.categories.values() for item in category_items),
                "structure_quality": "good" if categories_count >= 3 else "basic"
            }
        else:
            test_result["evaluation"] = "failed - no categorization performed"
            test_result["menu_analysis"] = {
                "likely_menu_content": False, 
                "analysis": "Cannot analyze - categorization failed"
            }
        
        return JSONResponse(content=test_result)
        
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"OpenAI categorization test execution error: {str(e)}",
                "categorization_engine": "openai-function-calling",
                "mode": "openai_exclusive",
                "input_text_length": len(request.extracted_text),
                "evaluation": "error - test execution failed"
            }
        )
