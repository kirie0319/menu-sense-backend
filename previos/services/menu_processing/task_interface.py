"""
🔗 TaskInterface - タスクインターフェース層

サービス層とタスク層の間の抽象化レイヤーです。
依存関係を逆転させ、サービス層がタスク層に直接依存しないようにします。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .task_execution_service import (
    TaskExecutionService, 
    TaskExecutionRequest, 
    TaskExecutionResult, 
    TaskStage, 
    ExecutionMode
)

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """コマンドタイプ"""
    EXECUTE_TASK = "execute_task"
    CHECK_STATUS = "check_status"
    CHECK_DEPENDENCIES = "check_dependencies"
    MARK_RUNNING = "mark_running"
    GET_PROGRESS = "get_progress"


@dataclass
class TaskCommand:
    """タスクコマンド"""
    command_type: CommandType
    session_id: str
    item_id: int
    stage: TaskStage
    execution_mode: ExecutionMode = ExecutionMode.REAL
    payload: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResponse:
    """タスクレスポンス"""
    success: bool
    command_type: CommandType
    session_id: str
    item_id: int
    stage: TaskStage
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: Optional[float] = None


class TaskInterface(ABC):
    """
    タスクインターフェース抽象クラス
    
    サービス層がタスク層にアクセスするための抽象化インターフェース。
    具体的な実装に依存せず、コマンドパターンでタスクを実行する。
    """
    
    @abstractmethod
    async def execute_command(self, command: TaskCommand) -> TaskResponse:
        """
        コマンド実行
        
        Args:
            command: 実行するコマンド
            
        Returns:
            TaskResponse: 実行結果
        """
        pass
    
    @abstractmethod
    async def execute_translation_task(self, command: TaskCommand) -> TaskResponse:
        """翻訳タスク実行"""
        pass
    
    @abstractmethod
    async def execute_description_task(self, command: TaskCommand) -> TaskResponse:
        """説明生成タスク実行"""
        pass
    
    @abstractmethod
    async def execute_image_task(self, command: TaskCommand) -> TaskResponse:
        """画像生成タスク実行"""
        pass
    
    @abstractmethod
    async def execute_ocr_task(self, command: TaskCommand) -> TaskResponse:
        """OCRタスク実行"""
        pass
    
    @abstractmethod
    async def check_task_status(self, session_id: str, item_id: int, stage: Optional[TaskStage] = None) -> TaskResponse:
        """タスク状態チェック"""
        pass
    
    @abstractmethod
    async def check_dependencies(self, session_id: str, item_id: int) -> TaskResponse:
        """依存関係チェック"""
        pass


class ServiceTaskInterface(TaskInterface):
    """
    サービス実装のタスクインターフェース
    
    TaskExecutionService を使用して
    タスクインターフェースを実装する。
    """
    
    def __init__(self, 
                 execution_service: Optional[TaskExecutionService] = None):
        """
        インターフェース初期化
        
        Args:
            execution_service: タスク実行サービス
        """
        self.execution_service = execution_service or TaskExecutionService()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    
    async def execute_command(self, command: TaskCommand) -> TaskResponse:
        """
        コマンド実行のメインエントリーポイント
        
        Args:
            command: 実行するコマンド
            
        Returns:
            TaskResponse: 実行結果
        """
        try:
            if command.command_type == CommandType.EXECUTE_TASK:
                return await self._execute_task_command(command)
            elif command.command_type == CommandType.CHECK_STATUS:
                return await self.check_task_status(command.session_id, command.item_id, command.stage)
            elif command.command_type == CommandType.CHECK_DEPENDENCIES:
                return await self.check_dependencies(command.session_id, command.item_id)
            elif command.command_type == CommandType.MARK_RUNNING:
                return await self._mark_running_command(command)
            elif command.command_type == CommandType.GET_PROGRESS:
                return await self._get_progress_command(command)
            else:
                raise ValueError(f"Unknown command type: {command.command_type}")
                
        except Exception as e:
            self.logger.error(f"Command execution failed: {e}")
            return TaskResponse(
                success=False,
                command_type=command.command_type,
                session_id=command.session_id,
                item_id=command.item_id,
                stage=command.stage,
                data={},
                error=str(e)
            )
    
    
    async def execute_translation_task(self, command: TaskCommand) -> TaskResponse:
        """翻訳タスク実行（サービス層で処理）"""
        return await self._execute_stage_task(command, TaskStage.TRANSLATION)
    
    
    async def execute_description_task(self, command: TaskCommand) -> TaskResponse:
        """説明生成タスク実行（サービス層で処理）"""
        return await self._execute_stage_task(command, TaskStage.DESCRIPTION)
    
    
    async def execute_image_task(self, command: TaskCommand) -> TaskResponse:
        """画像生成タスク実行（サービス層で処理）"""
        return await self._execute_stage_task(command, TaskStage.IMAGE)
    
    
    async def execute_ocr_task(self, command: TaskCommand) -> TaskResponse:
        """OCRタスク実行（サービス層で処理）"""
        return await self._execute_stage_task(command, TaskStage.OCR)
    
    
    async def check_task_status(self, session_id: str, item_id: int, stage: Optional[TaskStage] = None) -> TaskResponse:
        """タスク状態チェック"""
        try:
            # This method is now simplified, so we just return a placeholder response
            # In a real scenario, you would query the state service here
            return TaskResponse(
                success=True,
                command_type=CommandType.CHECK_STATUS,
                session_id=session_id,
                item_id=item_id,
                stage=stage or TaskStage.TRANSLATION,
                data={"status": "not_implemented", "message": "Status check not fully implemented"}
            )
            
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")
            return TaskResponse(
                success=False,
                command_type=CommandType.CHECK_STATUS,
                session_id=session_id,
                item_id=item_id,
                stage=stage or TaskStage.TRANSLATION,
                data={},
                error=str(e)
            )
    
    
    async def check_dependencies(self, session_id: str, item_id: int) -> TaskResponse:
        """依存関係チェック"""
        try:
            # This method is now simplified, so we just return a placeholder response
            # In a real scenario, you would query the state service here
            return TaskResponse(
                success=True,
                command_type=CommandType.CHECK_DEPENDENCIES,
                session_id=session_id,
                item_id=item_id,
                stage=TaskStage.TRANSLATION,
                data={"dependencies_met": False, "ready_stages": [], "pending_dependencies": [], "next_stage": None}
            )
            
        except Exception as e:
            self.logger.error(f"Dependency check failed: {e}")
            return TaskResponse(
                success=False,
                command_type=CommandType.CHECK_DEPENDENCIES,
                session_id=session_id,
                item_id=item_id,
                stage=TaskStage.TRANSLATION,
                data={},
                error=str(e)
            )
    
    
    # ==========================================
    # Private Implementation Methods
    # ==========================================
    
    async def _execute_task_command(self, command: TaskCommand) -> TaskResponse:
        """タスク実行コマンドの処理"""
        if command.stage == TaskStage.TRANSLATION:
            return await self.execute_translation_task(command)
        elif command.stage == TaskStage.DESCRIPTION:
            return await self.execute_description_task(command)
        elif command.stage == TaskStage.IMAGE:
            return await self.execute_image_task(command)
        elif command.stage == TaskStage.OCR:
            return await self.execute_ocr_task(command)
        else:
            raise ValueError(f"Unknown task stage: {command.stage}")
    
    
    async def _execute_stage_task(self, command: TaskCommand, stage: TaskStage) -> TaskResponse:
        """特定ステージのタスク実行"""
        try:
            # Mark task as running
            # This method is now simplified, so we just return a placeholder response
            # In a real scenario, you would query the state service here
            
            # Create execution request
            execution_request = TaskExecutionRequest(
                session_id=command.session_id,
                item_id=command.item_id,
                item_text=command.payload.get("item_text", ""),
                stage=stage,
                category=command.payload.get("category", "Other"),
                execution_mode=command.execution_mode,
                metadata=command.metadata
            )
            
            # Execute task using execution service
            if stage == TaskStage.TRANSLATION:
                result = await self.execution_service.execute_translation(execution_request)
            elif stage == TaskStage.DESCRIPTION:
                result = await self.execution_service.execute_description_generation(execution_request)
            elif stage == TaskStage.IMAGE:
                result = await self.execution_service.execute_image_generation(execution_request)
            elif stage == TaskStage.OCR:
                result = await self.execution_service.execute_ocr(execution_request)
            else:
                raise ValueError(f"Unsupported stage: {stage}")
            
            # Save result to state service
            # This method is now simplified, so we just return a placeholder response
            # In a real scenario, you would query the state service here
            
            # Return response
            return TaskResponse(
                success=result.success,
                command_type=CommandType.EXECUTE_TASK,
                session_id=command.session_id,
                item_id=command.item_id,
                stage=stage,
                data=result.result_data,
                error=result.error,
                execution_time=result.execution_time
            )
            
        except Exception as e:
            self.logger.error(f"Stage task execution failed: {e}")
            return TaskResponse(
                success=False,
                command_type=CommandType.EXECUTE_TASK,
                session_id=command.session_id,
                item_id=command.item_id,
                stage=stage,
                data={},
                error=str(e)
            )
    
    
    async def _mark_running_command(self, command: TaskCommand) -> TaskResponse:
        """実行中マークコマンドの処理"""
        try:
            # This method is now simplified, so we just return a placeholder response
            # In a real scenario, you would query the state service here
            return TaskResponse(
                success=True,
                command_type=CommandType.MARK_RUNNING,
                session_id=command.session_id,
                item_id=command.item_id,
                stage=command.stage,
                data={"marked_running": True}
            )
            
        except Exception as e:
            self.logger.error(f"Mark running failed: {e}")
            return TaskResponse(
                success=False,
                command_type=CommandType.MARK_RUNNING,
                session_id=command.session_id,
                item_id=command.item_id,
                stage=command.stage,
                data={},
                error=str(e)
            )
    
    
    async def _get_progress_command(self, command: TaskCommand) -> TaskResponse:
        """進捗取得コマンドの処理"""
        try:
            # This method is now simplified, so we just return a placeholder response
            # In a real scenario, you would query the state service here
            return TaskResponse(
                success=True,
                command_type=CommandType.GET_PROGRESS,
                session_id=command.session_id,
                item_id=command.item_id,
                stage=command.stage,
                data={"progress": 0.0, "message": "Progress not fully implemented"}
            )
            
        except Exception as e:
            self.logger.error(f"Get progress failed: {e}")
            return TaskResponse(
                success=False,
                command_type=CommandType.GET_PROGRESS,
                session_id=command.session_id,
                item_id=command.item_id,
                stage=command.stage,
                data={},
                error=str(e)
            )
    
    
    # ==========================================
    # Utility Methods
    # ==========================================
    
    async def get_interface_statistics(self) -> Dict[str, Any]:
        """インターフェース統計取得"""
        try:
            execution_stats = self.execution_service.get_execution_statistics()
            # This method is now simplified, so we just return a placeholder response
            # In a real scenario, you would query the state service here
            return {
                "interface_status": "active",
                "execution_service": execution_stats,
                "state_service": {"status": "not_implemented", "message": "State service not fully implemented"},
                "supported_commands": [cmd.value for cmd in CommandType],
                "supported_stages": [stage.value for stage in TaskStage]
            }
            
        except Exception as e:
            return {
                "interface_status": "degraded",
                "error": str(e)
            }
    
    
    async def health_check(self) -> Dict[str, Any]:
        """ヘルスチェック"""
        try:
            execution_health = await self.execution_service.health_check()
            # This method is now simplified, so we just return a placeholder response
            # In a real scenario, you would query the state service here
            return {
                "status": "healthy",
                "execution_service": execution_health,
                "state_service": {"status": "not_implemented", "message": "State service not fully implemented"},
                "overall_health": execution_health.get("overall_health", False)
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "execution_service": {"status": "unknown"},
                "state_service": {"status": "unknown"},
                "overall_health": False
            }


# ==========================================
# Convenience Factory Functions
# ==========================================

def create_service_task_interface() -> ServiceTaskInterface:
    """
    サービスタスクインターフェースのファクトリー関数
    
    Returns:
        ServiceTaskInterface: 設定済みインターフェース
    """
    return ServiceTaskInterface()


def create_task_command(
    command_type: CommandType,
    session_id: str,
    item_id: int,
    stage: TaskStage,
    execution_mode: ExecutionMode = ExecutionMode.REAL,
    payload: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> TaskCommand:
    """
    タスクコマンドのファクトリー関数
    
    Args:
        command_type: コマンドタイプ
        session_id: セッションID
        item_id: アイテムID
        stage: タスクステージ
        execution_mode: 実行モード
        payload: ペイロードデータ
        metadata: メタデータ
        
    Returns:
        TaskCommand: 作成されたコマンド
    """
    return TaskCommand(
        command_type=command_type,
        session_id=session_id,
        item_id=item_id,
        stage=stage,
        execution_mode=execution_mode,
        payload=payload or {},
        metadata=metadata or {}
    )


# ==========================================
# Export
# ==========================================

__all__ = [
    "TaskInterface",
    "ServiceTaskInterface", 
    "TaskCommand",
    "TaskResponse",
    "CommandType",
    "create_service_task_interface",
    "create_task_command"
]