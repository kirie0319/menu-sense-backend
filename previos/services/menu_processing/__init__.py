"""
🎯 Menu Processing Service Package

このパッケージはメニュー処理の統合サービス層を提供します。
エンドポイントからビジネスロジックを分離し、再利用可能なサービスとして提供します。

主要サービス:
- SessionManager: セッション管理
- TaskCoordinator: タスク調整
- FileHandler: ファイル操作
- MenuProcessingService: メニュー処理統合
- WorkflowOrchestrator: OCR統合ワークフロー
"""

from .session_manager import (
    SessionManager,
    ProcessingSession,
    SessionStatus
)

from .task_coordinator import (
    TaskCoordinator,
    TaskType,
    QueueMode,
    TaskInfo,
    TaskBatch
)

from .file_handler import (
    FileHandler,
    FileInfo
)

from .menu_processing_service import (
    MenuProcessingService,
    MenuItemsRequest,
    ProcessingResult
)

from .workflow_orchestrator import (
    WorkflowOrchestrator,
    OCRResult,
    CategoryResult,
    WorkflowResult
)

# New Task Separation Services
from .task_execution_service import (
    TaskExecutionService,
    TaskExecutionRequest,
    TaskExecutionResult,
    ExecutionMode,
    TaskStage
)

from .task_interface import (
    TaskInterface,
    ServiceTaskInterface,
    TaskCommand,
    TaskResponse,
    CommandType,
    create_service_task_interface,
    create_task_command
)


# ==========================================
# Service Factory Functions
# ==========================================

def create_session_manager() -> SessionManager:
    """SessionManagerのインスタンスを作成"""
    return SessionManager()


def create_task_coordinator() -> TaskCoordinator:
    """TaskCoordinatorのインスタンスを作成"""
    return TaskCoordinator()


def create_file_handler() -> FileHandler:
    """FileHandlerのインスタンスを作成"""
    return FileHandler()


def create_menu_processing_service(
    session_manager: SessionManager = None,
    task_coordinator: TaskCoordinator = None,
    file_handler: FileHandler = None
) -> MenuProcessingService:
    """
    MenuProcessingServiceのインスタンスを作成
    
    Args:
        session_manager: セッション管理サービス（オプション）
        task_coordinator: タスク調整サービス（オプション）
        file_handler: ファイル処理サービス（オプション）
    
    Returns:
        MenuProcessingService: 統合処理サービス
    """
    if session_manager is None:
        session_manager = create_session_manager()
    
    if task_coordinator is None:
        task_coordinator = create_task_coordinator()
    
    if file_handler is None:
        file_handler = create_file_handler()
    
    return MenuProcessingService(
        session_manager=session_manager,
        task_coordinator=task_coordinator,
        file_handler=file_handler
    )


def create_workflow_orchestrator(
    menu_processing_service: MenuProcessingService = None,
    file_handler: FileHandler = None
) -> WorkflowOrchestrator:
    """
    WorkflowOrchestratorのインスタンスを作成
    
    Args:
        menu_processing_service: メニュー処理サービス（オプション）
        file_handler: ファイル処理サービス（オプション）
    
    Returns:
        WorkflowOrchestrator: ワークフロー管理サービス
    """
    if file_handler is None:
        file_handler = create_file_handler()
    
    if menu_processing_service is None:
        menu_processing_service = create_menu_processing_service(file_handler=file_handler)
    
    return WorkflowOrchestrator(
        menu_processing_service=menu_processing_service,
        file_handler=file_handler
    )


def create_complete_service_suite() -> tuple[MenuProcessingService, WorkflowOrchestrator]:
    """
    完全なサービススイートを作成
    
    Returns:
        tuple: (MenuProcessingService, WorkflowOrchestrator)
    """
    # 共有サービス作成
    session_manager = create_session_manager()
    task_coordinator = create_task_coordinator()
    file_handler = create_file_handler()
    
    # メイン処理サービス作成
    menu_processing_service = MenuProcessingService(
        session_manager=session_manager,
        task_coordinator=task_coordinator,
        file_handler=file_handler
    )
    
    # ワークフロー管理サービス作成
    workflow_orchestrator = WorkflowOrchestrator(
        menu_processing_service=menu_processing_service,
        file_handler=file_handler
    )
    
    return menu_processing_service, workflow_orchestrator


# ==========================================
# New Task Separation Service Factory Functions
# ==========================================

def create_task_execution_service() -> TaskExecutionService:
    """TaskExecutionServiceのインスタンスを作成"""
    return TaskExecutionService()


def create_task_interface(
    execution_service: TaskExecutionService = None
) -> ServiceTaskInterface:
    """
    TaskInterfaceのインスタンスを作成
    
    Args:
        execution_service: タスク実行サービス（オプション）
    
    Returns:
        ServiceTaskInterface: タスクインターフェース
    """
    if execution_service is None:
        execution_service = create_task_execution_service()
    
    return ServiceTaskInterface(execution_service)


def create_task_separation_suite() -> tuple[TaskExecutionService, ServiceTaskInterface]:
    """
    タスク分離サービススイートを作成
    
    Returns:
        tuple: (TaskExecutionService, ServiceTaskInterface)
    """
    execution_service = create_task_execution_service()
    task_interface = ServiceTaskInterface(execution_service)
    
    return execution_service, task_interface


# ==========================================
# Public API
# ==========================================

__all__ = [
    # Core classes
    "SessionManager",
    "TaskCoordinator", 
    "FileHandler",
    "MenuProcessingService",
    "WorkflowOrchestrator",
    
    # New Task Separation classes
    "TaskExecutionService",
    "TaskInterface",
    "ServiceTaskInterface",
    
    # Data classes
    "ProcessingSession",
    "SessionStatus",
    "TaskType",
    "QueueMode",
    "TaskInfo",
    "TaskBatch",
    "FileInfo",
    "MenuItemsRequest",
    "ProcessingResult",
    "OCRResult",
    "CategoryResult",
    "WorkflowResult",
    
    # New Task Separation data classes
    "TaskExecutionRequest",
    "TaskExecutionResult",
    "ExecutionMode",
    "TaskStage",
    "TaskCommand",
    "TaskResponse",
    "CommandType",
    
    # Factory functions
    "create_session_manager",
    "create_task_coordinator",
    "create_file_handler",
    "create_menu_processing_service",
    "create_workflow_orchestrator",
    "create_complete_service_suite",
    
    # New Task Separation factory functions
    "create_task_execution_service",
    "create_task_interface",
    "create_task_separation_suite",
    "create_service_task_interface",
    "create_task_command"
]