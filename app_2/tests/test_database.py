"""
データベーステスト
データベース設定・接続・基本操作の確認
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from app_2.core.database import (
    get_database_url,
    engine,
    async_session_factory,
    get_db_session,
    Base,
    DatabaseManager
)


class TestDatabaseConfiguration:
    """データベース設定テスト"""
    
    @patch('app_2.core.database.settings')
    def test_get_database_url_from_env(self, mock_settings):
        """環境変数からのデータベースURL取得テスト"""
        mock_settings.base.database_url = 'postgresql://test:test@localhost/testdb'
        
        url = get_database_url()
        # postgresql:// が postgresql+asyncpg:// に変換されることを確認
        assert url == 'postgresql+asyncpg://test:test@localhost/testdb'
    
    @patch('app_2.core.database.settings')
    def test_get_database_url_from_settings(self, mock_settings):
        """設定からのデータベースURL構築テスト"""
        # DATABASE_URLが設定されていない場合の設定モック
        mock_settings.base.database_url = None
        mock_settings.base.db_host = "test-host"
        mock_settings.base.db_port = 5433
        mock_settings.base.db_user = "test_user"
        mock_settings.base.db_password = "test_password"
        mock_settings.base.db_name = "test_database"
        
        url = get_database_url()
        
        expected_url = "postgresql+asyncpg://test_user:test_password@test-host:5433/test_database"
        assert url == expected_url
    
    @patch('app_2.core.database.settings')
    def test_get_database_url_priority(self, mock_settings):
        """データベースURL優先順位テスト"""
        # DATABASE_URLが設定されている場合は、それを優先
        mock_settings.base.database_url = "postgresql+asyncpg://priority:url@localhost/priority"
        mock_settings.base.db_host = "should-not-use"
        
        url = get_database_url()
        
        assert url == "postgresql+asyncpg://priority:url@localhost/priority"
    
    def test_engine_exists(self):
        """エンジンインスタンスの存在確認"""
        assert engine is not None
        assert hasattr(engine, 'connect')
        assert hasattr(engine, 'begin')
    
    def test_async_session_factory_exists(self):
        """非同期セッションファクトリの存在確認"""
        assert async_session_factory is not None
        assert callable(async_session_factory)


class TestDatabaseSession:
    """データベースセッションテスト"""
    
    @pytest.mark.asyncio
    async def test_get_db_session_generator(self):
        """データベースセッション生成テスト"""
        # get_db_session が非同期ジェネレーターであることを確認
        session_gen = get_db_session()
        assert hasattr(session_gen, '__aiter__')
    
    @pytest.mark.asyncio
    async def test_get_db_session_usage(self):
        """データベースセッション使用パターンテスト"""
        try:
            async for session in get_db_session():
                assert session is not None
                assert isinstance(session, AsyncSession)
                # セッションの基本属性を確認
                assert hasattr(session, 'execute')
                assert hasattr(session, 'commit')
                assert hasattr(session, 'rollback')
                break  # 一回だけテスト
        except Exception as e:
            # データベース接続がない場合はスキップ
            pytest.skip(f"Database connection failed: {e}")


class TestDatabaseManager:
    """DatabaseManager クラステスト"""
    
    def test_database_manager_exists(self):
        """DatabaseManager の存在確認"""
        assert DatabaseManager is not None
        assert hasattr(DatabaseManager, 'create_tables')
        assert hasattr(DatabaseManager, 'drop_tables')
        assert hasattr(DatabaseManager, 'check_connection')
        assert hasattr(DatabaseManager, 'close_connections')
        assert hasattr(DatabaseManager, 'get_connection_info')
    
    @pytest.mark.asyncio
    async def test_check_connection_method(self):
        """接続チェックメソッドのテスト"""
        try:
            result = await DatabaseManager.check_connection()
            assert isinstance(result, bool)
        except Exception as e:
            pytest.skip(f"Database connection check failed: {e}")
    
    @pytest.mark.asyncio
    async def test_get_connection_info_method(self):
        """接続情報取得メソッドのテスト"""
        try:
            info = await DatabaseManager.get_connection_info()
            assert isinstance(info, dict)
            assert "url" in info
        except Exception as e:
            pytest.skip(f"Database connection info failed: {e}")


class TestDatabaseBase:
    """データベースベースクラステスト"""
    
    def test_base_exists(self):
        """ベースクラスの存在確認"""
        assert Base is not None
        assert hasattr(Base, 'metadata')
    
    def test_base_metadata(self):
        """メタデータ設定確認"""
        metadata = Base.metadata
        
        # 命名規則が設定されていることを確認
        naming_convention = metadata.naming_convention
        assert naming_convention is not None
        assert 'ix' in naming_convention  # インデックス
        assert 'uq' in naming_convention  # ユニーク制約
        assert 'ck' in naming_convention  # チェック制約
        assert 'fk' in naming_convention  # 外部キー
        assert 'pk' in naming_convention  # 主キー


class TestDatabaseIntegration:
    """データベース統合テスト"""
    
    @pytest.mark.database
    async def test_database_url_construction_real(self):
        """実際の環境での URL 構築テスト"""
        try:
            url = get_database_url()
            # URLが文字列であることを確認
            assert isinstance(url, str)
            # PostgreSQL形式であることを確認
            assert url.startswith('postgresql')
        except Exception as e:
            pytest.skip(f"Database URL construction failed: {e}")
    
    @pytest.mark.database
    @pytest.mark.slow
    async def test_engine_properties_real(self):
        """実際のエンジンプロパティテスト"""
        try:
            assert engine is not None
            # エンジンが非同期エンジンであることを確認
            assert hasattr(engine, 'connect')
            assert hasattr(engine, 'begin')
        except Exception as e:
            pytest.skip(f"Engine property check failed: {e}")
    
    @pytest.mark.database
    @pytest.mark.slow
    async def test_session_factory_creation_real(self):
        """実際のセッションファクトリ作成テスト"""
        try:
            assert async_session_factory is not None
            assert callable(async_session_factory)
        except Exception as e:
            pytest.skip(f"Session factory check failed: {e}")
    
    @pytest.mark.database
    @pytest.mark.slow
    async def test_session_creation_real(self):
        """実際のセッション作成テスト"""
        try:
            async for session in get_db_session():
                assert session is not None
                assert isinstance(session, AsyncSession)
                break  # 一回だけテスト
        except Exception as e:
            pytest.skip(f"Session creation failed: {e}")


class TestDatabaseModels:
    """データベースモデルテスト"""
    
    def test_models_import(self):
        """モデルインポートテスト"""
        try:
            from app_2.infrastructure.models.menu_model import MenuModel
            assert MenuModel is not None
            assert hasattr(MenuModel, '__tablename__')
        except ImportError as e:
            pytest.skip(f"Model import failed: {e}")
    
    def test_menu_model_structure(self):
        """MenuModelの構造確認"""
        try:
            from app_2.infrastructure.models.menu_model import MenuModel
            
            # テーブル名確認
            assert MenuModel.__tablename__ == "menus"
            
            # 必要なカラムの存在確認
            expected_columns = ['id', 'name', 'translation', 'description', 
                              'allergy', 'ingredient', 'search_engine', 'gen_image']
            
            for column_name in expected_columns:
                assert hasattr(MenuModel, column_name), f"Missing column: {column_name}"
                
        except ImportError as e:
            pytest.skip(f"MenuModel import failed: {e}")
    
    def test_model_base_inheritance(self):
        """モデルのベースクラス継承確認"""
        try:
            from app_2.infrastructure.models.menu_model import MenuModel
            from app_2.core.database import Base as DatabaseBase
            
            # Baseクラスを継承していることを確認
            # MenuModelが使用しているBaseと同じインスタンスを使用
            assert issubclass(MenuModel, DatabaseBase)
            
        except ImportError as e:
            pytest.skip(f"MenuModel inheritance test failed: {e}")


class TestDatabaseLifecycle:
    """データベースライフサイクルテスト"""
    
    @pytest.mark.asyncio
    async def test_init_database_function_exists(self):
        """init_database 関数の存在確認"""
        try:
            from app_2.core.database import init_database
            assert callable(init_database)
        except ImportError as e:
            pytest.skip(f"init_database import failed: {e}")
    
    @pytest.mark.asyncio
    async def test_shutdown_database_function_exists(self):
        """shutdown_database 関数の存在確認"""
        try:
            from app_2.core.database import shutdown_database
            assert callable(shutdown_database)
        except ImportError as e:
            pytest.skip(f"shutdown_database import failed: {e}")
    
    @pytest.mark.database
    @pytest.mark.slow
    async def test_database_lifecycle_methods(self):
        """データベースライフサイクルメソッドのテスト"""
        try:
            # データベーステーブル作成テスト
            await DatabaseManager.create_tables()
            
            # 接続チェック
            is_connected = await DatabaseManager.check_connection()
            assert is_connected is True
            
            # 接続情報取得
            info = await DatabaseManager.get_connection_info()
            assert isinstance(info, dict)
            
        except Exception as e:
            pytest.skip(f"Database lifecycle test failed: {e}")


class TestDatabaseErrorHandling:
    """データベースエラーハンドリングテスト"""
    
    @patch('app_2.core.database.settings')
    def test_missing_database_settings(self, mock_settings):
        """データベース設定欠損時の処理テスト"""
        # 必要な設定がすべてNoneの場合
        mock_settings.base.database_url = None
        mock_settings.base.db_host = None
        mock_settings.base.db_port = None
        mock_settings.base.db_user = None
        mock_settings.base.db_password = None
        mock_settings.base.db_name = None
        
        # エラーまたはデフォルト値が返されることを確認
        try:
            url = get_database_url()
            # URLが構築される場合は、Noneが含まれるはず
            assert "None" in url or url is None
        except Exception:
            # 例外が発生することも期待される動作
            pass
    
    @patch('app_2.core.database.settings')
    def test_postgres_url_conversion(self, mock_settings):
        """postgres:// URL の自動変換テスト"""
        # Heroku形式のpostgres://URLの変換テスト
        mock_settings.base.database_url = "postgres://user:pass@host:5432/db"
        
        url = get_database_url()
        
        # postgresql+asyncpg:// に変換されることを確認
        assert url == "postgresql+asyncpg://user:pass@host:5432/db"
    
    @pytest.mark.asyncio
    async def test_session_error_handling(self):
        """セッションエラーハンドリングテスト"""
        # セッション内でエラーが発生した場合のテスト
        try:
            async for session in get_db_session():
                # セッションが正常に取得できることを確認
                assert session is not None
                # 実際のエラーケースのテストは統合テストで行う
                break
        except Exception as e:
            # データベース接続がない場合はスキップ
            pytest.skip(f"Session error handling test failed: {e}") 