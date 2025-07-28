"""
🚀 TaskCoordinator - タスク投入調整専用サービス

このサービスはCeleryタスクキューへの投入調整とエラーハンドリングを担当します。
エンドポイントからタスク管理ロジックを分離し、再利用可能なサービスとして提供します。
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

from .session_manager import ProcessingSession


class TaskType(Enum):
    """タスクタイプ"""
    TRANSLATION = "translation"
    DESCRIPTION = "description"
    IMAGE = "image"


class QueueMode(Enum):
    """キューモード"""
    REAL = "real"
    TEST = "test"


# Task function mappings - avoid direct imports to prevent circular dependencies
PURE_TASK_MAPPING = {
    TaskType.TRANSLATION: {
        QueueMode.REAL: "pure_real_translate_menu_item",
        QueueMode.TEST: "pure_test_translate_menu_item"
    },
    TaskType.DESCRIPTION: {
        QueueMode.REAL: "pure_real_generate_menu_description", 
        QueueMode.TEST: "pure_test_generate_menu_description"
    },
    TaskType.IMAGE: {
        QueueMode.REAL: "pure_real_generate_menu_image",
        QueueMode.TEST: "pure_test_generate_menu_image"  # May not exist
    }
}

LEGACY_TASK_MAPPING = {
    TaskType.TRANSLATION: {
        QueueMode.REAL: "real_translate_menu_item",
        QueueMode.TEST: "test_translate_menu_item"
    },
    TaskType.DESCRIPTION: {
        QueueMode.REAL: "real_generate_menu_description",
        QueueMode.TEST: "test_generate_menu_description"
    },
    TaskType.IMAGE: {
        QueueMode.REAL: "real_generate_menu_image",
        QueueMode.TEST: "test_generate_menu_image"  # May not exist
    }
}


@dataclass
class TaskInfo:
    """タスク情報"""
    task_id: str
    task_type: TaskType
    item_id: int
    item_text: str
    queue_name: str
    category: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class TaskBatch:
    """タスクバッチ情報"""
    session_id: str
    total_tasks: int
    queued_tasks: List[TaskInfo]
    failed_tasks: List[TaskInfo]
    queue_mode: QueueMode

    @property
    def success_rate(self) -> float:
        """成功率を計算"""
        if self.total_tasks == 0:
            return 0.0
        successful_tasks = self.total_tasks - len(self.failed_tasks)
        return (successful_tasks / self.total_tasks) * 100


class TaskCoordinator:
    """
    タスク投入調整専用サービス
    
    責任:
    - タスクキュー選択
    - 並列タスク投入
    - エラーハンドリング
    - タスク投入統計
    """

    def __init__(self, use_pure_tasks: bool = True):
        self._task_batches: Dict[str, TaskBatch] = {}
        self._use_pure_tasks = use_pure_tasks  # フィーチャーフラグ
        
        # キュー設定
        self._queue_config = {
            QueueMode.REAL: {
                TaskType.TRANSLATION: "real_translate_queue",
                TaskType.DESCRIPTION: "real_description_queue",
                TaskType.IMAGE: "real_image_queue"
            },
            QueueMode.TEST: {
                TaskType.TRANSLATION: "translate_queue", 
                TaskType.DESCRIPTION: "description_queue",
                TaskType.IMAGE: "image_queue"
            }
        }
        
        # タスク関数キャッシュ - 遅延インポートのため
        self._task_function_cache = {}
    
    def _get_task_function(self, task_type: TaskType, queue_mode: QueueMode, use_pure: bool = None):
        """
        遅延インポートでタスク関数を取得
        
        Args:
            task_type: タスクタイプ
            queue_mode: キューモード
            use_pure: 純粋タスクを使用するか（Noneの場合はインスタンス設定を使用）
        
        Returns:
            タスク関数またはNone
        """
        if use_pure is None:
            use_pure = self._use_pure_tasks
        
        # キャッシュキーを生成
        cache_key = f"{task_type.value}_{queue_mode.value}_{use_pure}"
        
        if cache_key not in self._task_function_cache:
            try:
                if use_pure:
                    # 純粋タスクから取得
                    task_name = PURE_TASK_MAPPING[task_type][queue_mode]
                    from app.tasks import pure_menu_tasks
                    task_function = getattr(pure_menu_tasks, task_name, None)
                else:
                    # レガシータスクから取得
                    task_name = LEGACY_TASK_MAPPING[task_type][queue_mode]
                    from app.tasks import menu_item_parallel_tasks
                    task_function = getattr(menu_item_parallel_tasks, task_name, None)
                
                self._task_function_cache[cache_key] = task_function
            except (ImportError, AttributeError, KeyError) as e:
                logger.warning(f"Failed to import task function for {cache_key}: {e}")
                self._task_function_cache[cache_key] = None
        
        return self._task_function_cache[cache_key]

    async def queue_processing_tasks(
        self, 
        session: ProcessingSession, 
        categories: Optional[Dict[str, List[str]]] = None
    ) -> TaskBatch:
        """
        処理タスクを一括投入
        
        Args:
            session: 処理セッション
            categories: カテゴリ分類データ（オプション）
            
        Returns:
            TaskBatch: タスクバッチ情報
        """
        queue_mode = QueueMode.TEST if session.api_mode == "test_mode" else QueueMode.REAL
        
        # タスクバッチ初期化
        task_batch = TaskBatch(
            session_id=session.session_id,
            total_tasks=0,
            queued_tasks=[],
            failed_tasks=[],
            queue_mode=queue_mode
        )
        
        # メニューアイテムからタスク生成
        if categories:
            # カテゴリ分類済みの場合
            item_id = 0
            for category, items in categories.items():
                for item in items:
                    item_text = item if isinstance(item, str) else item.get('name', str(item))
                    await self._queue_item_tasks(
                        task_batch, session.session_id, item_id, item_text, category
                    )
                    item_id += 1
        else:
            # 通常のメニューアイテムリスト
            for item_id, item_text in enumerate(session.menu_items):
                await self._queue_item_tasks(
                    task_batch, session.session_id, item_id, item_text
                )
        
        # バッチ保存
        self._task_batches[session.session_id] = task_batch
        
        return task_batch

    async def queue_translation_tasks(
        self, 
        session_id: str, 
        items: List[str], 
        queue_mode: QueueMode = QueueMode.REAL
    ) -> List[TaskInfo]:
        """
        翻訳タスクのみを投入
        
        Args:
            session_id: セッションID
            items: アイテムリスト
            queue_mode: キューモード
            
        Returns:
            List[TaskInfo]: 投入されたタスク情報
        """
        tasks = []
        
        for item_id, item_text in enumerate(items):
            task_info = await self._queue_single_task(
                session_id, item_id, item_text, TaskType.TRANSLATION, queue_mode
            )
            if task_info:
                tasks.append(task_info)
        
        return tasks

    async def queue_description_tasks(
        self, 
        session_id: str, 
        items: List[str], 
        queue_mode: QueueMode = QueueMode.REAL
    ) -> List[TaskInfo]:
        """
        説明生成タスクのみを投入
        
        Args:
            session_id: セッションID
            items: アイテムリスト
            queue_mode: キューモード
            
        Returns:
            List[TaskInfo]: 投入されたタスク情報
        """
        tasks = []
        
        for item_id, item_text in enumerate(items):
            task_info = await self._queue_single_task(
                session_id, item_id, item_text, TaskType.DESCRIPTION, queue_mode
            )
            if task_info:
                tasks.append(task_info)
        
        return tasks

    def get_task_batch(self, session_id: str) -> Optional[TaskBatch]:
        """
        タスクバッチ情報を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            TaskBatch: タスクバッチ（存在しない場合はNone）
        """
        return self._task_batches.get(session_id)

    def get_task_statistics(self) -> Dict[str, Any]:
        """
        タスク統計を取得
        
        Returns:
            Dict: 統計情報
        """
        total_batches = len(self._task_batches)
        total_tasks = sum(batch.total_tasks for batch in self._task_batches.values())
        total_failed = sum(len(batch.failed_tasks) for batch in self._task_batches.values())
        
        return {
            "total_batches": total_batches,
            "total_tasks_queued": total_tasks,
            "total_failed_tasks": total_failed,
            "success_rate": ((total_tasks - total_failed) / total_tasks * 100) if total_tasks > 0 else 0,
            "average_batch_size": total_tasks / total_batches if total_batches > 0 else 0,
            "real_mode_batches": sum(1 for b in self._task_batches.values() if b.queue_mode == QueueMode.REAL),
            "test_mode_batches": sum(1 for b in self._task_batches.values() if b.queue_mode == QueueMode.TEST),
            "task_mode": "pure" if self._use_pure_tasks else "legacy",
            "using_pure_tasks": self._use_pure_tasks
        }

    def switch_to_pure_tasks(self) -> None:
        """純粋タスク関数に切り替え"""
        self._use_pure_tasks = True
        # キャッシュをクリアして新しいモードでタスク関数を再取得
        self._task_function_cache.clear()
    
    def switch_to_legacy_tasks(self) -> None:
        """レガシータスク関数に切り替え"""
        self._use_pure_tasks = False
        # キャッシュをクリアして新しいモードでタスク関数を再取得
        self._task_function_cache.clear()
    
    def is_using_pure_tasks(self) -> bool:
        """純粋タスク関数を使用中かどうか"""
        return self._use_pure_tasks
    
    def get_task_mode_info(self) -> Dict[str, Any]:
        """タスクモード情報を取得"""
        return {
            "using_pure_tasks": self._use_pure_tasks,
            "available_modes": ["pure", "legacy"],
            "current_mode": "pure" if self._use_pure_tasks else "legacy",
            "cache_size": len(self._task_function_cache),
            "cached_functions": list(self._task_function_cache.keys())
        }

    async def cleanup_batch(self, session_id: str) -> bool:
        """
        タスクバッチをクリーンアップ
        
        Args:
            session_id: セッションID
            
        Returns:
            bool: クリーンアップ実行フラグ
        """
        if session_id in self._task_batches:
            del self._task_batches[session_id]
            return True
        return False

    async def _queue_item_tasks(
        self, 
        task_batch: TaskBatch, 
        session_id: str, 
        item_id: int, 
        item_text: str, 
        category: str = "Other"
    ) -> None:
        """アイテム用のタスクを投入"""
        # 翻訳タスク
        translation_task = await self._queue_single_task(
            session_id, item_id, item_text, TaskType.TRANSLATION, task_batch.queue_mode, category
        )
        if translation_task:
            task_batch.queued_tasks.append(translation_task)
            task_batch.total_tasks += 1
        else:
            task_batch.failed_tasks.append(
                TaskInfo("failed", TaskType.TRANSLATION, item_id, item_text, "none")
            )
        
        # 説明生成タスク
        description_task = await self._queue_single_task(
            session_id, item_id, item_text, TaskType.DESCRIPTION, task_batch.queue_mode, category
        )
        if description_task:
            task_batch.queued_tasks.append(description_task)
            task_batch.total_tasks += 1
        else:
            task_batch.failed_tasks.append(
                TaskInfo("failed", TaskType.DESCRIPTION, item_id, item_text, "none")
            )

    async def _queue_single_task(
        self, 
        session_id: str, 
        item_id: int, 
        item_text: str, 
        task_type: TaskType, 
        queue_mode: QueueMode,
        category: str = "Other"
    ) -> Optional[TaskInfo]:
        """単一タスクを投入"""
        try:
            # キュー名取得
            queue_name = self._queue_config[queue_mode][task_type]
            
            # タスク関数取得（動的インポート）
            task_function = self._get_task_function(task_type, queue_mode)
            
            # タスク関数が None の場合はスキップ（未実装のタスクタイプ）
            if task_function is None:
                logger.warning(f"Task function not available for {task_type.value} in {queue_mode.value} mode")
                return None
            
            # タスク引数準備
            if queue_mode == QueueMode.REAL:
                if task_type == TaskType.TRANSLATION:
                    args = [session_id, item_id, item_text, category]
                else:  # DESCRIPTION
                    args = [session_id, item_id, item_text, "", category]
            else:  # TEST
                args = [session_id, item_id, item_text]
            
            # タスク投入
            result = task_function.apply_async(args=args, queue=queue_name)
            
            return TaskInfo(
                task_id=result.id,
                task_type=task_type,
                item_id=item_id,
                item_text=item_text,
                queue_name=queue_name,
                category=category,
                metadata={
                    "queue_mode": queue_mode.value,
                    "celery_task_id": result.id
                }
            )
            
        except Exception as e:
            print(f"❌ Failed to queue {task_type.value} task for item {item_id}: {str(e)}")
            return None