"""
Session Separation Test (MVP Simplified)
セッション管理分離後の動作確認テスト（MVP版）
"""

import pytest
from datetime import datetime, timezone
import uuid

from app_2.domain.entities.session_entity import SessionEntity, SessionStatus
from app_2.domain.entities.menu_entity import MenuEntity
from app_2.infrastructure.models.session_model import SessionModel
from app_2.infrastructure.models.menu_model import MenuModel


class TestSessionSeparationMVP:
    """セッション分離機能のテストクラス（MVP版）"""

    def test_session_entity_creation(self):
        """SessionEntity基本作成テスト"""
        session_id = str(uuid.uuid4())
        
        session = SessionEntity(
            session_id=session_id,
            status=SessionStatus.PENDING
        )
        
        assert session.session_id == session_id
        assert session.status == SessionStatus.PENDING
        assert session.created_at is not None
        assert session.updated_at is not None
        assert session.menu_ids == []

    def test_session_model_conversion(self):
        """SessionModel変換テスト"""
        session_id = str(uuid.uuid4())
        
        # Entity作成
        entity = SessionEntity(
            session_id=session_id,
            status=SessionStatus.PROCESSING
        )
        entity.add_menu_id("menu-1")
        entity.add_menu_id("menu-2")
        
        # Model変換
        model = SessionModel.from_entity(entity)
        
        assert model.session_id == session_id
        assert model.status == "processing"
        assert "menu-1" in model.menu_ids
        assert "menu-2" in model.menu_ids
        
        # Entity復元
        restored_entity = model.to_entity()
        
        assert restored_entity.session_id == session_id
        assert restored_entity.status == SessionStatus.PROCESSING
        assert "menu-1" in restored_entity.menu_ids
        assert "menu-2" in restored_entity.menu_ids

    def test_menu_model_with_session(self):
        """MenuModelセッション関連テスト"""
        session_id = str(uuid.uuid4())
        
        # MenuEntity作成
        menu = MenuEntity(
            id="menu-test-1",
            name="テストメニュー",
            translation="Test Menu",
            category="TEST",
            price="¥1000"
        )
        
        # セッション付きModel作成
        model = MenuModel.from_entity_with_session(menu, session_id)
        
        assert model.id == "menu-test-1"
        assert model.session_id == session_id
        assert model.name == "テストメニュー"
        assert model.translation == "Test Menu"
        
        # Entity復元
        restored_entity = model.to_entity()
        
        assert restored_entity.id == menu.id
        assert restored_entity.name == menu.name
        assert restored_entity.translation == menu.translation

    def test_session_status_management(self):
        """セッションステータス管理テスト"""
        session = SessionEntity(
            session_id="status-test",
            status=SessionStatus.PENDING
        )
        
        # 初期状態確認
        assert not session.is_processing()
        assert not session.is_completed()
        assert not session.is_failed()
        
        # ステータス更新
        session.update_status(SessionStatus.PROCESSING)
        assert session.is_processing()
        assert session.status == SessionStatus.PROCESSING
        
        session.update_status(SessionStatus.COMPLETED)
        assert session.is_completed()
        assert session.status == SessionStatus.COMPLETED
        
        # 失敗ステータス
        session.update_status(SessionStatus.FAILED)
        assert session.is_failed()
        assert session.status == SessionStatus.FAILED

    def test_session_menu_management(self):
        """セッションメニュー管理テスト"""
        session = SessionEntity(
            session_id="menu-test",
            status=SessionStatus.PROCESSING
        )
        
        # 初期状態
        assert len(session.menu_ids) == 0
        
        # メニューID追加
        session.add_menu_id("menu-1")
        assert len(session.menu_ids) == 1
        assert "menu-1" in session.menu_ids
        
        session.add_menu_id("menu-2")
        assert len(session.menu_ids) == 2
        assert "menu-2" in session.menu_ids
        
        # 重複追加は無視される
        session.add_menu_id("menu-1")
        assert len(session.menu_ids) == 2

    def test_session_to_dict(self):
        """セッション辞書変換テスト"""
        session = SessionEntity(
            session_id="dict-test",
            status=SessionStatus.PROCESSING
        )
        session.add_menu_id("menu-1")
        session.add_menu_id("menu-2")
        
        result = session.to_dict()
        
        assert result["session_id"] == "dict-test"
        assert result["status"] == "processing"
        assert result["menu_ids"] == ["menu-1", "menu-2"]
        assert result["menu_count"] == 2
        assert result["created_at"] is not None
        assert result["updated_at"] is not None

    def test_menu_model_update_from_entity(self):
        """MenuModel更新テスト"""
        # 初期モデル
        model = MenuModel.from_entity_with_session(
            MenuEntity(id="update-test", name="Original", translation="Original"),
            "session-1"
        )
        
        # 更新エンティティ
        updated_entity = MenuEntity(
            id="update-test",
            name="Updated",
            translation="Updated Translation",
            description="New Description"
        )
        
        # 更新実行
        model.update_from_entity(updated_entity)
        
        assert model.name == "Updated"
        assert model.translation == "Updated Translation"
        assert model.description == "New Description"

    def test_session_model_update_from_entity(self):
        """SessionModel更新テスト"""
        # 初期モデル
        initial_entity = SessionEntity(
            session_id="update-test",
            status=SessionStatus.PENDING
        )
        model = SessionModel.from_entity(initial_entity)
        
        # 更新エンティティ
        updated_entity = SessionEntity(
            session_id="update-test",
            status=SessionStatus.COMPLETED
        )
        updated_entity.add_menu_id("menu-1")
        updated_entity.add_menu_id("menu-2")
        
        # 更新実行
        model.update_from_entity(updated_entity)
        
        assert model.status == "completed"
        assert "menu-1" in model.menu_ids
        assert "menu-2" in model.menu_ids

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 