"""
Session Model - Infrastructure Layer
SQLAlchemy model for session data persistence (MVP Simplified)
"""

import json
from datetime import datetime, timezone
from typing import Dict, List

from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship

from app_2.core.database import Base
from app_2.domain.entities.session_entity import SessionEntity, SessionStatus


class SessionModel(Base):
    """
    セッションSQLAlchemyモデル（MVP版）
    
    処理セッション管理用のシンプルなDB構造
    """
    __tablename__ = "processing_sessions"

    # セッションID（UUID）
    session_id = Column(String, primary_key=True)
    
    # 処理ステータス
    status = Column(String, nullable=False, default="pending")
    
    # 関連するメニューID一覧（JSON配列形式）
    menu_ids = Column(Text, nullable=False, default="[]")
    
    # 段階別データ（JSON形式）- 新規追加
    stages_data = Column(Text, nullable=True, default="{}")
    
    # 現在の段階 - 新規追加
    current_stage = Column(String, nullable=True, default="initialized")
    
    # 作成日時
    created_at = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    
    # 更新日時
    updated_at = Column(DateTime, default=lambda: datetime.utcnow(), onupdate=lambda: datetime.utcnow(), nullable=False)

    # リレーション（逆参照）
    menus = relationship("MenuModel", back_populates="session")

    def to_entity(self) -> SessionEntity:
        """
        SQLAlchemyモデルをドメインエンティティに変換
        
        Returns:
            SessionEntity: ドメインエンティティ
        """
        # JSON文字列をパース
        try:
            menu_ids_list = json.loads(self.menu_ids) if self.menu_ids else []
        except json.JSONDecodeError:
            menu_ids_list = []
        
        # ステータスを列挙型に変換
        status = SessionStatus(self.status) if self.status else SessionStatus.PENDING
        
        return SessionEntity(
            session_id=self.session_id,
            status=status,
            menu_ids=menu_ids_list,
            created_at=self.created_at,
            updated_at=self.updated_at
        )

    @classmethod
    def from_entity(cls, entity: SessionEntity) -> "SessionModel":
        """
        ドメインエンティティからSQLAlchemyモデルを作成
        
        Args:
            entity: ドメインエンティティ
            
        Returns:
            SessionModel: SQLAlchemyモデル
        """
        # メニューIDリストをJSON文字列に変換
        menu_ids_json = json.dumps(entity.menu_ids, ensure_ascii=False)
        
        return cls(
            session_id=entity.session_id,
            status=entity.status.value,
            menu_ids=menu_ids_json,
            stages_data="{}",
            current_stage="initialized",
            created_at=entity.created_at,
            updated_at=entity.updated_at
        )
    
    def update_from_entity(self, entity: SessionEntity) -> None:
        """
        エンティティの内容でモデルを更新
        
        Args:
            entity: 更新内容のエンティティ
        """
        self.status = entity.status.value
        self.menu_ids = json.dumps(entity.menu_ids, ensure_ascii=False)
        self.updated_at = entity.updated_at or datetime.utcnow()
    
    def get_stages_data(self) -> Dict:
        """段階別データを辞書として取得"""
        try:
            return json.loads(self.stages_data) if self.stages_data else {}
        except json.JSONDecodeError:
            return {}
    
    def update_stage_data(self, stage: str, stage_data: Dict) -> None:
        """段階別データを更新"""
        current_stages = self.get_stages_data()
        current_stages[stage] = stage_data
        self.stages_data = json.dumps(current_stages, ensure_ascii=False)
        self.current_stage = stage
        self.updated_at = datetime.utcnow() 