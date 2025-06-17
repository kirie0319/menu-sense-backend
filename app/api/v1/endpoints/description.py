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

@router.get("/categories")
async def get_description_categories():
    """
    詳細説明でサポートされているカテゴリを取得
    
    Returns:
        サポートされているメニューカテゴリ情報
    """
    try:
        categories = get_supported_categories()
        
        response = {
            "supported_categories": categories,
            "description_architecture": "openai_chunked_processing",
            "category_features": {
                "japanese_categories": ["前菜", "メイン", "ドリンク", "デザート"],
                "english_categories": ["Appetizers", "Main Dishes", "Drinks", "Desserts"],
                "multilingual_support": "Handles both Japanese and English category names",
                "custom_categories": "Supports additional custom categories"
            },
            "description_quality": {
                "cultural_context": "Includes Japanese cultural background",
                "tourist_friendly": "Optimized for foreign visitors",
                "detailed_explanation": "Covers cooking methods, ingredients, and flavors"
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Categories information error: {str(e)}"
        )

@router.get("/features")
async def get_description_feature_list():
    """
    詳細説明の特徴一覧を取得
    
    Returns:
        詳細説明に含まれる特徴情報
    """
    try:
        features = get_description_features()
        
        response = {
            "description_features": features,
            "description_architecture": "openai_chunked_processing",
            "feature_details": {
                "cooking_methods": "Explains how the dish is prepared (grilled, fried, steamed, etc.)",
                "ingredients": "Lists main ingredients and their characteristics",
                "flavor_profiles": "Describes taste, texture, and sensory experience",
                "cultural_background": "Provides context about the dish's origin and significance",
                "serving_suggestions": "Mentions how the dish is typically served or enjoyed"
            },
            "quality_metrics": {
                "length": "30-80 words per description",
                "language_level": "Tourist-friendly English",
                "accuracy": "Culturally accurate and informative",
                "appeal": "Designed to attract and inform international visitors"
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Features information error: {str(e)}"
        )

@router.get("/examples")
async def get_description_examples():
    """
    詳細説明の例を取得
    
    Returns:
        説明例とその特徴
    """
    try:
        examples = get_example_descriptions()
        
        response = {
            "description_examples": examples,
            "description_architecture": "openai_chunked_processing",
            "example_analysis": {},
            "quality_guidelines": {
                "structure": "Dish type + cooking method + key ingredients + cultural context",
                "tone": "Informative yet appealing to tourists",
                "length": "Approximately 30-80 words",
                "focus": "Highlights what makes each dish unique and appealing"
            }
        }
        
        # 例の分析を追加
        for dish, description in examples.items():
            word_count = len(description.split())
            response["example_analysis"][dish] = {
                "word_count": word_count,
                "has_cooking_method": any(method in description.lower() for method in ["grilled", "fried", "steamed", "boiled"]),
                "has_cultural_context": "traditional" in description.lower() or "japanese" in description.lower(),
                "mentions_ingredients": any(ingredient in description.lower() for ingredient in ["chicken", "vegetables", "seafood", "rice"])
            }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Examples information error: {str(e)}"
        )

@router.post("/test")
async def test_description_generation(request: DescriptionRequest):
    """
    詳細説明生成のテスト用エンドポイント
    
    Args:
        request: テスト用詳細説明リクエスト
        
    Returns:
        詳細なテスト結果と生成分析
    """
    # 入力検証
    if not request.translated_data or not isinstance(request.translated_data, dict):
        raise HTTPException(
            status_code=400, 
            detail="Test data is required and must be a dictionary"
        )
    
    try:
        # テスト開始時刻
        import time
        start_time = time.time()
        
        # 詳細説明生成実行
        result = await add_descriptions(request.translated_data, request.session_id)
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        # 入力分析
        input_analysis = {
            "total_categories": len(request.translated_data),
            "categories": list(request.translated_data.keys()),
            "total_items": sum(len(items) for items in request.translated_data.values()),
            "items_per_category": {
                category: len(items) 
                for category, items in request.translated_data.items()
            }
        }
        
        # テスト結果を構築
        test_result = {
            "success": result.success,
            "description_architecture": "openai_chunked_processing",
            "processing_time_seconds": processing_time,
            "input_analysis": input_analysis,
            "final_menu": result.final_menu,
            "description_method": result.description_method,
            "metadata": result.metadata,
            "performance": {}
        }
        
        if result.success:
            # 成功時の詳細分析
            output_analysis = {
                "categories_processed": len(result.final_menu),
                "total_descriptions_added": sum(len(items) for items in result.final_menu.values()),
                "descriptions_with_content": sum(
                    1 for items in result.final_menu.values() 
                    for item in items 
                    if item.get("description") and len(item["description"]) > 10
                ),
                "processing_completeness": "complete" if len(result.final_menu) == len(request.translated_data) else "partial"
            }
            
            test_result["output_analysis"] = output_analysis
            test_result["performance"] = {
                "processing_speed": "fast" if processing_time < 20 else "medium" if processing_time < 60 else "slow",
                "description_service": result.metadata.get("successful_service", "unknown"),
                "chunked_processing": result.metadata.get("features", []),
                "items_per_second": round(output_analysis["total_descriptions_added"] / processing_time, 2) if processing_time > 0 else 0
            }
            
            # 説明品質評価
            if result.description_method == "openai":
                test_result["evaluation"] = "excellent - OpenAI description generation completed successfully"
            else:
                test_result["evaluation"] = "unknown - check description method"
            
            # 説明内容分析
            description_analysis = {
                "average_description_length": 0,
                "descriptions_with_cultural_context": 0,
                "descriptions_with_cooking_methods": 0
            }
            
            total_descriptions = 0
            total_length = 0
            
            for items in result.final_menu.values():
                for item in items:
                    description = item.get("description", "")
                    if description:
                        total_descriptions += 1
                        total_length += len(description.split())
                        
                        if "traditional" in description.lower() or "japanese" in description.lower():
                            description_analysis["descriptions_with_cultural_context"] += 1
                        
                        if any(method in description.lower() for method in ["grilled", "fried", "steamed", "boiled", "roasted"]):
                            description_analysis["descriptions_with_cooking_methods"] += 1
            
            if total_descriptions > 0:
                description_analysis["average_description_length"] = round(total_length / total_descriptions, 1)
            
            test_result["description_analysis"] = description_analysis
            
        else:
            # 失敗時の分析
            test_result["evaluation"] = "failed - description generation could not be completed"
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
                "error": f"Description test execution error: {str(e)}",
                "description_architecture": "openai_chunked_processing",
                "evaluation": "error - test execution failed",
                "processing_time_seconds": 0
            }
        )
