# app_2 テストスイート

app_2の基盤コンポーネントに対する包括的なテストスイートです。

## 📋 テスト構成

| テストファイル | 対象コンポーネント | テスト内容 |
|---------------|-------------------|------------|
| `test_prompt_loader.py` | PromptLoader | YAML読み込み・変数置換・エラーハンドリング |
| `test_menu_entity.py` | MenuEntity | ビジネスロジック・データ検証 |
| `test_config.py` | 設定システム | 環境変数読み込み・バリデーション |
| `test_database.py` | データベース | 接続・セッション管理・設定 |
| `integrations/test_google_integrations.py` | Google API統合 | Vision/Translate/Search（モック使用） |
| `integrations/test_openai_integration.py` | OpenAI統合 | プロンプト連携・AI生成（モック使用） |

## 🚀 テスト実行方法

### 前提条件

```bash
# 依存関係インストール
pip install pytest pytest-asyncio

# app_2ディレクトリに移動
cd menu_sensor_backend/app_2
```

### 基本実行

```bash
# 全テスト実行
pytest tests/

# 詳細出力
pytest tests/ -v

# 特定のテストファイル実行
pytest tests/test_prompt_loader.py -v

# 特定のテストクラス実行
pytest tests/test_menu_entity.py::TestMenuEntity -v

# 特定のテストメソッド実行
pytest tests/test_prompt_loader.py::TestPromptLoader::test_load_prompt_success -v
```

### マーカー別実行

```bash
# 単体テストのみ（外部依存なし）
pytest -m unit

# 統合テストのみ（外部API使用、モック推奨）
pytest -m integration

# 実行時間の長いテストを除外
pytest -m "not slow"

# データベーステストのみ
pytest -m database

# データベーステストを除外
pytest -m "not database"
```

### カバレッジ測定

```bash
# カバレッジ付きテスト実行
pip install pytest-cov
pytest tests/ --cov=app_2 --cov-report=html

# カバレッジレポート確認
open htmlcov/index.html
```

## 📊 テスト詳細

### 1. PromptLoader テスト (`test_prompt_loader.py`)

**目的**: YAML基盤プロンプト管理システムの検証

**テスト内容**:
- ✅ YAML ファイル読み込み（正常/異常）
- ✅ テンプレート変数置換
- ✅ エラーハンドリング（ファイル不存在、無効YAML）
- ✅ 実際のプロンプトファイル存在確認

**実行例**:
```bash
pytest tests/test_prompt_loader.py::TestPromptLoader::test_load_prompt_success -v
```

### 2. MenuEntity テスト (`test_menu_entity.py`)

**目的**: ドメインエンティティのビジネスロジック検証

**テスト内容**:
- ✅ エンティティ作成・属性アクセス
- ✅ `is_complete()` ビジネスロジック
- ✅ `has_generated_content()` ビジネスロジック
- ✅ エッジケース（空文字列、None値）

**実行例**:
```bash
pytest tests/test_menu_entity.py::TestMenuEntity::test_is_complete_with_complete_entity -v
```

### 3. 設定システムテスト (`test_config.py`)

**目的**: アプリケーション設定の読み込み・バリデーション検証

**テスト内容**:
- ✅ 環境変数からの設定読み込み
- ✅ デフォルト値設定
- ✅ 設定バリデーション
- ✅ 設定サマリー取得

**実行例**:
```bash
pytest tests/test_config.py::TestBaseSettings::test_environment_variable_loading -v
```

### 4. データベーステスト (`test_database.py`)

**目的**: データベース設定・接続・基本操作の確認

**テスト内容**:
- ✅ データベースURL構築
- ✅ 非同期エンジン・セッション作成
- ✅ エラーハンドリング
- ✅ モデル構造確認

**実行例**:
```bash
pytest tests/test_database.py::TestDatabaseConfiguration -v
```

### 5. Google API統合テスト (`integrations/test_google_integrations.py`)

**目的**: Google API統合の確認（モック使用）

**テスト内容**:
- ✅ GoogleCredentialManager（シングルトン、認証管理）
- ✅ GoogleVisionClient（OCR処理）
- ✅ GoogleTranslateClient（翻訳処理）
- ✅ GoogleSearchClient（画像検索）

**実行例**:
```bash
pytest tests/integrations/test_google_integrations.py::TestGoogleVisionClient -v
```

### 6. OpenAI統合テスト (`integrations/test_openai_integration.py`)

**目的**: OpenAI統合・プロンプト連携の確認（モック使用）

**テスト内容**:
- ✅ **OpenAIClient（統合クライアント）**: 専用クライアントへの委譲テスト
- ✅ **OpenAIBaseClient（ベースクライアント）**: プロンプトローダー統合・API呼び出し
- ✅ 詳細説明生成（`generate_description`）
- ✅ アレルゲン抽出（`extract_allergens`）
- ✅ 含有物抽出（`extract_ingredients`）
- ✅ カテゴライズ（`categorize_menu_item`）

**実行例**:
```bash
pytest tests/integrations/test_openai_integration.py::TestOpenAIClient::test_generate_description_delegation -v
pytest tests/integrations/test_openai_integration.py::TestOpenAIBaseClient::test_make_completion_request_success -v
```

## 🔧 テスト設定

### pytest.ini 設定

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --color=yes
    --durations=10

markers =
    unit: 単体テスト（外部依存なし）
    integration: 統合テスト（外部API使用、モック推奨）
    slow: 実行時間の長いテスト
    database: データベースを使用するテスト
```

### 共通フィクスチャ (`conftest.py`)

- **`temp_prompts_dir`**: テスト用プロンプトディレクトリ
- **`mock_settings`**: テスト用設定モック
- **`mock_openai_response`**: OpenAI APIレスポンスモック
- **`mock_google_*_response`**: Google APIレスポンスモック
- **`sample_menu_entity`**: テスト用MenuEntityサンプル

## ⚠️ 注意事項

### 外部依存について

- **API呼び出し**: 全てモックを使用（実際のAPI呼び出しなし）
- **データベース**: 接続テストは実際の設定に依存（スキップされる場合あり）
- **ファイルシステム**: 一時ディレクトリ使用

### 環境変数

テスト実行時は以下の環境変数が自動設定されます：
```bash
TESTING=true
LOG_LEVEL=ERROR
```

### スキップされるテスト

以下の条件でテストがスキップされる場合があります：
- 実際のプロンプトファイルが存在しない
- データベース接続設定が不完全
- 必要な依存関係が不足

## 📈 テスト結果の読み方

### 正常実行例

```bash
$ pytest tests/ -v

tests/test_prompt_loader.py::TestPromptLoader::test_init_with_default_path PASSED
tests/test_prompt_loader.py::TestPromptLoader::test_load_prompt_success PASSED
tests/test_menu_entity.py::TestMenuEntity::test_creation_with_required_fields PASSED
...

====== 45 passed, 3 skipped in 2.34s ======
```

### エラー例

```bash
$ pytest tests/test_config.py -v

tests/test_config.py::TestBaseSettings::test_environment_variable_loading FAILED
...
FAILED tests/test_config.py::TestBaseSettings::test_environment_variable_loading
```

## 🎯 次のステップ

基盤テストが完了したら、次の実装フェーズに進めます：

1. **Service層実装** → 各サービスの単体テスト追加
2. **Task層実装** → Celeryタスクのテスト追加
3. **API層実装** → エンドポイントのテスト追加
4. **統合テスト** → E2Eテストの追加

現在のテストスイートは、安全な実装進行のための基盤として機能します。 