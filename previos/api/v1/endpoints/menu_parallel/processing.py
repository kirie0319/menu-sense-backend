"""
🎯 メニューアイテム処理API - リファクタリング版

このファイルはメニューアイテムの並列処理APIエンドポイントを提供します。
ビジネスロジックはサービス層に委譲し、HTTPハンドリングのみを担当します。

エンドポイント:
- POST /process-menu-items: メニューアイテム並列処理開始
- GET /status/{session_id}/item/{item_id}: アイテム個別状況取得  
- GET /status/{session_id}: セッション全体進行状況取得
"""

from fastapi import APIRouter, HTTPException, Depends

from .models import MenuItemsRequest, MenuItemsResponse, ItemStatusResponse, SessionStatusResponse
from app.services.dependencies import MenuProcessingServiceDep, EventBroadcasterDep
from app.services.menu_processing import MenuItemsRequest as ServiceRequest

# FastAPIルーター作成
router = APIRouter()


@router.post("/process-menu-items", response_model=MenuItemsResponse)
async def process_menu_items(
    request: MenuItemsRequest,
    service: MenuProcessingServiceDep,
    broadcaster: EventBroadcasterDep
):
    """
    🎯 メニューアイテムを並列処理開始
    
    処理はサービス層に完全委譲し、エンドポイントはHTTP処理のみ担当
    """
    try:
        # サービスリクエストに変換
        service_request = ServiceRequest(
            menu_items=request.menu_items,
            test_mode=request.test_mode
        )
        
        # サービス層に処理を委譲
        result = await service.start_menu_processing(service_request)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # SSE処理開始イベント配信
        await broadcaster.broadcast_processing_started(
            session_id=result.session.session_id,
            total_items=result.session.total_items,
            menu_items=result.session.menu_items,
            api_mode=result.session.api_mode
        )
        
        # タスク投入イベント配信
        for item_id, item_text in enumerate(result.session.menu_items):
            await broadcaster.broadcast_task_queued(
                session_id=result.session.session_id,
                item_id=item_id,
                item_text=item_text
            )
        
        # HTTPレスポンス構築
        return MenuItemsResponse(
            success=True,
            session_id=result.session.session_id,
            total_items=result.session.total_items,
            message=result.message,
            test_mode=request.test_mode,
            api_integration=result.session.api_mode
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


@router.get("/status/{session_id}/item/{item_id}", response_model=ItemStatusResponse)
async def get_item_status(
    session_id: str, 
    item_id: int,
    service: MenuProcessingServiceDep
):
    """
    🔍 特定アイテムの処理状況を取得
    
    サービス層に委譲し、HTTPレスポンス変換のみ担当
    """
    try:
        # サービス層に処理を委譲
        result = await service.get_item_status(session_id, item_id)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # HTTPレスポンス構築
        return ItemStatusResponse(
            success=True,
            session_id=session_id,
            item_id=item_id,
            translation=result["translation"],
            description=result["description"],
            image=result["image"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get item status: {str(e)}")


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_session_status(
    session_id: str, 
    total_items: int,
    service: MenuProcessingServiceDep
):
    """
    📊 セッション全体の進行状況を取得
    
    サービス層に委譲し、HTTPレスポンス変換のみ担当
    """
    try:
        # サービス層に処理を委譲
        result = await service.get_session_status(session_id, total_items)
        
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
        
        # HTTPレスポンス構築
        return SessionStatusResponse(
            success=True,
            session_id=session_id,
            total_items=result["total_items"],
            completed_items=result["completed_items"],
            progress_percentage=result["progress_percentage"],
            items_status=result["items_status"],
            api_integration=result["api_integration"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session status: {str(e)}")


# エクスポート用
__all__ = ["router"] 