"""
Allergen Service Unit Tests - Menu Processor v2
アレルギー解析サービスの包括的なユニットテスト

実行方法:
cd app_2
python -m pytest tests/services/test_allergen_service.py -v
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

# Import the service under test
from app_2.services.allergen_service import AllergenService, get_allergen_service
from app_2.infrastructure.integrations.openai.allergen_client import AllergenClient


class TestAllergenService:
    """AllergenServiceのユニットテストクラス"""
    
    @pytest.fixture
    def mock_allergen_client(self):
        """モックAllergenClientフィクスチャ"""
        mock_client = AsyncMock(spec=AllergenClient)
        return mock_client
    
    @pytest.fixture
    def allergen_service(self, mock_allergen_client):
        """AllergenServiceインスタンスフィクスチャ"""
        return AllergenService(allergen_client=mock_allergen_client)
    
    def test_allergen_service_initialization(self, mock_allergen_client):
        """AllergenServiceの初期化テスト"""
        service = AllergenService(allergen_client=mock_allergen_client)
        assert service.allergen_client == mock_allergen_client
    
    def test_singleton_allergen_service(self):
        """シングルトンパターンのテスト"""
        service1 = get_allergen_service()
        service2 = get_allergen_service()
        assert service1 is service2
    
    @pytest.mark.asyncio
    async def test_analyze_allergens_success(self, allergen_service, mock_allergen_client):
        """正常なアレルギー解析のテスト"""
        # 期待されるレスポンス
        expected_response = {
            "allergens": [
                {
                    "allergen": "wheat",
                    "category": "grain",
                    "severity": "major",
                    "likelihood": "high",
                    "source": "pasta ingredients"
                },
                {
                    "allergen": "dairy",
                    "category": "dairy", 
                    "severity": "major",
                    "likelihood": "high",
                    "source": "cheese topping"
                }
            ],
            "allergen_free": False,
            "dietary_warnings": ["Contains gluten", "Contains dairy"],
            "notes": "Classic Italian pasta dish with cheese",
            "confidence": 0.95
        }
        
        # モックの設定
        mock_allergen_client.extract_allergens.return_value = expected_response
        
        # テスト実行
        result = await allergen_service.analyze_allergens("カルボナーラ", "パスタ")
        
        # 検証
        assert result == expected_response
        mock_allergen_client.extract_allergens.assert_called_once_with("カルボナーラ", "パスタ")
    
    @pytest.mark.asyncio 
    async def test_analyze_allergens_empty_menu_item(self, allergen_service):
        """空のメニューアイテムのテスト"""
        with pytest.raises(ValueError, match="Menu item cannot be empty"):
            await allergen_service.analyze_allergens("")
        
        with pytest.raises(ValueError, match="Menu item cannot be empty"):
            await allergen_service.analyze_allergens("   ")
        
        with pytest.raises(ValueError, match="Menu item cannot be empty"):
            await allergen_service.analyze_allergens(None)
    
    @pytest.mark.asyncio
    async def test_analyze_allergens_no_category(self, allergen_service, mock_allergen_client):
        """カテゴリなしの解析テスト"""
        expected_response = {
            "allergens": [],
            "allergen_free": True,
            "dietary_warnings": [],
            "notes": "Simple rice dish with minimal ingredients",
            "confidence": 0.8
        }
        
        mock_allergen_client.extract_allergens.return_value = expected_response
        
        result = await allergen_service.analyze_allergens("白米")
        
        assert result == expected_response
        mock_allergen_client.extract_allergens.assert_called_once_with("白米", "")
    
    @pytest.mark.asyncio
    async def test_analyze_allergens_client_exception(self, allergen_service, mock_allergen_client):
        """AllergenClientで例外が発生した場合のテスト"""
        # クライアントで例外を発生させる
        mock_allergen_client.extract_allergens.side_effect = Exception("OpenAI API error")
        
        # 例外が適切に伝播されることを確認
        with pytest.raises(Exception, match="OpenAI API error"):
            await allergen_service.analyze_allergens("テストメニュー")


class TestAllergenServiceIntegration:
    """AllergenServiceの統合テストクラス"""
    
    @pytest.mark.asyncio
    async def test_allergen_analysis_with_real_data_structures(self):
        """実際のデータ構造を使った統合テスト"""
        # AllergenClientをモック
        with patch('app_2.services.allergen_service.get_allergen_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # 複数のアレルゲンを含む複雑なレスポンス
            complex_response = {
                "allergens": [
                    {
                        "allergen": "shellfish",
                        "category": "seafood",
                        "severity": "major",
                        "likelihood": "high",
                        "source": "shrimp main ingredient"
                    },
                    {
                        "allergen": "wheat",
                        "category": "grain", 
                        "severity": "major",
                        "likelihood": "medium",
                        "source": "tempura batter"
                    },
                    {
                        "allergen": "soy",
                        "category": "vegetables",
                        "severity": "minor",
                        "likelihood": "high",
                        "source": "soy sauce seasoning"
                    }
                ],
                "allergen_free": False,
                "dietary_warnings": [
                    "Contains shellfish",
                    "May contain gluten",
                    "Contains soy products"
                ],
                "notes": "Japanese tempura dish with multiple allergen sources",
                "confidence": 0.92
            }
            
            mock_client.extract_allergens.return_value = complex_response
            
            # テスト実行
            service = AllergenService()
            result = await service.analyze_allergens("エビフライ", "天ぷら・フライ")
            
            # 詳細検証
            assert result["allergen_free"] is False
            assert len(result["allergens"]) == 3
            assert result["confidence"] > 0.9
            
            # 各アレルゲンの構造検証
            allergen_names = [a["allergen"] for a in result["allergens"]]
            assert "shellfish" in allergen_names
            assert "wheat" in allergen_names
            assert "soy" in allergen_names
            
            # 重大度レベルの検証
            severity_levels = [a["severity"] for a in result["allergens"]]
            assert "major" in severity_levels
            assert "minor" in severity_levels


class TestAllergenServiceErrorHandling:
    """エラーハンドリングの詳細テスト"""
    
    @pytest.fixture
    def failing_allergen_client(self):
        """失敗するAllergenClientのモック"""
        mock_client = AsyncMock(spec=AllergenClient)
        return mock_client
    
    @pytest.mark.asyncio
    async def test_timeout_error_handling(self, failing_allergen_client):
        """タイムアウトエラーのハンドリングテスト"""
        failing_allergen_client.extract_allergens.side_effect = asyncio.TimeoutError("Request timeout")
        
        service = AllergenService(allergen_client=failing_allergen_client)
        
        with pytest.raises(asyncio.TimeoutError):
            await service.analyze_allergens("複雑なメニュー")
    
    @pytest.mark.asyncio
    async def test_api_rate_limit_error(self, failing_allergen_client):
        """API制限エラーのハンドリングテスト"""
        failing_allergen_client.extract_allergens.side_effect = Exception("Rate limit exceeded")
        
        service = AllergenService(allergen_client=failing_allergen_client)
        
        with pytest.raises(Exception, match="Rate limit exceeded"):
            await service.analyze_allergens("テストメニュー")


class TestAllergenServiceRealWorldScenarios:
    """実世界のシナリオテスト"""
    
    @pytest.mark.asyncio 
    async def test_japanese_menu_items(self):
        """日本語メニューアイテムのテスト"""
        with patch('app_2.services.allergen_service.get_allergen_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            # 日本料理特有のアレルゲン情報
            japanese_food_response = {
                "allergens": [
                    {
                        "allergen": "soy",
                        "category": "vegetables",
                        "severity": "minor",
                        "likelihood": "high",
                        "source": "soy sauce, miso paste"
                    },
                    {
                        "allergen": "wheat",
                        "category": "grain",
                        "severity": "major", 
                        "likelihood": "medium",
                        "source": "possible wheat in miso"
                    },
                    {
                        "allergen": "fish",
                        "category": "seafood",
                        "severity": "major",
                        "likelihood": "high",
                        "source": "fish stock (dashi)"
                    }
                ],
                "allergen_free": False,
                "dietary_warnings": [
                    "Contains fish derivatives",
                    "Contains soy products",
                    "May contain gluten"
                ],
                "notes": "Traditional Japanese soup with multiple allergen sources",
                "confidence": 0.88
            }
            
            mock_client.extract_allergens.return_value = japanese_food_response
            
            service = AllergenService()
            result = await service.analyze_allergens("味噌汁", "汁物")
            
            # 日本料理特有の検証
            allergen_names = [a["allergen"] for a in result["allergens"]]
            assert "soy" in allergen_names  # 大豆（醤油・味噌）
            assert "fish" in allergen_names  # 魚（だし）
            assert len(result["dietary_warnings"]) > 0
    
    @pytest.mark.asyncio
    async def test_allergen_free_item(self):
        """アレルゲンフリーアイテムのテスト"""
        with patch('app_2.services.allergen_service.get_allergen_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            allergen_free_response = {
                "allergens": [],
                "allergen_free": True,
                "dietary_warnings": [],
                "notes": "Simple water-based beverage, no common allergens",
                "confidence": 0.99
            }
            
            mock_client.extract_allergens.return_value = allergen_free_response
            
            service = AllergenService()
            result = await service.analyze_allergens("水", "飲み物")
            
            assert result["allergen_free"] is True
            assert len(result["allergens"]) == 0
            assert result["confidence"] > 0.95
    
    @pytest.mark.asyncio
    async def test_complex_dish_multiple_allergens(self):
        """複雑な料理（複数アレルゲン）のテスト"""
        with patch('app_2.services.allergen_service.get_allergen_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            complex_dish_response = {
                "allergens": [
                    {
                        "allergen": "eggs",
                        "category": "protein",
                        "severity": "major",
                        "likelihood": "high",
                        "source": "pasta dough"
                    },
                    {
                        "allergen": "dairy",
                        "category": "dairy",
                        "severity": "major", 
                        "likelihood": "high",
                        "source": "cream sauce, cheese"
                    },
                    {
                        "allergen": "wheat",
                        "category": "grain",
                        "severity": "major",
                        "likelihood": "high",
                        "source": "pasta flour"
                    },
                    {
                        "allergen": "shellfish",
                        "category": "seafood",
                        "severity": "major",
                        "likelihood": "medium",
                        "source": "possible shared cooking equipment"
                    }
                ],
                "allergen_free": False,
                "dietary_warnings": [
                    "Contains eggs",
                    "Contains dairy products", 
                    "Contains gluten",
                    "May contain shellfish"
                ],
                "notes": "Rich Italian pasta with multiple major allergens",
                "confidence": 0.94
            }
            
            mock_client.extract_allergens.return_value = complex_dish_response
            
            service = AllergenService()
            result = await service.analyze_allergens("カルボナーラ", "パスタ")
            
            # 複数アレルゲンの検証
            assert len(result["allergens"]) >= 3
            assert result["allergen_free"] is False
            
            # 主要アレルゲンの存在確認
            allergen_names = [a["allergen"] for a in result["allergens"]]
            major_allergens = ["eggs", "dairy", "wheat"]
            for allergen in major_allergens:
                assert allergen in allergen_names


# デバッグ用の実行可能スクリプト
if __name__ == "__main__":
    import sys
    import os
    
    # app_2をPython pathに追加
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
    
    # 簡単なテスト実行
    async def debug_allergen_service():
        """デバッグ用の簡易テスト実行"""
        print("🧪 Allergen Service Debug Test Starting...")
        
        # モッククライアントでのテスト
        mock_client = AsyncMock(spec=AllergenClient)
        mock_client.extract_allergens.return_value = {
            "allergens": [
                {
                    "allergen": "shellfish",
                    "category": "seafood",
                    "severity": "major",
                    "likelihood": "high",
                    "source": "main ingredient"
                }
            ],
            "allergen_free": False,
            "dietary_warnings": ["Contains shellfish"],
            "notes": "Shrimp-based dish",
            "confidence": 0.95
        }
        
        service = AllergenService(allergen_client=mock_client)
        
        try:
            result = await service.analyze_allergens("エビフライ", "フライ")
            print(f"✅ Test Success: {result}")
            print(f"📊 Allergens found: {len(result['allergens'])}")
            print(f"🛡️ Allergen free: {result['allergen_free']}")
            print(f"📈 Confidence: {result['confidence']}")
        except Exception as e:
            print(f"❌ Test Failed: {e}")
        
        print("🧪 Allergen Service Debug Test Completed")
    
    # 非同期関数の実行
    asyncio.run(debug_allergen_service()) 