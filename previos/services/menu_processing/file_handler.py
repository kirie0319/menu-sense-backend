"""
📁 FileHandler - ファイル操作専用サービス

このサービスは一時ファイルの保存・管理・クリーンアップを担当します。
エンドポイントからファイル操作ロジックを分離し、安全なファイル管理を提供します。
"""

import os
import time
import uuid
import aiofiles
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from pathlib import Path
from fastapi import UploadFile

from app.core.config.base import base_settings


@dataclass
class FileInfo:
    """ファイル情報"""
    file_id: str
    original_name: str
    saved_path: str
    content_type: str
    size_bytes: int
    created_at: float
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    @property
    def exists(self) -> bool:
        """ファイルが存在するかチェック"""
        return os.path.exists(self.saved_path)

    @property
    def age_seconds(self) -> float:
        """ファイルの経過時間（秒）"""
        return time.time() - self.created_at

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "file_id": self.file_id,
            "original_name": self.original_name,
            "saved_path": self.saved_path,
            "content_type": self.content_type,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "session_id": self.session_id,
            "exists": self.exists,
            "age_seconds": self.age_seconds,
            "metadata": self.metadata
        }


class FileHandler:
    """
    ファイル操作専用サービス
    
    責任:
    - 一時ファイル保存
    - ファイル形式検証
    - ファイル管理
    - 自動クリーンアップ
    """

    def __init__(self):
        self._managed_files: Dict[str, FileInfo] = {}
        self._upload_dir = Path(base_settings.upload_dir)
        self._max_file_age = 3600  # 1時間
        self._max_file_size = 50 * 1024 * 1024  # 50MB
        
        # アップロードディレクトリの作成
        self._upload_dir.mkdir(parents=True, exist_ok=True)

    async def save_temp_file(
        self, 
        file: UploadFile, 
        session_id: Optional[str] = None,
        prefix: str = "temp"
    ) -> FileInfo:
        """
        一時ファイルを保存
        
        Args:
            file: アップロードファイル
            session_id: セッションID（オプション）
            prefix: ファイル名プレフィックス
            
        Returns:
            FileInfo: 保存されたファイル情報
            
        Raises:
            ValueError: ファイル検証エラー
            IOError: ファイル保存エラー
        """
        # ファイル検証
        await self._validate_upload_file(file)
        
        # ファイルID生成
        file_id = self._generate_file_id()
        
        # ファイルパス生成
        file_path = self._generate_file_path(file_id, file.filename, prefix, session_id)
        
        try:
            # ファイル保存
            content = await file.read()
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # ファイル情報作成
            file_info = FileInfo(
                file_id=file_id,
                original_name=file.filename,
                saved_path=str(file_path),
                content_type=file.content_type,
                size_bytes=len(content),
                created_at=time.time(),
                session_id=session_id,
                metadata={
                    "prefix": prefix,
                    "upload_method": "temp_file"
                }
            )
            
            # 管理対象に追加
            self._managed_files[file_id] = file_info
            
            return file_info
            
        except Exception as e:
            # エラー時のクリーンアップ
            if os.path.exists(file_path):
                os.remove(file_path)
            raise IOError(f"Failed to save file: {str(e)}")

    async def save_ocr_temp_file(
        self, 
        file: UploadFile, 
        session_id: str
    ) -> FileInfo:
        """
        OCR用一時ファイルを保存
        
        Args:
            file: アップロードファイル
            session_id: セッションID
            
        Returns:
            FileInfo: 保存されたファイル情報
        """
        return await self.save_temp_file(file, session_id, "ocr_parallel")

    async def get_file_info(self, file_id: str) -> Optional[FileInfo]:
        """
        ファイル情報を取得
        
        Args:
            file_id: ファイルID
            
        Returns:
            FileInfo: ファイル情報（存在しない場合はNone）
        """
        return self._managed_files.get(file_id)

    async def cleanup_file(self, file_id: str) -> bool:
        """
        ファイルをクリーンアップ
        
        Args:
            file_id: ファイルID
            
        Returns:
            bool: クリーンアップ実行フラグ
        """
        file_info = self._managed_files.get(file_id)
        if file_info is None:
            return False
        
        # ファイル削除
        if os.path.exists(file_info.saved_path):
            try:
                os.remove(file_info.saved_path)
            except Exception as e:
                print(f"⚠️ Failed to remove file {file_info.saved_path}: {str(e)}")
        
        # 管理対象から除外
        del self._managed_files[file_id]
        return True

    async def cleanup_session_files(self, session_id: str) -> int:
        """
        セッションのファイルをクリーンアップ
        
        Args:
            session_id: セッションID
            
        Returns:
            int: クリーンアップされたファイル数
        """
        session_files = [
            file_id for file_id, file_info in self._managed_files.items()
            if file_info.session_id == session_id
        ]
        
        cleanup_count = 0
        for file_id in session_files:
            if await self.cleanup_file(file_id):
                cleanup_count += 1
        
        return cleanup_count

    async def cleanup_old_files(self) -> int:
        """
        古いファイルを自動クリーンアップ
        
        Returns:
            int: クリーンアップされたファイル数
        """
        old_files = [
            file_id for file_id, file_info in self._managed_files.items()
            if file_info.age_seconds > self._max_file_age
        ]
        
        cleanup_count = 0
        for file_id in old_files:
            if await self.cleanup_file(file_id):
                cleanup_count += 1
        
        return cleanup_count

    def get_file_statistics(self) -> Dict[str, Any]:
        """
        ファイル統計を取得
        
        Returns:
            Dict: 統計情報
        """
        total_files = len(self._managed_files)
        total_size = sum(f.size_bytes for f in self._managed_files.values())
        
        by_session = {}
        for file_info in self._managed_files.values():
            session = file_info.session_id or "no_session"
            by_session[session] = by_session.get(session, 0) + 1
        
        return {
            "total_files": total_files,
            "total_size_mb": total_size / (1024 * 1024),
            "average_file_size_mb": (total_size / total_files / (1024 * 1024)) if total_files > 0 else 0,
            "files_by_session": by_session,
            "oldest_file_age": max((f.age_seconds for f in self._managed_files.values()), default=0),
            "upload_directory": str(self._upload_dir)
        }

    def list_managed_files(self) -> List[Dict[str, Any]]:
        """
        管理中のファイル一覧を取得
        
        Returns:
            List[Dict]: ファイル情報リスト
        """
        return [file_info.to_dict() for file_info in self._managed_files.values()]

    async def _validate_upload_file(self, file: UploadFile) -> None:
        """アップロードファイルの検証（拡張子フォールバック付き）"""
        # ファイル名チェック
        if not file.filename or not file.filename.strip():
            raise ValueError("File name is required")
        
        # ファイル形式チェック（MIMEタイプ + 拡張子フォールバック）
        is_valid_image = False
        
        # 1. MIMEタイプによる検証
        if file.content_type and file.content_type.startswith('image/'):
            is_valid_image = True
        
        # 2. MIMEタイプが無効な場合、拡張子による検証
        if not is_valid_image:
            valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
            file_ext = Path(file.filename).suffix.lower()
            if file_ext in valid_extensions:
                is_valid_image = True
                # ログ出力をより詳細に
                print(f"📁 [FileHandler] MIME type fallback: '{file.filename}' (content_type='{file.content_type}') -> valid by extension '{file_ext}'")
        
        if not is_valid_image:
            # 詳細なエラーメッセージ
            print(f"❌ [FileHandler] Invalid file: '{file.filename}' (content_type='{file.content_type}')")
            raise ValueError(f"Only image files are allowed. Received: {file.filename} (content_type: {file.content_type})")
        
        # ファイルサイズチェック（概算）
        if hasattr(file, 'size') and file.size > self._max_file_size:
            raise ValueError(f"File size exceeds maximum limit ({self._max_file_size / (1024*1024):.1f}MB)")

    def _generate_file_id(self) -> str:
        """ファイルID生成"""
        return f"file_{int(time.time())}_{str(uuid.uuid4())[:8]}"

    def _generate_file_path(
        self, 
        file_id: str, 
        original_name: str, 
        prefix: str, 
        session_id: Optional[str]
    ) -> Path:
        """ファイルパス生成"""
        # ファイル名の安全化
        safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-")
        
        # セッションIDの組み込み
        if session_id:
            filename = f"{prefix}_{session_id}_{file_id}_{safe_name}"
        else:
            filename = f"{prefix}_{file_id}_{safe_name}"
        
        return self._upload_dir / filename