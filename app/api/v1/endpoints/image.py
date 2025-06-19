from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Dict, List

from app.services.image import get_image_service_status, get_supported_categories, get_image_features, get_category_styles, get_supported_styles, combine_menu_with_images
from app.services.image.async_manager import get_async_manager

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

@router.post("/generate-async")
async def generate_menu_images_async(request: ImageGenerationRequest):
    """
    Imagen 3で詳細説明付きメニューの画像を非同期生成するエンドポイント
    
    Args:
        request: 画像生成リクエスト（final_menu, session_id）
        
    Returns:
        ジョブID付きレスポンス（即座に返却）
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
        # 非同期マネージャーを取得
        async_manager = get_async_manager()
        
        # 非同期画像生成を開始
        success, message, job_id = async_manager.start_async_generation(
            request.final_menu, 
            request.session_id
        )
        
        if success and job_id:
            # 成功レスポンス
            total_items = sum(len(items) for items in request.final_menu.values())
            response = {
                "success": True,
                "job_id": job_id,
                "session_id": request.session_id,
                "status": "queued",
                "message": message,
                "image_architecture": "imagen3_async_food_photography",
                "total_items": total_items,
                "estimated_time_seconds": total_items * 2,
                "status_endpoint": f"/api/v1/image/status/{job_id}",
                "processing_info": {
                    "mode": "async",
                    "chunks_created": message.split()[-2] if "chunks" in message else "unknown",
                    "parallel_processing": True,
                    "redis_tracking": True
                }
            }
            
            return JSONResponse(content=response, status_code=202)  # 202 Accepted
        else:
            # 失敗レスポンス
            raise HTTPException(
                status_code=500,
                detail=f"Failed to start async image generation: {message}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Async image generation start error: {str(e)}"
        )

@router.get("/status/{job_id}")
async def get_async_generation_status(job_id: str):
    """
    非同期画像生成ジョブの進行状況を取得
    
    Args:
        job_id: ジョブID
        
    Returns:
        ジョブ進行状況情報
    """
    try:
        # 非同期マネージャーを取得
        async_manager = get_async_manager()
        
        # ジョブステータスを取得
        status_info = async_manager.get_job_status(job_id)
        
        if not status_info.get("found", False):
            raise HTTPException(
                status_code=404,
                detail=f"Job not found: {job_id}"
            )
        
        # レスポンスを構築
        response = {
            "job_id": job_id,
            "found": True,
            "status": status_info.get("status", "unknown"),
            "progress_percent": status_info.get("progress_percent", 0),
            "image_architecture": "imagen3_async_food_photography",
            "processing_info": {
                "total_chunks": status_info.get("total_chunks", 0),
                "completed_chunks": status_info.get("completed_chunks", 0),
                "failed_chunks": status_info.get("failed_chunks", 0),
                "total_items": status_info.get("total_items", 0),
                "session_id": status_info.get("session_id")
            },
            "timestamps": {
                "created_at": status_info.get("created_at", 0),
                "estimated_time": status_info.get("estimated_time", 0)
            }
        }
        
        # 完了時の情報を追加
        if status_info.get("status") in ["completed", "partial_completed"]:
            response.update({
                "images_generated": status_info.get("images_generated", {}),
                "total_images": status_info.get("total_images", 0),
                "completed_at": status_info.get("completed_at", 0)
            })
            
            # 成功率計算
            total_items = status_info.get("total_items", 0)
            total_images = status_info.get("total_images", 0)
            response["success_rate"] = round((total_images / total_items) * 100, 2) if total_items > 0 else 0
        
        return JSONResponse(content=response)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Status retrieval error: {str(e)}"
        )

@router.delete("/jobs/{job_id}")
async def cancel_async_generation(job_id: str):
    """
    非同期画像生成ジョブをキャンセル
    
    Args:
        job_id: ジョブID
        
    Returns:
        キャンセル結果
    """
    try:
        # 非同期マネージャーを取得
        async_manager = get_async_manager()
        
        # ジョブをキャンセル
        success, message = async_manager.cancel_job(job_id)
        
        if success:
            response = {
                "success": True,
                "job_id": job_id,
                "message": message,
                "status": "cancelled"
            }
            return JSONResponse(content=response)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to cancel job: {message}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Job cancellation error: {str(e)}"
        )

@router.get("/async-status")
async def get_async_manager_status():
    """
    非同期画像生成マネージャーの状態を取得
    
    Returns:
        マネージャー状態情報
    """
    try:
        # 非同期マネージャーを取得
        async_manager = get_async_manager()
        
        # マネージャー統計を取得
        stats = async_manager.get_manager_stats()
        
        response = {
            "async_manager": stats,
            "image_architecture": "imagen3_async_food_photography",
            "status": "operational",
            "endpoints": {
                "start_async": "/api/v1/image/generate-async",
                "check_status": "/api/v1/image/status/{job_id}",
                "cancel_job": "/api/v1/image/jobs/{job_id}",
                "manager_status": "/api/v1/image/async-status"
            },
            "usage_info": {
                "async_processing": "Recommended for all menu sizes - Only available processing method",
                "sync_processing": "DEPRECATED - No longer available via API endpoints",
                "status_polling": "Check status every 5-10 seconds",
                "job_retention": "Jobs are kept for 24 hours",
                "migration_note": "All image generation now uses async processing for better performance"
            }
        }
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Async manager status error: {str(e)}"
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
                "real_time_progress",
                "async_processing"  # 新機能追加
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
                "Use async endpoint (/generate-async) for all image generation",
                "Provide well-structured menu data with descriptions for best results",
                "Use detailed descriptions for more accurate image generation",
                "Monitor job progress using /status/{job_id} endpoint"
            ]
        
        return JSONResponse(content=response)
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Image generation status check error: {str(e)}"
        )

# 画像生成 情報取得系エンドポイントは削除されました（パイプライン統合により不要）
# - /categories: パイプライン設定で統合
# - /styles: パイプライン設定で統合
# - /features: パイプライン設定で統合

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


