"""
OCRService テスト
Google Vision API を使用したテキスト抽出サービスの包括的検証
"""
import pytest
import os
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Union

from app_2.services.ocr_service import OCRService, get_ocr_service


class TestOCRService:
    """OCRService 単体テスト"""
    
    def test_init_with_default_vision_client(self):
        """デフォルトVisionClientでの初期化テスト"""
        with patch('app_2.services.ocr_service.get_google_vision_client') as mock_get_client:
            mock_vision_client = Mock()
            mock_get_client.return_value = mock_vision_client
            
            service = OCRService()
            
            assert service.vision_client is mock_vision_client
            mock_get_client.assert_called_once()
    
    def test_init_with_custom_vision_client(self):
        """カスタムVisionClientでの初期化テスト"""
        mock_vision_client = Mock()
        
        service = OCRService(vision_client=mock_vision_client)
        
        assert service.vision_client is mock_vision_client

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_success_word_level(self):
        """位置情報付きテキスト抽出成功テスト（wordレベル）"""
        # モック設定
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = [
            {"text": "Pizza", "x_center": 100.0, "y_center": 200.0},
            {"text": "Margherita", "x_center": 150.0, "y_center": 200.0},
            {"text": "¥1200", "x_center": 200.0, "y_center": 250.0}
        ]
        
        service = OCRService(vision_client=mock_vision_client)
        
        # テスト実行
        image_data = b"fake_image_data"
        result = await service.extract_text_with_positions(image_data, level="word")
        
        # 検証
        expected_result = [
            {"text": "Pizza", "x_center": 100.0, "y_center": 200.0},
            {"text": "Margherita", "x_center": 150.0, "y_center": 200.0},
            {"text": "¥1200", "x_center": 200.0, "y_center": 250.0}
        ]
        assert result == expected_result
        mock_vision_client.extract_text_with_positions.assert_called_once_with(image_data, "word")

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_success_paragraph_level(self):
        """位置情報付きテキスト抽出成功テスト（paragraphレベル）"""
        # モック設定
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = [
            {"text": "Pizza Margherita", "x_center": 125.0, "y_center": 200.0},
            {"text": "¥1200", "x_center": 200.0, "y_center": 250.0}
        ]
        
        service = OCRService(vision_client=mock_vision_client)
        
        # テスト実行
        image_data = b"fake_image_data"
        result = await service.extract_text_with_positions(image_data, level="paragraph")
        
        # 検証
        expected_result = [
            {"text": "Pizza Margherita", "x_center": 125.0, "y_center": 200.0},
            {"text": "¥1200", "x_center": 200.0, "y_center": 250.0}
        ]
        assert result == expected_result
        mock_vision_client.extract_text_with_positions.assert_called_once_with(image_data, "paragraph")

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_default_level(self):
        """位置情報付きテキスト抽出デフォルトレベルテスト"""
        # モック設定
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = []
        
        service = OCRService(vision_client=mock_vision_client)
        
        # テスト実行（levelパラメータなし）
        image_data = b"fake_image_data"
        result = await service.extract_text_with_positions(image_data)
        
        # 検証 - デフォルトは"word"レベル
        mock_vision_client.extract_text_with_positions.assert_called_once_with(image_data, "word")

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_empty_result(self):
        """テキスト抽出結果が空の場合のテスト"""
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = []
        
        service = OCRService(vision_client=mock_vision_client)
        
        # テスト実行
        image_data = b"fake_image_data"
        result = await service.extract_text_with_positions(image_data, level="word")
        
        # 検証
        assert result == []
        mock_vision_client.extract_text_with_positions.assert_called_once_with(image_data, "word")

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_empty_image_data(self):
        """空の画像データでのテスト"""
        mock_vision_client = AsyncMock()
        service = OCRService(vision_client=mock_vision_client)
        
        # テスト実行・検証
        with pytest.raises(ValueError, match="Image data is empty"):
            await service.extract_text_with_positions(b"")

        with pytest.raises(ValueError, match="Image data is empty"):
            await service.extract_text_with_positions(None)

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_vision_api_exception(self):
        """Vision API例外発生時のテスト"""
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.side_effect = Exception("Vision API Error")
        
        service = OCRService(vision_client=mock_vision_client)
        
        # テスト実行・検証
        image_data = b"fake_image_data"
        with pytest.raises(Exception, match="Vision API Error"):
            await service.extract_text_with_positions(image_data, level="word")

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_japanese_text(self):
        """日本語テキスト抽出テスト"""
        # モック設定
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = [
            {"text": "ブレンドコーヒー", "x_center": 120.0, "y_center": 240.0},
            {"text": "カフェラテ", "x_center": 120.0, "y_center": 280.0},
            {"text": "¥400", "x_center": 200.0, "y_center": 240.0},
            {"text": "¥500", "x_center": 200.0, "y_center": 280.0}
        ]
        
        service = OCRService(vision_client=mock_vision_client)
        
        # テスト実行
        image_data = b"fake_japanese_menu_image"
        result = await service.extract_text_with_positions(image_data, level="word")
        
        # 検証
        assert len(result) == 4
        assert any(item["text"] == "ブレンドコーヒー" for item in result)
        assert any(item["text"] == "カフェラテ" for item in result)
        assert any(item["text"] == "¥400" for item in result)

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_large_image(self):
        """大きな画像データでのテスト"""
        # モック設定
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = [
            {"text": "Large Menu", "x_center": 500.0, "y_center": 600.0}
        ]
        
        service = OCRService(vision_client=mock_vision_client)
        
        # 大きな画像データをシミュレート（1MB）
        large_image_data = b"x" * (1024 * 1024)
        
        # テスト実行
        result = await service.extract_text_with_positions(large_image_data, level="paragraph")
        
        # 検証
        assert len(result) == 1
        assert result[0]["text"] == "Large Menu"
        mock_vision_client.extract_text_with_positions.assert_called_once_with(large_image_data, "paragraph")


class TestOCRServiceIntegration:
    """OCRService インテグレーションテスト - 実際の画像ファイルを使用"""
    
    @pytest.fixture
    def test_image_path(self):
        """テスト画像ファイルのパスを提供"""
        current_dir = Path(__file__).parent.parent  # tests/services から tests へ
        image_path = current_dir / "data" / "menu_test.webp"
        return image_path
    
    @pytest.fixture
    def coffee_menu_expected_positions(self):
        """コーヒーショップメニューから期待される位置情報付きテキスト要素"""
        return [
            {"text": "DRINKS", "x_center": 150.0, "y_center": 50.0},
            {"text": "COFFEE", "x_center": 80.0, "y_center": 100.0},
            {"text": "TEA", "x_center": 80.0, "y_center": 200.0},
            {"text": "ブレンド", "x_center": 120.0, "y_center": 130.0},
            {"text": "¥400", "x_center": 200.0, "y_center": 130.0}
        ]

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_with_mock(self, test_image_path, coffee_menu_expected_positions):
        """位置情報付きテキスト抽出テスト（モック使用）"""
        # モック設定
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = coffee_menu_expected_positions
        
        service = OCRService(vision_client=mock_vision_client)
        
        # 実際の画像ファイルを読み込み
        if test_image_path.exists():
            with open(test_image_path, 'rb') as f:
                image_data = f.read()
            
            # テスト実行
            result = await service.extract_text_with_positions(image_data, level="word")
            
            # 検証
            assert result == coffee_menu_expected_positions
            mock_vision_client.extract_text_with_positions.assert_called_once_with(image_data, "word")
        else:
            pytest.skip(f"Test image not found: {test_image_path}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_extract_text_with_positions_real_api(self, test_image_path):
        """実際のGoogle Vision APIを使用した位置情報付きテキスト抽出テスト
        
        注意: このテストは実際のGoogle Vision API認証情報が必要です。
        認証情報がない場合はスキップされます。
        """
        try:
            # 実際のOCRServiceを使用
            service = OCRService()  # デフォルトクライアントを使用
            
            if test_image_path.exists():
                with open(test_image_path, 'rb') as f:
                    image_data = f.read()
                
                # 実際のOCR実行（wordレベル）
                result_word = await service.extract_text_with_positions(image_data, level="word")
                
                # 基本的な検証
                assert isinstance(result_word, list)
                
                if result_word:  # 結果がある場合のみ詳細検証
                    # 各要素が正しい構造を持つかチェック
                    for item in result_word:
                        assert isinstance(item, dict)
                        assert "text" in item
                        assert "x_center" in item
                        assert "y_center" in item
                        assert isinstance(item["text"], str)
                        assert isinstance(item["x_center"], (int, float))
                        assert isinstance(item["y_center"], (int, float))
                
                # paragraphレベルもテスト
                result_paragraph = await service.extract_text_with_positions(image_data, level="paragraph")
                assert isinstance(result_paragraph, list)
                
                # paragraphレベルの方がword数が少ないか等しいはず
                assert len(result_paragraph) <= len(result_word)
                
                print(f"Word level OCR結果: {len(result_word)}個の要素")
                print(f"Paragraph level OCR結果: {len(result_paragraph)}個の要素")
                
                if result_word:
                    print(f"最初の要素例: {result_word[0]}")
                
            else:
                pytest.skip(f"Test image not found: {test_image_path}")
                
        except Exception as e:
            # Google Vision API認証エラーの場合はスキップ
            if any(keyword in str(e).lower() for keyword in ["authentication", "credentials", "permission"]):
                pytest.skip(f"Google Vision API credentials not available: {e}")
            else:
                raise

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_file_validation(self, test_image_path):
        """ファイル読み込み検証テスト（APIコールはモック）"""
        # ファイル読み込みをテストしつつ、APIコールはモック
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = [
            {"text": "Sample Text", "x_center": 100.0, "y_center": 200.0}
        ]
        
        service = OCRService(vision_client=mock_vision_client)
        
        if test_image_path.exists():
            with open(test_image_path, 'rb') as f:
                image_data = f.read()
            
            # バイトデータが正しく読み込まれているかチェック
            assert len(image_data) > 0
            assert isinstance(image_data, bytes)
            
            # OCR処理実行
            result = await service.extract_text_with_positions(image_data, level="paragraph")
            
            # 検証
            expected_result = [{"text": "Sample Text", "x_center": 100.0, "y_center": 200.0}]
            assert result == expected_result
            mock_vision_client.extract_text_with_positions.assert_called_once_with(image_data, "paragraph")
        else:
            pytest.skip(f"Test image not found: {test_image_path}")


class TestOCRServiceFactory:
    """OCRService ファクトリー関数テスト"""
    
    def test_get_ocr_service_returns_singleton(self):
        """get_ocr_service がシングルトンを返すことをテスト"""
        service1 = get_ocr_service()
        service2 = get_ocr_service()
        
        assert service1 is service2
        assert isinstance(service1, OCRService)
    
    def test_get_ocr_service_with_lru_cache(self):
        """@lru_cache デコレータが正しく動作することをテスト"""
        # キャッシュクリア
        get_ocr_service.cache_clear()
        
        # 初回呼び出し
        service1 = get_ocr_service()
        
        # 2回目呼び出し（キャッシュから取得）
        service2 = get_ocr_service()
        
        # 同じインスタンスが返されることを確認
        assert service1 is service2
        
        # キャッシュ情報確認
        cache_info = get_ocr_service.cache_info()
        assert cache_info.hits >= 1
        assert cache_info.misses == 1

    def test_get_ocr_service_type_consistency(self):
        """ファクトリー関数が常に同じ型のインスタンスを返すことをテスト"""
        # キャッシュクリア
        get_ocr_service.cache_clear()
        
        # 複数回呼び出してすべて同じ型であることを確認
        services = [get_ocr_service() for _ in range(5)]
        
        # すべてOCRServiceインスタンス
        for service in services:
            assert isinstance(service, OCRService)
        
        # すべて同じインスタンス
        for i in range(1, len(services)):
            assert services[i] is services[0]


class TestOCRServiceErrorHandling:
    """OCRService エラーハンドリング特化テスト"""
    
    @pytest.mark.asyncio
    async def test_extract_text_with_positions_none_image_data(self):
        """Noneの画像データでのテスト"""
        mock_vision_client = AsyncMock()
        service = OCRService(vision_client=mock_vision_client)
        
        with pytest.raises(ValueError, match="Image data is empty"):
            await service.extract_text_with_positions(None)

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_zero_length_data(self):
        """0バイトの画像データでのテスト"""
        mock_vision_client = AsyncMock()
        service = OCRService(vision_client=mock_vision_client)
        
        with pytest.raises(ValueError, match="Image data is empty"):
            await service.extract_text_with_positions(b"")

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_invalid_level(self):
        """無効なlevelパラメータでのテスト"""
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.return_value = []
        
        service = OCRService(vision_client=mock_vision_client)
        image_data = b"fake_image_data"
        
        # 無効なlevelでも処理は通る（GoogleVisionClientに委譲）
        result = await service.extract_text_with_positions(image_data, level="invalid")
        
        assert result == []
        mock_vision_client.extract_text_with_positions.assert_called_once_with(image_data, "invalid")

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_network_timeout(self):
        """ネットワークタイムアウト例外のテスト"""
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.side_effect = TimeoutError("Network timeout")
        
        service = OCRService(vision_client=mock_vision_client)
        image_data = b"fake_image_data"
        
        with pytest.raises(TimeoutError, match="Network timeout"):
            await service.extract_text_with_positions(image_data)

    @pytest.mark.asyncio
    async def test_extract_text_with_positions_api_quota_exceeded(self):
        """APIクォータ超過例外のテスト"""
        mock_vision_client = AsyncMock()
        mock_vision_client.extract_text_with_positions.side_effect = Exception("Quota exceeded")
        
        service = OCRService(vision_client=mock_vision_client)
        image_data = b"fake_image_data"
        
        with pytest.raises(Exception, match="Quota exceeded"):
            await service.extract_text_with_positions(image_data)


# テスト実行用のヘルパー
def run_unit_tests():
    """単体テストのみを実行するヘルパー関数"""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/services/test_ocr_service.py::TestOCRService",
        "tests/services/test_ocr_service.py::TestOCRServiceFactory",
        "tests/services/test_ocr_service.py::TestOCRServiceErrorHandling",
        "-v", "-s", "--tb=short"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0


def run_integration_tests():
    """インテグレーションテストのみを実行するヘルパー関数"""
    import subprocess
    import sys
    
    cmd = [
        sys.executable, "-m", "pytest", 
        "tests/services/test_ocr_service.py::TestOCRServiceIntegration",
        "-v", "-s", "--tb=short"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    return result.returncode == 0


if __name__ == "__main__":
    # 直接実行時は単体テストを実行
    print("Running OCR Service Unit Tests...")
    run_unit_tests() 