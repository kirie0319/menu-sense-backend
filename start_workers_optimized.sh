#!/bin/bash

# =================================================
# 最適化されたCeleryワーカー起動スクリプト
# あなたの要件に特化した戦略的ワーカー配分
# =================================================

echo "🚀 最適化されたCeleryワーカーを起動中..."
echo "📊 戦略的ワーカー配分:"
echo "   - 翻訳: 2ワーカー (並列処理)"
echo "   - 詳細説明: 2ワーカー (並列処理)" 
echo "   - バッチ処理: 1ワーカー (8個ずつ制御)"
echo "   - OCR+カテゴライズ: 1ワーカー (シーケンシャル)"
echo ""

# 既存のワーカーを停止
echo "🛑 既存のワーカーを停止中..."
pkill -f "celery.*worker" 2>/dev/null || true
sleep 2

# Redis接続確認
echo "📦 Redis接続確認中..."
redis-cli ping > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Redis接続成功"
else
    echo "❌ Redis接続失敗 - Redisを起動してください"
    exit 1
fi

# ワーカー1: 並列翻訳専用 (2 concurrency)
echo "🌍 翻訳ワーカー起動中..."
nohup celery -A app.tasks.celery_app worker \
    -Q translation_queue \
    -c 2 \
    -n translation_worker@%h \
    --loglevel=info \
    > logs/celery_translation.log 2>&1 &

sleep 1

# ワーカー2: 並列詳細説明専用 (2 concurrency)  
echo "📝 詳細説明ワーカー起動中..."
nohup celery -A app.tasks.celery_app worker \
    -Q description_queue \
    -c 2 \
    -n description_worker@%h \
    --loglevel=info \
    > logs/celery_description.log 2>&1 &

sleep 1

# ワーカー3: バッチ処理制御専用 (1 concurrency)
echo "⚡ バッチ処理ワーカー起動中..."
nohup celery -A app.tasks.celery_app worker \
    -Q item_processing_queue \
    -c 1 \
    -n batch_worker@%h \
    --loglevel=info \
    > logs/celery_batch.log 2>&1 &

sleep 1

# ワーカー4: OCR+カテゴライズ (1 concurrency)
echo "👁️ OCR+カテゴライズワーカー起動中..."
nohup celery -A app.tasks.celery_app worker \
    -Q ocr_queue,categorization_queue \
    -c 1 \
    -n ocr_categorization_worker@%h \
    --loglevel=info \
    > logs/celery_ocr_cat.log 2>&1 &

sleep 1

# ワーカー5: 低優先度キュー共有 (1 concurrency)
echo "🎨 その他ワーカー起動中..."
nohup celery -A app.tasks.celery_app worker \
    -Q image_queue,pipeline_queue,default \
    -c 1 \
    -n misc_worker@%h \
    --loglevel=info \
    > logs/celery_misc.log 2>&1 &

sleep 2

# ログディレクトリ作成
mkdir -p logs

# ワーカー状態確認
echo ""
echo "📊 ワーカー状態確認中..."
sleep 3

# Celeryステータス確認
python -c "
import sys
sys.path.insert(0, '.')
from app.tasks.celery_app import celery_app
try:
    inspector = celery_app.control.inspect()
    stats = inspector.stats()
    if stats:
        print(f'✅ {len(stats)} ワーカーがアクティブです')
        for worker_name, worker_stats in stats.items():
            pool = worker_stats.get('pool', {})
            processes = pool.get('processes', [])
            print(f'   📌 {worker_name}: {len(processes)} プロセス')
    else:
        print('⚠️ ワーカーが見つかりません')
except Exception as e:
    print(f'❌ ステータス確認エラー: {e}')
"

echo ""
echo "🎉 最適化されたワーカー配分完了!"
echo ""
echo "📋 使用方法:"
echo "   - ワーカー状況確認: python worker_monitor.py --status"
echo "   - リアルタイム監視: python worker_monitor.py --monitor"
echo "   - ワーカー停止: pkill -f 'celery.*worker'"
echo ""
echo "🔧 ワーカー配分:"
echo "   - translation_queue: 2 プロセス (並列翻訳)"
echo "   - description_queue: 2 プロセス (並列詳細説明)"
echo "   - item_processing_queue: 1 プロセス (バッチ制御)"
echo "   - ocr_queue + categorization_queue: 1 プロセス"
echo "   - その他: 1 プロセス"
echo "   合計: 7 プロセス (最適化済み)" 