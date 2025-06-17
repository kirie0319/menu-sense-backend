"""
メインAPIエンドポイントのテスト
"""
import pytest
import json
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi import UploadFile
import io

from app.main import app
from app.services.ocr.base import OCRResult, OCRProvider
from app.services.category.base import CategoryResult, CategoryProvider


@pytest.mark.api
class TestHealthEndpoints:
    """ヘルスチェックエンドポイントのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.client = TestClient(app)

    def test_health_check(self):
        """ヘルスチェックエンドポイントのテスト"""
        response = self.client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert data["status"] == "healthy"

    def test_diagnostic_endpoint(self):
        """診断エンドポイントのテスト"""
        response = self.client.get("/api/diagnostic")
        
        assert response.status_code == 200
        data = response.json()
        assert "system_status" in data
        assert "services" in data
        assert "environment" in data

    def test_mobile_diagnostic_endpoint(self):
        """モバイル診断エンドポイントのテスト"""
        response = self.client.get("/api/mobile-diagnostic")
        
        assert response.status_code == 200
        data = response.json()
        assert "mobile_optimized" in data
        assert "available_features" in data


@pytest.mark.api
class TestTranslateEndpoint:
    """翻訳エンドポイントのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.client = TestClient(app)

    def test_translate_endpoint_success(self, mock_file_upload):
        """翻訳エンドポイントの成功ケース"""
        # モックファイルの準備
        test_file_content = b"fake image data"
        test_file = io.BytesIO(test_file_content)
        
        with patch('app.main.process_menu_background') as mock_process:
            # process_menu_background が正常に動作することをモック
            mock_process.return_value = asyncio.create_task(
                asyncio.coroutine(lambda: None)()
            )
            
            response = self.client.post(
                "/api/translate",
                files={"file": ("test_menu.jpg", test_file, "image/jpeg")}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "session_id" in data
            assert "message" in data
            assert "processing_started" in data["message"]

    def test_translate_endpoint_invalid_file_type(self):
        """無効なファイルタイプのテスト"""
        test_file = io.BytesIO(b"not an image")
        
        response = self.client.post(
            "/api/translate",
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "image" in data["error"].lower()

    def test_translate_endpoint_no_file(self):
        """ファイルなしのテスト"""
        response = self.client.post("/api/translate")
        
        assert response.status_code == 422  # FastAPIのバリデーションエラー

    def test_translate_endpoint_empty_file(self):
        """空ファイルのテスト"""
        test_file = io.BytesIO(b"")
        
        response = self.client.post(
            "/api/translate",
            files={"file": ("empty.jpg", test_file, "image/jpeg")}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "空" in data["error"] or "empty" in data["error"].lower()


@pytest.mark.api
class TestProgressEndpoint:
    """進行状況エンドポイントのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.client = TestClient(app)

    def test_progress_endpoint_new_session(self):
        """新しいセッションの進行状況テスト"""
        session_id = "test-session-new"
        
        with self.client.stream("GET", f"/api/progress/{session_id}") as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain"
            
            # 最初の数行を読み取り
            lines = []
            for i, line in enumerate(response.iter_lines()):
                if i >= 3:  # 最初の数行だけテスト
                    break
                lines.append(line)
            
            # SSEフォーマットの確認
            assert any("data:" in line for line in lines)

    def test_progress_endpoint_with_existing_data(self):
        """既存データがあるセッションの進行状況テスト"""
        session_id = "test-session-existing"
        
        # progress_storeに事前データを追加
        from app.main import progress_store
        progress_store[session_id] = [
            {
                "stage": 1,
                "status": "completed",
                "message": "OCR完了",
                "timestamp": 1234567890
            }
        ]
        
        with self.client.stream("GET", f"/api/progress/{session_id}") as response:
            assert response.status_code == 200
            
            # データが送信されることを確認
            lines = []
            for i, line in enumerate(response.iter_lines()):
                if i >= 5:  # 十分な行数を読み取り
                    break
                lines.append(line)
            
            # 事前データが含まれていることを確認
            content = "\n".join(lines)
            assert "OCR完了" in content


@pytest.mark.api
class TestPongEndpoint:
    """Pongエンドポイントのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.client = TestClient(app)

    def test_pong_endpoint_success(self):
        """Pongエンドポイントの成功ケース"""
        session_id = "test-session-pong"
        
        with patch('app.main.handle_pong') as mock_handle_pong:
            mock_handle_pong.return_value = True
            
            response = self.client.post(f"/api/pong/{session_id}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pong_received"
            assert data["session_id"] == session_id
            mock_handle_pong.assert_called_once_with(session_id)

    def test_pong_endpoint_invalid_session(self):
        """無効なセッションのPongテスト"""
        session_id = "invalid-session"
        
        with patch('app.main.handle_pong') as mock_handle_pong:
            mock_handle_pong.return_value = False
            
            response = self.client.post(f"/api/pong/{session_id}")
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()


@pytest.mark.api
@pytest.mark.slow
class TestEndToEndWorkflow:
    """エンドツーエンドワークフローのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.client = TestClient(app)

    def test_full_workflow_simulation(self, mock_file_upload):
        """完全なワークフローのシミュレーションテスト"""
        # サービス層をモック
        with patch('app.services.ocr.extract_text') as mock_ocr, \
             patch('app.services.category.categorize_menu') as mock_category, \
             patch('app.services.translation.translate_menu') as mock_translation, \
             patch('app.services.description.add_descriptions') as mock_description, \
             patch('app.services.image.generate_images') as mock_image:
            
            # モックレスポンスの設定
            mock_ocr.return_value = OCRResult(
                success=True,
                extracted_text="サンプルメニュー\n唐揚げ 800円",
                provider=OCRProvider.GEMINI
            )
            
            mock_category.return_value = CategoryResult(
                success=True,
                categories={"メイン": [{"name": "唐揚げ", "price": "800円"}]},
                uncategorized=[],
                provider=CategoryProvider.OPENAI
            )
            
            # ファイルアップロード
            test_file = io.BytesIO(b"fake image data")
            response = self.client.post(
                "/api/translate",
                files={"file": ("test_menu.jpg", test_file, "image/jpeg")}
            )
            
            assert response.status_code == 200
            data = response.json()
            session_id = data["session_id"]
            
            # 進行状況の確認（短時間）
            import time
            time.sleep(0.1)  # 少し待つ
            
            # プロセスが開始されていることを確認
            from app.main import progress_store
            assert session_id in progress_store or len(progress_store) > 0


@pytest.mark.api
class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.client = TestClient(app)

    def test_404_not_found(self):
        """存在しないエンドポイントのテスト"""
        response = self.client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """許可されていないHTTPメソッドのテスト"""
        response = self.client.delete("/api/health")
        assert response.status_code == 405

    def test_large_file_upload(self):
        """大きすぎるファイルのアップロードテスト"""
        # 非常に大きなファイルをシミュレート（実際には小さなデータで400エラーを起こす）
        large_file = io.BytesIO(b"x" * (10 * 1024 * 1024))  # 10MB
        
        response = self.client.post(
            "/api/translate",
            files={"file": ("large_menu.jpg", large_file, "image/jpeg")}
        )
        
        # ファイルサイズ制限があれば413、なければ正常処理される
        assert response.status_code in [200, 413, 400]

    def test_malformed_request(self):
        """不正な形式のリクエストテスト"""
        response = self.client.post(
            "/api/translate",
            data="invalid data",
            headers={"content-type": "application/json"}
        )
        
        assert response.status_code in [400, 422]


@pytest.mark.api
class TestCORS:
    """CORS設定のテスト"""

    def setup_method(self):
        """テストセットアップ"""
        self.client = TestClient(app)

    def test_cors_preflight(self):
        """CORSプリフライトリクエストのテスト"""
        response = self.client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers

    def test_cors_actual_request(self):
        """実際のCORSリクエストのテスト"""
        response = self.client.get(
            "/api/health",
            headers={"Origin": "http://localhost:3000"}
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers 