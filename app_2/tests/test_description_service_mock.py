"""
Description Service モックテスト
OpenAI APIをモックして description_client と describe_service をテスト
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from app_2.infrastructure.integrations.openai import DescriptionClient, get_description_client
from app_2.services.describe_service import DescribeService, get_describe_service


class TestDescriptionClientMock:
    """DescriptionClient のモックテスト"""
    
    def setup_method(self):
        """各テストメソッド実行前にキャッシュをクリア"""
        # lru_cache をクリア
        get_description_client.cache_clear()
        get_describe_service.cache_clear()
    
    def teardown_method(self):
        """各テストメソッド実行後にキャッシュをクリア"""
        # lru_cache をクリア
        get_description_client.cache_clear()
        get_describe_service.cache_clear()
    
    @pytest.mark.asyncio
    async def test_generate_description_success_with_mock(self):
        """正常な説明生成テスト（完全モック版）"""
        # OpenAIBaseClient全体をモック
        with patch('app_2.infrastructure.integrations.openai.description_client.OpenAIBaseClient') as mock_base:
            # モックインスタンスを設定
            mock_instance = Mock()
            mock_instance._get_prompts.return_value = (
                "You are a culinary expert.",
                "Generate a description for: 唐揚げ Category: 揚げ物"
            )
            mock_instance._make_completion_request = AsyncMock(
                return_value="唐揚げは、ジューシーで香ばしい日本の代表的な揚げ物料理です。"
            )
            mock_base.return_value = mock_instance
            
            # テスト実行
            client = DescriptionClient()
            result = await client.generate_description("唐揚げ", "揚げ物")
            
            # アサーション
            assert "description" in result
            assert isinstance(result["description"], str)
            assert "ジューシーで香ばしい" in result["description"]
            
            # モックメソッドが正しく呼ばれたことを確認
            mock_instance._get_prompts.assert_called_once_with("description", "唐揚げ", "揚げ物")
            mock_instance._make_completion_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_description_api_error_fallback(self):
        """API エラー時のフォールバックテスト（モック版）"""
        with patch('app_2.infrastructure.integrations.openai.description_client.OpenAIBaseClient') as mock_base:
            # エラーを発生させるモック
            mock_instance = Mock()
            mock_instance._get_prompts.return_value = (
                "System prompt",
                "User prompt"
            )
            mock_instance._make_completion_request = AsyncMock(
                side_effect=Exception("Mocked API Error")
            )
            mock_base.return_value = mock_instance
            
            client = DescriptionClient()
            result = await client.generate_description("寿司", "和食")
            
            # フォールバック説明が返されることを確認
            assert "description" in result
            assert "厳選された食材を使用して丁寧に調理された料理" in result["description"]
            assert "寿司" in result["description"]
    
    def test_get_description_client_singleton_after_cache_clear(self):
        """キャッシュクリア後のシングルトンパターンのテスト"""
        # キャッシュをクリア
        get_description_client.cache_clear()
        
        client1 = get_description_client()
        client2 = get_description_client()
        
        assert client1 is client2
        assert isinstance(client1, DescriptionClient)


class TestDescribeServiceMock:
    """DescribeService のモックテスト"""
    
    def setup_method(self):
        """各テストメソッド実行前にキャッシュをクリア"""
        get_description_client.cache_clear()
        get_describe_service.cache_clear()
    
    def teardown_method(self):
        """各テストメソッド実行後にキャッシュをクリア"""
        get_description_client.cache_clear()
        get_describe_service.cache_clear()
    
    @pytest.mark.asyncio
    async def test_generate_menu_description_success(self):
        """正常な説明生成テスト（DescriptionClientをモック）"""
        mock_client = AsyncMock()
        mock_client.generate_description.return_value = {
            "description": "モックで生成された美味しい料理の説明です。"
        }
        
        service = DescribeService(description_client=mock_client)
        result = await service.generate_menu_description("ハンバーガー", "洋食")
        
        # アサーション
        assert "description" in result
        assert isinstance(result["description"], str)
        
        # モッククライアントが正しく呼ばれたことを確認
        mock_client.generate_description.assert_called_once_with(
            menu_item="ハンバーガー", 
            category="洋食"
        )
    
    @pytest.mark.asyncio
    async def test_generate_menu_description_empty_input(self):
        """空の入力での例外テスト"""
        mock_client = AsyncMock()
        service = DescribeService(description_client=mock_client)
        
        with pytest.raises(ValueError, match="Menu item cannot be empty"):
            await service.generate_menu_description("")
    
    @pytest.mark.asyncio
    async def test_generate_menu_description_whitespace_input(self):
        """空白文字のみの入力での例外テスト"""
        mock_client = AsyncMock()
        service = DescribeService(description_client=mock_client)
        
        with pytest.raises(ValueError, match="Menu item cannot be empty"):
            await service.generate_menu_description("   ")
    
    @pytest.mark.asyncio
    async def test_generate_menu_description_client_error(self):
        """クライアントエラー時の例外伝播テスト"""
        mock_client = AsyncMock()
        mock_client.generate_description.side_effect = Exception("Client Error")
        
        service = DescribeService(description_client=mock_client)
        
        with pytest.raises(Exception, match="Client Error"):
            await service.generate_menu_description("ピザ", "イタリアン")
    
    def test_get_describe_service_singleton_after_cache_clear(self):
        """キャッシュクリア後のシングルトンパターンのテスト"""
        # キャッシュをクリア
        get_describe_service.cache_clear()
        
        service1 = get_describe_service()
        service2 = get_describe_service()
        
        assert service1 is service2
        assert isinstance(service1, DescribeService)


class TestDescriptionIntegrationMock:
    """Description 統合モックテスト"""
    
    def setup_method(self):
        """各テストメソッド実行前にキャッシュをクリア"""
        get_description_client.cache_clear()
        get_describe_service.cache_clear()
    
    def teardown_method(self):
        """各テストメソッド実行後にキャッシュをクリア"""
        get_description_client.cache_clear()
        get_describe_service.cache_clear()
    
    @pytest.mark.asyncio
    async def test_end_to_end_description_generation_with_proper_mock(self):
        """エンドツーエンドの説明生成テスト（適切なモック使用）"""
        # DescriptionClient をモック
        with patch('app_2.services.describe_service.get_description_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.generate_description.return_value = {
                "description": "統合テスト用の詳細な料理説明です。この料理は特別な調理法で作られており、独特の風味があります。"
            }
            mock_get_client.return_value = mock_client
            
            # キャッシュをクリアしてから新しいサービスを取得
            get_describe_service.cache_clear()
            
            # DescribeService を使用
            service = DescribeService()  # 直接インスタンス化してモックが確実に適用されるように
            result = await service.generate_menu_description("特製ラーメン", "中華")
            
            # アサーション
            assert "description" in result
            assert "統合テスト用の詳細な料理説明" in result["description"]
            assert len(result["description"]) > 50  # 十分な長さの説明
            
            # モックが正しく呼ばれたことを確認
            mock_client.generate_description.assert_called_once_with(
                menu_item="特製ラーメン",
                category="中華"
            )


if __name__ == "__main__":
    """テスト実行用スクリプト"""
    import asyncio
    import sys
    
    def run_mock_tests():
        """モックテストを実行"""
        print("🧪 Description Service モックテスト開始")
        print("=" * 60)
        
        # pytest を使用してテストを実行
        import subprocess
        
        test_cmd = [
            sys.executable, "-m", "pytest", 
            __file__, 
            "-v", "-s", "--tb=short"
        ]
        
        result = subprocess.run(test_cmd, capture_output=True, text=True)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    
    if __name__ == "__main__":
        success = run_mock_tests()
        sys.exit(0 if success else 1) 