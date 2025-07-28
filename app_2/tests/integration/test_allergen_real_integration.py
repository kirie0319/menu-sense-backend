"""
Real Allergen Integration Tests - Menu Processor v2
実際のOpenAI APIを使用したアレルギー解析の統合テスト

実行方法:
cd menu_sensor_backend
python -m pytest app_2/tests/integration/test_allergen_real_integration.py -v -s

注意: 実際のOpenAI APIキーが必要です
"""
import pytest
import asyncio
import os
from typing import Dict, Any

from app_2.services.allergen_service import get_allergen_service
from app_2.infrastructure.integrations.openai.allergen_client import get_allergen_client
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("allergen_real_integration_test")


@pytest.mark.integration
class TestRealAllergenIntegration:
    """実際のOpenAI APIを使用したアレルギー解析統合テスト"""
    
    @pytest.fixture(scope="class")
    def skip_if_no_api_key(self):
        """OpenAI APIキーが設定されていない場合はテストをスキップ"""
        if not settings.ai.openai_api_key:
            pytest.skip("OpenAI API key not configured")
    
    @pytest.mark.asyncio
    async def test_real_allergen_analysis_japanese_food(self, skip_if_no_api_key):
        """日本料理の実際のアレルギー解析テスト"""
        service = get_allergen_service()
        
        try:
            # 典型的な日本料理でテスト
            result = await service.analyze_allergens("エビフライ", "フライ")
            
            print(f"\n🧪 Real API Test - エビフライ:")
            print(f"  📊 Allergens: {len(result.get('allergens', []))}")
            print(f"  🛡️ Allergen free: {result.get('allergen_free', False)}")
            print(f"  📈 Confidence: {result.get('confidence', 0)}")
            print(f"  ⚠️ Warnings: {result.get('dietary_warnings', [])}")
            
            # 基本的な検証
            assert isinstance(result, dict)
            assert "allergens" in result
            assert "allergen_free" in result
            assert "confidence" in result
            
            # エビフライは甲殻類アレルゲンを含むはず
            if result.get("allergens"):
                allergen_names = [a.get("allergen", "").lower() for a in result["allergens"]]
                # 甲殻類関連のアレルゲンが検出されることを期待
                shellfish_related = any("shellfish" in name or "shrimp" in name or "prawn" in name 
                                       for name in allergen_names)
                assert shellfish_related, f"Shellfish allergen not detected in: {allergen_names}"
            
            assert result.get("confidence", 0) > 0.5, "Confidence should be reasonable"
            
        except Exception as e:
            logger.error(f"Real allergen analysis test failed: {e}")
            pytest.fail(f"Real API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_real_allergen_analysis_pasta(self, skip_if_no_api_key):
        """パスタ料理の実際のアレルギー解析テスト"""
        service = get_allergen_service()
        
        try:
            # 複数のアレルゲンを含む料理でテスト
            result = await service.analyze_allergens("カルボナーラ", "パスタ")
            
            print(f"\n🧪 Real API Test - カルボナーラ:")
            print(f"  📊 Allergens: {len(result.get('allergens', []))}")
            print(f"  🛡️ Allergen free: {result.get('allergen_free', False)}")
            print(f"  📈 Confidence: {result.get('confidence', 0)}")
            
            # 詳細なアレルゲン情報を表示
            for allergen in result.get("allergens", []):
                print(f"    - {allergen.get('allergen', 'unknown')}: {allergen.get('severity', 'unknown')}")
            
            # 基本的な検証
            assert isinstance(result, dict)
            assert "allergens" in result
            
            # カルボナーラは複数のアレルゲンを含むはず（卵、乳製品、小麦など）
            if result.get("allergens"):
                allergen_names = [a.get("allergen", "").lower() for a in result["allergens"]]
                
                # 期待されるアレルゲンのチェック
                expected_allergens = ["egg", "dairy", "wheat", "milk", "gluten"]
                found_expected = any(expected in " ".join(allergen_names) for expected in expected_allergens)
                assert found_expected, f"Expected allergens not found in: {allergen_names}"
            
        except Exception as e:
            logger.error(f"Real pasta allergen analysis test failed: {e}")
            pytest.fail(f"Real API test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_real_allergen_analysis_simple_item(self, skip_if_no_api_key):
        """シンプルなアイテムの実際のアレルギー解析テスト"""
        service = get_allergen_service()
        
        try:
            # アレルゲンフリーの可能性が高いアイテム
            result = await service.analyze_allergens("白米", "ご飯・米")
            
            print(f"\n🧪 Real API Test - 白米:")
            print(f"  📊 Allergens: {len(result.get('allergens', []))}")
            print(f"  🛡️ Allergen free: {result.get('allergen_free', False)}")
            print(f"  📈 Confidence: {result.get('confidence', 0)}")
            print(f"  📝 Notes: {result.get('notes', 'No notes')}")
            
            # 基本的な検証
            assert isinstance(result, dict)
            assert "allergens" in result
            assert "allergen_free" in result
            
            # 白米は比較的アレルゲンフリーの可能性が高い
            # ただし、AIの判断に依存するため厳密な検証は避ける
            assert result.get("confidence", 0) > 0.7, "Confidence should be high for simple items"
            
        except Exception as e:
            logger.error(f"Real simple item allergen analysis test failed: {e}")
            pytest.fail(f"Real API test failed: {e}")


class TestAllergenClientDirectly:
    """AllergenClientを直接テストする統合テスト"""
    
    @pytest.fixture(scope="class")
    def skip_if_no_api_key(self):
        """OpenAI APIキーが設定されていない場合はテストをスキップ"""
        if not settings.ai.openai_api_key:
            pytest.skip("OpenAI API key not configured")
    
    @pytest.mark.asyncio
    async def test_allergen_client_function_calling(self, skip_if_no_api_key):
        """AllergenClientのFunction Calling機能テスト"""
        client = get_allergen_client()
        
        try:
            # Function Callingスキーマの検証
            schema = client._get_allergen_function_schema()
            
            assert isinstance(schema, list)
            assert len(schema) > 0
            assert "name" in schema[0]
            assert schema[0]["name"] == "extract_allergens"
            
            # 実際のFunction Calling実行
            result = await client.extract_allergens("寿司", "和食")
            
            print(f"\n🧪 Function Calling Test - 寿司:")
            print(f"  📊 Result type: {type(result)}")
            print(f"  📊 Allergens: {len(result.get('allergens', []))}")
            print(f"  🛡️ Allergen free: {result.get('allergen_free', False)}")
            
            # Function Callingの結果検証
            assert isinstance(result, dict)
            required_fields = ["allergens", "allergen_free", "confidence"]
            for field in required_fields:
                assert field in result, f"Required field '{field}' missing from result"
            
            # アレルゲン構造の検証
            for allergen in result.get("allergens", []):
                assert isinstance(allergen, dict)
                required_allergen_fields = ["allergen", "category", "severity", "likelihood"]
                for field in required_allergen_fields:
                    assert field in allergen, f"Required allergen field '{field}' missing"
            
        except Exception as e:
            logger.error(f"AllergenClient Function Calling test failed: {e}")
            pytest.fail(f"Function Calling test failed: {e}")


# デバッグ用の実行可能スクリプト
if __name__ == "__main__":
    import sys
    import os
    
    # プロジェクトルートをPython pathに追加
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
    
    async def debug_real_allergen_integration():
        """デバッグ用の実際のAPI統合テスト"""
        print("🔬 Real Allergen Integration Debug Test Starting...")
        
        # API キーチェック
        if not settings.ai.openai_api_key:
            print("⚠️ OpenAI API key not configured - skipping real API tests")
            return
        
        try:
            service = get_allergen_service()
            
            # テストケース1: 日本料理
            print("\n🍤 Testing Japanese food - エビフライ:")
            result1 = await service.analyze_allergens("エビフライ", "フライ")
            print(f"  Result: {result1}")
            
            # テストケース2: 複雑なパスタ
            print("\n🍝 Testing Italian pasta - カルボナーラ:")
            result2 = await service.analyze_allergens("カルボナーラ", "パスタ")
            print(f"  Result: {result2}")
            
            # テストケース3: シンプルなアイテム
            print("\n🍚 Testing simple item - 白米:")
            result3 = await service.analyze_allergens("白米", "ご飯")
            print(f"  Result: {result3}")
            
            print("\n✅ All real API tests completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Real API test failed: {e}")
            import traceback
            traceback.print_exc()
    
    # 非同期関数の実行
    asyncio.run(debug_real_allergen_integration()) 