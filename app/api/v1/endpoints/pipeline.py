"""
パイプライン並列化エンドポイント専用のAPIハンドラー

完全パイプライン並列化 (Stage 1-5全体) のエンドポイント:
- /api/v1/pipeline/process: 完全パイプライン処理
- /api/v1/pipeline/process-advanced: 高度パイプライン処理
- フロントエンド完全互換
- 既存エンドポイントとの統合
"""

import os
import aiofiles
from fastapi import APIRouter, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any

from app.core.config import settings

router = APIRouter()

@router.post("/process")
async def process_full_pipeline(
    file: UploadFile = File(...),
    pipeline_mode: Optional[str] = Query("smart", description="Pipeline mode: smart, aggressive, conservative"),
    force_strategy: Optional[str] = Query(None, description="Force specific strategy: worker_pipeline, category_pipeline, sequential_pipeline"),
    enable_streaming: Optional[bool] = Query(True, description="Enable streaming results")
):
    """
    完全パイプライン並列化処理エンドポイント
    
    Stage 1-5全体を最適化された並列処理で実行
    フロントエンド完全互換のレスポンス形式
    """
    
    # ファイル形式チェック
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    try:
        # ファイルを一時保存
        file_path = f"{settings.UPLOAD_DIR}/{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # パイプライン処理オプション設定
        pipeline_options = {
            "pipeline_mode": pipeline_mode,
            "enable_streaming": enable_streaming
        }
        
        # 強制戦略の設定
        if force_strategy:
            if force_strategy == "worker_pipeline":
                pipeline_options["force_worker_pipeline"] = True
            elif force_strategy == "category_pipeline":
                pipeline_options["force_category_pipeline"] = True
            elif force_strategy == "sequential_pipeline":
                pipeline_options["force_sequential_pipeline"] = True
        
        # パイプライン処理実行
        from app.services.pipeline import process_full_pipeline
        
        result = await process_full_pipeline(
            image_path=file_path,
            session_id=f"pipeline-{file.filename}",
            options=pipeline_options
        )
        
        if result.success:
            # フロントエンド互換のレスポンス形式に変換
            response_data = {
                # 既存エンドポイント互換フィールド
                "extracted_text": result.extracted_text,
                "categories": result.categories,
                "translated_categories": result.translated_categories,
                "final_menu": result.final_menu,
                "images_generated": result.images_generated,
                
                # パイプライン並列化メタデータ
                "pipeline_processing": True,
                "pipeline_mode": result.pipeline_mode,
                "total_processing_time": result.total_processing_time,
                "total_categories": result.total_categories,
                "total_items": result.total_items,
                "optimizations_applied": result.optimizations_applied,
                
                # 互換性確保
                "success": True,
                "message": f"Pipeline processing completed in {result.total_processing_time:.2f}s with {len(result.optimizations_applied)} optimizations"
            }
            
            # メタデータの追加
            if result.metadata:
                response_data["pipeline_metadata"] = result.metadata
            
            return JSONResponse(content=response_data)
        
        else:
            # エラー時のレスポンス
            raise HTTPException(
                status_code=500, 
                detail=f"Pipeline processing failed: {result.error}"
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline processing error: {str(e)}")
    
    finally:
        # ファイルクリーンアップ
        if os.path.exists(file_path):
            os.remove(file_path)

@router.post("/process-advanced")
async def process_advanced_pipeline(
    file: UploadFile = File(...),
    pipeline_mode: Optional[str] = Query("aggressive", description="Pipeline mode for advanced processing"),
    max_workers: Optional[int] = Query(None, description="Override max workers"),
    category_threshold: Optional[int] = Query(None, description="Override category threshold"),
    item_threshold: Optional[int] = Query(None, description="Override item threshold"),
    enable_early_stage5: Optional[bool] = Query(True, description="Enable Stage 3→5 overlap"),
    enable_category_pipelining: Optional[bool] = Query(True, description="Enable category-level pipelining")
):
    """
    高度パイプライン並列化処理エンドポイント
    
    より詳細な制御オプション付きの完全パイプライン処理
    """
    
    # ファイル形式チェック
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="Only image files are allowed")
    
    try:
        # ファイルを一時保存
        file_path = f"{settings.UPLOAD_DIR}/{file.filename}"
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # 高度なパイプライン処理オプション設定
        advanced_options = {
            "pipeline_mode": pipeline_mode,
            "force_worker_pipeline": True,  # 高度モードではワーカーパイプラインを強制
            "advanced_mode": True
        }
        
        # オプションのオーバーライド
        if max_workers is not None:
            advanced_options["override_max_workers"] = max_workers
        
        if category_threshold is not None:
            advanced_options["override_category_threshold"] = category_threshold
        
        if item_threshold is not None:
            advanced_options["override_item_threshold"] = item_threshold
        
        advanced_options.update({
            "enable_early_stage5": enable_early_stage5,
            "enable_category_pipelining": enable_category_pipelining
        })
        
        # 高度パイプライン処理実行
        from app.services.pipeline import process_full_pipeline
        
        result = await process_full_pipeline(
            image_path=file_path,
            session_id=f"advanced-pipeline-{file.filename}",
            options=advanced_options
        )
        
        if result.success:
            # 高度モード専用レスポンス
            response_data = {
                # 基本結果
                "extracted_text": result.extracted_text,
                "categories": result.categories,
                "translated_categories": result.translated_categories,
                "final_menu": result.final_menu,
                "images_generated": result.images_generated,
                
                # 高度パイプラインメタデータ
                "advanced_pipeline_processing": True,
                "pipeline_mode": result.pipeline_mode,
                "total_processing_time": result.total_processing_time,
                "total_categories": result.total_categories,
                "total_items": result.total_items,
                "optimizations_applied": result.optimizations_applied,
                
                # 詳細性能データ
                "performance_metrics": {
                    "processing_speed": result.total_items / result.total_processing_time if result.total_processing_time > 0 else 0,
                    "optimization_count": len(result.optimizations_applied),
                    "categories_per_second": result.total_categories / result.total_processing_time if result.total_processing_time > 0 else 0
                },
                
                # ステータス
                "success": True,
                "message": f"Advanced pipeline completed: {result.total_items} items in {result.total_processing_time:.2f}s"
            }
            
            # 詳細メタデータ
            if result.metadata:
                response_data["detailed_metadata"] = result.metadata
            
            return JSONResponse(content=response_data)
        
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Advanced pipeline processing failed: {result.error}"
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Advanced pipeline processing error: {str(e)}")
    
    finally:
        # ファイルクリーンアップ
        if os.path.exists(file_path):
            os.remove(file_path)

@router.get("/status")
async def get_pipeline_status():
    """パイプライン処理の状況を取得"""
    try:
        from app.services.pipeline import PipelineProcessingService
        
        service = PipelineProcessingService()
        
        # Celeryワーカー状況の確認
        from app.tasks.celery_app import get_worker_stats, test_celery_connection
        
        connection_ok, connection_msg = test_celery_connection()
        worker_stats = get_worker_stats()
        
        status_data = {
            "pipeline_service_available": service.is_available(),
            "pipeline_enabled": service.pipeline_enabled,
            "pipeline_mode": service.pipeline_mode,
            "max_workers": service.max_workers,
            "category_threshold": service.category_threshold,
            "item_threshold": service.item_threshold,
            
            # Celery状況
            "celery_connection": connection_ok,
            "celery_message": connection_msg,
            "active_workers": worker_stats.get("worker_count", 0),
            
            # 最適化フラグ
            "optimizations": {
                "early_stage5_enabled": service.early_stage5_enabled,
                "category_pipelining_enabled": service.category_pipelining_enabled,
                "streaming_enabled": service.streaming_enabled
            },
            
            # 現在の設定値
            "current_config": {
                "ENABLE_FULL_PIPELINE_PARALLEL": settings.ENABLE_FULL_PIPELINE_PARALLEL,
                "PIPELINE_PARALLEL_MODE": settings.PIPELINE_PARALLEL_MODE,
                "MAX_PIPELINE_WORKERS": settings.MAX_PIPELINE_WORKERS,
                "ENABLE_CATEGORY_PIPELINING": settings.ENABLE_CATEGORY_PIPELINING,
                "ENABLE_STREAMING_RESULTS": settings.ENABLE_STREAMING_RESULTS
            }
        }
        
        return JSONResponse(content=status_data)
        
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to get pipeline status: {str(e)}"},
            status_code=500
        )

@router.get("/config")
async def get_pipeline_config():
    """パイプライン設定の詳細を取得"""
    try:
        config_data = {
            # 基本設定
            "pipeline_enabled": settings.ENABLE_FULL_PIPELINE_PARALLEL,
            "pipeline_mode": settings.PIPELINE_PARALLEL_MODE,
            "max_workers": settings.MAX_PIPELINE_WORKERS,
            
            # 閾値設定
            "thresholds": {
                "category_threshold": settings.PIPELINE_CATEGORY_THRESHOLD,
                "item_threshold": settings.PIPELINE_ITEM_THRESHOLD,
                "overlap_min_categories": settings.MIN_CATEGORIES_FOR_OVERLAP
            },
            
            # 最適化設定
            "optimizations": {
                "early_stage5_start": settings.ENABLE_EARLY_STAGE5_START,
                "category_pipelining": settings.ENABLE_CATEGORY_PIPELINING,
                "streaming_results": settings.ENABLE_STREAMING_RESULTS,
                "stage3_to_stage5_overlap": settings.STAGE3_TO_STAGE5_OVERLAP,
                "category_level_overlap": settings.CATEGORY_LEVEL_OVERLAP
            },
            
            # タイムアウト設定
            "timeouts": {
                "pipeline_total_timeout": settings.PIPELINE_TOTAL_TIMEOUT
            },
            
            # デバッグ・テスト用フラグ
            "debug_flags": {
                "force_sequential_pipeline": settings.FORCE_SEQUENTIAL_PIPELINE,
                "log_pipeline_performance": settings.LOG_PIPELINE_PERFORMANCE,
                "enable_pipeline_monitoring": settings.ENABLE_PIPELINE_MONITORING
            }
        }
        
        return JSONResponse(content=config_data)
        
    except Exception as e:
        return JSONResponse(
            content={"error": f"Failed to get pipeline config: {str(e)}"},
            status_code=500
        ) 