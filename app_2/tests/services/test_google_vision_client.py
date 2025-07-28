"""
GoogleVisionClient テスト
Google Cloud Vision API との統合テスト
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import List, Dict, Union
from google.cloud import vision

from app_2.infrastructure.integrations.google.google_vision_client import GoogleVisionClient, get_google_vision_client


class TestGoogleVisionClient:
    """GoogleVisionClient 単体テスト"""
    
    @patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager')
    def test_init_with_credential_manager(self, mock_get_credential_manager):
        """認証情報マネージャーでの初期化テスト"""
        mock_credential_manager = Mock()
        mock_vision_client = Mock()
        mock_credential_manager.get_vision_client.return_value = mock_vision_client
        mock_get_credential_manager.return_value = mock_credential_manager
        
        client = GoogleVisionClient()
        
        assert client.client is mock_vision_client
        mock_get_credential_manager.assert_called_once()
        mock_credential_manager.get_vision_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_extract_text_success(self):
        """テキスト抽出成功テスト"""
        # モック設定
        mock_vision_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        
        # full_text_annotationのモック
        mock_full_text_annotation = Mock()
        mock_full_text_annotation.text = "Pizza Margherita\nSpaghetti Carbonara\n¥1200\nCaesar Salad"
        mock_response.full_text_annotation = mock_full_text_annotation
        
        mock_vision_client.document_text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            client.client = mock_vision_client
            
            # テスト実行
            image_data = b"fake_image_data"
            result = await client.extract_text(image_data)
            
            # 検証
            expected_result = ["Pizza Margherita", "Spaghetti Carbonara", "¥1200", "Caesar Salad"]
            assert result == expected_result
            
            # Vision APIが正しく呼び出されたかチェック
            mock_vision_client.document_text_detection.assert_called_once()
            call_args = mock_vision_client.document_text_detection.call_args[1]
            assert call_args['image'].content == image_data

    @pytest.mark.asyncio
    async def test_extract_text_empty_result(self):
        """テキスト抽出結果が空の場合のテスト"""
        # モック設定
        mock_vision_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        mock_response.full_text_annotation = None
        
        mock_vision_client.document_text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            client.client = mock_vision_client
            
            # テスト実行
            image_data = b"fake_image_data"
            result = await client.extract_text(image_data)
            
            # 検証
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_text_with_empty_text(self):
        """空のテキストアノテーションの場合のテスト"""
        # モック設定
        mock_vision_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        
        mock_full_text_annotation = Mock()
        mock_full_text_annotation.text = ""
        mock_response.full_text_annotation = mock_full_text_annotation
        
        mock_vision_client.document_text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            client.client = mock_vision_client
            
            # テスト実行
            image_data = b"fake_image_data"
            result = await client.extract_text(image_data)
            
            # 検証
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_text_vision_api_error(self):
        """Vision API エラーの場合のテスト"""
        # モック設定
        mock_vision_client = Mock()
        mock_response = Mock()
        mock_response.error.message = "Vision API quota exceeded"
        
        mock_vision_client.document_text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            client.client = mock_vision_client
            
            # テスト実行・検証
            image_data = b"fake_image_data"
            with pytest.raises(Exception, match="Vision API error: Vision API quota exceeded"):
                await client.extract_text(image_data)

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_word_level_success(self):
        """位置情報付きテキスト抽出成功テスト（wordレベル）"""
        # モック設定
        mock_vision_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        
        # 複雑なVision API レスポンス構造をモック
        mock_page = Mock()
        mock_block = Mock()
        mock_paragraph = Mock()
        
        # Word 1: "Pizza"
        mock_word1 = Mock()
        mock_symbol1_1 = Mock()
        mock_symbol1_1.text = "P"
        mock_symbol1_2 = Mock()
        mock_symbol1_2.text = "i"
        mock_symbol1_3 = Mock()
        mock_symbol1_3.text = "z"
        mock_symbol1_4 = Mock()
        mock_symbol1_4.text = "z"
        mock_symbol1_5 = Mock()
        mock_symbol1_5.text = "a"
        mock_word1.symbols = [mock_symbol1_1, mock_symbol1_2, mock_symbol1_3, mock_symbol1_4, mock_symbol1_5]
        
        # Bounding box for word 1
        mock_vertex1_1 = Mock()
        mock_vertex1_1.x = 90
        mock_vertex1_1.y = 190
        mock_vertex1_2 = Mock()
        mock_vertex1_2.x = 110
        mock_vertex1_2.y = 190
        mock_vertex1_3 = Mock()
        mock_vertex1_3.x = 110
        mock_vertex1_3.y = 210
        mock_vertex1_4 = Mock()
        mock_vertex1_4.x = 90
        mock_vertex1_4.y = 210
        
        mock_word1.bounding_box = Mock()
        mock_word1.bounding_box.vertices = [mock_vertex1_1, mock_vertex1_2, mock_vertex1_3, mock_vertex1_4]
        
        # Word 2: "¥500"
        mock_word2 = Mock()
        mock_symbol2_1 = Mock()
        mock_symbol2_1.text = "¥"
        mock_symbol2_2 = Mock()
        mock_symbol2_2.text = "5"
        mock_symbol2_3 = Mock()
        mock_symbol2_3.text = "0"
        mock_symbol2_4 = Mock()
        mock_symbol2_4.text = "0"
        mock_word2.symbols = [mock_symbol2_1, mock_symbol2_2, mock_symbol2_3, mock_symbol2_4]
        
        # Bounding box for word 2
        mock_vertex2_1 = Mock()
        mock_vertex2_1.x = 190
        mock_vertex2_1.y = 240
        mock_vertex2_2 = Mock()
        mock_vertex2_2.x = 210
        mock_vertex2_2.y = 240
        mock_vertex2_3 = Mock()
        mock_vertex2_3.x = 210
        mock_vertex2_3.y = 260
        mock_vertex2_4 = Mock()
        mock_vertex2_4.x = 190
        mock_vertex2_4.y = 260
        
        mock_word2.bounding_box = Mock()
        mock_word2.bounding_box.vertices = [mock_vertex2_1, mock_vertex2_2, mock_vertex2_3, mock_vertex2_4]
        
        mock_paragraph.words = [mock_word1, mock_word2]
        mock_block.paragraphs = [mock_paragraph]
        mock_page.blocks = [mock_block]
        
        mock_full_text_annotation = Mock()
        mock_full_text_annotation.pages = [mock_page]
        mock_response.full_text_annotation = mock_full_text_annotation
        
        mock_vision_client.document_text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            client.client = mock_vision_client
            
            # テスト実行
            image_data = b"fake_image_data"
            result = await client.extract_text_with_positions(image_data, level="word")
            
            # 検証
            assert len(result) == 2
            
            # 最初のword（Pizza）
            assert result[0]["text"] == "Pizza"
            assert result[0]["x_center"] == 100.0  # (90+110+110+90)/4
            assert result[0]["y_center"] == 200.0  # (190+190+210+210)/4
            
            # 2番目のword（¥500）
            assert result[1]["text"] == "¥500"
            assert result[1]["x_center"] == 200.0  # (190+210+210+190)/4
            assert result[1]["y_center"] == 250.0  # (240+240+260+260)/4

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_paragraph_level_success(self):
        """位置情報付きテキスト抽出成功テスト（paragraphレベル）"""
        # モック設定
        mock_vision_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        
        # Paragraph構造をモック
        mock_page = Mock()
        mock_block = Mock()
        mock_paragraph = Mock()
        
        # Word 1: "Pizza"
        mock_word1 = Mock()
        mock_symbol1_1 = Mock()
        mock_symbol1_1.text = "P"
        mock_symbol1_2 = Mock()
        mock_symbol1_2.text = "i"
        mock_symbol1_3 = Mock()
        mock_symbol1_3.text = "z"
        mock_symbol1_4 = Mock()
        mock_symbol1_4.text = "z"
        mock_symbol1_5 = Mock()
        mock_symbol1_5.text = "a"
        mock_word1.symbols = [mock_symbol1_1, mock_symbol1_2, mock_symbol1_3, mock_symbol1_4, mock_symbol1_5]
        
        # Word 2: "Margherita"
        mock_word2 = Mock()
        mock_symbol2_1 = Mock()
        mock_symbol2_1.text = "M"
        mock_symbol2_2 = Mock()
        mock_symbol2_2.text = "a"
        mock_symbol2_3 = Mock()
        mock_symbol2_3.text = "r"
        mock_word2.symbols = [mock_symbol2_1, mock_symbol2_2, mock_symbol2_3]  # 簡略化
        
        mock_paragraph.words = [mock_word1, mock_word2]
        
        # Paragraph bounding box
        mock_vertex1 = Mock()
        mock_vertex1.x = 80
        mock_vertex1.y = 180
        mock_vertex2 = Mock()
        mock_vertex2.x = 200
        mock_vertex2.y = 180
        mock_vertex3 = Mock()
        mock_vertex3.x = 200
        mock_vertex3.y = 220
        mock_vertex4 = Mock()
        mock_vertex4.x = 80
        mock_vertex4.y = 220
        
        mock_paragraph.bounding_box = Mock()
        mock_paragraph.bounding_box.vertices = [mock_vertex1, mock_vertex2, mock_vertex3, mock_vertex4]
        
        mock_block.paragraphs = [mock_paragraph]
        mock_page.blocks = [mock_block]
        
        mock_full_text_annotation = Mock()
        mock_full_text_annotation.pages = [mock_page]
        mock_response.full_text_annotation = mock_full_text_annotation
        
        mock_vision_client.document_text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            client.client = mock_vision_client
            
            # テスト実行
            image_data = b"fake_image_data"
            result = await client.extract_text_with_positions(image_data, level="paragraph")
            
            # 検証
            assert len(result) == 1
            assert result[0]["text"] == "PizzaMar"  # 簡略化したテキスト
            assert result[0]["x_center"] == 140.0  # (80+200+200+80)/4
            assert result[0]["y_center"] == 200.0  # (180+180+220+220)/4

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_empty_result(self):
        """位置情報付きテキスト抽出で空結果の場合のテスト"""
        # モック設定
        mock_vision_client = Mock()
        mock_response = Mock()
        mock_response.error.message = ""
        mock_response.full_text_annotation = None
        
        mock_vision_client.document_text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            client.client = mock_vision_client
            
            # テスト実行
            image_data = b"fake_image_data"
            result = await client.extract_text_with_positions(image_data, level="word")
            
            # 検証
            assert result == []

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_vision_api_error(self):
        """位置情報付きテキスト抽出でVision API エラーの場合のテスト"""
        # モック設定
        mock_vision_client = Mock()
        mock_response = Mock()
        mock_response.error.message = "Invalid image format"
        
        mock_vision_client.document_text_detection.return_value = mock_response
        
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            client.client = mock_vision_client
            
            # テスト実行・検証
            image_data = b"fake_image_data"
            with pytest.raises(Exception, match="Vision API error: Invalid image format"):
                await client.extract_text_with_positions(image_data, level="word")

    def test_calculate_bounding_box_center_success(self):
        """バウンディングボックス中心計算成功テスト"""
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            
            # モック bounding box
            mock_bounding_box = Mock()
            
            mock_vertex1 = Mock()
            mock_vertex1.x = 100
            mock_vertex1.y = 200
            mock_vertex2 = Mock()
            mock_vertex2.x = 150
            mock_vertex2.y = 200
            mock_vertex3 = Mock()
            mock_vertex3.x = 150
            mock_vertex3.y = 250
            mock_vertex4 = Mock()
            mock_vertex4.x = 100
            mock_vertex4.y = 250
            
            mock_bounding_box.vertices = [mock_vertex1, mock_vertex2, mock_vertex3, mock_vertex4]
            
            # テスト実行
            x_center, y_center = client._calculate_bounding_box_center(mock_bounding_box)
            
            # 検証
            assert x_center == 125.0  # (100+150+150+100)/4
            assert y_center == 225.0  # (200+200+250+250)/4

    def test_calculate_bounding_box_center_empty_bounding_box(self):
        """空のバウンディングボックスでの中心計算テスト"""
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            
            # 空のbounding box
            mock_bounding_box = None
            
            # テスト実行
            x_center, y_center = client._calculate_bounding_box_center(mock_bounding_box)
            
            # 検証
            assert x_center == 0.0
            assert y_center == 0.0

    def test_calculate_bounding_box_center_no_vertices(self):
        """頂点がないバウンディングボックスでの中心計算テスト"""
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            
            # 頂点がないbounding box
            mock_bounding_box = Mock()
            mock_bounding_box.vertices = []
            
            # テスト実行
            x_center, y_center = client._calculate_bounding_box_center(mock_bounding_box)
            
            # 検証
            assert x_center == 0.0
            assert y_center == 0.0

    def test_calculate_bounding_box_center_missing_coordinates(self):
        """座標が欠けている頂点での中心計算テスト"""
        with patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager'):
            client = GoogleVisionClient()
            
            # 座標が一部欠けている頂点
            mock_bounding_box = Mock()
            
            mock_vertex1 = Mock()
            mock_vertex1.x = 100
            mock_vertex1.y = 200
            mock_vertex2 = Mock()
            # x座標なし
            mock_vertex2.y = 200
            
            mock_bounding_box.vertices = [mock_vertex1, mock_vertex2]
            
            # テスト実行
            x_center, y_center = client._calculate_bounding_box_center(mock_bounding_box)
            
            # 検証 - 有効な座標のみで計算
            assert x_center == 100.0  # 100/1
            assert y_center == 200.0  # (200+200)/2


class TestGoogleVisionClientFactory:
    """GoogleVisionClient ファクトリー関数テスト"""
    
    @patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager')
    def test_get_google_vision_client_returns_singleton(self, mock_get_credential_manager):
        """get_google_vision_client がシングルトンを返すことをテスト"""
        mock_credential_manager = Mock()
        mock_vision_client = Mock()
        mock_credential_manager.get_vision_client.return_value = mock_vision_client
        mock_get_credential_manager.return_value = mock_credential_manager
        
        client1 = get_google_vision_client()
        client2 = get_google_vision_client()
        
        assert client1 is client2
        assert isinstance(client1, GoogleVisionClient)

    @patch('app_2.infrastructure.integrations.google.google_vision_client.get_google_credential_manager')
    def test_get_google_vision_client_with_lru_cache(self, mock_get_credential_manager):
        """@lru_cache デコレータが正しく動作することをテスト"""
        mock_credential_manager = Mock()
        mock_vision_client = Mock()
        mock_credential_manager.get_vision_client.return_value = mock_vision_client
        mock_get_credential_manager.return_value = mock_credential_manager
        
        # キャッシュクリア
        get_google_vision_client.cache_clear()
        
        # 初回呼び出し
        client1 = get_google_vision_client()
        
        # 2回目呼び出し（キャッシュから取得）
        client2 = get_google_vision_client()
        
        # 同じインスタンスが返されることを確認
        assert client1 is client2
        
        # キャッシュ情報確認
        cache_info = get_google_vision_client.cache_info()
        assert cache_info.hits >= 1
        assert cache_info.misses == 1


class TestGoogleVisionClientIntegration:
    """GoogleVisionClient インテグレーションテスト"""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_extract_text_with_real_api(self):
        """実際のGoogle Vision APIを使用したテキスト抽出テスト
        
        注意: このテストは実際のGoogle Vision API認証情報が必要です。
        認証情報がない場合はスキップされます。
        """
        try:
            # 実際のGoogleVisionClientを使用
            client = GoogleVisionClient()
            
            # 簡単なテスト画像データ（Base64エンコードされた小さな画像など）
            # 実際のテストでは適切な画像データを使用する
            test_image_data = b"fake_image_data_for_api_test"
            
            # 実際のAPI呼び出し
            result = await client.extract_text(test_image_data)
            
            # 基本的な検証
            assert isinstance(result, list)
            
        except Exception as e:
            # Google Vision API認証エラーの場合はスキップ
            if any(keyword in str(e).lower() for keyword in ["authentication", "credentials", "permission", "quota"]):
                pytest.skip(f"Google Vision API not available: {e}")
            else:
                raise

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_extract_text_with_positions_with_real_api(self):
        """実際のGoogle Vision APIを使用した位置情報付きテキスト抽出テスト
        
        注意: このテストは実際のGoogle Vision API認証情報が必要です。
        認証情報がない場合はスキップされます。
        """
        try:
            # 実際のGoogleVisionClientを使用
            client = GoogleVisionClient()
            
            # 簡単なテスト画像データ
            test_image_data = b"fake_image_data_for_api_test"
            
            # 実際のAPI呼び出し（wordレベル）
            result_word = await client.extract_text_with_positions(test_image_data, level="word")
            
            # 基本的な検証
            assert isinstance(result_word, list)
            
            # 結果がある場合の構造検証
            if result_word:
                for item in result_word:
                    assert isinstance(item, dict)
                    assert "text" in item
                    assert "x_center" in item
                    assert "y_center" in item
                    assert isinstance(item["text"], str)
                    assert isinstance(item["x_center"], (int, float))
                    assert isinstance(item["y_center"], (int, float))
            
            # paragraphレベルもテスト
            result_paragraph = await client.extract_text_with_positions(test_image_data, level="paragraph")
            assert isinstance(result_paragraph, list)
            
        except Exception as e:
            # Google Vision API認証エラーの場合はスキップ
            if any(keyword in str(e).lower() for keyword in ["authentication", "credentials", "permission", "quota"]):
                pytest.skip(f"Google Vision API not available: {e}")
            else:
                raise


# テスト実行用のヘルパー
def run_vision_client_unit_tests():
    """GoogleVisionClient 単体テストのみを実行するヘルパー関数"""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/services/test_google_vision_client.py::TestGoogleVisionClient",
        "tests/services/test_google_vision_client.py::TestGoogleVisionClientFactory",
        "-v", "-s", "--tb=short"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0


def run_vision_client_integration_tests():
    """GoogleVisionClient インテグレーションテストのみを実行するヘルパー関数"""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/services/test_google_vision_client.py::TestGoogleVisionClientIntegration",
        "-v", "-s", "--tb=short"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0


if __name__ == "__main__":
    # 直接実行時は単体テストを実行
    print("Running GoogleVisionClient Unit Tests...")
    run_vision_client_unit_tests() 