#!/usr/bin/env python3
"""
パフォーマンス ベンチマーク & 比較ツール

このツールは：
1. 最適化前後の処理時間を比較
2. タスクの実行速度を測定
3. スループットの計算
4. 並列処理の効果測定
5. メモリ使用量の監視
"""

import time
import asyncio
import sys
import json
import statistics
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import queue

class PerformanceBenchmark:
    def __init__(self):
        self.results = []
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
    
    def colored_text(self, text, color):
        """カラー付きテキスト"""
        return f"{self.colors.get(color, '')}{text}{self.colors['reset']}"
    
    def print_header(self, title):
        """ヘッダーを表示"""
        print(self.colored_text("=" * 80, 'cyan'))
        print(self.colored_text(f"🚀 {title}", 'bold'))
        print(self.colored_text(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 'white'))
        print(self.colored_text("=" * 80, 'cyan'))
    
    def test_celery_basic(self):
        """基本的なCeleryタスクの速度テスト"""
        self.print_header("基本的なCeleryタスク速度テスト")
        
        try:
            sys.path.insert(0, '.')
            from app.tasks.image_tasks import hello_world_task
            
            print("🧪 Hello Worldタスクの速度を測定中...")
            
            # 単一タスクテスト
            start_time = time.time()
            result = hello_world_task.delay()
            
            # 結果を待機（最大15秒）
            timeout = 15
            for i in range(timeout * 5):
                if result.ready():
                    break
                time.sleep(0.2)
                if i % 10 == 0:  # 2秒ごとに表示
                    print(f"  ⏳ 待機中... {i*0.2:.1f}秒")
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.ready():
                if result.successful():
                    task_result = result.get()
                    print(f"  ✅ タスク完了: {self.colored_text(f'{duration:.2f}秒', 'green')}")
                    print(f"  📊 結果: {task_result.get('message', 'N/A')}")
                    return {'success': True, 'duration': duration, 'result': task_result}
                else:
                    print(f"  ❌ タスク失敗: {result.result}")
                    return {'success': False, 'duration': duration, 'error': str(result.result)}
            else:
                print(f"  ⏰ タイムアウト: {self.colored_text(f'{duration:.2f}秒', 'red')}")
                return {'success': False, 'duration': duration, 'error': 'Timeout'}
                
        except Exception as e:
            print(f"  ❌ テストエラー: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_concurrent_tasks(self, num_tasks=5):
        """並列タスクの速度テスト"""
        self.print_header(f"並列タスク速度テスト ({num_tasks}タスク)")
        
        try:
            sys.path.insert(0, '.')
            from app.tasks.image_tasks import hello_world_task
            
            print(f"🧪 {num_tasks}個のタスクを並列実行中...")
            
            # 複数タスクを並列実行
            start_time = time.time()
            tasks = []
            
            for i in range(num_tasks):
                task = hello_world_task.delay()
                tasks.append(task)
                print(f"  📤 タスク{i+1}を送信")
            
            print(f"  ⏳ {num_tasks}個のタスク完了を待機中...")
            
            # 全タスクの完了を待機
            completed_tasks = 0
            timeout = 30  # 30秒タイムアウト
            
            for i in range(timeout * 5):
                ready_count = sum(1 for task in tasks if task.ready())
                if ready_count > completed_tasks:
                    completed_tasks = ready_count
                    print(f"  ✅ 完了: {completed_tasks}/{num_tasks}")
                
                if ready_count == num_tasks:
                    break
                
                time.sleep(0.2)
            
            end_time = time.time()
            total_duration = end_time - start_time
            
            # 結果の集計
            successful_tasks = 0
            failed_tasks = 0
            individual_times = []
            
            for i, task in enumerate(tasks):
                if task.ready():
                    if task.successful():
                        successful_tasks += 1
                        # 個別のタスク時間は推定
                        individual_times.append(total_duration / num_tasks)
                    else:
                        failed_tasks += 1
                else:
                    failed_tasks += 1
            
            # 統計情報を表示
            print(f"\n📊 並列実行結果:")
            print(f"  ⏱️ 総実行時間: {self.colored_text(f'{total_duration:.2f}秒', 'cyan')}")
            print(f"  ✅ 成功タスク: {self.colored_text(str(successful_tasks), 'green')}")
            print(f"  ❌ 失敗タスク: {self.colored_text(str(failed_tasks), 'red')}")
            
            if successful_tasks > 0:
                avg_time = total_duration / successful_tasks
                throughput = successful_tasks / total_duration
                print(f"  📈 平均処理時間: {self.colored_text(f'{avg_time:.2f}秒/タスク', 'cyan')}")
                print(f"  🚀 スループット: {self.colored_text(f'{throughput:.2f}タスク/秒', 'green')}")
                
                # 逐次実行との比較
                sequential_time = num_tasks * 4.0  # 推定4秒/タスク
                speedup = sequential_time / total_duration
                print(f"  ⚡ 推定速度向上: {self.colored_text(f'{speedup:.1f}倍', 'green')}")
            
            return {
                'success': True,
                'total_duration': total_duration,
                'successful_tasks': successful_tasks,
                'failed_tasks': failed_tasks,
                'throughput': successful_tasks / total_duration if total_duration > 0 else 0
            }
            
        except Exception as e:
            print(f"  ❌ 並列テストエラー: {e}")
            return {'success': False, 'error': str(e)}
    
    def test_image_chunk_performance(self):
        """画像生成チャンクのパフォーマンステスト"""
        self.print_header("画像生成チャンク パフォーマンステスト")
        
        try:
            sys.path.insert(0, '.')
            from app.tasks.image_tasks import test_image_chunk_task
            
            # テスト用のモックデータ
            chunk_data = [
                {"japanese_name": "テスト料理1", "english_name": "Test Dish 1"},
                {"japanese_name": "テスト料理2", "english_name": "Test Dish 2"},
                {"japanese_name": "テスト料理3", "english_name": "Test Dish 3"},
            ]
            
            chunk_info = {
                "chunk_id": 1,
                "total_chunks": 1,
                "category": "test_category"
            }
            
            print(f"🧪 画像生成チャンク（{len(chunk_data)}アイテム）の処理時間を測定中...")
            
            start_time = time.time()
            result = test_image_chunk_task.delay(chunk_data, chunk_info)
            
            # 進行状況を監視
            last_progress = -1
            timeout = 20  # 20秒タイムアウト
            
            for i in range(timeout * 5):
                if result.ready():
                    break
                
                # タスクの進行状況を取得
                if hasattr(result, 'info') and result.info:
                    progress = result.info.get('progress', 0)
                    if progress > last_progress:
                        print(f"  📊 進行状況: {progress}%")
                        last_progress = progress
                
                time.sleep(0.2)
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.ready() and result.successful():
                task_result = result.get()
                items_processed = task_result.get('items_processed', 0)
                processing_time = task_result.get('processing_time', duration)
                
                print(f"  ✅ チャンク処理完了: {self.colored_text(f'{duration:.2f}秒', 'green')}")
                print(f"  📊 処理アイテム数: {self.colored_text(str(items_processed), 'cyan')}")
                print(f"  ⚡ 処理速度: {self.colored_text(f'{items_processed/duration:.2f}アイテム/秒', 'green')}")
                
                return {
                    'success': True,
                    'duration': duration,
                    'items_processed': items_processed,
                    'throughput': items_processed / duration
                }
            else:
                print(f"  ❌ チャンク処理失敗: {duration:.2f}秒")
                error = result.result if result.ready() else "Timeout"
                return {'success': False, 'duration': duration, 'error': str(error)}
                
        except Exception as e:
            print(f"  ❌ 画像チャンクテストエラー: {e}")
            return {'success': False, 'error': str(e)}
    
    def benchmark_comparison(self):
        """最適化前後の比較ベンチマーク"""
        self.print_header("最適化効果 比較ベンチマーク")
        
        print("🔍 現在の設定でのパフォーマンスを測定し、理論値と比較します\n")
        
        # 1. 基本タスクテスト
        basic_result = self.test_celery_basic()
        
        print("\n" + "─" * 60)
        
        # 2. 並列タスクテスト  
        concurrent_result = self.test_concurrent_tasks(5)
        
        print("\n" + "─" * 60)
        
        # 3. 画像チャンクテスト
        chunk_result = self.test_image_chunk_performance()
        
        print("\n" + "─" * 60)
        
        # 4. 総合評価
        self.display_benchmark_summary(basic_result, concurrent_result, chunk_result)
    
    def display_benchmark_summary(self, basic_result, concurrent_result, chunk_result):
        """ベンチマーク結果の総合評価を表示"""
        print(self.colored_text("\n📈 ベンチマーク総合評価:", 'bold'))
        
        # 基本タスクの評価
        if basic_result.get('success'):
            basic_time = basic_result['duration']
            if basic_time < 2.0:
                basic_score = "優秀"
                basic_color = "green"
            elif basic_time < 5.0:
                basic_score = "良好"
                basic_color = "yellow"
            else:
                basic_score = "改善必要"
                basic_color = "red"
            
            print(f"  🎯 基本タスク性能: {self.colored_text(basic_score, basic_color)} ({basic_time:.2f}秒)")
        else:
            print(f"  ❌ 基本タスク: {self.colored_text('エラー', 'red')}")
        
        # 並列タスクの評価
        if concurrent_result.get('success'):
            throughput = concurrent_result['throughput']
            success_rate = concurrent_result['successful_tasks'] / (concurrent_result['successful_tasks'] + concurrent_result['failed_tasks']) * 100
            
            if throughput > 2.0:
                concurrent_score = "優秀"
                concurrent_color = "green"
            elif throughput > 1.0:
                concurrent_score = "良好" 
                concurrent_color = "yellow"
            else:
                concurrent_score = "改善必要"
                concurrent_color = "red"
                
            print(f"  🚀 並列処理性能: {self.colored_text(concurrent_score, concurrent_color)} ({throughput:.2f}タスク/秒, 成功率{success_rate:.1f}%)")
        else:
            print(f"  ❌ 並列処理: {self.colored_text('エラー', 'red')}")
        
        # 画像チャンクの評価
        if chunk_result.get('success'):
            chunk_throughput = chunk_result['throughput']
            
            if chunk_throughput > 1.5:
                chunk_score = "優秀"
                chunk_color = "green"
            elif chunk_throughput > 0.8:
                chunk_score = "良好"
                chunk_color = "yellow" 
            else:
                chunk_score = "改善必要"
                chunk_color = "red"
                
            print(f"  🎨 画像処理性能: {self.colored_text(chunk_score, chunk_color)} ({chunk_throughput:.2f}アイテム/秒)")
        else:
            print(f"  ❌ 画像処理: {self.colored_text('エラー', 'red')}")
        
        # 推奨アクション
        print(self.colored_text("\n💡 推奨アクション:", 'magenta'))
        
        if not any(result.get('success') for result in [basic_result, concurrent_result, chunk_result]):
            print("  🚨 Celeryワーカーが起動していません:")
            print("    celery -A app.tasks.celery_app worker --concurrency=6 --loglevel=info")
        elif concurrent_result.get('throughput', 0) < 1.0:
            print("  🔧 並列処理を最適化:")
            print("    python apply_optimization.py --apply")
        elif basic_result.get('duration', 0) > 3.0:
            print("  ⚡ Redisとネットワークを確認:")
            print("    redis-cli ping")
        else:
            print("  ✅ パフォーマンスは良好です！")
            print("  📊 継続的な監視を推奨: python worker_monitor.py --monitor")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="パフォーマンス ベンチマークツール")
    parser.add_argument("--basic", action="store_true", help="基本タスクテスト")
    parser.add_argument("--concurrent", type=int, default=5, help="並列タスクテスト（デフォルト5タスク）")
    parser.add_argument("--image", action="store_true", help="画像チャンクテスト")
    parser.add_argument("--full", action="store_true", help="全ベンチマーク実行")
    
    args = parser.parse_args()
    
    benchmark = PerformanceBenchmark()
    
    if args.full:
        benchmark.benchmark_comparison()
    elif args.basic:
        benchmark.test_celery_basic()
    elif args.concurrent:
        benchmark.test_concurrent_tasks(args.concurrent)
    elif args.image:
        benchmark.test_image_chunk_performance()
    else:
        parser.print_help()
        print("\n💡 おすすめ:")
        print("  全ベンチマーク実行: python performance_benchmark.py --full")
        print("  基本テスト: python performance_benchmark.py --basic")
        print("  並列テスト: python performance_benchmark.py --concurrent 10")
        print("  画像処理テスト: python performance_benchmark.py --image")

if __name__ == "__main__":
    main() 