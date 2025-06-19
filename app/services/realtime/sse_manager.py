"""
Server-Sent Events (SSE) 管理サービス
"""
import asyncio
from typing import Dict, Any, Optional
from .types import SessionId, ProgressData, PingData, ProgressStatus
from .session_manager import get_session_manager

class SSEManager:
    """SSE通信を管理するクラス"""
    
    def __init__(self):
        self.session_manager = get_session_manager()
        # 設定値の取得
        self._get_settings()
    
    def _get_settings(self):
        """設定値を取得（循環インポート回避）"""
        try:
            from app.core.config import settings
            self.ping_interval = settings.SSE_PING_INTERVAL
            self.max_no_pong_time = settings.SSE_MAX_NO_PONG_TIME
        except ImportError:
            # フォールバック値
            self.ping_interval = 30  # 30秒
            self.max_no_pong_time = 120  # 2分
    
    async def send_progress(
        self, 
        session_id: SessionId, 
        stage: int, 
        status: str, 
        message: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """進行状況をクライアントに送信（Ping/Pong対応 + リアルタイム反映強化）"""
        
        # ProgressDataオブジェクトを作成
        try:
            progress_status = ProgressStatus(status)
        except ValueError:
            # 不明なステータスの場合はACTIVEとして扱う
            progress_status = ProgressStatus.ACTIVE
        
        progress_data = {
            "stage": stage,
            "status": status,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        if data:
            progress_data.update(data)
        
        # セッションマネージャーに追加
        self.session_manager.add_progress(session_id, progress_data)
        
        # 送信データの詳細ログ（デバッグ用）
        self._log_progress_data(session_id, stage, status, message, data)
        
        # Stage 4でのPing/Pong開始（重複回避）
        if (stage == 4 and status == "active" and 
            not self.session_manager.is_ping_scheduled(session_id)):
            self.session_manager.set_ping_scheduled(session_id, True)
            asyncio.create_task(self.start_ping_pong(session_id))
    
    def _log_progress_data(
        self, 
        session_id: SessionId, 
        stage: int, 
        status: str, 
        message: str, 
        data: Optional[Dict[str, Any]]
    ) -> None:
        """進行状況データのログ出力"""
        data_keys = list(data.keys()) if data else []
        data_summary = {}
        
        if data:
            for key in ['translatedCategories', 'translated_categories', 'partial_results', 
                       'partial_menu', 'processing_category']:
                if key in data:
                    if isinstance(data[key], dict):
                        data_summary[key] = f"{len(data[key])} categories"
                    else:
                        data_summary[key] = str(data[key])
        
        print(f"📤 SSE Data sent for {session_id}: Stage {stage} - {status}")
        print(f"   📋 Message: {message}")
        print(f"   🔑 Data keys: {data_keys}")
        print(f"   📊 Data summary: {data_summary}")
        
        # Stage別の詳細ログ
        if stage == 3:
            self._log_stage3_data(data)
        elif stage == 4:
            self._log_stage4_data(data)
    
    def _log_stage3_data(self, data: Optional[Dict[str, Any]]) -> None:
        """Stage 3翻訳データのログ"""
        if data and ('translatedCategories' in data or 'translated_categories' in data):
            translated_data = data.get('translatedCategories') or data.get('translated_categories')
            if translated_data and isinstance(translated_data, dict):
                print(f"   🌍 Stage 3 translation data: {len(translated_data)} categories")
                for cat_name, items in translated_data.items():
                    if isinstance(items, list):
                        print(f"      - {cat_name}: {len(items)} items")
    
    def _log_stage4_data(self, data: Optional[Dict[str, Any]]) -> None:
        """Stage 4説明データのログ"""
        if data:
            if "processing_category" in data:
                print(f"   🍽️ Processing: {data['processing_category']}")
            if "category_completed" in data:
                print(f"   ✅ Completed: {data['category_completed']}")
            if "progress_percent" in data:
                print(f"   📊 Progress: {data['progress_percent']}%")
            if "partial_results" in data and isinstance(data['partial_results'], dict):
                print(f"   🔄 Partial results: {len(data['partial_results'])} categories")
            if "partial_menu" in data and isinstance(data['partial_menu'], dict):
                print(f"   🔄 Partial menu: {len(data['partial_menu'])} categories")
    
    async def send_ping(self, session_id: SessionId) -> None:
        """クライアントにPingを送信"""
        if self.session_manager.session_exists(session_id):
            ping_data = PingData(session_id)
            self.session_manager.add_progress(session_id, ping_data.to_dict())
            print(f"🏓 Ping sent to {session_id}")
    
    async def start_ping_pong(self, session_id: SessionId) -> None:
        """Ping/Pong機能を開始"""
        print(f"🏓 Starting Ping/Pong for session {session_id}")
        
        # Ping/Pongセッションを作成
        self.session_manager.create_ping_pong_session(session_id)
        
        try:
            while (self.session_manager.session_exists(session_id) and 
                   self.session_manager.is_ping_pong_active(session_id)):
                
                # Ping送信
                await self.send_ping(session_id)
                self.session_manager.increment_ping_count(session_id)
                
                # Pongチェック
                await self._check_pong_timeout(session_id)
                
                # 指定間隔で待機
                await asyncio.sleep(self.ping_interval)
                
        except asyncio.CancelledError:
            print(f"🏓 Ping/Pong cancelled for session {session_id}")
        except Exception as e:
            print(f"⚠️ Ping/Pong error for session {session_id}: {e}")
        finally:
            # クリーンアップ
            self._cleanup_ping_pong(session_id)
    
    async def _check_pong_timeout(self, session_id: SessionId) -> None:
        """Pongタイムアウトをチェック"""
        ping_pong_session = self.session_manager.get_ping_pong_session(session_id)
        if ping_pong_session:
            current_time = asyncio.get_event_loop().time()
            time_since_last_pong = current_time - ping_pong_session.last_pong
            
            if time_since_last_pong > self.max_no_pong_time:
                print(f"⚠️ No Pong received from {session_id} for {self.max_no_pong_time}s, connection may be lost")
                # 接続切断を検知（ただし処理は継続）
                await self.send_progress(
                    session_id, 
                    0, 
                    "warning", 
                    f"Connection unstable (no response for {self.max_no_pong_time}s)",
                    {"connection_warning": True}
                )
    
    def _cleanup_ping_pong(self, session_id: SessionId) -> None:
        """Ping/Pongのクリーンアップ"""
        if self.session_manager.get_ping_pong_session(session_id):
            self.session_manager.deactivate_ping_pong(session_id)
        
        self.session_manager.set_ping_scheduled(session_id, False)
        print(f"🏓 Ping/Pong cleanup completed for {session_id}")
    
    async def handle_pong(self, session_id: SessionId) -> bool:
        """クライアントからのPongを処理"""
        success = self.session_manager.update_last_pong(session_id)
        if success:
            print(f"🏓 Pong received from {session_id}")
        return success
    
    async def stage4_heartbeat(self, session_id: SessionId, initial_message: str) -> None:
        """Stage 4専用のハートビート機能（廃止済み - Ping/Pongに置き換え）"""
        print(f"💓 Legacy heartbeat function called for {session_id}, but Ping/Pong is now used instead")
        # この関数は何もしない（Ping/Pong機能が置き換え）
        pass

# シングルトンインスタンスを取得する関数
_sse_manager_instance: Optional[SSEManager] = None

def get_sse_manager() -> SSEManager:
    """SSEManagerのシングルトンインスタンスを取得"""
    global _sse_manager_instance
    if _sse_manager_instance is None:
        _sse_manager_instance = SSEManager()
    return _sse_manager_instance 