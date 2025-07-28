"""
Pipeline Endpoint - Enhanced Menu Processing with Staged Updates
OCR→Mapping→Categorize処理の段階別DB更新とSSE配信対応エンドポイント
"""
import uuid
from typing import Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Query
from fastapi.responses import JSONResponse

from app_2.pipelines.pipeline_runner import get_menu_processing_pipeline
from app_2.utils.logger import get_logger

logger = get_logger("pipeline_endpoint")

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/process", response_model=Dict[str, Any])
async def process_menu_image(
    file: UploadFile = File(..., description="メニュー画像ファイル (JPEG, PNG, WEBP対応)")
) -> JSONResponse:
    """
    メニュー画像の段階別処理（Enhanced Pipeline）
    
    各段階でDB更新とSSE配信を実行:
    1. OCR処理 → DB保存 → SSE配信（テキスト抽出結果）
    2. Mapping処理 → DB保存 → SSE配信（位置情報整形結果）
    3. Categorize処理 → DB保存 → SSE配信（メニュー構造とアイテム表示）
    4. Parallel Tasks開始（翻訳、説明、アレルギー、画像検索、成分分析）
    
    Args:
        file: アップロードされた画像ファイル
        
    Returns:
        JSONResponse: 処理結果
        {
            "session_id": "uuid",
            "status": "success", 
            "processing_steps": {
                "step1_ocr": {"db_updated": true, "sse_broadcasted": true, ...},
                "step2_mapping": {"db_updated": true, "sse_broadcasted": true, ...},
                "step3_categorize": {"db_updated": true, "sse_broadcasted": true, ...},
                "step4_parallel_tasks": {"parallel_tasks_triggered": true}
            },
            "final_results": {...},
            "saved_menu_items": [...],
            "processing_time": 12.5,
            "message": "Enhanced Pipeline with realtime updates completed successfully"
        }
    
    SSE配信:
        クライアントは session_id を使ってSSEチャンネルを購読すると、
        各段階の完了時にリアルタイムで結果を受信できます。
        
        チャンネル: sse:{session_id}
        メッセージタイプ:
        - stage_completed (OCR、Mapping、Categorize完了時)
        - progress_update (進捗更新)
        - error (エラー発生時)
    """
    
    # セッションID生成
    session_id = str(uuid.uuid4())
    
    try:
        logger.info(f"🚀 Enhanced Pipeline processing started: session={session_id}, file={file.filename}")
        
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
        
        logger.info(f"📊 Image loaded: {len(image_data)} bytes for enhanced pipeline processing")
        
        # Pipeline Runnerに処理を委譲（段階別処理対応版）
        pipeline = get_menu_processing_pipeline()
        result = await pipeline.process_menu_image(
            session_id=session_id,
            image_data=image_data,
            filename=file.filename
        )
        
        # 段階別処理の結果ログ
        processing_steps = result.get("processing_steps", {})
        logger.info(f"📈 Enhanced Pipeline stages completed for session={session_id}:")
        
        for step_name, step_data in processing_steps.items():
            db_updated = step_data.get("db_updated", False)
            sse_broadcasted = step_data.get("sse_broadcasted", False)
            logger.info(f"  ✓ {step_name}: DB={db_updated}, SSE={sse_broadcasted}")
        
        logger.info(f"✅ Enhanced Pipeline processing completed: session={session_id}")
        
        # レスポンスにSSE情報を追加
        result["sse_info"] = {
            "channel": f"sse:{session_id}",
            "connection_url": f"/api/v1/sse/stream/{session_id}",
            "message": "Connect to SSE for real-time updates"
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Enhanced Pipeline processing failed: session={session_id}, error={e}")
        
        # エラー時の統一レスポンス
        error_response = {
            "session_id": session_id,
            "status": "error",
            "error": {
                "type": "processing_error",
                "message": str(e),
                "timestamp": "now"
            },
            "sse_info": {
                "channel": f"sse:{session_id}",
                "connection_url": f"/api/v1/sse/stream/{session_id}",
                "message": "Error details have been broadcasted via SSE"
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )


@router.post("/process-with-session", response_model=Dict[str, Any])
async def process_menu_image_with_session(
    session_id: str = Query(..., description="フロントエンドで生成されたセッションID"),
    file: UploadFile = File(..., description="メニュー画像ファイル (JPEG, PNG, WEBP対応)")
) -> JSONResponse:
    """
    指定されたセッションIDでメニュー画像を処理（フロントエンド連携用）
    
    Args:
        session_id: フロントエンドで生成されたセッションID
        file: アップロードされた画像ファイル
        
    Returns:
        JSONResponse: 処理結果（既存のprocessエンドポイントと同じ形式）
    """
    
    try:
        logger.info(f"🚀 Enhanced Pipeline processing started with custom session: session={session_id}, file={file.filename}")
        
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
        
        logger.info(f"📊 Image loaded: {len(image_data)} bytes for enhanced pipeline processing")
        
        # Pipeline Runnerに処理を委譲（カスタムセッションID使用）
        pipeline = get_menu_processing_pipeline()
        result = await pipeline.process_menu_image(
            session_id=session_id,  # フロントエンドからのセッションIDを使用
            image_data=image_data,
            filename=file.filename
        )
        
        # 段階別処理の結果ログ
        processing_steps = result.get("processing_steps", {})
        logger.info(f"📈 Enhanced Pipeline stages completed for custom session={session_id}:")
        
        for step_name, step_data in processing_steps.items():
            db_updated = step_data.get("db_updated", False)
            sse_broadcasted = step_data.get("sse_broadcasted", False)
            logger.info(f"  ✓ {step_name}: DB={db_updated}, SSE={sse_broadcasted}")
        
        logger.info(f"✅ Enhanced Pipeline processing completed: custom session={session_id}")
        
        # レスポンスにSSE情報を追加
        result["sse_info"] = {
            "channel": f"sse:{session_id}",
            "connection_url": f"/api/v1/sse/stream/{session_id}",
            "message": "Connect to SSE for real-time updates"
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Enhanced Pipeline processing failed: custom session={session_id}, error={e}")
        
        # エラー時の統一レスポンス
        error_response = {
            "session_id": session_id,
            "status": "error",
            "error": {
                "type": "processing_error",
                "message": str(e),
                "timestamp": "now"
            },
            "sse_info": {
                "channel": f"sse:{session_id}",
                "connection_url": f"/api/v1/sse/stream/{session_id}",
                "message": "Error details have been broadcasted via SSE"
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response
        )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """
    Enhanced Pipelineのヘルスチェック
    
    Returns:
        Dict: ステータス情報
    """
    return {
        "status": "healthy",
        "service": "enhanced_pipeline",
        "version": "2.1.0",
        "architecture": "Staged Processing with Realtime Updates",
        "processing_stages": [
            "OCR (Text Extraction)",
            "Mapping (Position Formatting)", 
            "Categorize (Menu Structure Analysis)",
            "Parallel Tasks (Translation, Description, Allergen, Image Search, Ingredients)"
        ],
        "features": [
            "Stage-by-stage DB updates",
            "Real-time SSE broadcasting",
            "Progressive result display",
            "Parallel background processing"
        ],
        "sse_channels": "sse:{session_id}",
        "message": "Enhanced Pipeline: OCR → Mapping → Categorize with realtime DB updates and SSE broadcasts"
    }


@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str) -> Dict[str, Any]:
    """
    セッションの段階別処理状況を取得
    
    Args:
        session_id: セッションID
        
    Returns:
        Dict: セッション状況
    """
    try:
        from app_2.core.database import async_session_factory
        from app_2.services.dependencies import get_session_repository
        
        async with async_session_factory() as db_session:
            session_repo = get_session_repository(db_session)
            
            # セッションモデルを直接取得して段階データを確認
            from sqlalchemy import select
            from app_2.infrastructure.models.session_model import SessionModel
            
            stmt = select(SessionModel).where(SessionModel.session_id == session_id)
            result = await db_session.execute(stmt)
            session_model = result.scalar_one_or_none()
            
            if not session_model:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session not found: {session_id}"
                )
            
            # 段階データを取得
            stages_data = session_model.get_stages_data()
            
            return {
                "session_id": session_id,
                "status": session_model.status,
                "current_stage": session_model.current_stage,
                "stages_completed": list(stages_data.keys()),
                "stages_data": stages_data,
                "created_at": session_model.created_at.isoformat(),
                "updated_at": session_model.updated_at.isoformat(),
                "menu_ids": session_model.menu_ids
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session status {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session status: {str(e)}"
        ) 