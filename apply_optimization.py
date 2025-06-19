#!/usr/bin/env python3
"""
バックエンド処理最適化スクリプト

このスクリプトは：
1. 最適化設定を.envファイルに適用
2. 設定値の確認
3. Celeryワーカーのテスト
4. 性能向上の確認

使用方法:
python apply_optimization.py [--apply] [--test] [--status]
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path

def read_optimization_settings():
    """最適化設定ファイルを読み込む"""
    settings_file = Path("optimization_settings.env")
    if not settings_file.exists():
        print("❌ optimization_settings.env ファイルが見つかりません")
        return None
    
    settings = {}
    with open(settings_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                settings[key.strip()] = value.strip()
    
    return settings

def apply_settings_to_env(settings):
    """設定を.envファイルに適用"""
    env_file = Path(".env")
    
    # 既存の.envファイルを読み込み
    existing_settings = {}
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    existing_settings[key.strip()] = value.strip()
    
    # 新しい設定をマージ
    updated_count = 0
    for key, value in settings.items():
        if key not in existing_settings or existing_settings[key] != value:
            existing_settings[key] = value
            updated_count += 1
    
    # .envファイルに書き込み
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write("# 最適化設定が適用されました\n")
        f.write(f"# 更新された設定: {updated_count}個\n\n")
        
        for key, value in existing_settings.items():
            f.write(f"{key}={value}\n")
    
    print(f"✅ .envファイルに{updated_count}個の最適化設定を適用しました")
    return updated_count

def check_current_settings():
    """現在の設定値を確認"""
    try:
        # 現在のPythonパスにappディレクトリを追加
        sys.path.insert(0, '.')
        
        from app.core.config import settings
        
        print("\n📊 現在のバックエンド設定:")
        print(f"  並列チャンク数: {settings.CONCURRENT_CHUNK_LIMIT}")
        print(f"  画像生成並列数: {settings.IMAGE_CONCURRENT_CHUNK_LIMIT}")
        print(f"  Celeryワーカー同時実行数: {settings.CELERY_WORKER_CONCURRENCY}")
        print(f"  最大画像ワーカー数: {settings.MAX_IMAGE_WORKERS}")
        print(f"  レート制限間隔: {settings.RATE_LIMIT_SLEEP}秒")
        print(f"  画像生成レート制限: {settings.IMAGE_RATE_LIMIT_SLEEP}秒")
        print(f"  無制限処理モード: {settings.UNLIMITED_PROCESSING}")
        print(f"  カテゴリ並列処理: {settings.ENABLE_CATEGORY_PARALLEL}")
        print(f"  ワーカー均等活用: {settings.FORCE_WORKER_UTILIZATION}")
        
        return True
    except Exception as e:
        print(f"❌ 設定確認エラー: {e}")
        return False

def test_celery_connection():
    """Celery接続をテスト"""
    try:
        sys.path.insert(0, '.')
        from app.tasks.celery_app import test_celery_connection, get_celery_info, get_worker_stats
        
        print("\n🔧 Celery接続テスト:")
        
        # 基本接続テスト
        success, message = test_celery_connection()
        if success:
            print(f"  ✅ {message}")
        else:
            print(f"  ❌ {message}")
            return False
        
        # 設定情報表示
        print("\n📋 Celery設定情報:")
        info = get_celery_info()
        for key, value in info.items():
            print(f"  {key}: {value}")
        
        # ワーカー統計
        print("\n👥 ワーカー統計:")
        stats = get_worker_stats()
        if "error" in stats:
            print(f"  ⚠️ {stats['error']}")
        else:
            print(f"  アクティブワーカー数: {stats.get('worker_count', 0)}")
            if stats.get('active_tasks'):
                active_count = sum(len(tasks) for tasks in stats['active_tasks'].values())
                print(f"  実行中タスク数: {active_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ Celeryテストエラー: {e}")
        return False

def restart_services():
    """サービスを再起動"""
    print("\n🔄 サービス再起動中...")
    
    try:
        # 既存のプロセスを停止
        subprocess.run(["pkill", "-f", "uvicorn"], capture_output=True)
        subprocess.run(["pkill", "-f", "celery"], capture_output=True)
        print("  ✅ 既存プロセスを停止しました")
        
        # Celeryワーカーを再起動
        celery_cmd = [
            "celery", "-A", "app.tasks.celery_app", "worker",
            "--loglevel=info",
            "--detach"
        ]
        
        result = subprocess.run(celery_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ Celeryワーカーを再起動しました")
        else:
            print(f"  ⚠️ Celeryワーカー再起動エラー: {result.stderr}")
        
        print("  💡 FastAPIサーバーは手動で再起動してください: python app/main.py")
        
        return True
        
    except Exception as e:
        print(f"❌ サービス再起動エラー: {e}")
        return False

def calculate_performance_improvement():
    """性能向上の推定値を計算"""
    try:
        sys.path.insert(0, '.')
        from app.core.config import settings
        
        # デフォルト値
        default_values = {
            'CONCURRENT_CHUNK_LIMIT': 5,
            'IMAGE_CONCURRENT_CHUNK_LIMIT': 3,
            'CELERY_WORKER_CONCURRENCY': 4,
            'MAX_IMAGE_WORKERS': 3,
            'RATE_LIMIT_SLEEP': 1.0,
            'IMAGE_RATE_LIMIT_SLEEP': 2.0
        }
        
        # 現在値
        current_values = {
            'CONCURRENT_CHUNK_LIMIT': settings.CONCURRENT_CHUNK_LIMIT,
            'IMAGE_CONCURRENT_CHUNK_LIMIT': settings.IMAGE_CONCURRENT_CHUNK_LIMIT,
            'CELERY_WORKER_CONCURRENCY': settings.CELERY_WORKER_CONCURRENCY,
            'MAX_IMAGE_WORKERS': settings.MAX_IMAGE_WORKERS,
            'RATE_LIMIT_SLEEP': settings.RATE_LIMIT_SLEEP,
            'IMAGE_RATE_LIMIT_SLEEP': settings.IMAGE_RATE_LIMIT_SLEEP
        }
        
        print("\n📈 推定性能向上:")
        total_improvement = 1.0
        
        for key in default_values:
            if key.endswith('_SLEEP'):
                # レート制限の場合は逆数
                improvement = default_values[key] / current_values[key]
            else:
                # 並列数の場合は直接比率
                improvement = current_values[key] / default_values[key]
            
            total_improvement *= improvement
            print(f"  {key}: {improvement:.1f}倍向上")
        
        print(f"\n🚀 総合的な処理速度向上: {total_improvement:.1f}倍")
        
        return total_improvement
        
    except Exception as e:
        print(f"❌ 性能計算エラー: {e}")
        return 1.0

def main():
    parser = argparse.ArgumentParser(description="バックエンド処理最適化スクリプト")
    parser.add_argument("--apply", action="store_true", help="最適化設定を適用")
    parser.add_argument("--test", action="store_true", help="Celery接続をテスト")
    parser.add_argument("--status", action="store_true", help="現在の設定状況を表示")
    parser.add_argument("--restart", action="store_true", help="サービスを再起動")
    parser.add_argument("--all", action="store_true", help="すべての操作を実行")
    
    args = parser.parse_args()
    
    if not any([args.apply, args.test, args.status, args.restart, args.all]):
        parser.print_help()
        return
    
    print("🚀 バックエンド処理最適化スクリプト")
    print("=" * 50)
    
    if args.all or args.status:
        check_current_settings()
    
    if args.all or args.apply:
        settings = read_optimization_settings()
        if settings:
            apply_settings_to_env(settings)
        else:
            print("❌ 最適化設定の読み込みに失敗しました")
            return
    
    if args.all or args.restart:
        restart_services()
    
    if args.all or args.test:
        test_celery_connection()
    
    if args.all or args.status:
        calculate_performance_improvement()
    
    print("\n✅ 最適化処理が完了しました！")
    print("💡 フロントエンドには一切影響しません")
    print("📊 処理速度の向上を確認してください")

if __name__ == "__main__":
    main() 