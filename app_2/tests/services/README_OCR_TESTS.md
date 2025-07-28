# OCR Tests Documentation

## 概要

このディレクトリには、Google Vision APIを使用したOCR（Optical Character Recognition）機能の包括的なテストが含まれています。

## テスト構成

### 1. テストファイル

```
tests/services/
├── test_ocr_service.py           # OCRService 単体・統合テスト
├── test_google_vision_client.py  # GoogleVisionClient 単体・統合テスト
├── test_ocr_suite.py            # テスト実行管理スイート
└── README_OCR_TESTS.md          # このファイル
```

### 2. テストカテゴリ

#### A. 単体テスト (Unit Tests)
- **OCRService 単体テスト**: モック使用、API非依存
- **GoogleVisionClient 単体テスト**: モック使用、API非依存
- **ファクトリー関数テスト**: シングルトンパターンの検証
- **エラーハンドリングテスト**: 例外処理の検証

#### B. 統合テスト (Integration Tests)
- **実API使用テスト**: Google Vision API実行（認証情報必要）
- **ファイル読み込みテスト**: 実際の画像ファイル使用
- **エンドツーエンドテスト**: OCR → 位置情報抽出フロー

## 実行方法

### 1. 全テスト実行

```bash
# 方法1: テストスイート使用（推奨）
cd menu_sensor_backend/app_2
python tests/services/test_ocr_suite.py

# 方法2: pytest直接実行
pytest tests/services/test_ocr_service.py tests/services/test_google_vision_client.py -v
```

### 2. カテゴリ別実行

```bash
# 単体テストのみ
python tests/services/test_ocr_suite.py unit

# 統合テストのみ
python tests/services/test_ocr_suite.py integration

# OCRServiceのみ
python tests/services/test_ocr_suite.py ocr_service

# GoogleVisionClientのみ
python tests/services/test_ocr_suite.py google_vision
```

### 3. 個別テストクラス実行

```bash
# OCRService 単体テスト
pytest tests/services/test_ocr_service.py::TestOCRService -v

# GoogleVisionClient エラーハンドリングテスト
pytest tests/services/test_google_vision_client.py::TestGoogleVisionClient::test_extract_text_vision_api_error -v

# 統合テスト（API認証情報必要）
pytest tests/services/test_ocr_service.py::TestOCRServiceIntegration -v -m integration
```

### 4. pytest マーク使用

```bash
# OCR関連テストのみ
pytest -m ocr

# 単体テストのみ
pytest -m unit

# 統合テストのみ
pytest -m integration
```

## 環境設定

### 1. 必須パッケージ

```bash
pip install pytest pytest-asyncio google-cloud-vision
```

### 2. Google Vision API認証設定

#### 方法A: サービスアカウントキー使用
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
```

#### 方法B: gcloud CLI認証
```bash
gcloud auth application-default login
```

#### 方法C: 環境変数設定
```bash
export GOOGLE_CLOUD_PROJECT_ID="your-project-id"
export GEMINI_API_KEY="your-api-key"  # Vision APIキー
```

### 3. テストデータ準備

```bash
# テスト画像配置
mkdir -p tests/data
# menu_test.webp などの画像ファイルを配置
```

## テストクラス詳細

### TestOCRService

OCRServiceの基本機能テスト

- `test_init_*`: 初期化テスト
- `test_extract_text_with_positions_*`: 位置情報付きテキスト抽出テスト
- `test_*_level`: wordレベル/paragraphレベル抽出テスト
- `test_*_japanese_text`: 日本語テキスト処理テスト
- `test_*_empty_*`: 空データ処理テスト
- `test_*_exception`: 例外処理テスト

### TestGoogleVisionClient

GoogleVisionClientの基本機能テスト

- `test_extract_text_*`: 基本テキスト抽出テスト
- `test_extract_text_with_positions_*`: 位置情報付き抽出テスト
- `test_calculate_bounding_box_center_*`: 座標計算テスト
- `test_*_vision_api_error`: VisionAPIエラー処理テスト

### TestOCRServiceIntegration / TestGoogleVisionClientIntegration

実環境での統合テスト

- 実際のGoogle Vision API呼び出し
- 実際の画像ファイル処理
- API認証情報が必要

### TestOCRServiceFactory / TestGoogleVisionClientFactory

ファクトリー関数テスト

- シングルトンパターン検証
- `@lru_cache`デコレータ動作確認

### TestOCRServiceErrorHandling

エラーハンドリング特化テスト

- 各種例外シナリオ
- ネットワークエラー処理
- APIクォータ超過処理

## テスト実行結果の読み方

### 成功例
```
🔬 OCR Unit Tests - 単体テスト実行中...
============================================================

📋 実行中: OCRService Unit Tests
----------------------------------------
✅ OCRService Unit Tests: PASSED

📋 実行中: GoogleVisionClient Unit Tests
----------------------------------------
✅ GoogleVisionClient Unit Tests: PASSED

📊 OCR Test Suite - 実行結果サマリー
============================================================
✅ 成功したテスト (2):
   - OCRService Unit Tests
   - GoogleVisionClient Unit Tests

📈 成功率: 100.0% (2/2)
🎉 全てのテストが成功しました！
```

### 失敗例
```
❌ GoogleVisionClient Integration Tests: FAILED
STDOUT: E   google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

## トラブルシューティング

### 1. 認証エラー
```
google.auth.exceptions.DefaultCredentialsError
```
**解決方法**: Google Cloud認証情報を設定
```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
# または
gcloud auth application-default login
```

### 2. テストファイル不足
```
❌ 必要なテストファイルが見つかりません
```
**解決方法**: 正しいディレクトリで実行していることを確認
```bash
cd menu_sensor_backend/app_2
python tests/services/test_ocr_suite.py
```

### 3. 画像ファイル不足
```
⚠️ テスト画像ファイルが見つかりません
```
**解決方法**: テスト画像を配置
```bash
mkdir -p tests/data
# テスト用の画像ファイル（.webp, .jpg, .png）を配置
```

### 4. パッケージ不足
```
ModuleNotFoundError: No module named 'google.cloud'
```
**解決方法**: 必要なパッケージをインストール
```bash
pip install google-cloud-vision pytest pytest-asyncio
```

### 5. Vision API クォータ超過
```
google.api_core.exceptions.ResourceExhausted: 429 Quota exceeded
```
**解決方法**: 
- 単体テストのみ実行（APIを使わない）
- 時間をおいて再実行
- Google Cloud Console でクォータ確認

## ベストプラクティス

### 1. テスト実行順序
1. 環境検証: `python tests/services/test_ocr_suite.py unit`
2. 単体テスト: `python tests/services/test_ocr_suite.py unit`
3. 統合テスト: `python tests/services/test_ocr_suite.py integration`

### 2. 継続的インテグレーション
```yaml
# .github/workflows/test.yml 例
- name: Run OCR Unit Tests
  run: python tests/services/test_ocr_suite.py unit
  
- name: Run OCR Integration Tests
  run: python tests/services/test_ocr_suite.py integration
  env:
    GOOGLE_APPLICATION_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
```

### 3. ローカル開発
```bash
# 開発中は単体テストを頻繁に実行
python tests/services/test_ocr_suite.py unit

# 機能完成時に統合テスト実行
python tests/services/test_ocr_suite.py integration
```

## テストデータ

### 推奨画像形式
- **フォーマット**: WEBP, JPEG, PNG
- **サイズ**: 1MB以下
- **内容**: 日本語・英語混在のメニュー画像
- **解像度**: 300x300px以上

### サンプル画像例
```
tests/data/
├── menu_test.webp         # カフェメニュー（日英混在）
├── restaurant_menu.jpg    # レストランメニュー
└── price_list.png         # 価格表
```

## 拡張・カスタマイズ

### 新しいテストケース追加

1. **単体テスト追加**:
   ```python
   # test_ocr_service.py に追加
   @pytest.mark.asyncio
   async def test_extract_text_with_positions_custom_scenario(self):
       # カスタムテストロジック
   ```

2. **統合テスト追加**:
   ```python
   # TestOCRServiceIntegration に追加
   @pytest.mark.integration
   @pytest.mark.asyncio
   async def test_custom_integration_scenario(self):
       # 実API使用テスト
   ```

3. **テストスイート更新**:
   ```python
   # test_ocr_suite.py のtest_commands に追加
   ```

## 参考リンク

- [Google Cloud Vision API Documentation](https://cloud.google.com/vision/docs)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock Documentation](https://docs.python.org/3/library/unittest.mock.html) 