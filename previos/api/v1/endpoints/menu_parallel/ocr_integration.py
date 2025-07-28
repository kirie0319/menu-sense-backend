"""
🚀 OCR統合処理API - リファクタリング版

このファイルはOCR → カテゴリ分類 → 並列処理の統合APIエンドポイントを提供します。
複雑なワークフローはサービス層に委譲し、HTTPハンドリングのみを担当します。

エンドポイント:
- POST /ocr-to-parallel: OCR統合ワークフロー実行
- POST /ocr-standalone: 単体OCR処理
- GET /ocr-status: OCRサービス状態確認
"""

from fastapi import APIRouter, HTTPException, File, UploadFile, Depends
from fastapi.responses import JSONResponse

from app.services.dependencies import WorkflowOrchestratorDep, EventBroadcasterDep

# FastAPIルーター作成
router = APIRouter()


@router.post("/ocr-to-parallel")
async def ocr_categorize_and_parallel_process(
    orchestrator: WorkflowOrchestratorDep,
    broadcaster: EventBroadcasterDep,
    file: UploadFile = File(...),
    use_real_apis: bool = True
):
    """
    🚀 OCR → カテゴリ分類 → 並列処理の完全統合フロー
    
    ワークフロー全体をサービス層に委譲し、エンドポイントはHTTP処理のみ担当
    """
    try:
        # デバッグ情報
        print(f"🔍 [OCR-to-Parallel] Received file: {file.filename}")
        print(f"🔍 [OCR-to-Parallel] Content type: {file.content_type}")
        print(f"🔍 [OCR-to-Parallel] File size: {getattr(file, 'size', 'unknown')}")
        
        # ワークフロー実行をサービス層に委譲
        result = await orchestrator.process_ocr_to_parallel(file, use_real_apis)
        
        if not result.success:
            raise HTTPException(status_code=500, detail=result.error)
        
        # 並列処理開始イベント配信
        await broadcaster.broadcast_parallel_processing_started(
            session_id=result.session_id,
            ocr_summary=result.ocr_result.to_summary(),
            categorization_summary=result.category_result.to_summary()
        )
        
        # 各アイテムのタスク投入イベント配信
        for category, items in result.category_result.categories.items():
            for item_id, item in enumerate(items):
                item_text = item if isinstance(item, str) else item.get('name', str(item))
                await broadcaster.broadcast_task_queued(
                    session_id=result.session_id,
                    item_id=item_id,
                    item_text=item_text,
                    category=category
                )
        
        # HTTPレスポンス構築
        return {
            "success": True,
            "session_id": result.session_id,
            "processing_summary": {
                "ocr": result.ocr_result.to_summary(),
                "categorization": result.category_result.to_summary(),
                "parallel_processing": {
                    "success": True,
                    "total_tasks_queued": result.processing_result.task_batch.total_tasks,
                    "api_mode": result.processing_result.session.api_mode,
                    "task_queues": ["real_translate_queue", "real_description_queue"] if use_real_apis else ["translate_queue", "description_queue"]
                }
            },
            "streaming_url": result.streaming_url,
            "status_url": result.status_url,
            "api_integration": result.processing_result.session.api_mode,
            "message": result.message
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR to parallel processing failed: {str(e)}")


@router.post("/ocr-standalone")
async def process_image_standalone_ocr(
    orchestrator: WorkflowOrchestratorDep,
    file: UploadFile = File(...)
) -> JSONResponse:
    """
    単体OCR処理エンドポイント
    
    サービス層に委譲し、HTTPレスポンス変換のみ担当
    """
    try:
        # サービス層に処理を委譲
        result = await orchestrator.process_standalone_ocr(file)
        
        # HTTPレスポンス構築
        return JSONResponse(
            status_code=200 if result["status"] == "success" else 500,
            content=result
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": f"OCR processing failed: {str(e)}"
            }
        )


@router.get("/ocr-status")
async def get_ocr_status_unified(
    orchestrator: WorkflowOrchestratorDep
):
    """
    OCR状態確認エンドポイント
    
    サービス層に委譲し、HTTPレスポンス変換のみ担当
    """
    try:
        # サービス層に処理を委譲
        status = orchestrator.get_ocr_service_status()
        
        # HTTPレスポンス構築
        return JSONResponse(content=status)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR status check error: {str(e)}")


# エクスポート用
__all__ = ["router"] 