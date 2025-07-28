"""
SSE（Server-Sent Events）設定
リアルタイム進行状況通知、ハートビート、接続管理設定を管理
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()


class SSESettings(BaseModel):
    """SSE（Server-Sent Events）設定クラス"""
    
    # ===== SSE基本設定 =====
    sse_heartbeat_interval: int = int(os.getenv("SSE_HEARTBEAT_INTERVAL", 5))  # ハートビート間隔（秒）
    sse_ping_interval: int = int(os.getenv("SSE_PING_INTERVAL", 15))  # Ping間隔（秒）
    sse_max_no_pong_time: int = int(os.getenv("SSE_MAX_NO_PONG_TIME", 60))  # Pongタイムアウト（秒）
    
    # ===== SSE接続管理設定 =====
    sse_max_connections: int = int(os.getenv("SSE_MAX_CONNECTIONS", 1000))  # 最大同時接続数
    sse_connection_timeout: int = int(os.getenv("SSE_CONNECTION_TIMEOUT", 300))  # 接続タイムアウト（5分）
    sse_retry_interval: int = int(os.getenv("SSE_RETRY_INTERVAL", 3000))  # クライアント再接続間隔（ミリ秒）
    
    # ===== SSEメッセージ設定 =====
    sse_max_message_size: int = int(os.getenv("SSE_MAX_MESSAGE_SIZE", 8192))  # 最大メッセージサイズ（バイト）
    sse_compression_enabled: bool = os.getenv("SSE_COMPRESSION_ENABLED", "false").lower() == "true"  # メッセージ圧縮
    sse_json_encoding: str = os.getenv("SSE_JSON_ENCODING", "utf-8")  # JSON エンコーディング
    
    # ===== SSE進行状況通知設定 =====
    sse_progress_throttle: float = float(os.getenv("SSE_PROGRESS_THROTTLE", 0.5))  # 進行状況更新間隔（秒）
    sse_batch_progress_enabled: bool = os.getenv("SSE_BATCH_PROGRESS_ENABLED", "true").lower() == "true"  # バッチ進行状況通知
    sse_detailed_progress: bool = os.getenv("SSE_DETAILED_PROGRESS", "true").lower() == "true"  # 詳細進行状況
    
    # ===== SSEイベント設定 =====
    sse_event_types: list = [
        "progress",      # 進行状況更新
        "stage_start",   # Stage開始
        "stage_complete", # Stage完了
        "error",         # エラー通知
        "heartbeat",     # ハートビート
        "ping",          # Ping
        "pong",          # Pong
        "connection",    # 接続状態
        "result"         # 結果通知
    ]
    
    # ===== SSEセキュリティ設定 =====
    sse_cors_enabled: bool = os.getenv("SSE_CORS_ENABLED", "true").lower() == "true"  # CORS有効化
    sse_auth_required: bool = os.getenv("SSE_AUTH_REQUIRED", "false").lower() == "true"  # 認証必須
    sse_rate_limit_enabled: bool = os.getenv("SSE_RATE_LIMIT_ENABLED", "true").lower() == "true"  # レート制限
    sse_max_events_per_minute: int = int(os.getenv("SSE_MAX_EVENTS_PER_MINUTE", 60))  # 分あたり最大イベント数
    
    class Config:
        env_file = ".env"
    
    def get_heartbeat_config(self) -> dict:
        """ハートビート設定辞書を取得"""
        return {
            "heartbeat_interval": self.sse_heartbeat_interval,
            "ping_interval": self.sse_ping_interval,
            "max_no_pong_time": self.sse_max_no_pong_time
        }
    
    def get_connection_config(self) -> dict:
        """接続管理設定辞書を取得"""
        return {
            "max_connections": self.sse_max_connections,
            "connection_timeout": self.sse_connection_timeout,
            "retry_interval": self.sse_retry_interval
        }
    
    def get_message_config(self) -> dict:
        """メッセージ設定辞書を取得"""
        return {
            "max_message_size": self.sse_max_message_size,
            "compression_enabled": self.sse_compression_enabled,
            "json_encoding": self.sse_json_encoding
        }
    
    def get_progress_config(self) -> dict:
        """進行状況通知設定辞書を取得"""
        return {
            "progress_throttle": self.sse_progress_throttle,
            "batch_progress_enabled": self.sse_batch_progress_enabled,
            "detailed_progress": self.sse_detailed_progress
        }
    
    def get_security_config(self) -> dict:
        """セキュリティ設定辞書を取得"""
        return {
            "cors_enabled": self.sse_cors_enabled,
            "auth_required": self.sse_auth_required,
            "rate_limit_enabled": self.sse_rate_limit_enabled,
            "max_events_per_minute": self.sse_max_events_per_minute
        }
    
    def get_event_headers(self) -> dict:
        """SSEレスポンスヘッダーを取得"""
        headers = {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # nginx用
        }
        
        if self.sse_cors_enabled:
            headers.update({
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
                "Access-Control-Allow-Methods": "GET, OPTIONS"
            })
        
        return headers
    
    def format_sse_message(self, event_type: str, data: Any, event_id: Optional[str] = None) -> str:
        """SSEメッセージをフォーマット"""
        import json
        
        # データをJSON文字列に変換
        if isinstance(data, dict) or isinstance(data, list):
            data_str = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
        else:
            data_str = str(data)
        
        # メッセージサイズチェック
        if len(data_str.encode(self.sse_json_encoding)) > self.sse_max_message_size:
            # メッセージが大きすぎる場合は切り詰める
            data_str = data_str[:self.sse_max_message_size//2] + "...[truncated]"
        
        # SSEフォーマットに変換
        message_parts = []
        
        if event_id:
            message_parts.append(f"id: {event_id}")
        
        if event_type in self.sse_event_types:
            message_parts.append(f"event: {event_type}")
        
        # データを複数行に分割（SSE仕様）
        for line in data_str.split('\n'):
            message_parts.append(f"data: {line}")
        
        message_parts.append("")  # 空行で終了
        
        return "\n".join(message_parts) + "\n"
    
    def create_heartbeat_message(self, timestamp: Optional[float] = None) -> str:
        """ハートビートメッセージを作成"""
        import time
        
        if timestamp is None:
            timestamp = time.time()
        
        data = {
            "type": "heartbeat",
            "timestamp": timestamp,
            "server_time": int(timestamp)
        }
        
        return self.format_sse_message("heartbeat", data)
    
    def create_ping_message(self, ping_id: str) -> str:
        """Pingメッセージを作成"""
        import time
        
        data = {
            "type": "ping",
            "ping_id": ping_id,
            "timestamp": time.time()
        }
        
        return self.format_sse_message("ping", data)
    
    def create_progress_message(self, stage: int, status: str, message: str, 
                              metadata: Optional[Dict] = None, event_id: Optional[str] = None) -> str:
        """進行状況メッセージを作成"""
        import time
        
        data = {
            "stage": stage,
            "status": status,
            "message": message,
            "timestamp": time.time()
        }
        
        if metadata:
            data["metadata"] = metadata
        
        return self.format_sse_message("progress", data, event_id)
    
    def create_error_message(self, error_type: str, error_message: str, 
                           stage: Optional[int] = None) -> str:
        """エラーメッセージを作成"""
        import time
        
        data = {
            "type": "error",
            "error_type": error_type,
            "message": error_message,
            "timestamp": time.time()
        }
        
        if stage is not None:
            data["stage"] = stage
        
        return self.format_sse_message("error", data)
    
    def is_valid_event_type(self, event_type: str) -> bool:
        """イベントタイプの妥当性をチェック"""
        return event_type in self.sse_event_types
    
    def should_throttle_progress(self, last_update: float) -> bool:
        """進行状況更新をスロットルするかチェック"""
        import time
        return (time.time() - last_update) < self.sse_progress_throttle
    
    def validate_configuration(self) -> list:
        """SSE設定の妥当性を検証"""
        issues = []
        
        # 間隔設定の検証
        if self.sse_heartbeat_interval <= 0:
            issues.append("SSE_HEARTBEAT_INTERVAL must be positive")
        
        if self.sse_ping_interval <= 0:
            issues.append("SSE_PING_INTERVAL must be positive")
        
        if self.sse_max_no_pong_time <= 0:
            issues.append("SSE_MAX_NO_PONG_TIME must be positive")
        
        # 接続設定の検証
        if self.sse_max_connections <= 0:
            issues.append("SSE_MAX_CONNECTIONS must be positive")
        
        if self.sse_connection_timeout <= 0:
            issues.append("SSE_CONNECTION_TIMEOUT must be positive")
        
        if self.sse_retry_interval <= 0:
            issues.append("SSE_RETRY_INTERVAL must be positive")
        
        # メッセージ設定の検証
        if self.sse_max_message_size <= 0:
            issues.append("SSE_MAX_MESSAGE_SIZE must be positive")
        
        if self.sse_max_message_size > 1024 * 1024:  # 1MB
            issues.append("SSE_MAX_MESSAGE_SIZE should not exceed 1MB")
        
        # 進行状況設定の検証
        if self.sse_progress_throttle < 0:
            issues.append("SSE_PROGRESS_THROTTLE must be non-negative")
        
        if self.sse_progress_throttle > 10:
            issues.append("SSE_PROGRESS_THROTTLE should not exceed 10 seconds")
        
        # セキュリティ設定の検証
        if self.sse_max_events_per_minute <= 0:
            issues.append("SSE_MAX_EVENTS_PER_MINUTE must be positive")
        
        if self.sse_max_events_per_minute > 1000:
            issues.append("SSE_MAX_EVENTS_PER_MINUTE should not exceed 1000")
        
        # エンコーディング検証
        valid_encodings = ["utf-8", "utf-16", "ascii"]
        if self.sse_json_encoding not in valid_encodings:
            issues.append(f"SSE_JSON_ENCODING must be one of {valid_encodings}")
        
        # 論理的整合性の検証
        if self.sse_heartbeat_interval >= self.sse_ping_interval:
            issues.append("SSE_HEARTBEAT_INTERVAL should be less than SSE_PING_INTERVAL")
        
        if self.sse_ping_interval >= self.sse_max_no_pong_time:
            issues.append("SSE_PING_INTERVAL should be less than SSE_MAX_NO_PONG_TIME")
        
        return issues
    
    def get_performance_recommendations(self) -> list:
        """SSEパフォーマンス改善の推奨事項を取得"""
        recommendations = []
        
        # ハートビート間隔の推奨
        if self.sse_heartbeat_interval < 3:
            recommendations.append("Consider increasing SSE_HEARTBEAT_INTERVAL to reduce server load")
        
        if self.sse_heartbeat_interval > 10:
            recommendations.append("Consider decreasing SSE_HEARTBEAT_INTERVAL for better responsiveness")
        
        # 最大接続数の推奨
        if self.sse_max_connections > 5000:
            recommendations.append("SSE_MAX_CONNECTIONS is very high - ensure server can handle the load")
        
        # メッセージサイズの推奨
        if self.sse_max_message_size > 64 * 1024:  # 64KB
            recommendations.append("Consider reducing SSE_MAX_MESSAGE_SIZE for better performance")
        
        # 進行状況スロットルの推奨
        if self.sse_progress_throttle < 0.1:
            recommendations.append("Consider increasing SSE_PROGRESS_THROTTLE to reduce message frequency")
        
        # 圧縮の推奨
        if not self.sse_compression_enabled and self.sse_max_message_size > 1024:
            recommendations.append("Consider enabling SSE_COMPRESSION_ENABLED for large messages")
        
        # レート制限の推奨
        if not self.sse_rate_limit_enabled:
            recommendations.append("Consider enabling SSE_RATE_LIMIT_ENABLED for production use")
        
        return recommendations
    
    def get_status_summary(self) -> dict:
        """SSE設定の状態サマリーを取得"""
        return {
            "heartbeat_interval": self.sse_heartbeat_interval,
            "max_connections": self.sse_max_connections,
            "compression_enabled": self.sse_compression_enabled,
            "cors_enabled": self.sse_cors_enabled,
            "auth_required": self.sse_auth_required,
            "rate_limit_enabled": self.sse_rate_limit_enabled,
            "supported_events": len(self.sse_event_types),
            "configuration_issues": len(self.validate_configuration()),
            "performance_recommendations": len(self.get_performance_recommendations())
        }


# グローバルインスタンス
sse_settings = SSESettings()


# 後方互換性のための関数（移行期間中のみ使用）
def get_sse_settings():
    """SSE設定を取得（後方互換性用）"""
    return sse_settings 