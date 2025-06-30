# Railway本番環境でのデータベース接続トラブルシューティングガイド

## よくある問題と解決策

### 1. 環境変数の問題

#### 症状
- `DATABASE_URL`が正しく設定されていない
- 本番環境でDB接続エラーが発生

#### 確認方法
```bash
# Railway CLIを使用
railway run env | grep DATABASE_URL
railway run env | grep RAILWAY_ENVIRONMENT
```

#### 解決策
- Railway ダッシュボードで環境変数を確認
- `DATABASE_URL`が自動的に設定されているか確認
- 手動で設定する場合は正しい形式を使用

### 2. SSL接続の問題

#### 症状
- `SSL connection is required`エラー
- `no pg_hba.conf entry`エラー

#### 解決策
`database.py`に以下の設定を追加（すでに実装済み）：
```python
# SSL mode for production
if "sslmode" not in db_url and os.getenv("RAILWAY_ENVIRONMENT") == "production":
    if "?" in db_url:
        db_url += "&sslmode=require"
    else:
        db_url += "?sslmode=require"
```

### 3. asyncpgドライバーの問題

#### 症状
- asyncpgでの接続が失敗
- `InvalidCatalogNameError`
- `ConnectionDoesNotExistError`

#### 解決策
psycopg2へのフォールバック実装：

```python
# app/core/database_fallback.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_sync_database_url():
    """Get sync database URL with psycopg2"""
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if db_url.startswith("postgres://"):
            return db_url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif db_url.startswith("postgresql://"):
            return db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return None

# Sync engine for fallback
sync_engine = create_engine(get_sync_database_url())
SyncSession = sessionmaker(bind=sync_engine)
```

### 4. 接続プールの枯渇

#### 症状
- `too many connections`エラー
- 断続的な接続エラー
- レスポンスの遅延

#### 解決策
環境変数で接続プールを調整：
```bash
DB_POOL_SIZE=5          # デフォルト: 5
DB_MAX_OVERFLOW=10      # デフォルト: 10
DB_POOL_TIMEOUT=30      # デフォルト: 30秒
DB_POOL_RECYCLE=1800    # デフォルト: 30分
```

### 5. ワーカープロセスの問題

#### 症状
- Celeryワーカーがクラッシュ
- DB同期ワーカーが動作しない

#### 解決策
Procfileに複数のプロセスを定義：
```procfile
web: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
worker: celery -A app.tasks.celery_app worker --loglevel=info
db_sync: python -m app.tasks.db_sync_worker
```

### 診断ツールの使用

作成した診断ツールを使用してDB接続を確認：

```bash
# ローカルでテスト
python railway_db_check.py

# Railway環境でテスト
railway run python railway_db_check.py
```

このツールは以下をチェックします：
- 環境変数の設定
- 各種ドライバーでの接続テスト（asyncpg、psycopg2、SQLAlchemy）
- テーブルの存在確認
- レコード数の確認

### 推奨事項

1. **本番環境では常にSSLを有効化**
2. **接続プールサイズを適切に設定**
3. **ヘルスチェックエンドポイントを実装**
4. **ログとモニタリングを設定**
5. **asyncpgが問題の場合はpsycopg2にフォールバック**

### ヘルスチェックエンドポイントの例

```python
# app/api/v1/endpoints/health.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db_session

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}

@router.get("/health/db")
async def db_health_check(db: AsyncSession = Depends(get_db_session)):
    """Database health check"""
    try:
        result = await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
```

### Railway特有の注意点

1. **環境変数は自動的に注入される**
   - `DATABASE_URL`は手動設定不要
   - `RAILWAY_ENVIRONMENT`で環境を判定

2. **プライベートネットワーク**
   - 内部通信は高速
   - 外部からのアクセスは制限

3. **リソース制限**
   - メモリとCPUの制限に注意
   - 接続数の上限を確認

4. **デプロイメント**
   - Blue-Greenデプロイメント中の接続管理
   - マイグレーション実行のタイミング 