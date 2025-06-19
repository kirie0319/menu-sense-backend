#!/usr/bin/env python3
"""
Celeryワーカー リアルタイム監視ダッシュボード

このツールは：
1. ワーカーの動作状況をリアルタイム表示
2. 処理時間とパフォーマンス統計
3. タスクキューの状況
4. メモリ・CPU使用率
5. 設定値の確認
"""

import time
import os
import sys
import subprocess
import json
import threading
from datetime import datetime, timedelta
from collections import defaultdict, deque
import psutil

class WorkerMonitor:
    def __init__(self):
        self.stats_history = deque(maxlen=60)  # 60秒分の履歴
        self.task_times = defaultdict(list)
        self.running = True
        self.start_time = time.time()
        
        # カラー定義
        self.colors = {
            'green': '\033[92m',
            'yellow': '\033[93m', 
            'red': '\033[91m',
            'blue': '\033[94m',
            'cyan': '\033[96m',
            'magenta': '\033[95m',
            'white': '\033[97m',
            'reset': '\033[0m',
            'bold': '\033[1m'
        }
    
    def clear_screen(self):
        """画面をクリア"""
        os.system('clear' if os.name == 'posix' else 'cls')
    
    def colored_text(self, text, color):
        """カラー付きテキスト"""
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def get_celery_info(self):
        """Celery接続情報を取得"""
        try:
            sys.path.insert(0, '.')
            from app.tasks.celery_app import test_celery_connection, get_celery_info, get_worker_stats
            
            # 接続テスト
            connection_success, connection_msg = test_celery_connection()
            
            # 設定情報
            config_info = get_celery_info()
            
            # ワーカー統計
            worker_stats = get_worker_stats()
            
            return {
                'connection': {'success': connection_success, 'message': connection_msg},
                'config': config_info,
                'workers': worker_stats
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_redis_info(self):
        """Redis接続情報を取得"""
        try:
            result = subprocess.run(['redis-cli', 'info'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                info = {}
                for line in result.stdout.split('\n'):
                    if ':' in line and not line.startswith('#'):
                        key, value = line.split(':', 1)
                        info[key] = value.strip()
                
                return {
                    'connected': True,
                    'memory_used': info.get('used_memory_human', 'N/A'),
                    'connected_clients': info.get('connected_clients', 'N/A'),
                    'keyspace_hits': info.get('keyspace_hits', 'N/A'),
                    'keyspace_misses': info.get('keyspace_misses', 'N/A')
                }
            else:
                return {'connected': False, 'error': 'Redis not responding'}
        except Exception as e:
            return {'connected': False, 'error': str(e)}
    
    def get_system_info(self):
        """システム情報を取得"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Celeryプロセスの詳細
            celery_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['cmdline'] and any('celery' in arg for arg in proc.info['cmdline']):
                        celery_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used': f"{memory.used / 1024**3:.1f}GB",
                'memory_total': f"{memory.total / 1024**3:.1f}GB",
                'disk_percent': disk.percent,
                'celery_processes': celery_processes
            }
        except Exception as e:
            return {'error': str(e)}
    
    def get_backend_config(self):
        """バックエンド設定を取得"""
        try:
            sys.path.insert(0, '.')
            from app.core.config import settings
            
            return {
                'concurrent_chunk_limit': settings.CONCURRENT_CHUNK_LIMIT,
                'image_concurrent_chunk_limit': settings.IMAGE_CONCURRENT_CHUNK_LIMIT,
                'celery_worker_concurrency': settings.CELERY_WORKER_CONCURRENCY,
                'max_image_workers': settings.MAX_IMAGE_WORKERS,
                'rate_limit_sleep': settings.RATE_LIMIT_SLEEP,
                'image_rate_limit_sleep': settings.IMAGE_RATE_LIMIT_SLEEP,
                'unlimited_processing': settings.UNLIMITED_PROCESSING,
                'enable_category_parallel': settings.ENABLE_CATEGORY_PARALLEL,
                'force_worker_utilization': settings.FORCE_WORKER_UTILIZATION,
                'redis_url': settings.REDIS_URL
            }
        except Exception as e:
            return {'error': str(e)}
    
    def display_header(self):
        """ヘッダー情報を表示"""
        uptime = int(time.time() - self.start_time)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        print(self.colored_text("=" * 80, 'cyan'))
        print(self.colored_text("🚀 Celeryワーカー リアルタイム監視ダッシュボード", 'bold'))
        print(self.colored_text(f"⏰ {current_time} | 監視時間: {uptime}秒", 'white'))
        print(self.colored_text("=" * 80, 'cyan'))
    
    def display_celery_status(self, celery_info):
        """Celery状態を表示"""
        print(self.colored_text("\n📊 Celery状態:", 'yellow'))
        
        if 'error' in celery_info:
            print(f"  ❌ エラー: {celery_info['error']}")
            return
        
        # 接続状況
        conn = celery_info['connection']
        if conn['success']:
            print(f"  ✅ {self.colored_text(conn['message'], 'green')}")
        else:
            print(f"  ❌ {self.colored_text(conn['message'], 'red')}")
        
        # 設定情報
        config = celery_info['config']
        print(f"  🔧 ワーカー同時実行数: {self.colored_text(str(config.get('worker_concurrency', 'N/A')), 'cyan')}")
        print(f"  📥 プリフェッチ数: {self.colored_text(str(config.get('worker_prefetch_multiplier', 'N/A')), 'cyan')}")
        print(f"  🔄 最大タスク/プロセス: {self.colored_text(str(config.get('worker_max_tasks_per_child', 'N/A')), 'cyan')}")
        
        # ワーカー統計
        workers = celery_info['workers']
        if 'error' in workers:
            print(f"  ⚠️ ワーカー情報取得エラー: {workers['error']}")
        else:
            worker_count = workers.get('worker_count', 0)
            if worker_count > 0:
                print(f"  👥 アクティブワーカー数: {self.colored_text(str(worker_count), 'green')}")
                
                if workers.get('active_tasks'):
                    total_active = sum(len(tasks) for tasks in workers['active_tasks'].values())
                    print(f"  ⚡ 実行中タスク数: {self.colored_text(str(total_active), 'yellow')}")
            else:
                print(f"  ⚠️ ワーカーが見つかりません")
    
    def display_system_status(self, system_info):
        """システム状態を表示"""
        print(self.colored_text("\n💻 システム状態:", 'yellow'))
        
        if 'error' in system_info:
            print(f"  ❌ エラー: {system_info['error']}")
            return
        
        # CPU・メモリ
        cpu_color = 'green' if system_info['cpu_percent'] < 50 else 'yellow' if system_info['cpu_percent'] < 80 else 'red'
        mem_color = 'green' if system_info['memory_percent'] < 50 else 'yellow' if system_info['memory_percent'] < 80 else 'red'
        
        print(f"  🖥️  CPU使用率: {self.colored_text(f'{system_info['cpu_percent']:.1f}%', cpu_color)}")
        print(f"  🧠 メモリ使用率: {self.colored_text(f'{system_info['memory_percent']:.1f}%', mem_color)} ({system_info['memory_used']}/{system_info['memory_total']})")
        print(f"  💾 ディスク使用率: {system_info['disk_percent']:.1f}%")
        
        # Celeryプロセス詳細
        celery_procs = system_info.get('celery_processes', [])
        if celery_procs:
            print(f"  🔄 Celeryプロセス数: {self.colored_text(str(len(celery_procs)), 'cyan')}")
            for proc in celery_procs[:3]:  # 最大3つまで表示
                cpu = proc.get('cpu_percent', 0)
                mem = proc.get('memory_percent', 0)
                print(f"    └─ PID {proc['pid']}: CPU {cpu:.1f}%, MEM {mem:.1f}%")
        else:
            print(f"  ⚠️ Celeryプロセスが見つかりません")
    
    def display_redis_status(self, redis_info):
        """Redis状態を表示"""
        print(self.colored_text("\n📦 Redis状態:", 'yellow'))
        
        if redis_info['connected']:
            print(f"  ✅ {self.colored_text('Redis接続成功', 'green')}")
            print(f"  💾 メモリ使用量: {self.colored_text(redis_info['memory_used'], 'cyan')}")
            print(f"  🔗 接続クライアント数: {self.colored_text(redis_info['connected_clients'], 'cyan')}")
            
            # キャッシュヒット率計算
            hits = int(redis_info.get('keyspace_hits', 0))
            misses = int(redis_info.get('keyspace_misses', 0))
            if hits + misses > 0:
                hit_rate = hits / (hits + misses) * 100
                hit_color = 'green' if hit_rate > 80 else 'yellow' if hit_rate > 50 else 'red'
                print(f"  🎯 キャッシュヒット率: {self.colored_text(f'{hit_rate:.1f}%', hit_color)}")
        else:
            print(f"  ❌ {self.colored_text(f'Redis接続失敗: {redis_info.get('error', 'Unknown')}', 'red')}")
    
    def display_backend_config(self, config):
        """バックエンド設定を表示"""
        print(self.colored_text("\n⚙️ バックエンド設定:", 'yellow'))
        
        if 'error' in config:
            print(f"  ❌ エラー: {config['error']}")
            return
        
        print(f"  🔄 並列チャンク数: {self.colored_text(str(config['concurrent_chunk_limit']), 'cyan')}")
        print(f"  🎨 画像生成並列数: {self.colored_text(str(config['image_concurrent_chunk_limit']), 'cyan')}")
        print(f"  👥 Celeryワーカー数: {self.colored_text(str(config['celery_worker_concurrency']), 'cyan')}")
        print(f"  🖼️ 最大画像ワーカー数: {self.colored_text(str(config['max_image_workers']), 'cyan')}")
        print(f"  ⏱️ レート制限間隔: {self.colored_text(f'{config['rate_limit_sleep']}秒', 'cyan')}")
        print(f"  🚀 無制限処理モード: {self.colored_text(str(config['unlimited_processing']), 'green' if config['unlimited_processing'] else 'yellow')}")
        print(f"  ⚡ カテゴリ並列処理: {self.colored_text(str(config['enable_category_parallel']), 'green' if config['enable_category_parallel'] else 'yellow')}")
    
    def display_performance_tips(self):
        """パフォーマンス改善のヒントを表示"""
        print(self.colored_text("\n💡 パフォーマンス最適化のヒント:", 'magenta'))
        print("  🔧 最適化設定を適用: python apply_optimization.py --apply")
        print("  ⚡ Celeryワーカー起動: celery -A app.tasks.celery_app worker --concurrency=6 --loglevel=info")
        print("  📊 詳細テスト実行: python apply_optimization.py --test")
        print("  🚀 全体最適化: python apply_optimization.py --all")
    
    def run_monitor(self):
        """監視を実行"""
        try:
            while self.running:
                self.clear_screen()
                
                # データ収集
                celery_info = self.get_celery_info()
                system_info = self.get_system_info()
                redis_info = self.get_redis_info()
                config_info = self.get_backend_config()
                
                # 表示
                self.display_header()
                self.display_celery_status(celery_info)
                self.display_system_status(system_info)
                self.display_redis_status(redis_info)
                self.display_backend_config(config_info)
                self.display_performance_tips()
                
                print(self.colored_text("\n⌨️ 終了するには Ctrl+C を押してください", 'white'))
                print(self.colored_text("=" * 80, 'cyan'))
                
                # 2秒間隔で更新
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(self.colored_text("\n\n👋 監視を終了します...", 'yellow'))
            self.running = False

class PerformanceBenchmark:
    """パフォーマンス測定クラス"""
    
    def __init__(self):
        self.results = []
    
    def run_simple_test(self):
        """簡単なパフォーマンステストを実行"""
        try:
            sys.path.insert(0, '.')
            from app.tasks.image_tasks import hello_world_task
            
            print("🧪 簡単なタスクでパフォーマンステスト中...")
            
            start_time = time.time()
            result = hello_world_task.delay()
            
            # 結果を待機（最大10秒）
            for i in range(50):  # 10秒間チェック
                if result.ready():
                    break
                time.sleep(0.2)
                print(f"  ⏳ 待機中... {i*0.2:.1f}秒")
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.ready():
                print(f"  ✅ タスク完了: {duration:.2f}秒")
                return {'success': True, 'duration': duration, 'result': result.get()}
            else:
                print(f"  ⏰ タイムアウト: {duration:.2f}秒")
                return {'success': False, 'duration': duration, 'error': 'Timeout'}
                
        except Exception as e:
            print(f"  ❌ テストエラー: {e}")
            return {'success': False, 'error': str(e)}

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Celeryワーカー監視ツール")
    parser.add_argument("--monitor", "-m", action="store_true", help="リアルタイム監視開始")
    parser.add_argument("--test", "-t", action="store_true", help="パフォーマンステスト実行")
    parser.add_argument("--status", "-s", action="store_true", help="現在の状況を1回表示")
    
    args = parser.parse_args()
    
    if args.monitor:
        monitor = WorkerMonitor()
        monitor.run_monitor()
    elif args.test:
        benchmark = PerformanceBenchmark()
        benchmark.run_simple_test()
    elif args.status:
        monitor = WorkerMonitor()
        # 1回だけ表示
        celery_info = monitor.get_celery_info()
        system_info = monitor.get_system_info()
        redis_info = monitor.get_redis_info()
        config_info = monitor.get_backend_config()
        
        monitor.display_header()
        monitor.display_celery_status(celery_info)
        monitor.display_system_status(system_info)
        monitor.display_redis_status(redis_info)
        monitor.display_backend_config(config_info)
    else:
        parser.print_help()
        print("\n💡 おすすめ:")
        print("  リアルタイム監視: python worker_monitor.py --monitor")
        print("  現在の状況確認: python worker_monitor.py --status") 
        print("  パフォーマンステスト: python worker_monitor.py --test")

if __name__ == "__main__":
    main() 