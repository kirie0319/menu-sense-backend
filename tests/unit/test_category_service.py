"""
カテゴリ分類サービスのユニットテスト
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json

from app.services.category import categorize_menu, get_category_service_status
from app.services.category.base import CategoryResult, CategoryProvider
from app.services.category.openai import OpenAICategoryService


@pytest.mark.unit
@pytest.mark.category
class TestCategoryService:
    """カテゴリ分類サービスのテスト"""

    @pytest.mark.asyncio
    async def test_categorize_menu_success(self, sample_menu_text, test_session_id):
        """メニューカテゴリ分類の成功ケース"""
        with patch('app.services.category.category_manager.categorize_menu') as mock_categorize:
            # モックの戻り値を設定
            mock_categorize.return_value = CategoryResult(
                success=True,
                categories={
                    "お寿司": [
                        {"name": "まぐろ", "price": "500円"},
                        {"name": "サーモン", "price": "450円"}
                    ],
                    "飲み物": [
                        {"name": "ビール", "price": "400円"}
                    ]
                },
                uncategorized=[],
                provider=CategoryProvider.OPENAI,
                metadata={"model": "gpt-4", "processing_time": 3.2}
            )
            
            result = await categorize_menu(sample_menu_text, test_session_id)
            
            assert result.success is True
            assert "お寿司" in result.categories
            assert "飲み物" in result.categories
            assert len(result.categories["お寿司"]) == 2
            assert result.uncategorized == []
            assert result.provider == CategoryProvider.OPENAI
            mock_categorize.assert_called_once_with(sample_menu_text, test_session_id)

    @pytest.mark.asyncio
    async def test_categorize_menu_with_uncategorized(self, sample_menu_text, test_session_id):
        """未分類アイテムがある場合のテスト"""
        with patch('app.services.category.category_manager.categorize_menu') as mock_categorize:
            mock_categorize.return_value = CategoryResult(
                success=True,
                categories={
                    "メイン": [{"name": "唐揚げ", "price": "800円"}]
                },
                uncategorized=["不明な料理", "???"],
                provider=CategoryProvider.OPENAI,
                metadata={"model": "gpt-4"}
            )
            
            result = await categorize_menu(sample_menu_text, test_session_id)
            
            assert result.success is True
            assert len(result.uncategorized) == 2
            assert "不明な料理" in result.uncategorized

    @pytest.mark.asyncio
    async def test_categorize_menu_failure(self, sample_menu_text, test_session_id):
        """カテゴリ分類の失敗ケース"""
        with patch('app.services.category.category_manager.categorize_menu') as mock_categorize:
            mock_categorize.return_value = CategoryResult(
                success=False,
                categories={},
                uncategorized=[],
                provider=CategoryProvider.OPENAI,
                error="OpenAI API接続エラー",
                metadata={"error_code": "api_timeout"}
            )
            
            result = await categorize_menu(sample_menu_text, test_session_id)
            
            assert result.success is False
            assert result.error == "OpenAI API接続エラー"
            assert result.categories == {}

    @pytest.mark.asyncio
    async def test_get_category_service_status(self):
        """カテゴリサービスのステータス取得テスト"""
        with patch('app.services.category.category_manager.get_service_status') as mock_status:
            mock_status.return_value = {
                "available_services": ["openai"],
                "default_service": "openai",
                "health": "healthy",
                "openai_model": "gpt-4"
            }
            
            status = await get_category_service_status()
            
            assert "openai" in status["available_services"]
            assert status["default_service"] == "openai"
            assert status["health"] == "healthy"


@pytest.mark.unit
@pytest.mark.category
class TestOpenAICategoryService:
    """OpenAI カテゴリ分類サービスのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.service = OpenAICategoryService()

    @pytest.mark.asyncio
    async def test_categorize_menu_with_mock(self, sample_menu_text, test_session_id):
        """OpenAI APIをモックしたカテゴリ分類テスト"""
        # モックレスポンスの準備
        mock_response_content = {
            "categories": {
                "お寿司": [
                    {"name": "まぐろ", "price": "500円"},
                    {"name": "サーモン", "price": "450円"}
                ],
                "飲み物": [
                    {"name": "ビール", "price": "400円"},
                    {"name": "日本酒", "price": "600円"}
                ]
            },
            "uncategorized": []
        }
        
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            # モックOpenAIクライアント
            mock_client = Mock()
            mock_response = Mock()
            mock_choice = Mock()
            mock_message = Mock()
            mock_function_call = Mock()
            
            mock_function_call.name = "categorize_menu_items"
            mock_function_call.arguments = json.dumps(mock_response_content)
            mock_message.function_call = mock_function_call
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai_class.return_value = mock_client
            
            result = await self.service.categorize_menu(sample_menu_text, test_session_id)
            
            assert result.success is True
            assert "お寿司" in result.categories
            assert "飲み物" in result.categories
            assert len(result.categories["お寿司"]) == 2
            assert result.provider == CategoryProvider.OPENAI

    @pytest.mark.asyncio
    async def test_categorize_menu_api_error(self, sample_menu_text, test_session_id):
        """OpenAI API エラーのテスト"""
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("API接続エラー")
            )
            mock_openai_class.return_value = mock_client
            
            result = await self.service.categorize_menu(sample_menu_text, test_session_id)
            
            assert result.success is False
            assert "API接続エラー" in result.error
            assert result.categories == {}

    @pytest.mark.asyncio
    async def test_categorize_menu_invalid_json_response(self, sample_menu_text, test_session_id):
        """無効なJSON レスポンスのテスト"""
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_choice = Mock()
            mock_message = Mock()
            mock_function_call = Mock()
            
            mock_function_call.name = "categorize_menu_items"
            mock_function_call.arguments = "invalid json"  # 無効なJSON
            mock_message.function_call = mock_function_call
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai_class.return_value = mock_client
            
            result = await self.service.categorize_menu(sample_menu_text, test_session_id)
            
            assert result.success is False
            assert "JSON" in result.error or "パース" in result.error

    def test_create_categorization_prompt(self):
        """カテゴリ分類プロンプト作成のテスト"""
        sample_text = "唐揚げ 800円\nライス 200円"
        prompt = self.service._create_categorization_prompt(sample_text)
        
        assert "カテゴリ" in prompt
        assert "分類" in prompt
        assert sample_text in prompt

    def test_get_function_definition(self):
        """Function Calling 定義のテスト"""
        function_def = self.service._get_function_definition()
        
        assert function_def["name"] == "categorize_menu_items"
        assert "parameters" in function_def
        assert "properties" in function_def["parameters"]
        assert "categories" in function_def["parameters"]["properties"]

    @pytest.mark.asyncio
    async def test_validate_categorization_result(self):
        """カテゴリ分類結果の検証テスト"""
        # 正常なケース
        valid_result = {
            "categories": {
                "メイン": [{"name": "唐揚げ", "price": "800円"}]
            },
            "uncategorized": []
        }
        is_valid = await self.service._validate_categorization_result(valid_result)
        assert is_valid is True
        
        # 無効なケース - categoriesキーがない
        invalid_result = {"uncategorized": []}
        is_valid = await self.service._validate_categorization_result(invalid_result)
        assert is_valid is False
        
        # 無効なケース - categoriesが辞書でない
        invalid_result2 = {"categories": "invalid", "uncategorized": []}
        is_valid = await self.service._validate_categorization_result(invalid_result2)
        assert is_valid is False


@pytest.mark.unit
@pytest.mark.category
class TestCategoryResult:
    """CategoryResult データクラスのテスト"""

    def test_successful_result_creation(self):
        """成功結果の作成テスト"""
        categories = {
            "メイン": [{"name": "唐揚げ", "price": "800円"}],
            "サイド": [{"name": "サラダ", "price": "300円"}]
        }
        
        result = CategoryResult(
            success=True,
            categories=categories,
            uncategorized=[],
            provider=CategoryProvider.OPENAI,
            metadata={"model": "gpt-4", "total_items": 2}
        )
        
        assert result.success is True
        assert len(result.categories) == 2
        assert "メイン" in result.categories
        assert result.uncategorized == []
        assert result.provider == CategoryProvider.OPENAI
        assert result.error is None

    def test_error_result_creation(self):
        """エラー結果の作成テスト"""
        result = CategoryResult(
            success=False,
            categories={},
            uncategorized=[],
            provider=CategoryProvider.OPENAI,
            error="APIキーが無効です",
            metadata={"error_code": "invalid_api_key"}
        )
        
        assert result.success is False
        assert result.categories == {}
        assert result.error == "APIキーが無効です"
        assert result.metadata["error_code"] == "invalid_api_key"

    def test_result_to_dict(self):
        """結果の辞書変換テスト"""
        categories = {"メイン": [{"name": "唐揚げ", "price": "800円"}]}
        
        result = CategoryResult(
            success=True,
            categories=categories,
            uncategorized=["不明な料理"],
            provider=CategoryProvider.OPENAI
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["categories"] == categories
        assert result_dict["uncategorized"] == ["不明な料理"]
        assert result_dict["provider"] == "openai"

    def test_get_total_items(self):
        """総アイテム数取得のテスト"""
        categories = {
            "メイン": [{"name": "料理1"}, {"name": "料理2"}],
            "サイド": [{"name": "料理3"}]
        }
        
        result = CategoryResult(
            success=True,
            categories=categories,
            uncategorized=["料理4", "料理5"],
            provider=CategoryProvider.OPENAI
        )
        
        total_items = result.get_total_items()
        assert total_items == 5  # 3個（カテゴリ内） + 2個（未分類）


# エッジケーステスト
@pytest.mark.unit
@pytest.mark.category
class TestCategoryEdgeCases:
    """カテゴリ分類のエッジケーステスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.service = OpenAICategoryService()

    @pytest.mark.asyncio
    async def test_empty_text_input(self, test_session_id):
        """空文字列入力のテスト"""
        result = await self.service.categorize_menu("", test_session_id)
        
        assert result.success is False
        assert "空" in result.error or "入力" in result.error

    @pytest.mark.asyncio
    async def test_very_long_text_input(self, test_session_id):
        """非常に長いテキスト入力のテスト"""
        long_text = "料理名 価格\n" * 1000  # 非常に長いテキスト
        
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=Exception("テキストが長すぎます")
            )
            mock_openai_class.return_value = mock_client
            
            result = await self.service.categorize_menu(long_text, test_session_id)
            
            assert result.success is False
            assert "長すぎます" in result.error

    @pytest.mark.asyncio
    async def test_special_characters_in_menu(self, test_session_id):
        """特殊文字を含むメニューのテスト"""
        special_text = "🍣 寿司 ¥500\n🍺 ビール €4.00\n🍜 ラーメン $8"
        
        with patch('openai.AsyncOpenAI') as mock_openai_class:
            mock_client = Mock()
            mock_response = Mock()
            mock_choice = Mock()
            mock_message = Mock()
            mock_function_call = Mock()
            
            mock_function_call.name = "categorize_menu_items"
            mock_function_call.arguments = json.dumps({
                "categories": {
                    "日本料理": [{"name": "🍣 寿司", "price": "¥500"}]
                },
                "uncategorized": []
            })
            mock_message.function_call = mock_function_call
            mock_choice.message = mock_message
            mock_response.choices = [mock_choice]
            
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_openai_class.return_value = mock_client
            
            result = await self.service.categorize_menu(special_text, test_session_id)
            
            assert result.success is True
            assert "日本料理" in result.categories 