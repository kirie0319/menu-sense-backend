# Menu Processor v2

Clean Architecture-based menu processing system with pipeline architecture

## 🚀 概要

Menu Processor v2は、Clean Architectureパターンに基づいて設計されたメニュー処理システムです。非同期処理、パイプライン アーキテクチャ、自動化されたデータベース管理機能を提供します。

## 🏗️ アーキテクチャ

```
app_2/
├── api/           # API層（エンドポイント）
├── core/          # コア設定・DB管理
├── domain/        # ドメイン層（ビジネスロジック）
├── infrastructure/ # インフラ層（DB、外部API）
├── services/      # サービス層（アプリケーションロジック）
├── tasks/         # 非同期タスク（Celery）
├── pipelines/     # パイプライン処理
├── sse/           # Server-Sent Events
└── docs/          # ドキュメント
```

## ⚡ 主要機能

### 🔄 自動DB初期化機能

開発効率向上のため、アプリケーション起動時に自動でデータベースを初期化する機能を提供。

```bash
# 開発時（毎回DB初期化）
AUTO_RESET_DATABASE=true python -m app_2.main

# 本番時（データ保持）
AUTO_RESET_DATABASE=false python -m app_2.main
```

**詳細**: [自動DB初期化機能仕様書](docs/auto_reset_database.md)

### 🏛️ Clean Architecture

- **ドメイン層**: 純粋なビジネスロジック
- **インフラ層**: データベース、外部API統合
- **サービス層**: アプリケーション固有ロジック
- **API層**: RESTful エンドポイント

### 🔄 非同期処理

- **Celery**: バックグラウンドタスク処理
- **Redis**: タスクキュー・結果ストレージ
- **AsyncIO**: 非同期I/O処理

## 🛠️ セットアップ

### 1. 環境設定

```bash
# プロジェクトルートに移動
cd menu_sensor_backend

# 環境変数設定
cp .env.example .env
# .envファイルを編集
```

### 2. 必要な環境変数

```bash
# データベース
DATABASE_URL=postgresql://user:pass@host:port/dbname

# 自動DB初期化（開発時）
AUTO_RESET_DATABASE=true

# AI API
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# AWS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Redis
REDIS_URL=redis://localhost:6379/0
```

### 3. アプリケーション起動

```bash
# 開発モード
python -m app_2.main

# 本番モード
AUTO_RESET_DATABASE=false python -m app_2.main
```

## 📊 データベース

### スキーマ

```sql
CREATE TABLE menus (
    id VARCHAR PRIMARY KEY,        -- メニューID (UUID)
    name VARCHAR NOT NULL,         -- 元言語の料理名
    translation VARCHAR NOT NULL,  -- 翻訳済み料理名
    description TEXT,              -- GPT生成の詳細説明
    allergy TEXT,                  -- アレルゲン情報
    ingredient TEXT,               -- 主な含有成分
    search_engine TEXT,            -- Google画像検索結果
    gen_image VARCHAR              -- 生成画像URL
);
```

### 管理コマンド

```bash
# データベースクリア
python app_2/scripts/clear_database.py

# 強制クリア（確認なし）
python app_2/scripts/clear_database.py --force
```

## 🧪 テスト

```bash
# テストスイート実行
cd app_2
pytest tests/ -v

# カバレッジ付きテスト
pytest tests/ --cov=app_2 --cov-report=html
```

## 📚 ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [自動DB初期化機能](docs/auto_reset_database.md) | 自動リセット機能の詳細仕様 |
| [テストガイド](tests/README.md) | テスト実行方法・構成 |

## ⚙️ 設定

### 主要設定項目

| 設定項目 | デフォルト | 説明 |
|----------|------------|------|
| `AUTO_RESET_DATABASE` | `false` | 起動時DB自動初期化 |
| `DEBUG_MODE` | `false` | デバッグモード |
| `HOST` | `0.0.0.0` | サーバーホスト |
| `PORT` | `8000` | サーバーポート |

### AI設定

| 設定項目 | 説明 |
|----------|------|
| `OPENAI_API_KEY` | OpenAI API認証キー |
| `GEMINI_API_KEY` | Google Gemini API認証キー |
| `OPENAI_MODEL_NAME` | 使用するOpenAIモデル |

## 🔧 開発

### コード品質

- **Clean Architecture**: レイヤー分離
- **Type Hints**: 型安全性
- **Async/Await**: 非同期処理
- **Pydantic**: データ検証

### 開発フロー

1. 機能実装（domain → infrastructure → services → api）
2. テスト作成・実行
3. 自動DB初期化で動作確認
4. ドキュメント更新

## 🚨 注意事項

### ⚠️ 本番環境

- **必須**: `AUTO_RESET_DATABASE=false`
- **推奨**: `DEBUG_MODE=false`
- **セキュリティ**: API キーの適切な管理

### 🔒 データ安全性

- 自動リセット機能は開発時のみ使用
- 本番データのバックアップを定期的に実施
- 環境変数の設定を慎重に確認

## 📞 サポート

問題や質問がある場合：

1. [ドキュメント](docs/)を確認
2. [テストスイート](tests/)で動作検証
3. ログ出力を確認（`DEBUG_MODE=true`）

---

**Menu Processor v2** - Clean, Efficient, Scalable 