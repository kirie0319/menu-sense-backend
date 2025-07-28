"""
Real Ingredient Integration Tests - Menu Processor v2
実際のOpenAI APIを使用した成分解析の統合テスト

実行方法:
cd menu_sensor_backend
python -m pytest app_2/tests/integration/test_ingredient_real_integration.py -v -s

注意: 実際のOpenAI APIキーが必要です
"""
import pytest
import asyncio
import os
from typing import Dict, Any, List

from app_2.services.ingredient_service import get_ingredient_service
from app_2.infrastructure.integrations.openai.ingredient_client import get_ingredient_client
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("ingredient_real_integration_test")


@pytest.mark.integration
class TestRealIngredientIntegration:
    """実際のOpenAI APIを使用した成分解析統合テスト"""
    
    @pytest.fixture(scope="class")
    def skip_if_no_api_key(self):
        """OpenAI APIキーが設定されていない場合はテストをスキップ"""
        if not settings.ai.openai_api_key:
            pytest.skip("OpenAI API key not configured")
    
    @pytest.mark.asyncio
    async def test_real_ingredient_analysis_japanese_food(self, skip_if_no_api_key):
        """日本料理の実際の成分解析テスト"""
        service = get_ingredient_service()
        
        try:
            # 典型的な日本料理でテスト
            result = await service.analyze_ingredients("エビフライ", "フライ")
            
            print(f"\n🧪 Real API Test - エビフライ:")
            print(f"  📊 Main ingredients: {len(result.get('main_ingredients', []))}")
            print(f"  🍳 Cooking methods: {result.get('cooking_method', [])}")
            print(f"  🍽️ Cuisine: {result.get('cuisine_category', 'unknown')}")
            print(f"  🥬 Vegetarian: {result.get('dietary_info', {}).get('vegetarian', False)}")
            print(f"  🌱 Vegan: {result.get('dietary_info', {}).get('vegan', False)}")
            print(f"  🌾 Gluten-free: {result.get('dietary_info', {}).get('gluten_free', False)}")
            print(f"  📈 Confidence: {result.get('confidence', 0)}")
            
            # 基本的な検証
            assert isinstance(result, dict)
            assert "main_ingredients" in result
            assert "dietary_info" in result
            assert "confidence" in result
            
            # エビフライの特徴的な成分をチェック
            ingredient_names = [ing.get("ingredient", "").lower() for ing in result.get("main_ingredients", [])]
            
            # エビ（seafood/shrimp）が含まれることを期待
            seafood_found = any("shrimp" in name or "prawn" in name or "seafood" in name or "shellfish" in name 
                               for name in ingredient_names)
            assert seafood_found, f"Seafood ingredient not found in: {ingredient_names}"
            
            # エビフライは肉食なのでベジタリアンではない
            dietary_info = result.get("dietary_info", {})
            assert dietary_info.get("vegetarian", True) is False, "Fried shrimp should not be vegetarian"
            assert dietary_info.get("vegan", True) is False, "Fried shrimp should not be vegan"
            
            assert result.get("confidence", 0) > 0.5, "Confidence should be reasonable"
            
        except Exception as e:
            logger.error(f"Real ingredient analysis test failed: {e}")
            pytest.fail(f"Real API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_real_ingredient_analysis_pasta(self, skip_if_no_api_key):
        """パスタ料理の実際の成分解析テスト"""
        service = get_ingredient_service()
        
        try:
            # 複合的な料理でテスト
            result = await service.analyze_ingredients("カルボナーラ", "パスタ")
            
            print(f"\n🧪 Real API Test - カルボナーラ:")
            print(f"  📊 Main ingredients: {len(result.get('main_ingredients', []))}")
            print(f"  🍳 Cooking methods: {result.get('cooking_method', [])}")
            print(f"  🍽️ Cuisine: {result.get('cuisine_category', 'unknown')}")
            print(f"  📈 Confidence: {result.get('confidence', 0)}")
            
            # 詳細な成分情報を表示
            for ingredient in result.get("main_ingredients", []):
                print(f"    - {ingredient.get('ingredient', 'unknown')}: {ingredient.get('category', 'unknown')}")
            
            # 基本的な検証
            assert isinstance(result, dict)
            assert "main_ingredients" in result
            
            # カルボナーラの典型的な成分をチェック
            ingredient_names = [ing.get("ingredient", "").lower() for ing in result.get("main_ingredients", [])]
            
            # パスタ・卵・チーズのいずれかが含まれることを期待
            expected_components = ["pasta", "egg", "cheese", "cream", "bacon", "pancetta"]
            found_expected = any(expected in " ".join(ingredient_names) for expected in expected_components)
            assert found_expected, f"Expected pasta components not found in: {ingredient_names}"
            
            # カルボナーラは卵とチーズを含むのでベジタリアンかもしれないがビーガンではない
            dietary_info = result.get("dietary_info", {})
            assert dietary_info.get("vegan", True) is False, "Carbonara should not be vegan (contains eggs/cheese)"
            
        except Exception as e:
            logger.error(f"Real pasta ingredient analysis test failed: {e}")
            pytest.fail(f"Real API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_real_ingredient_analysis_vegetarian_item(self, skip_if_no_api_key):
        """ベジタリアン料理の実際の成分解析テスト"""
        service = get_ingredient_service()
        
        try:
            # ベジタリアン料理でテスト
            result = await service.analyze_ingredients("野菜サラダ", "サラダ")
            
            print(f"\n🧪 Real API Test - 野菜サラダ:")
            print(f"  📊 Main ingredients: {len(result.get('main_ingredients', []))}")
            print(f"  🥬 Vegetarian: {result.get('dietary_info', {}).get('vegetarian', False)}")
            print(f"  🌱 Vegan: {result.get('dietary_info', {}).get('vegan', False)}")
            print(f"  🌾 Gluten-free: {result.get('dietary_info', {}).get('gluten_free', False)}")
            print(f"  📈 Confidence: {result.get('confidence', 0)}")
            print(f"  📝 Flavor: {result.get('flavor_profile', {})}")
            
            # 基本的な検証
            assert isinstance(result, dict)
            assert "main_ingredients" in result
            assert "dietary_info" in result
            
            # 野菜サラダは一般的にベジタリアン食品
            dietary_info = result.get("dietary_info", {})
            # ドレッシング次第だが、基本的にはベジタリアン
            vegetarian_likely = dietary_info.get("vegetarian", False)
            print(f"    Vegetarian classification: {vegetarian_likely}")
            
            assert result.get("confidence", 0) > 0.7, "Confidence should be high for simple items"
            
        except Exception as e:
            logger.error(f"Real vegetarian item ingredient analysis test failed: {e}")
            pytest.fail(f"Real API test failed: {e}")


class TestIngredientServiceConvenienceMethodsReal:
    """IngredientServiceの便利メソッドの実際のAPIテスト"""
    
    @pytest.fixture(scope="class")
    def skip_if_no_api_key(self):
        """OpenAI APIキーが設定されていない場合はテストをスキップ"""
        if not settings.ai.openai_api_key:
            pytest.skip("OpenAI API key not configured")
    
    @pytest.mark.asyncio
    async def test_get_main_ingredients_real(self, skip_if_no_api_key):
        """実際のAPIを使用した主要成分取得テスト"""
        service = get_ingredient_service()
        
        try:
            # 主要成分の取得テスト
            ingredients = await service.get_main_ingredients("寿司", "和食")
            
            print(f"\n🧪 Real API Test - 寿司の主要成分:")
            print(f"  📊 Found ingredients: {ingredients}")
            
            # 基本的な検証
            assert isinstance(ingredients, list)
            
            # 寿司の基本的な成分（米、魚など）が含まれることを期待
            if ingredients:
                ingredient_str = " ".join(ingredients).lower()
                rice_or_fish = any(component in ingredient_str 
                                 for component in ["rice", "fish", "salmon", "tuna", "seafood"])
                print(f"    Rice or fish components found: {rice_or_fish}")
            
        except Exception as e:
            logger.error(f"Real get_main_ingredients test failed: {e}")
            pytest.fail(f"Real API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_dietary_classification_real(self, skip_if_no_api_key):
        """実際のAPIを使用した食事制限分類テスト"""
        service = get_ingredient_service()
        
        try:
            # ベジタリアン判定テスト
            is_vegetarian_salad = await service.is_vegetarian("グリーンサラダ", "サラダ")
            is_vegetarian_beef = await service.is_vegetarian("牛肉ステーキ", "肉料理")
            
            print(f"\n🧪 Real API Test - 食事制限分類:")
            print(f"  🥬 グリーンサラダ - Vegetarian: {is_vegetarian_salad}")
            print(f"  🥩 牛肉ステーキ - Vegetarian: {is_vegetarian_beef}")
            
            # ビーガン判定テスト
            is_vegan_salad = await service.is_vegan("グリーンサラダ", "サラダ")
            is_vegan_cheese = await service.is_vegan("チーズピザ", "ピザ")
            
            print(f"  🌱 グリーンサラダ - Vegan: {is_vegan_salad}")
            print(f"  🧀 チーズピザ - Vegan: {is_vegan_cheese}")
            
            # グルテンフリー判定テスト
            is_gf_rice = await service.is_gluten_free("白米", "ご飯")
            is_gf_pasta = await service.is_gluten_free("パスタ", "パスタ")
            
            print(f"  🍚 白米 - Gluten-free: {is_gf_rice}")
            print(f"  🍝 パスタ - Gluten-free: {is_gf_pasta}")
            
            # 基本的な期待値チェック（柔軟に）
            # 牛肉ステーキは確実にベジタリアンではない
            assert is_vegetarian_beef is False, "Beef steak should not be vegetarian"
            
            # チーズピザは確実にビーガンではない
            assert is_vegan_cheese is False, "Cheese pizza should not be vegan"
            
            # パスタは一般的にグルテンを含む
            # （ただし、グルテンフリーパスタの可能性もあるので厳密にはチェックしない）
            
        except Exception as e:
            logger.error(f"Real dietary classification test failed: {e}")
            pytest.fail(f"Real API test failed: {e}")


class TestIngredientClientDirectly:
    """IngredientClientを直接テストする統合テスト"""
    
    @pytest.fixture(scope="class")
    def skip_if_no_api_key(self):
        """OpenAI APIキーが設定されていない場合はテストをスキップ"""
        if not settings.ai.openai_api_key:
            pytest.skip("OpenAI API key not configured")
    
    @pytest.mark.asyncio
    async def test_ingredient_client_function_calling(self, skip_if_no_api_key):
        """IngredientClientのFunction Calling機能テスト"""
        client = get_ingredient_client()
        
        try:
            # Function Callingスキーマの検証
            schema = client._get_ingredient_function_schema()
            
            assert isinstance(schema, list)
            assert len(schema) > 0
            assert "name" in schema[0]
            assert schema[0]["name"] == "extract_ingredients"
            
            # 実際のFunction Calling実行
            result = await client.extract_ingredients("親子丼", "丼物")
            
            print(f"\n🧪 Function Calling Test - 親子丼:")
            print(f"  📊 Result type: {type(result)}")
            print(f"  📊 Main ingredients: {len(result.get('main_ingredients', []))}")
            print(f"  🍳 Cooking methods: {result.get('cooking_method', [])}")
            print(f"  🍽️ Cuisine category: {result.get('cuisine_category', 'unknown')}")
            
            # Function Callingの結果検証
            assert isinstance(result, dict)
            required_fields = ["main_ingredients", "dietary_info", "confidence"]
            for field in required_fields:
                assert field in result, f"Required field '{field}' missing from result"
            
            # 主要成分の構造検証
            for ingredient in result.get("main_ingredients", []):
                assert isinstance(ingredient, dict)
                required_ingredient_fields = ["ingredient", "category"]
                for field in required_ingredient_fields:
                    assert field in ingredient, f"Required ingredient field '{field}' missing"
            
            # 食事制限情報の構造検証
            dietary_info = result.get("dietary_info", {})
            required_dietary_fields = ["vegetarian", "vegan", "gluten_free"]
            for field in required_dietary_fields:
                assert field in dietary_info, f"Required dietary field '{field}' missing"
            
        except Exception as e:
            logger.error(f"IngredientClient Function Calling test failed: {e}")
            pytest.fail(f"Function Calling test failed: {e}")


# デバッグ用の実行可能スクリプト
if __name__ == "__main__":
    import sys
    import os
    
    # プロジェクトルートをPython pathに追加
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    
    async def debug_real_ingredient_integration():
        """デバッグ用の実際のAPI統合テスト"""
        print("🔬 Real Ingredient Integration Debug Test Starting...")
        
        # API キーチェック
        if not settings.ai.openai_api_key:
            print("⚠️ OpenAI API key not configured - skipping real API tests")
            return
        
        try:
            service = get_ingredient_service()
            
            # テストケース1: 日本料理
            print("\n🍤 Testing Japanese food - エビフライ:")
            result1 = await service.analyze_ingredients("エビフライ", "フライ")
            print(f"  Result: {result1}")
            
            # 便利メソッドのテスト
            print("\n📊 Testing convenience methods:")
            ingredients = await service.get_main_ingredients("エビフライ", "フライ")
            print(f"  Main ingredients: {ingredients}")
            
            is_veg = await service.is_vegetarian("エビフライ", "フライ")
            print(f"  Is vegetarian: {is_veg}")
            
            is_vegan = await service.is_vegan("エビフライ", "フライ")
            print(f"  Is vegan: {is_vegan}")
            
            is_gf = await service.is_gluten_free("エビフライ", "フライ")
            print(f"  Is gluten-free: {is_gf}")
            
            # テストケース2: ベジタリアン料理
            print("\n🥗 Testing vegetarian food - 野菜サラダ:")
            result2 = await service.analyze_ingredients("野菜サラダ", "サラダ")
            print(f"  Vegetarian: {result2.get('dietary_info', {}).get('vegetarian', False)}")
            print(f"  Vegan: {result2.get('dietary_info', {}).get('vegan', False)}")
            print(f"  Confidence: {result2.get('confidence', 0)}")
            
            # テストケース3: 複雑な料理
            print("\n🍝 Testing complex dish - カルボナーラ:")
            result3 = await service.analyze_ingredients("カルボナーラ", "パスタ")
            print(f"  Main ingredients count: {len(result3.get('main_ingredients', []))}")
            print(f"  Cuisine: {result3.get('cuisine_category', 'unknown')}")
            
            print("\n✅ All real API tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Real API test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # 非同期関数の実行
    asyncio.run(debug_real_ingredient_integration()) 