# 🐳 Docker起動手順（初心者向け）

このドキュメントでは、DockerでFastAPIサーバーと3つのワーカーを起動する手順を説明します。

## 📋 前提条件

- Docker Desktop がインストールされていること
- API認証情報（OpenAI、Gemini、Google Cloud）があること

## 🚀 起動手順

### 1. 環境変数ファイルの設定

**🎉 既存の`.env`ファイルがある場合（推奨）:**
```bash
# 既存の.envをDocker用にコピー（API キーなど既設定済み）
cp .env .env.docker
# → Docker用設定が自動追加されます
```

**📝 新規で作成する場合:**
```bash
# サンプルファイルからコピー
cp env.docker.example .env.docker
```

### 2. 環境変数の確認

既存の`.env`を使った場合、API キーは既に設定済みです！以下を確認：

```bash
# 設定内容を確認
head -20 .env.docker
```

新規作成の場合は、以下の必須項目を設定してください：

```env
# 必須：OpenAI API キー
OPENAI_API_KEY=sk-your-actual-key-here

# 必須：Gemini API キー  
GEMINI_API_KEY=your-actual-gemini-key-here

# 必須：Google Cloud プロジェクトID
GOOGLE_CLOUD_PROJECT_ID=your-project-id

# 必須：Google Cloud認証JSON（1行で設定）
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"..."}
```

### 3. Dockerコンテナの起動

```bash
# 全サービスを起動（初回はイメージのビルドも行われます）
docker-compose up -d
```

### 4. 起動確認

```bash
# サービスの状態確認
docker-compose ps

# ログ確認
docker-compose logs -f
```

## 📊 サービス構成

起動されるサービス：

- **api**: FastAPIサーバー (ポート8000)
- **redis**: メッセージブローカー (ポート6379) + ヘルスチェック付き
- **worker-translation**: 翻訳専用ワーカー (8並行) - `real_translate_queue`
- **worker-description**: 詳細説明専用ワーカー (6並行) - `real_description_queue`  
- **worker-image**: 画像生成専用ワーカー (3並行) - `real_image_queue`

### 🔧 最新の修正点（ワーカー問題解決済み）

- ✅ **キュー名修正**: 正しいキュー名（`real_*_queue`）に変更済み
- ✅ **詳細ログ**: デバッグレベルのログで問題特定しやすく
- ✅ **ヘルスチェック**: Redisの健全性確認付き
- ✅ **依存関係**: ワーカーはRedis準備完了後に起動

## 🌐 アクセス方法

起動後、以下のURLでアクセスできます：

- API: http://localhost:8000
- API文書: http://localhost:8000/docs

## 🛠️ 便利なコマンド

### サービスの停止
```bash
docker-compose down
```

### サービスの再起動
```bash
docker-compose restart
```

### 特定のサービスのログ確認
```bash
# FastAPIサーバーのログ
docker-compose logs -f api

# 翻訳ワーカーのログ
docker-compose logs -f worker-translation

# 詳細説明ワーカーのログ
docker-compose logs -f worker-description

# 画像生成ワーカーのログ
docker-compose logs -f worker-image
```

### ワーカーの状態確認
```bash
# コンテナ内でCeleryステータス確認
docker-compose exec worker-translation celery -A app.tasks.celery_app inspect stats
```

### 完全な再構築
```bash
# イメージを再ビルドして起動
docker-compose up -d --build
```

### データのクリーンアップ
```bash
# 停止して全データを削除
docker-compose down -v

# 未使用のDockerリソースをクリーンアップ
docker system prune
```

## 🐛 トラブルシューティング

### Q: サービスが起動しない
```bash
# エラーログを確認
docker-compose logs

# 環境変数ファイルが正しく設定されているか確認
cat .env.docker
```

### Q: API認証エラーが発生する
- `.env.docker` ファイルのAPI キーが正しく設定されているか確認
- Google Credentials JSON が正しい形式で1行に設定されているか確認

### Q: ワーカーがタスクを処理しない
```bash
# Redisの接続確認
docker-compose exec redis redis-cli ping

# ワーカーの詳細ログ確認（デバッグレベル）
docker-compose logs -f worker-translation
docker-compose logs -f worker-description  
docker-compose logs -f worker-image

# Celeryワーカーの状態確認
docker-compose exec worker-translation celery -A app.tasks.celery_app inspect stats
docker-compose exec worker-translation celery -A app.tasks.celery_app inspect active

# キュー内のタスク確認
docker-compose exec worker-translation celery -A app.tasks.celery_app inspect reserved

# 正しいキューが使われているか確認
docker-compose exec worker-translation celery -A app.tasks.celery_app inspect registered
```

### Q: ポートが使用中エラー
```bash
# 使用中のポートを確認
lsof -i :8000
lsof -i :6379

# 必要に応じて他のプロセスを停止するか、docker-compose.ymlのポート番号を変更
```

## 📁 ファイル構成

```
├── Dockerfile              # アプリケーション用コンテナ設定
├── docker-compose.yml      # 全サービスの設定
├── .dockerignore           # Dockerイメージから除外するファイル
├── env.docker.example      # 環境変数サンプル
└── .env.docker            # 実際の環境変数（要作成）
```

## 🎉 成功例

正常に起動すると、以下のような出力が表示されます：

```
$ docker-compose ps
NAME                    COMMAND                  SERVICE             STATUS
menu-sensor-api-1       "python -m uvicorn a…"   api                 running
menu-sensor-redis-1     "docker-entrypoint.s…"   redis               running
menu-sensor-worker-description-1   "celery -A app.tasks.c…"   worker-description   running
menu-sensor-worker-image-1         "celery -A app.tasks.c…"   worker-image         running
menu-sensor-worker-translation-1   "celery -A app.tasks.c…"   worker-translation   running
```

これで Docker での起動は完了です！🎉 