"""
Ingredient Service Unit Tests - Menu Processor v2
成分解析サービスの包括的なユニットテスト

実行方法:
cd app_2
python -m pytest tests/services/test_ingredient_service.py -v
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Import the service under test
from app_2.services.ingredient_service import IngredientService, get_ingredient_service
from app_2.infrastructure.integrations.openai.ingredient_client import IngredientClient


class TestIngredientService:
    """IngredientServiceのユニットテストクラス"""
    
    @pytest.fixture
    def mock_ingredient_client(self):
        """モックIngredientClientフィクスチャ"""
        mock_client = AsyncMock(spec=IngredientClient)
        return mock_client
    
    @pytest.fixture
    def ingredient_service(self, mock_ingredient_client):
        """IngredientServiceインスタンスフィクスチャ"""
        return IngredientService(ingredient_client=mock_ingredient_client)
    
    def test_ingredient_service_initialization(self, mock_ingredient_client):
        """IngredientServiceの初期化テスト"""
        service = IngredientService(ingredient_client=mock_ingredient_client)
        assert service.ingredient_client == mock_ingredient_client
    
    def test_singleton_ingredient_service(self):
        """シングルトンパターンのテスト"""
        service1 = get_ingredient_service()
        service2 = get_ingredient_service()
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_analyze_ingredients_success(self, ingredient_service, mock_ingredient_client):
        """正常な成分解析のテスト"""
        # 期待されるレスポンス
        expected_response = {
            "main_ingredients": [
                {
                    "ingredient": "chicken",
                    "category": "protein",
                    "quantity": "main",
                    "preparation": "grilled"
                },
                {
                    "ingredient": "rice",
                    "category": "carbohydrates",
                    "quantity": "main",
                    "preparation": "steamed"
                },
                {
                    "ingredient": "vegetables",
                    "category": "vegetables",
                    "quantity": "side",
                    "preparation": "stir-fried"
                }
            ],
            "cooking_method": ["grilling", "steaming", "stir-frying"],
            "cuisine_category": "japanese",
            "flavor_profile": {
                "taste": ["savory", "umami"],
                "texture": "tender",
                "intensity": "medium"
            },
            "dietary_info": {
                "vegetarian": False,
                "vegan": False,
                "gluten_free": True,
                "dairy_free": True,
                "low_carb": False,
                "keto_friendly": False
            },
            "confidence": 0.92
        }
        
        # モックの設定
        mock_ingredient_client.extract_ingredients.return_value = expected_response
        
        # テスト実行
        result = await ingredient_service.analyze_ingredients("チキン照り焼き丼", "丼物")
        
        # 検証
        assert result == expected_response
        mock_ingredient_client.extract_ingredients.assert_called_once_with("チキン照り焼き丼", "丼物")
    
    @pytest.mark.asyncio 
    async def test_analyze_ingredients_empty_menu_item(self, ingredient_service):
        """空のメニューアイテムのテスト"""
        with pytest.raises(ValueError, match="Menu item cannot be empty"):
            await ingredient_service.analyze_ingredients("")
        
        with pytest.raises(ValueError, match="Menu item cannot be empty"):
            await ingredient_service.analyze_ingredients("   ")
        
        with pytest.raises(ValueError, match="Menu item cannot be empty"):
            await ingredient_service.analyze_ingredients(None)
    
    @pytest.mark.asyncio
    async def test_analyze_ingredients_no_category(self, ingredient_service, mock_ingredient_client):
        """カテゴリなしの解析テスト"""
        expected_response = {
            "main_ingredients": [
                {
                    "ingredient": "rice",
                    "category": "carbohydrates",
                    "quantity": "main",
                    "preparation": "steamed"
                }
            ],
            "cooking_method": ["steaming"],
            "cuisine_category": "asian",
            "flavor_profile": {
                "taste": ["neutral"],
                "texture": "soft",
                "intensity": "mild"
            },
            "dietary_info": {
                "vegetarian": True,
                "vegan": True,
                "gluten_free": True,
                "dairy_free": True,
                "low_carb": False,
                "keto_friendly": False
            },
            "confidence": 0.88
        }
        
        mock_ingredient_client.extract_ingredients.return_value = expected_response
        
        result = await ingredient_service.analyze_ingredients("白米")
        
        assert result == expected_response
        mock_ingredient_client.extract_ingredients.assert_called_once_with("白米", "")
    
    @pytest.mark.asyncio
    async def test_analyze_ingredients_client_exception(self, ingredient_service, mock_ingredient_client):
        """IngredientClientで例外が発生した場合のテスト"""
        # クライアントで例外を発生させる
        mock_ingredient_client.extract_ingredients.side_effect = Exception("OpenAI API error")
        
        # 例外が適切に伝播されることを確認
        with pytest.raises(Exception, match="OpenAI API error"):
            await ingredient_service.analyze_ingredients("テストメニュー")


class TestIngredientServiceConvenienceMethods:
    """IngredientServiceの便利メソッドのテストクラス"""
    
    @pytest.fixture
    def mock_ingredient_client(self):
        """モックIngredientClientフィクスチャ"""
        mock_client = AsyncMock(spec=IngredientClient)
        return mock_client
    
    @pytest.fixture
    def ingredient_service(self, mock_ingredient_client):
        """IngredientServiceインスタンスフィクスチャ"""
        return IngredientService(ingredient_client=mock_ingredient_client)
    
    @pytest.mark.asyncio
    async def test_get_main_ingredients_success(self, ingredient_service, mock_ingredient_client):
        """主要成分取得の成功テスト"""
        # モックレスポンス
        mock_response = {
            "main_ingredients": [
                {"ingredient": "tomato", "category": "vegetables"},
                {"ingredient": "cheese", "category": "dairy"},
                {"ingredient": "basil", "category": "herbs"}
            ],
            "confidence": 0.9
        }
        
        mock_ingredient_client.extract_ingredients.return_value = mock_response
        
        # テスト実行
        result = await ingredient_service.get_main_ingredients("マルゲリータピザ", "ピザ")
        
        # 検証
        expected_ingredients = ["tomato", "cheese", "basil"]
        assert result == expected_ingredients
        mock_ingredient_client.extract_ingredients.assert_called_once_with("マルゲリータピザ", "ピザ")
    
    @pytest.mark.asyncio
    async def test_get_main_ingredients_empty_result(self, ingredient_service, mock_ingredient_client):
        """主要成分が空の場合のテスト"""
        mock_response = {
            "main_ingredients": [],
            "confidence": 0.5
        }
        
        mock_ingredient_client.extract_ingredients.return_value = mock_response
        
        result = await ingredient_service.get_main_ingredients("不明なメニュー")
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_get_main_ingredients_error_handling(self, ingredient_service, mock_ingredient_client):
        """主要成分取得のエラーハンドリングテスト"""
        mock_ingredient_client.extract_ingredients.side_effect = Exception("API error")
        
        result = await ingredient_service.get_main_ingredients("テストメニュー")
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_is_vegetarian_true(self, ingredient_service, mock_ingredient_client):
        """ベジタリアン判定（True）のテスト"""
        mock_response = {
            "dietary_info": {
                "vegetarian": True,
                "vegan": False,
                "gluten_free": True
            },
            "confidence": 0.9
        }
        
        mock_ingredient_client.extract_ingredients.return_value = mock_response
        
        result = await ingredient_service.is_vegetarian("野菜サラダ")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_vegetarian_false(self, ingredient_service, mock_ingredient_client):
        """ベジタリアン判定（False）のテスト"""
        mock_response = {
            "dietary_info": {
                "vegetarian": False,
                "vegan": False,
                "gluten_free": False
            },
            "confidence": 0.95
        }
        
        mock_ingredient_client.extract_ingredients.return_value = mock_response
        
        result = await ingredient_service.is_vegetarian("牛肉ステーキ")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_vegan_true(self, ingredient_service, mock_ingredient_client):
        """ビーガン判定（True）のテスト"""
        mock_response = {
            "dietary_info": {
                "vegetarian": True,
                "vegan": True,
                "gluten_free": True
            },
            "confidence": 0.88
        }
        
        mock_ingredient_client.extract_ingredients.return_value = mock_response
        
        result = await ingredient_service.is_vegan("豆腐サラダ")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_vegan_false(self, ingredient_service, mock_ingredient_client):
        """ビーガン判定（False）のテスト"""
        mock_response = {
            "dietary_info": {
                "vegetarian": True,
                "vegan": False,  # チーズなどが含まれる
                "gluten_free": True
            },
            "confidence": 0.92
        }
        
        mock_ingredient_client.extract_ingredients.return_value = mock_response
        
        result = await ingredient_service.is_vegan("チーズサラダ")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_is_gluten_free_true(self, ingredient_service, mock_ingredient_client):
        """グルテンフリー判定（True）のテスト"""
        mock_response = {
            "dietary_info": {
                "vegetarian": True,
                "vegan": True,
                "gluten_free": True
            },
            "confidence": 0.9
        }
        
        mock_ingredient_client.extract_ingredients.return_value = mock_response
        
        result = await ingredient_service.is_gluten_free("白米")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_is_gluten_free_false(self, ingredient_service, mock_ingredient_client):
        """グルテンフリー判定（False）のテスト"""
        mock_response = {
            "dietary_info": {
                "vegetarian": True,
                "vegan": True,
                "gluten_free": False  # 小麦を含む
            },
            "confidence": 0.95
        }
        
        mock_ingredient_client.extract_ingredients.return_value = mock_response
        
        result = await ingredient_service.is_gluten_free("パスタ")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_dietary_info_error_handling(self, ingredient_service, mock_ingredient_client):
        """食事制限情報のエラーハンドリングテスト"""
        mock_ingredient_client.extract_ingredients.side_effect = Exception("API error")
        
        # 全ての食事制限チェックメソッドでFalseが返されることを確認
        assert await ingredient_service.is_vegetarian("テストメニュー") is False
        assert await ingredient_service.is_vegan("テストメニュー") is False
        assert await ingredient_service.is_gluten_free("テストメニュー") is False


class TestIngredientServiceIntegration:
    """IngredientServiceの統合テストクラス"""
    
    @pytest.mark.asyncio
    async def test_ingredient_analysis_with_real_data_structures(self):
        """実際のデータ構造を使った統合テスト"""
        # IngredientClientをモック
        with patch('app_2.services.ingredient_service.get_ingredient_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # 複数の成分を含む複雑なレスポンス
            complex_response = {
                "main_ingredients": [
                    {
                        "ingredient": "shrimp",
                        "category": "seafood",
                        "quantity": "main",
                        "preparation": "tempura_fried"
                    },
                    {
                        "ingredient": "wheat_flour",
                        "category": "grains",
                        "quantity": "medium",
                        "preparation": "batter"
                    },
                    {
                        "ingredient": "vegetables",
                        "category": "vegetables",
                        "quantity": "side",
                        "preparation": "tempura_fried"
                    }
                ],
                "cooking_method": ["deep_frying", "tempura"],
                "cuisine_category": "japanese",
                "flavor_profile": {
                    "taste": ["savory", "umami", "crispy"],
                    "texture": "crispy_outside_tender_inside",
                    "intensity": "medium"
                },
                "dietary_info": {
                    "vegetarian": False,
                    "vegan": False,
                    "gluten_free": False,
                    "dairy_free": True,
                    "low_carb": False,
                    "keto_friendly": False
                },
                "confidence": 0.94
            }
            
            mock_client.extract_ingredients.return_value = complex_response
            
            # テスト実行
            service = IngredientService()
            result = await service.analyze_ingredients("エビと野菜の天ぷら", "天ぷら")
            
            # 詳細検証
            assert len(result["main_ingredients"]) == 3
            assert result["cuisine_category"] == "japanese"
            assert result["confidence"] > 0.9
            
            # 各成分の構造検証
            ingredient_names = [ing["ingredient"] for ing in result["main_ingredients"]]
            assert "shrimp" in ingredient_names
            assert "wheat_flour" in ingredient_names
            assert "vegetables" in ingredient_names
            
            # 食事制限情報の検証
            dietary_info = result["dietary_info"]
            assert dietary_info["vegetarian"] is False  # エビが含まれる
            assert dietary_info["vegan"] is False
            assert dietary_info["gluten_free"] is False  # 小麦粉が含まれる
            assert dietary_info["dairy_free"] is True


class TestIngredientServiceErrorHandling:
    """エラーハンドリングの詳細テスト"""
    
    @pytest.fixture
    def failing_ingredient_client(self):
        """失敗するIngredientClientのモック"""
        mock_client = AsyncMock(spec=IngredientClient)
        return mock_client
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, failing_ingredient_client):
        """タイムアウトエラーのハンドリングテスト"""
        failing_ingredient_client.extract_ingredients.side_effect = asyncio.TimeoutError("Request timeout")
        
        service = IngredientService(ingredient_client=failing_ingredient_client)
        
        with pytest.raises(asyncio.TimeoutError):
            await service.analyze_ingredients("複雑なメニュー")
    
    @pytest.mark.asyncio
    async def test_api_rate_limit_error(self, failing_ingredient_client):
        """API制限エラーのハンドリングテスト"""
        failing_ingredient_client.extract_ingredients.side_effect = Exception("Rate limit exceeded")
        
        service = IngredientService(ingredient_client=failing_ingredient_client)
        
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await service.analyze_ingredients("テストメニュー")


class TestIngredientServiceRealWorldScenarios:
    """実世界のシナリオテスト"""
    
    @pytest.mark.asyncio 
    async def test_japanese_cuisine_analysis(self):
        """日本料理の成分解析テスト"""
        with patch('app_2.services.ingredient_service.get_ingredient_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # 日本料理特有の成分分析情報
            japanese_food_response = {
                "main_ingredients": [
                    {
                        "ingredient": "rice",
                        "category": "carbohydrates",
                        "quantity": "main",
                        "preparation": "sushi_rice"
                    },
                    {
                        "ingredient": "fish",
                        "category": "protein",
                        "quantity": "main",
                        "preparation": "raw_sashimi"
                    },
                    {
                        "ingredient": "nori",
                        "category": "seaweed",
                        "quantity": "small",
                        "preparation": "dried"
                    }
                ],
                "cooking_method": ["raw", "seasoning"],
                "cuisine_category": "japanese",
                "flavor_profile": {
                    "taste": ["umami", "fresh", "oceanic"],
                    "texture": "soft_rice_tender_fish",
                    "intensity": "medium"
                },
                "dietary_info": {
                    "vegetarian": False,
                    "vegan": False,
                    "gluten_free": True,
                    "dairy_free": True,
                    "low_carb": False,
                    "keto_friendly": False
                },
                "confidence": 0.96
            }
            
            mock_client.extract_ingredients.return_value = japanese_food_response
            
            service = IngredientService()
            result = await service.analyze_ingredients("寿司", "和食")
            
            # 日本料理特有の検証
            ingredient_names = [ing["ingredient"] for ing in result["main_ingredients"]]
            assert "rice" in ingredient_names  # 米
            assert "fish" in ingredient_names  # 魚
            assert "nori" in ingredient_names  # 海苔
            assert result["cuisine_category"] == "japanese"
    
    @pytest.mark.asyncio
    async def test_vegetarian_item_analysis(self):
        """ベジタリアン料理の成分解析テスト"""
        with patch('app_2.services.ingredient_service.get_ingredient_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            vegetarian_response = {
                "main_ingredients": [
                    {
                        "ingredient": "mixed_vegetables",
                        "category": "vegetables",
                        "quantity": "main",
                        "preparation": "fresh"
                    },
                    {
                        "ingredient": "olive_oil",
                        "category": "oils",
                        "quantity": "small",
                        "preparation": "dressing"
                    }
                ],
                "cooking_method": ["raw", "dressing"],
                "cuisine_category": "mediterranean",
                "flavor_profile": {
                    "taste": ["fresh", "crispy", "light"],
                    "texture": "crisp",
                    "intensity": "light"
                },
                "dietary_info": {
                    "vegetarian": True,
                    "vegan": True,
                    "gluten_free": True,
                    "dairy_free": True,
                    "low_carb": True,
                    "keto_friendly": True
                },
                "confidence": 0.98
            }
            
            mock_client.extract_ingredients.return_value = vegetarian_response
            
            service = IngredientService()
            result = await service.analyze_ingredients("グリーンサラダ", "サラダ")
            
            assert result["dietary_info"]["vegetarian"] is True
            assert result["dietary_info"]["vegan"] is True
            assert result["dietary_info"]["gluten_free"] is True
            assert result["confidence"] > 0.95
    
    @pytest.mark.asyncio
    async def test_complex_dish_multiple_ingredients(self):
        """複雑な料理（複数成分）のテスト"""
        with patch('app_2.services.ingredient_service.get_ingredient_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            complex_dish_response = {
                "main_ingredients": [
                    {
                        "ingredient": "pasta",
                        "category": "carbohydrates",
                        "quantity": "main",
                        "preparation": "boiled"
                    },
                    {
                        "ingredient": "eggs",
                        "category": "protein",
                        "quantity": "main",
                        "preparation": "raw_in_sauce"
                    },
                    {
                        "ingredient": "cheese",
                        "category": "dairy",
                        "quantity": "medium",
                        "preparation": "grated"
                    },
                    {
                        "ingredient": "bacon",
                        "category": "meat",
                        "quantity": "medium",
                        "preparation": "fried"
                    }
                ],
                "cooking_method": ["boiling", "frying", "tossing"],
                "cuisine_category": "italian",
                "flavor_profile": {
                    "taste": ["rich", "creamy", "savory"],
                    "texture": "creamy",
                    "intensity": "high"
                },
                "dietary_info": {
                    "vegetarian": False,
                    "vegan": False,
                    "gluten_free": False,
                    "dairy_free": False,
                    "low_carb": False,
                    "keto_friendly": False
                },
                "confidence": 0.97
            }
            
            mock_client.extract_ingredients.return_value = complex_dish_response
            
            service = IngredientService()
            result = await service.analyze_ingredients("カルボナーラ", "パスタ")
            
            # 複数成分の検証
            assert len(result["main_ingredients"]) >= 3
            assert result["dietary_info"]["vegetarian"] is False
            
            # 主要成分の存在確認
            ingredient_names = [ing["ingredient"] for ing in result["main_ingredients"]]
            main_ingredients = ["pasta", "eggs", "cheese", "bacon"]
            for ingredient in main_ingredients:
                assert ingredient in ingredient_names


# デバッグ用の実行可能スクリプト
if __name__ == "__main__":
    import sys
    import os
    
    # app_2をPython pathに追加
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
    # 簡単なテスト実行
    async def debug_ingredient_service():
        """デバッグ用の簡易テスト実行"""
        print("🧪 Ingredient Service Debug Test Starting...")
        
        # モッククライアントでのテスト
        mock_client = AsyncMock(spec=IngredientClient)
        mock_client.extract_ingredients.return_value = {
            "main_ingredients": [
                {
                    "ingredient": "chicken",
                    "category": "protein",
                    "quantity": "main",
                    "preparation": "grilled"
                },
                {
                    "ingredient": "rice",
                    "category": "carbohydrates",
                    "quantity": "main",
                    "preparation": "steamed"
                }
            ],
            "cooking_method": ["grilling", "steaming"],
            "cuisine_category": "japanese",
            "dietary_info": {
                "vegetarian": False,
                "vegan": False,
                "gluten_free": True,
                "dairy_free": True
            },
            "confidence": 0.95
        }
        
        service = IngredientService(ingredient_client=mock_client)
        
        try:
            # 基本的な成分解析テスト
            result = await service.analyze_ingredients("チキン照り焼き丼", "丼物")
            print(f"✅ Basic Test Success: {len(result['main_ingredients'])} ingredients found")
            print(f"📊 Ingredients: {[ing['ingredient'] for ing in result['main_ingredients']]}")
            print(f"🥬 Vegetarian: {result['dietary_info']['vegetarian']}")
            print(f"🌱 Vegan: {result['dietary_info']['vegan']}")
            print(f"🌾 Gluten-free: {result['dietary_info']['gluten_free']}")
            print(f"📈 Confidence: {result['confidence']}")
            
            # 便利メソッドのテスト
            main_ingredients = await service.get_main_ingredients("チキン照り焼き丼", "丼物")
            print(f"✅ Main Ingredients: {main_ingredients}")
            
            is_veg = await service.is_vegetarian("チキン照り焼き丼", "丼物")
            print(f"✅ Is Vegetarian: {is_veg}")
            
        except Exception as e:
            print(f"❌ Test Failed: {e}")
        
        print("🧪 Ingredient Service Debug Test Completed")
    
    # 非同期関数の実行
    asyncio.run(debug_ingredient_service()) 