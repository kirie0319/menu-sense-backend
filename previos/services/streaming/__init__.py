"""
📡 Streaming Service Package

このパッケージはSSEストリーミングと進行状況追跡のサービス層を提供します。
グローバル状態を排除し、セッション別のストリーミング管理を実現します。

主要サービス:
- SSEManager: SSEストリーミング管理
- ProgressTracker: 進行状況追跡
- EventBroadcaster: イベント配信（統合）
"""

from .sse_manager import (
    SSEManager,
    SSEEvent,
    StreamSession,
    EventType
)

from .progress_tracker import (
    ProgressTracker,
    ItemProgress,
    SessionProgress,
    ItemStatus
)


# ==========================================
# Integrated Event Broadcasting
# ==========================================

class EventBroadcaster:
    """
    イベント配信統合サービス
    
    SSEManager と ProgressTracker を統合し、
    進行状況の変更を自動的にSSEで配信します。
    """

    def __init__(self, sse_manager: SSEManager, progress_tracker: ProgressTracker):
        self.sse_manager = sse_manager
        self.progress_tracker = progress_tracker

    async def broadcast_progress_update(self, session_id: str, total_items: int) -> bool:
        """
        進行状況更新を配信
        
        Args:
            session_id: セッションID
            total_items: 合計アイテム数
            
        Returns:
            bool: 配信成功フラグ
        """
        try:
            # 現在の進行状況を取得
            current_progress = await self.progress_tracker.track_session_progress(
                session_id, total_items
            )
            
            # 変更があった場合のみ配信
            if self.progress_tracker.detect_progress_changes(session_id, current_progress):
                # 進行状況イベント生成・送信
                progress_event = self.progress_tracker.generate_progress_event(current_progress)
                await self.sse_manager.send_event(session_id, progress_event)
                
                # 完了チェック
                if current_progress.completed_items >= current_progress.total_items:
                    completion_event = self.progress_tracker.generate_completion_event(current_progress)
                    await self.sse_manager.send_event(session_id, completion_event)
                
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Failed to broadcast progress update: {str(e)}")
            return False

    async def broadcast_processing_started(
        self, 
        session_id: str, 
        total_items: int, 
        menu_items: list,
        api_mode: str
    ) -> bool:
        """
        処理開始イベントを配信
        
        Args:
            session_id: セッションID
            total_items: 合計アイテム数
            menu_items: メニューアイテム
            api_mode: APIモード
            
        Returns:
            bool: 配信成功フラグ
        """
        event_data = {
            "type": "processing_started",
            "session_id": session_id,
            "total_items": total_items,
            "menu_items": menu_items,
            "api_integration": api_mode,
            "message": f"🚀 Started processing {total_items} menu items with {api_mode}"
        }
        
        # セッション情報更新
        self.sse_manager.update_session_info(session_id, total_items)
        
        return await self.sse_manager.send_event(session_id, event_data)

    async def broadcast_task_queued(
        self, 
        session_id: str, 
        item_id: int, 
        item_text: str, 
        category: str = "Other"
    ) -> bool:
        """
        タスク投入イベントを配信
        
        Args:
            session_id: セッションID
            item_id: アイテムID
            item_text: アイテムテキスト
            category: カテゴリ
            
        Returns:
            bool: 配信成功フラグ
        """
        event_data = {
            "type": "tasks_queued",
            "session_id": session_id,
            "item_id": item_id,
            "item_text": item_text,
            "category": category,
            "queued_tasks": ["translation", "description"],
            "message": f"📤 Queued processing tasks for: {item_text}"
        }
        
        return await self.sse_manager.send_event(session_id, event_data)

    async def broadcast_parallel_processing_started(
        self, 
        session_id: str, 
        ocr_summary: dict, 
        categorization_summary: dict
    ) -> bool:
        """
        並列処理開始イベントを配信
        
        Args:
            session_id: セッションID
            ocr_summary: OCRサマリー
            categorization_summary: カテゴリ分類サマリー
            
        Returns:
            bool: 配信成功フラグ
        """
        total_items = categorization_summary.get("total_items", 0)
        
        event_data = {
            "type": "parallel_processing_started",
            "session_id": session_id,
            "ocr_result": ocr_summary,
            "categorization_result": categorization_summary,
            "message": f"🚀 OCR → Categorization complete. Starting parallel processing for {total_items} menu items"
        }
        
        # セッション情報更新
        self.sse_manager.update_session_info(session_id, total_items)
        
        return await self.sse_manager.send_event(session_id, event_data)


# ==========================================
# Service Factory Functions  
# ==========================================

def create_sse_manager() -> SSEManager:
    """SSEManagerのインスタンスを作成"""
    return SSEManager()


def create_progress_tracker() -> ProgressTracker:
    """ProgressTrackerのインスタンスを作成"""
    return ProgressTracker()


def create_event_broadcaster(
    sse_manager: SSEManager = None,
    progress_tracker: ProgressTracker = None
) -> EventBroadcaster:
    """
    EventBroadcasterのインスタンスを作成
    
    Args:
        sse_manager: SSE管理サービス（オプション）
        progress_tracker: 進行状況追跡サービス（オプション）
    
    Returns:
        EventBroadcaster: イベント配信サービス
    """
    if sse_manager is None:
        sse_manager = create_sse_manager()
    
    if progress_tracker is None:
        progress_tracker = create_progress_tracker()
    
    return EventBroadcaster(sse_manager, progress_tracker)


def create_streaming_suite() -> tuple[SSEManager, ProgressTracker, EventBroadcaster]:
    """
    完全なストリーミングサービススイートを作成
    
    Returns:
        tuple: (SSEManager, ProgressTracker, EventBroadcaster)
    """
    sse_manager = create_sse_manager()
    progress_tracker = create_progress_tracker()
    event_broadcaster = EventBroadcaster(sse_manager, progress_tracker)
    
    return sse_manager, progress_tracker, event_broadcaster


# ==========================================
# Legacy Support Functions
# ==========================================

def send_sse_event(session_id: str, event_data: dict) -> None:
    """
    レガシー互換性のための関数
    
    Note: 新しいコードでは EventBroadcaster を使用してください
    """
    print(f"⚠️  Legacy send_sse_event called for session {session_id}")
    print(f"    Event type: {event_data.get('type', 'unknown')}")
    print(f"    Please migrate to EventBroadcaster for better session management")


def initialize_session(session_id: str, total_items: int = 0) -> None:
    """
    レガシー互換性のための関数
    
    Note: 新しいコードでは SSEManager.update_session_info を使用してください
    """
    print(f"⚠️  Legacy initialize_session called for session {session_id}")
    print(f"    Total items: {total_items}")
    print(f"    Please migrate to SSEManager for better session management")


# ==========================================
# Public API
# ==========================================

__all__ = [
    # Core classes
    "SSEManager",
    "ProgressTracker", 
    "EventBroadcaster",
    
    # Data classes
    "SSEEvent",
    "StreamSession",
    "EventType",
    "ItemProgress",
    "SessionProgress",
    "ItemStatus",
    
    # Factory functions
    "create_sse_manager",
    "create_progress_tracker",
    "create_event_broadcaster",
    "create_streaming_suite",
    
    # Legacy support
    "send_sse_event",
    "initialize_session"
]