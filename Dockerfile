# Python 3.13をベースイメージとして使用
FROM python:3.13

# 作業ディレクトリを設定
WORKDIR /app

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    redis-tools \
    curl \
    && rm -rf /var/lib/apt/lists/*

# requirements.txtをコピーして依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ログディレクトリを作成
RUN mkdir -p logs

# アップロードディレクトリを作成
RUN mkdir -p uploads

# Celeryヘルスチェックスクリプトを追加
RUN echo '#!/bin/bash\ncelery -A app.tasks.celery_app inspect ping --timeout=10' > /usr/local/bin/celery-healthcheck && \
    chmod +x /usr/local/bin/celery-healthcheck

# 環境変数設定
ENV PYTHONUNBUFFERED=1
ENV CELERY_LOG_LEVEL=INFO

# ポート8000を公開
EXPOSE 8000

# デフォルトコマンド（FastAPIサーバーを起動）
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 