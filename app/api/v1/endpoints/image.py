from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List

from app.services.image import generate_images, get_image_service_status, get_supported_categories, get_image_features, get_category_styles, get_supported_styles, combine_menu_with_images

router = APIRouter()

class ImageGenerationRequest(BaseModel):
    """画像生成リクエストモデル"""
    final_menu: Dict[str, List[Dict]]
    session_id: Optional[str] = None

class ImageGenerationResponse(BaseModel):
    """画像生成レスポンスモデル"""
    success: bool
    images_generated: Dict[str, List[Dict]] = {}
    total_images: int = 0
    total_items: int = 0
    image_method: str = ""
    metadata: Dict = {}
    error: Optional[str] = None

@router.post("/generate")
async def generate_menu_images(request: ImageGenerationRequest):
    """
    Imagen 3で詳細説明付きメニューの画像を生成するエンドポイント
    
    Args:
        request: 画像生成リクエスト（final_menu, session_id）
        
    Returns:
        Imagen 3 画像生成結果
    """
    # 入力検証
    if not request.final_menu or not isinstance(request.final_menu, dict):
        raise HTTPException(
            status_code=400, 
            detail="Final menu data is required and must be a dictionary"
        )
    
    # メニューデータの妥当性チェック
    has_items = any(
        isinstance(items, list) and len(items) > 0 
        for items in request.final_menu.values()
    )
    
    if not has_items:
        raise HTTPException(
            status_code=400, 
            detail="At least one category must contain menu items with descriptions"
        )
    
    # メニューアイテムの基本構造チェック
    valid_items = True
    for category, items in request.final_menu.items():
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
        # Imagen 3画像生成を実行
        result = await generate_images(request.final_menu, request.session_id)
        
        # 結果を辞書形式に変換
        response_data = result.to_dict()
        
        # 画像生成エンジンの追加情報
        response_data["image_architecture"] = "imagen3_food_photography"
        
        # スキップされた場合も成功として扱う（画像生成はオプショナル）
        if result.success:
            return JSONResponse(content=response_data)
        else:
            # エラーの場合は詳細情報を含めて500エラー
            raise HTTPException(
                status_code=500, 
                detail=response_data
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Image generation processing error: {str(e)}"
        )

@router.get("/status")
async def get_image_generation_status():
    """
    画像生成サービスの状態を取得するエンドポイント
    
    Returns:
        Imagen 3 画像生成サービスの利用可能性と詳細ステータス
    """
    try:
        status = get_image_service_status()
        
        # Imagen 3サービスの状態を確認
        imagen3_status = status.get("imagen3", {"available": False})
        
        # 全体の健康状態を判定
        is_healthy = imagen3_status["available"]
        
        response = {
            "status": "healthy" if is_healthy else "unavailable",
            "image_architecture": "imagen3_food_photography",
            "primary_service": {
                "name": "Imagen 3 Image Generation",
                "available": imagen3_status["available"],
                "details": imagen3_status
            },
            "service_details": status,
            "features": [],
            "supported_categories": get_supported_categories(),
            "image_features": get_image_features(),
            "recommendations": []
        }
        
        # 機能リストを構築
        if imagen3_status["available"]:
            response["features"].extend([
                "imagen3_image_generation",
                "professional_food_photography",
                "japanese_cuisine_focus",
                "category_specific_styling",
                "high_quality_generation",
                "real_time_progress"
            ])
        
        # 推奨事項を追加
        if not imagen3_status["available"]:
            response["recommendations"] = [
                "Set GEMINI_API_KEY environment variable",
                "Install required packages: google-genai, pillow",
                "Enable IMAGE_GENERATION_ENABLED in settings",
                "Check Imagen 3 API access permissions and quotas",
                "Verify internet connectivity"
            ]
        else:
            response["recommendations"] = [
                "Image generation service is operational",
                "Imagen 3 handles professional food photography generation",
                "Provide well-structured menu data with descriptions for best results",
                "Use detailed descriptions for more accurate image generation"
            ]
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Image generation status check error: {str(e)}"
        )

@router.get("/categories")
async def get_image_categories():
    """
    画像生成でサポートされているカテゴリを取得
    
    Returns:
        サポートされているメニューカテゴリ情報
    """
    try:
        categories = get_supported_categories()
        
        response = {
            "supported_categories": categories,
            "image_architecture": "imagen3_food_photography",
            "category_features": {
                "japanese_categories": ["前菜", "メイン", "ドリンク", "デザート"],
                "english_categories": ["Appetizers", "Main Dishes", "Drinks", "Desserts"],
                "multilingual_support": "Handles both Japanese and English category names",
                "custom_categories": "Supports additional custom categories"
            },
            "image_quality": {
                "professional_photography": "High-quality restaurant photography style",
                "category_specific_styling": "Each category has optimized visual presentation",
                "japanese_cuisine_focus": "Specialized for Japanese food aesthetics"
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Categories information error: {str(e)}"
        )

@router.get("/styles")
async def get_image_styles():
    """
    画像生成のスタイル一覧を取得
    
    Returns:
        サポートされているスタイル情報
    """
    try:
        styles = get_supported_styles()
        category_styles = get_category_styles()
        
        response = {
            "supported_styles": styles,
            "category_styles": category_styles,
            "image_architecture": "imagen3_food_photography",
            "style_details": {
                "professional_lighting": "Studio-quality lighting for appetizing appearance",
                "category_specific_presentation": "Tailored presentation for each food category",
                "japanese_aesthetic": "Traditional and modern Japanese food presentation",
                "clean_background": "Neutral backgrounds that highlight the food"
            },
            "technical_specifications": {
                "aspect_ratio": "1:1 (square format)",
                "image_format": "PNG with transparency support",
                "quality": "High resolution restaurant photography",
                "lighting": "Professional studio lighting"
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Styles information error: {str(e)}"
        )

@router.get("/features")
async def get_image_feature_list():
    """
    画像生成の特徴一覧を取得
    
    Returns:
        画像生成に含まれる特徴情報
    """
    try:
        features = get_image_features()
        
        response = {
            "image_features": features,
            "image_architecture": "imagen3_food_photography",
            "feature_details": {
                "professional_lighting": "Studio-quality lighting that makes food look appetizing",
                "appetizing_appearance": "Optimized color and presentation for food appeal",
                "clean_background": "Neutral backgrounds that don't distract from the food",
                "high_quality_photography": "Restaurant-grade image quality",
                "category_specific_styling": "Tailored presentation for appetizers, mains, drinks, desserts"
            },
            "quality_metrics": {
                "resolution": "High resolution suitable for digital menus",
                "color_accuracy": "True-to-life food colors",
                "composition": "Professional food photography composition",
                "consistency": "Consistent style across all generated images"
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Features information error: {str(e)}"
        )

@router.post("/combine")
async def combine_menu_and_images(request: dict):
    """
    メニューデータと生成された画像を統合
    
    Args:
        request: final_menu と images_generated を含む辞書
        
    Returns:
        統合されたメニューデータ
    """
    # 入力検証
    if not isinstance(request, dict):
        raise HTTPException(
            status_code=400, 
            detail="Request must be a dictionary"
        )
    
    final_menu = request.get("final_menu")
    images_generated = request.get("images_generated")
    
    if not final_menu or not isinstance(final_menu, dict):
        raise HTTPException(
            status_code=400, 
            detail="final_menu is required and must be a dictionary"
        )
    
    if not images_generated or not isinstance(images_generated, dict):
        raise HTTPException(
            status_code=400, 
            detail="images_generated is required and must be a dictionary"
        )
    
    try:
        # メニューと画像を統合
        combined_menu = combine_menu_with_images(final_menu, images_generated)
        
        # 統計情報を生成
        total_items = sum(len(items) for items in final_menu.values())
        items_with_images = sum(
            1 for items in combined_menu.values() 
            for item in items 
            if item.get("image_generated")
        )
        
        response = {
            "success": True,
            "combined_menu": combined_menu,
            "image_architecture": "imagen3_food_photography",
            "statistics": {
                "total_items": total_items,
                "items_with_images": items_with_images,
                "items_without_images": total_items - items_with_images,
                "image_coverage_percent": round((items_with_images / total_items) * 100, 2) if total_items > 0 else 0
            },
            "integration_features": [
                "image_url_mapping",
                "generation_status_tracking",
                "prompt_preservation",
                "error_information_inclusion"
            ]
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Menu and image combination error: {str(e)}"
        )

@router.post("/test")
async def test_image_generation(request: ImageGenerationRequest):
    """
    画像生成のテスト用エンドポイント
    
    Args:
        request: テスト用画像生成リクエスト
        
    Returns:
        詳細なテスト結果と生成分析
    """
    # 入力検証
    if not request.final_menu or not isinstance(request.final_menu, dict):
        raise HTTPException(
            status_code=400, 
            detail="Test data is required and must be a dictionary"
        )
    
    try:
        # テスト開始時刻
        import time
        start_time = time.time()
        
        # 画像生成実行
        result = await generate_images(request.final_menu, request.session_id)
        
        end_time = time.time()
        processing_time = round(end_time - start_time, 2)
        
        # 入力分析
        input_analysis = {
            "total_categories": len(request.final_menu),
            "categories": list(request.final_menu.keys()),
            "total_items": sum(len(items) for items in request.final_menu.values()),
            "items_per_category": {
                category: len(items) 
                for category, items in request.final_menu.items()
            },
            "items_with_descriptions": sum(
                1 for items in request.final_menu.values() 
                for item in items 
                if item.get("description") and len(item["description"]) > 10
            )
        }
        
        # テスト結果を構築
        test_result = {
            "success": result.success,
            "image_architecture": "imagen3_food_photography",
            "processing_time_seconds": processing_time,
            "input_analysis": input_analysis,
            "images_generated": result.images_generated,
            "total_images": result.total_images,
            "image_method": result.image_method,
            "metadata": result.metadata,
            "performance": {}
        }
        
        if result.success:
            # 成功時の詳細分析
            output_analysis = {
                "categories_processed": len(result.images_generated),
                "total_images_generated": result.total_images,
                "successful_images": result.total_images,
                "failed_images": result.total_items - result.total_images if result.total_items > 0 else 0,
                "processing_completeness": "complete" if len(result.images_generated) == len(request.final_menu) else "partial"
            }
            
            test_result["output_analysis"] = output_analysis
            test_result["performance"] = {
                "processing_speed": "fast" if processing_time < 30 else "medium" if processing_time < 120 else "slow",
                "image_service": result.metadata.get("successful_service", "unknown"),
                "generation_features": result.metadata.get("features", []),
                "images_per_minute": round((result.total_images * 60) / processing_time, 2) if processing_time > 0 else 0
            }
            
            # 画像生成品質評価
            if result.image_method == "imagen3":
                if result.total_images > 0:
                    test_result["evaluation"] = "excellent - Imagen 3 image generation completed successfully"
                else:
                    skipped_reason = result.metadata.get("skipped_reason", "Unknown reason")
                    test_result["evaluation"] = f"skipped - {skipped_reason}"
            else:
                test_result["evaluation"] = "unknown - check image generation method"
            
            # 画像内容分析
            if result.images_generated:
                image_analysis = {
                    "categories_with_images": len([cat for cat, imgs in result.images_generated.items() if imgs]),
                    "average_images_per_category": 0,
                    "categories_analysis": {}
                }
                
                total_categories_with_images = 0
                total_images_count = 0
                
                for category, images in result.images_generated.items():
                    if images:
                        total_categories_with_images += 1
                        successful_in_category = sum(1 for img in images if img.get("generation_success", img.get("image_url") is not None))
                        total_images_count += len(images)
                        
                        image_analysis["categories_analysis"][category] = {
                            "total_items": len(images),
                            "successful_images": successful_in_category,
                            "success_rate": round((successful_in_category / len(images)) * 100, 2) if len(images) > 0 else 0
                        }
                
                if total_categories_with_images > 0:
                    image_analysis["average_images_per_category"] = round(total_images_count / total_categories_with_images, 1)
                
                test_result["image_analysis"] = image_analysis
            
        else:
            # 失敗時の分析
            test_result["evaluation"] = "failed - image generation could not be completed"
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
                "error": f"Image generation test execution error: {str(e)}",
                "image_architecture": "imagen3_food_photography",
                "evaluation": "error - test execution failed",
                "processing_time_seconds": 0
            }
        )
