# メニュー翻訳システム - データベース実装とRailway接続まとめ

## 📋 概要

このドキュメントは、メニュー翻訳バックエンドシステムのデータベース実装からRailway PostgreSQL接続までのプロセスをまとめたものです。

## 🏗️ プロジェクト構成

### システムアーキテクチャ
- **フレームワーク**: FastAPI
- **データベース**: PostgreSQL + SQLAlchemy (非同期)
- **キャッシュ/キュー**: Redis + Celery
- **OCR**: Google Vision API / Gemini OCR
- **翻訳**: OpenAI GPT-4 / Google Translate
- **画像生成**: Google Imagen 3
- **ストレージ**: AWS S3

### 処理フロー
1. **Stage 1**: OCR処理（画像→テキスト）
2. **Stage 2**: 翻訳処理（日本語→英語）
3. **Stage 3**: 詳細説明生成
4. **Stage 4**: 画像生成

## 📊 実装完了内容

### 1. TDDによるデータベース実装
- ✅ 7つのフェーズすべて完了
- ✅ SQLAlchemyモデル作成
- ✅ 非同期リポジトリパターン実装
- ✅ サービスレイヤー統合
- ✅ FastAPI エンドポイント追加
- ✅ JSONからDBへの移行ツール作成

### 2. データベーススキーマ
```sql
-- 主要テーブル
- sessions: セッション管理
- menu_items: メニューアイテム
- processing_providers: AI処理プロバイダー追跡
- menu_item_images: 生成画像管理
- categories: カテゴリ管理
```

### 3. デュアルストレージ戦略
- **Primary**: PostgreSQL（永続化、検索、分析）
- **Secondary**: Redis（後方互換性、一時データ）

## 🔧 セットアップ手順

### 1. ローカルデータベース設定

#### PostgreSQLユーザーとデータベース作成
```bash
# PostgreSQLでユーザー作成
CREATE USER menu_user WITH PASSWORD 'menu_password';
CREATE DATABASE menu_translation_db OWNER menu_user;
GRANT ALL PRIVILEGES ON DATABASE menu_translation_db TO menu_user;
```

#### 必要パッケージのインストール
```bash
pip install asyncpg
```

#### データベース初期化
```python
from app.core.database import init_database
import asyncio
asyncio.run(init_database())
```

### 2. 環境変数設定

#### AWS Secrets Manager無効化（ローカル開発）
```bash
export USE_AWS_SECRETS_MANAGER=false
```

#### データベース接続設定（.env）
```
DB_HOST=localhost
DB_PORT=5432
DB_USER=menu_user
DB_PASSWORD=menu_password
DB_NAME=menu_translation_db
```

## 🚂 Railway接続設定

### 1. Railway CLIリンク
```bash
railway link -p bb6fd571-f183-494d-ad40-0cf4c0e32536
# Project: keen-beauty
# Environment: production
# Service: Postgres
```

### 2. database.py更新
DATABASE_URLを優先的に使用するように更新：
```python
def get_database_url() -> str:
    # Priority 1: DATABASE_URL (for Railway)
    if os.getenv("DATABASE_URL"):
        db_url = os.getenv("DATABASE_URL")
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
        return db_url
    # ... 既存のコード
```

### 3. Railway DB情報
- **ホスト**: maglev.proxy.rlwy.net
- **ポート**: 25873
- **ユーザー**: postgres
- **データベース**: railway
- **PostgreSQL**: バージョン 16.8

### 4. Railway DBテーブル作成
```bash
DATABASE_URL="postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:25873/railway" \
python -c "from app.core.database import init_database; import asyncio; asyncio.run(init_database())"
```

## 📈 移行結果

### JSONからデータベースへの移行
- **移行ファイル数**: 5個（4個成功、1個失敗）
- **セッション数**: 4個
- **メニューアイテム数**: 18個
- **生成画像数**: 18個
- **処理記録数**: 54個

## 🐳 Docker環境

### docker-compose構成
- Redis（Celeryブローカー）
- FastAPI（APIサーバー）
- Celeryワーカー×3（翻訳、説明、画像）
- ※PostgreSQLコンテナは含まれない（外部DB使用）

### Docker起動（Railway DB使用）
```bash
DATABASE_URL="postgresql://postgres:PASSWORD@maglev.proxy.rlwy.net:25873/railway" \
docker-compose up
```

## 🚀 Railwayデプロイ準備

### 確認済み事項
- ✅ Procfile設定
- ✅ requirements.txt（asyncpg含む）
- ✅ DATABASE_URL自動設定
- ✅ database.pyのDATABASE_URL対応

### 必要な追加設定
- ⚠️ Redisサービスの追加（Celery用）
- ⚠️ 環境変数の設定（API Keys等）
- ⚠️ Celeryワーカーの設定

## 📝 トラブルシューティング

### AWSエラーについて
- 原因：無効なセッショントークン
- 解決：`USE_AWS_SECRETS_MANAGER=false`で無効化
- Google系サービスはデフォルト認証で動作継続

### データベース接続確認方法
```bash
# 直接確認
PGPASSWORD=password psql -h host -p port -U user -d database -c "\dt"

# Pythonスクリプトで確認
python check_database_connection.py
```

## 🎯 現在の状態

- **ローカルDB**: 4セッション、18アイテム保存済み
- **Railway DB**: テーブル作成完了、データ移行準備完了
- **システム**: 本番デプロイ可能な状態

## 📚 関連ファイル

- `DATABASE_IMPLEMENTATION_SUMMARY.md`: 実装詳細
- `app/core/database.py`: DB接続設定
- `app/models/menu_translation.py`: データモデル
- `app/repositories/menu_translation_repository.py`: リポジトリ層
- `app/services/menu_translation_service.py`: サービス層
- `migrate_json_to_database.py`: 移行スクリプト 