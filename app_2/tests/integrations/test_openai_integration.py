"""
OpenAI Integration Test
OpenAI Client の統合機能をテスト
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from app_2.infrastructure.integrations.openai import OpenAIClient, get_openai_client


class TestOpenAIIntegration:
    """OpenAI統合機能のテストクラス"""
    
    @pytest.fixture
    def client(self):
        """テスト用のOpenAIClientインスタンス"""
        return OpenAIClient()
    
    @pytest.fixture
    def mock_dependencies(self):
        """依存クライアントのモック"""
        with patch('app_2.infrastructure.integrations.openai.openai_client.get_description_client') as mock_desc, \
             patch('app_2.infrastructure.integrations.openai.openai_client.get_allergen_client') as mock_allergen, \
             patch('app_2.infrastructure.integrations.openai.openai_client.get_ingredient_client') as mock_ingredient:
            
            # モックの戻り値を設定
            mock_desc.return_value = Mock()
            mock_allergen.return_value = Mock()
            mock_ingredient.return_value = Mock()
            
            yield {
                'description': mock_desc.return_value,
                'allergen': mock_allergen.return_value,
                'ingredient': mock_ingredient.return_value
            }

    # =====================
    # Function Calling Tests
    # =====================

    @pytest.mark.asyncio
    async def test_extract_allergens_detailed(self, client, mock_dependencies):
        """アレルゲン抽出詳細機能のテスト"""
        # モックの設定
        expected_result = {
            "allergens": ["egg", "milk"],
            "confidence": 0.9
        }
        mock_dependencies['allergen'].extract_allergens = AsyncMock(return_value=expected_result)
        
        # テスト実行
        result = await client.extract_allergens_detailed("卵サンドイッチ")
        
        # 検証
        assert result == expected_result
        mock_dependencies['allergen'].extract_allergens.assert_called_once_with("卵サンドイッチ")

    @pytest.mark.asyncio
    async def test_extract_ingredients_detailed(self, client, mock_dependencies):
        """含有物抽出詳細機能のテスト"""
        # モックの設定
        expected_result = {
            "ingredients": ["bread", "egg", "mayonnaise"],
            "confidence": 0.8
        }
        mock_dependencies['ingredient'].extract_ingredients = AsyncMock(return_value=expected_result)
        
        # テスト実行
        result = await client.extract_ingredients_detailed("卵サンドイッチ")
        
        # 検証
        assert result == expected_result
        mock_dependencies['ingredient'].extract_ingredients.assert_called_once_with("卵サンドイッチ")

    @pytest.mark.asyncio
    async def test_generate_description_detailed(self, client, mock_dependencies):
        """詳細説明生成機能のテスト"""
        # モックの設定
        expected_result = {
            "description": "美味しい卵サンドイッチです。"
        }
        mock_dependencies['description'].generate_description = AsyncMock(return_value=expected_result)
        
        # テスト実行
        result = await client.generate_description_detailed("卵サンドイッチ", "サンドイッチ")
        
        # 検証
        assert result == expected_result
        mock_dependencies['description'].generate_description.assert_called_once_with("卵サンドイッチ", "サンドイッチ")

    @pytest.mark.asyncio
    async def test_analyze_menu_item_comprehensive(self, client, mock_dependencies):
        """包括的分析機能のテスト"""
        # モックの設定
        mock_dependencies['allergen'].extract_allergens = AsyncMock(return_value={"allergens": ["egg"]})
        mock_dependencies['ingredient'].extract_ingredients = AsyncMock(return_value={"ingredients": ["bread", "egg"]})
        mock_dependencies['description'].generate_description = AsyncMock(return_value={"description": "美味しいサンドイッチ"})
        
        # テスト実行
        result = await client.analyze_menu_item_comprehensive("卵サンドイッチ", "サンドイッチ")
        
        # 検証
        assert result["menu_item"] == "卵サンドイッチ"
        assert result["category"] == "サンドイッチ"
        assert result["allergens"]["allergens"] == ["egg"]
        assert result["ingredients"]["ingredients"] == ["bread", "egg"]
        assert result["description"]["description"] == "美味しいサンドイッチ"
        assert result["analysis_status"] == "completed"

    # =====================
    # Legacy Compatibility Tests
    # =====================

    @pytest.mark.asyncio
    async def test_extract_allergens_simple(self, client, mock_dependencies):
        """アレルゲン抽出シンプル機能のテスト"""
        # モックの設定
        mock_dependencies['allergen'].extract_allergens = AsyncMock(return_value={"allergens": ["egg", "milk"]})
        
        # テスト実行
        result = await client.extract_allergens("卵サンドイッチ")
        
        # 検証
        assert result == "egg, milk"

    @pytest.mark.asyncio
    async def test_extract_ingredients_simple(self, client, mock_dependencies):
        """含有物抽出シンプル機能のテスト"""
        # モックの設定
        mock_dependencies['ingredient'].extract_ingredients = AsyncMock(return_value={"ingredients": ["bread", "egg"]})
        
        # テスト実行
        result = await client.extract_ingredients("卵サンドイッチ")
        
        # 検証
        assert result == "bread, egg"

    @pytest.mark.asyncio
    async def test_generate_description_simple(self, client, mock_dependencies):
        """詳細説明生成シンプル機能のテスト"""
        # モックの設定
        mock_dependencies['description'].generate_description = AsyncMock(return_value={"description": "美味しいサンドイッチです。"})
        
        # テスト実行
        result = await client.generate_description("卵サンドイッチ", "サンドイッチ")
        
        # 検証
        assert result == "美味しいサンドイッチです。"

    # =====================
    # Singleton Test
    # =====================

    def test_singleton_behavior(self):
        """シングルトン動作のテスト"""
        client1 = get_openai_client()
        client2 = get_openai_client()
        
        # 同じインスタンスであることを確認
        assert client1 is client2
        
        # 基本メソッドが存在することを確認
        assert hasattr(client1, 'extract_allergens')
        assert hasattr(client1, 'extract_ingredients')
        assert hasattr(client1, 'generate_description')
        assert hasattr(client1, 'analyze_menu_item_comprehensive') 