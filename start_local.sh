#!/bin/bash

# ローカル環境でアプリケーションを起動するスクリプト

set -e

PROJECT_DIR="/Users/mbp231/Desktop/menu_sensor/menu_sensor_backend"
VENV_PATH="$PROJECT_DIR/venv"

echo "🚀 ローカル環境でアプリケーションを起動します..."

# プロジェクトディレクトリに移動
cd "$PROJECT_DIR"

# 仮想環境の確認
if [ ! -d "$VENV_PATH" ]; then
    echo "❌ 仮想環境が見つかりません。先に 'python3 -m venv venv' を実行してください。"
    exit 1
fi

# 仮想環境をアクティベート
source "$VENV_PATH/bin/activate"

# Redisの確認
echo "🔍 Redisサービスを確認中..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️ Redisが起動していません。Redisを起動中..."
    if command -v brew > /dev/null 2>&1; then
        brew services start redis
    else
        echo "❌ Redisを手動で起動してください: redis-server"
        exit 1
    fi
    sleep 2
fi

echo "✅ Redis接続確認完了"

# .envファイルの確認
if [ ! -f ".env" ]; then
    echo "⚠️ .envファイルが見つかりません。env_example.txtから作成中..."
    cp env_example.txt .env
    echo "📝 .envファイルを編集して必要な設定を追加してください"
fi

# ログディレクトリの作成
mkdir -p logs
mkdir -p uploads

echo "🎯 アプリケーションのプロセスを起動します..."

# tmuxセッションの作成（tmuxがある場合）
if command -v tmux > /dev/null 2>&1; then
    echo "📱 tmuxセッションを使用してプロセスを管理します"
    
    # 既存のセッションを終了
    tmux kill-session -t menu_sensor 2>/dev/null || true
    
    # 新しいセッションを作成
    tmux new-session -d -s menu_sensor
    
    # FastAPIサーバー
    tmux rename-window -t menu_sensor:0 'fastapi'
    tmux send-keys -t menu_sensor:0 "cd $PROJECT_DIR && source venv/bin/activate && python -m uvicorn app_2.main:app --host 0.0.0.0 --port 8000 --reload" C-m
    
    # 翻訳ワーカー
    tmux new-window -t menu_sensor -n 'translate-worker'
    tmux send-keys -t menu_sensor:1 "cd $PROJECT_DIR && source venv/bin/activate && celery -A app_2.core.celery_app worker --queues=real_translate_queue --concurrency=8 --hostname=translation_worker@%h --loglevel=info" C-m
    
    # 説明ワーカー
    tmux new-window -t menu_sensor -n 'description-worker'
    tmux send-keys -t menu_sensor:2 "cd $PROJECT_DIR && source venv/bin/activate && celery -A app_2.core.celery_app worker --queues=real_description_queue --concurrency=6 --hostname=description_worker@%h --loglevel=info" C-m
    
    # 画像ワーカー
    tmux new-window -t menu_sensor -n 'image-worker'
    tmux send-keys -t menu_sensor:3 "cd $PROJECT_DIR && source venv/bin/activate && celery -A app_2.core.celery_app worker --queues=real_image_queue --concurrency=3 --hostname=image_worker@%h --loglevel=info" C-m
    
    echo "✅ すべてのプロセスがtmuxセッション 'menu_sensor' で起動しました"
    echo "📋 tmuxセッションにアタッチするには: tmux attach -t menu_sensor"
    echo "📋 セッションを終了するには: tmux kill-session -t menu_sensor"
    echo "📋 ウィンドウ間の移動: Ctrl+b → 数字キー (0-3)"
    
else
    echo "⚠️ tmuxが見つかりません。手動で各プロセスを起動してください:"
    echo "   ターミナル1: python -m uvicorn app_2.main:app --host 0.0.0.0 --port 8000 --reload"
    echo "   ターミナル2: celery -A app_2.core.celery_app worker --queues=real_translate_queue --concurrency=8"
    echo "   ターミナル3: celery -A app_2.core.celery_app worker --queues=real_description_queue --concurrency=6"
    echo "   ターミナル4: celery -A app_2.core.celery_app worker --queues=real_image_queue --concurrency=3"
fi

echo "🌐 FastAPI server: http://localhost:8000"
echo "📚 API docs: http://localhost:8000/docs" 