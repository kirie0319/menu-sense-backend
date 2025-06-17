# Menu Sensor Backend - テストフレームワーク

リファクタリングに備えた包括的なテストスイートが整備されました。

## 📁 テスト構造

```
tests/
├── conftest.py                 # pytest共通設定とフィクスチャ
├── unit/                      # ユニットテスト
│   ├── test_ocr_service.py    # OCRサービスのテスト
│   └── test_category_service.py # カテゴリサービスのテスト
├── integration/               # 統合テスト
│   └── test_workflow_integration.py # ワークフロー統合テスト
├── api/                       # APIエンドポイントテスト
│   └── test_main_endpoints.py # メインAPIのテスト
└── fixtures/                  # テストデータとヘルパー
    ├── sample_data.py         # サンプルデータ
    └── ...
```

## 🏷️ テストマーカー

テストは以下のマーカーで分類されています：

- `@pytest.mark.unit` - ユニットテスト
- `@pytest.mark.integration` - 統合テスト
- `@pytest.mark.api` - APIエンドポイントテスト
- `@pytest.mark.slow` - 実行時間が長いテスト
- `@pytest.mark.external` - 外部API依存のテスト
- `@pytest.mark.mock` - モックを使用するテスト
- `@pytest.mark.ocr` - OCR関連テスト
- `@pytest.mark.translation` - 翻訳関連テスト
- `@pytest.mark.category` - カテゴリ分類関連テスト

## 🚀 テスト実行方法

### 1. 依存関係のインストール

```bash
# テスト用依存関係をインストール
pip install -r requirements-test.txt

# または自動インストール
python run_tests.py --install-deps
```

### 2. 基本的なテスト実行

```bash
# 全テストを実行
python run_tests.py

# または直接pytest
pytest tests/
```

### 3. 特定のテストタイプを実行

```bash
# ユニットテストのみ
python run_tests.py --unit

# 統合テストのみ
python run_tests.py --integration

# APIテストのみ
python run_tests.py --api

# 外部API依存テストを除外（推奨）
python run_tests.py --fast
```

### 4. カバレッジ測定

```bash
# カバレッジ付きでテスト実行
python run_tests.py --coverage

# カバレッジレポートはhtmlcov/に生成されます
open htmlcov/index.html
```

### 5. 並列実行

```bash
# 4つのプロセスで並列実行
python run_tests.py --parallel 4
```

### 6. 特定のテストを実行

```bash
# 特定のファイル
python run_tests.py --file tests/unit/test_ocr_service.py

# 特定のテスト関数
python run_tests.py --test test_extract_text_success

# 特定のクラス
pytest tests/unit/test_ocr_service.py::TestOCRService
```

## 🛠️ テスト開発ガイド

### ユニットテストの作成

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.unit
@pytest.mark.ocr
class TestOCRService:
    """OCRサービスのテスト"""
    
    @pytest.mark.asyncio
    async def test_extract_text_success(self, test_image_path, test_session_id):
        """テキスト抽出の成功ケース"""
        with patch('app.services.ocr.extract_text') as mock_extract:
            mock_extract.return_value = OCRResult(
                success=True,
                extracted_text="サンプルテキスト",
                provider=OCRProvider.GEMINI
            )
            
            result = await extract_text(test_image_path, test_session_id)
            
            assert result.success is True
            assert "サンプルテキスト" in result.extracted_text
```

### 統合テストの作成

```python
@pytest.mark.integration
class TestWorkflowIntegration:
    """ワークフロー統合テスト"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, test_session_id):
        """完全ワークフローのテスト"""
        # 複数のサービスが連携して動作することを確認
        pass
```

### APIテストの作成

```python
from fastapi.testclient import TestClient
from app.main import app

@pytest.mark.api
class TestHealthEndpoints:
    """ヘルスチェックエンドポイントのテスト"""
    
    def setup_method(self):
        self.client = TestClient(app)
    
    def test_health_check(self):
        response = self.client.get("/api/health")
        assert response.status_code == 200
```

## 📊 テストカバレッジの目標

- **全体**: 80%以上
- **ユニットテスト**: 90%以上
- **統合テスト**: 70%以上
- **APIテスト**: 85%以上

## 🔧 継続的インテグレーション

### GitHub Actions設定例

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt
      
      - name: Run tests
        run: python run_tests.py --coverage --fast
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 🧪 テストデータ

### サンプルデータの使用

```python
from tests.fixtures.sample_data import SampleMenuData, get_sample_menu_by_complexity

# 基本的なメニューデータ
simple_menu = get_sample_menu_by_complexity("simple")

# 複雑なメニューデータ  
complex_menu = get_sample_menu_by_complexity("complex")
```

### フィクスチャの使用

```python
def test_with_sample_data(sample_menu_text, sample_categorized_menu):
    """サンプルデータを使用したテスト"""
    # sample_menu_text と sample_categorized_menu は自動的に注入される
    pass
```

## 🚫 モックとテスト隔離

外部APIへの依存を避けるため、以下をモック化しています：

- **Gemini API** (`google.generativeai`)
- **OpenAI API** (`openai.AsyncOpenAI`)
- **Google Cloud APIs** (`google.cloud.*`)
- **ファイルシステム操作**
- **ネットワーク通信**

## 📝 テストベストプラクティス

### 1. テスト命名規則

```python
def test_[機能]_[条件]_[期待結果](self):
    """例: test_extract_text_with_valid_image_returns_success"""
    pass
```

### 2. AAA パターン

```python
def test_example(self):
    # Arrange (準備)
    input_data = "test input"
    
    # Act (実行)
    result = function_to_test(input_data)
    
    # Assert (検証)
    assert result == expected_output
```

### 3. テストの独立性

```python
def setup_method(self):
    """各テストメソッド実行前の初期化"""
    self.service = ServiceClass()

def teardown_method(self):
    """各テストメソッド実行後のクリーンアップ"""
    # 必要に応じてクリーンアップ
    pass
```

## 🔍 デバッグ

### テスト失敗時のデバッグ

```bash
# 詳細出力でテスト実行
python run_tests.py --verbose

# 特定のテストのみを詳細実行
pytest tests/unit/test_ocr_service.py::TestOCRService::test_extract_text_success -v -s

# pdb デバッガーを使用
pytest --pdb tests/unit/test_ocr_service.py
```

### ログ出力の確認

```python
import logging

def test_with_logging(caplog):
    """ログ出力をテストする"""
    with caplog.at_level(logging.INFO):
        function_that_logs()
        
    assert "Expected log message" in caplog.text
```

## 💡 テスト追加のガイドライン

新しい機能を追加する際は、以下の順序でテストを作成してください：

1. **ユニットテスト**: 新機能の個別テスト
2. **統合テスト**: 既存機能との統合テスト
3. **APIテスト**: エンドポイントのテスト（該当する場合）
4. **エラーハンドリングテスト**: 異常系のテスト

## 📚 参考資料

- [pytest公式ドキュメント](https://docs.pytest.org/)
- [FastAPI テストガイド](https://fastapi.tiangolo.com/tutorial/testing/)
- [unittest.mock ドキュメント](https://docs.python.org/3/library/unittest.mock.html)

---

このテストフレームワークにより、安全で確実なリファクタリングが可能になります。テストを継続的に実行し、コードの品質を維持してください。 