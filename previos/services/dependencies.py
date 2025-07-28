"""
🔧 Dependency Injection Setup

このモジュールは新しいサービス層の依存性注入を管理します。
FastAPIのDependency Injectionシステムを使用して、
サービスインスタンスの生成と管理を行います。
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

# Menu Processing Services
from .menu_processing import (
    SessionManager,
    TaskCoordinator, 
    FileHandler,
    MenuProcessingService,
    WorkflowOrchestrator,
    create_complete_service_suite
)

# New Task Separation Services
from .menu_processing.task_execution_service import TaskExecutionService
from .menu_processing.task_interface import ServiceTaskInterface, TaskInterface

# Streaming Services
from .streaming import (
    SSEManager,
    ProgressTracker,
    EventBroadcaster,
    create_streaming_suite
)


# ==========================================
# Service Instance Cache
# ==========================================

@lru_cache()
def get_session_manager() -> SessionManager:
    """SessionManager シングルトンインスタンスを取得"""
    return SessionManager()


@lru_cache()
def get_task_coordinator() -> TaskCoordinator:
    """TaskCoordinator シングルトンインスタンスを取得"""
    return TaskCoordinator()


@lru_cache()
def get_file_handler() -> FileHandler:
    """FileHandler シングルトンインスタンスを取得"""
    return FileHandler()


@lru_cache()
def get_sse_manager() -> SSEManager:
    """SSEManager シングルトンインスタンスを取得"""
    return SSEManager()


@lru_cache()
def get_progress_tracker() -> ProgressTracker:
    """ProgressTracker シングルトンインスタンスを取得"""
    return ProgressTracker()


# ==========================================
# New Task Separation Service Cache
# ==========================================

@lru_cache()
def get_task_execution_service() -> TaskExecutionService:
    """TaskExecutionService シングルトンインスタンスを取得"""
    return TaskExecutionService()


@lru_cache()
def get_task_interface() -> ServiceTaskInterface:
    """TaskInterface シングルトンインスタンスを取得"""
    execution_service = get_task_execution_service()
    return ServiceTaskInterface(execution_service)


# ==========================================
# Composite Service Dependencies
# ==========================================

def get_menu_processing_service(
    session_manager: Annotated[SessionManager, Depends(get_session_manager)],
    task_coordinator: Annotated[TaskCoordinator, Depends(get_task_coordinator)],
    file_handler: Annotated[FileHandler, Depends(get_file_handler)]
) -> MenuProcessingService:
    """MenuProcessingService インスタンスを取得"""
    return MenuProcessingService(
        session_manager=session_manager,
        task_coordinator=task_coordinator,
        file_handler=file_handler
    )


def get_workflow_orchestrator(
    menu_processing_service: Annotated[MenuProcessingService, Depends(get_menu_processing_service)],
    file_handler: Annotated[FileHandler, Depends(get_file_handler)]
) -> WorkflowOrchestrator:
    """WorkflowOrchestrator インスタンスを取得"""
    return WorkflowOrchestrator(
        menu_processing_service=menu_processing_service,
        file_handler=file_handler
    )


def get_event_broadcaster(
    sse_manager: Annotated[SSEManager, Depends(get_sse_manager)],
    progress_tracker: Annotated[ProgressTracker, Depends(get_progress_tracker)]
) -> EventBroadcaster:
    """EventBroadcaster インスタンスを取得"""
    return EventBroadcaster(
        sse_manager=sse_manager,
        progress_tracker=progress_tracker
    )


# ==========================================
# Streaming Integration Dependencies
# ==========================================

def get_integrated_streaming_service(
    sse_manager: Annotated[SSEManager, Depends(get_sse_manager)],
    progress_tracker: Annotated[ProgressTracker, Depends(get_progress_tracker)],
    event_broadcaster: Annotated[EventBroadcaster, Depends(get_event_broadcaster)]
) -> tuple[SSEManager, ProgressTracker, EventBroadcaster]:
    """統合ストリーミングサービスを取得"""
    return sse_manager, progress_tracker, event_broadcaster


# ==========================================
# Complete Service Suite Dependencies
# ==========================================

def get_complete_menu_service_suite(
    menu_processing_service: Annotated[MenuProcessingService, Depends(get_menu_processing_service)],
    workflow_orchestrator: Annotated[WorkflowOrchestrator, Depends(get_workflow_orchestrator)],
    event_broadcaster: Annotated[EventBroadcaster, Depends(get_event_broadcaster)]
) -> tuple[MenuProcessingService, WorkflowOrchestrator, EventBroadcaster]:
    """完全なメニューサービススイートを取得"""
    return menu_processing_service, workflow_orchestrator, event_broadcaster


# ==========================================
# Legacy Support Dependencies
# ==========================================

def get_legacy_sse_support(
    event_broadcaster: Annotated[EventBroadcaster, Depends(get_event_broadcaster)]
) -> EventBroadcaster:
    """
    レガシーSSE互換性のためのDependency
    
    既存のshared_state.pyの代替として使用されます。
    """
    return event_broadcaster


# ==========================================
# Service Status Dependencies
# ==========================================

def get_service_health_checker() -> dict:
    """
    サービスヘルスチェック情報を取得
    
    Returns:
        dict: サービス状態情報
    """
    try:
        # 各サービスの基本的なヘルスチェック
        session_manager = get_session_manager()
        task_coordinator = get_task_coordinator()
        file_handler = get_file_handler()
        sse_manager = get_sse_manager()
        progress_tracker = get_progress_tracker()
        
        return {
            "status": "healthy",
            "services": {
                "session_manager": {
                    "status": "active",
                    "statistics": session_manager.get_session_statistics()
                },
                "task_coordinator": {
                    "status": "active", 
                    "statistics": task_coordinator.get_task_statistics()
                },
                "file_handler": {
                    "status": "active",
                    "statistics": file_handler.get_file_statistics()
                },
                "sse_manager": {
                    "status": "active",
                    "statistics": sse_manager.get_streaming_statistics()
                },
                "progress_tracker": {
                    "status": "active",
                    "statistics": progress_tracker.get_tracking_statistics()
                }
            },
            "integration_ready": True,
            "legacy_compatibility": True
        }
        
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "integration_ready": False,
            "legacy_compatibility": False
        }


# ==========================================
# Cleanup Dependencies
# ==========================================

async def cleanup_all_services() -> dict:
    """
    全サービスのクリーンアップを実行
    
    Returns:
        dict: クリーンアップ結果
    """
    cleanup_results = {}
    
    try:
        # セッション関連クリーンアップ
        session_manager = get_session_manager()
        expired_sessions = await session_manager.cleanup_expired_sessions()
        cleanup_results["expired_sessions"] = expired_sessions
        
        # ファイル関連クリーンアップ
        file_handler = get_file_handler()
        old_files = await file_handler.cleanup_old_files()
        cleanup_results["old_files"] = old_files
        
        # ストリーミング関連クリーンアップ
        sse_manager = get_sse_manager()
        inactive_streams = await sse_manager.cleanup_inactive_sessions()
        cleanup_results["inactive_streams"] = inactive_streams
        
        return {
            "success": True,
            "cleanup_results": cleanup_results,
            "message": "All services cleaned up successfully"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Cleanup failed"
        }


# ==========================================
# Type Aliases for Dependency Injection
# ==========================================

# 基本サービス
SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]
TaskCoordinatorDep = Annotated[TaskCoordinator, Depends(get_task_coordinator)]
FileHandlerDep = Annotated[FileHandler, Depends(get_file_handler)]
SSEManagerDep = Annotated[SSEManager, Depends(get_sse_manager)]
ProgressTrackerDep = Annotated[ProgressTracker, Depends(get_progress_tracker)]

# 新しいタスク分離サービス
TaskExecutionServiceDep = Annotated[TaskExecutionService, Depends(get_task_execution_service)]
TaskInterfaceDep = Annotated[ServiceTaskInterface, Depends(get_task_interface)]

# 複合サービス
MenuProcessingServiceDep = Annotated[MenuProcessingService, Depends(get_menu_processing_service)]
WorkflowOrchestratorDep = Annotated[WorkflowOrchestrator, Depends(get_workflow_orchestrator)]
EventBroadcasterDep = Annotated[EventBroadcaster, Depends(get_event_broadcaster)]

# 統合サービス
IntegratedStreamingDep = Annotated[
    tuple[SSEManager, ProgressTracker, EventBroadcaster], 
    Depends(get_integrated_streaming_service)
]

CompleteMenuServiceDep = Annotated[
    tuple[MenuProcessingService, WorkflowOrchestrator, EventBroadcaster],
    Depends(get_complete_menu_service_suite)
]


# ==========================================
# Export
# ==========================================

__all__ = [
    # Basic service getters
    "get_session_manager",
    "get_task_coordinator", 
    "get_file_handler",
    "get_sse_manager",
    "get_progress_tracker",
    
    # Task separation service getters
    "get_task_execution_service",
    "get_task_interface",
    
    # Composite service getters
    "get_menu_processing_service",
    "get_workflow_orchestrator",
    "get_event_broadcaster",
    
    # Integration getters
    "get_integrated_streaming_service",
    "get_complete_menu_service_suite",
    
    # Utility getters
    "get_legacy_sse_support",
    "get_service_health_checker",
    "cleanup_all_services",
    
    # Type aliases
    "SessionManagerDep",
    "TaskCoordinatorDep",
    "FileHandlerDep", 
    "SSEManagerDep",
    "ProgressTrackerDep",
    "TaskExecutionServiceDep",
    "TaskInterfaceDep",
    "MenuProcessingServiceDep",
    "WorkflowOrchestratorDep",
    "EventBroadcasterDep",
    "IntegratedStreamingDep",
    "CompleteMenuServiceDep"
]