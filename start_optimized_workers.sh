#!/bin/bash

# 最適化されたCeleryワーカー起動スクリプト
# 各ワーカーのConcurrencyを最適化

echo "🚀 Starting optimized Celery workers..."
echo "📋 Configuration:"
echo "   - Translation Worker: Concurrency 8 (real_translate_queue)"
echo "   - Description Worker: Concurrency 6 (real_description_queue)"
echo "   - Image Worker: Concurrency 3 (real_image_queue)"
echo ""

# ログディレクトリ作成
mkdir -p logs

# 翻訳専用ワーカー (Concurrency: 8)
echo "🌍 Starting Translation Worker (Concurrency: 8)..."
nohup celery -A app.tasks.celery_app worker \
  --queues=real_translate_queue \
  --concurrency=8 \
  --hostname=translate_worker@%h \
  --loglevel=info \
  > logs/translate_worker.log 2>&1 &

TRANSLATE_PID=$!
echo "   Translation Worker PID: $TRANSLATE_PID"

# 説明生成専用ワーカー (Concurrency: 6)
echo "📝 Starting Description Worker (Concurrency: 6)..."
nohup celery -A app.tasks.celery_app worker \
  --queues=real_description_queue \
  --concurrency=6 \
  --hostname=description_worker@%h \
  --loglevel=info \
  > logs/description_worker.log 2>&1 &

DESCRIPTION_PID=$!
echo "   Description Worker PID: $DESCRIPTION_PID"

# 画像生成専用ワーカー (Concurrency: 3)
echo "🎨 Starting Image Worker (Concurrency: 3)..."
nohup celery -A app.tasks.celery_app worker \
  --queues=real_image_queue \
  --concurrency=3 \
  --hostname=image_worker@%h \
  --loglevel=info \
  > logs/image_worker.log 2>&1 &

IMAGE_PID=$!
echo "   Image Worker PID: $IMAGE_PID"

echo ""
echo "✅ All workers started!"
echo "📊 Worker PIDs:"
echo "   - Translation: $TRANSLATE_PID"
echo "   - Description: $DESCRIPTION_PID"
echo "   - Image: $IMAGE_PID"
echo ""
echo "📝 Log files:"
echo "   - logs/translate_worker.log"
echo "   - logs/description_worker.log"  
echo "   - logs/image_worker.log"
echo ""
echo "🔍 Monitor workers with:"
echo "   celery -A app.tasks.celery_app inspect active"
echo ""
echo "🛑 Stop all workers with:"
echo "   pkill -f celery" 