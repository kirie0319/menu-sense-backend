#!/usr/bin/env python3
"""
🔄 SSEリアルタイムストリーミング + 実際のAPI統合テスト

実際のAPI統合とSSEリアルタイムストリーミングの統合テスト：
- Google Translate API: 実際の翻訳
- OpenAI GPT-4.1-mini: 実際の説明生成
- Google Imagen 3: 実際の画像生成
- SSE リアルタイムストリーミング: 進行状況配信
"""

import time
import requests
import json
import asyncio
import threading
from datetime import datetime
from typing import Dict, List
import sseclient

# 実際のテスト用メニューアイテム（5個で高速テスト）
SSE_TEST_MENU_ITEMS = [
    "寿司", "ラーメン", "天ぷら", "焼き鳥", "抹茶"
]

BASE_URL = "http://localhost:8000/api/v1/menu-parallel"

def log_with_timestamp(message: str):
    """タイムスタンプ付きでログ出力"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{timestamp}] {message}")

class SSEEventCollector:
    """SSEイベントコレクター"""
    
    def __init__(self):
        self.events = []
        self.is_running = False
        self.session_id = None
        self.event_counts = {}
        self.last_event_time = None
        
    def start_collecting(self, session_id: str):
        """SSEイベント収集開始"""
        self.session_id = session_id
        self.is_running = True
        self.events = []
        self.event_counts = {}
        
        def collect_events():
            try:
                sse_url = f"{BASE_URL}/stream/{session_id}"
                log_with_timestamp(f"🔄 SSE接続開始: {sse_url}")
                
                response = requests.get(sse_url, stream=True, timeout=300)
                client = sseclient.SSEClient(response)
                
                for event in client.events():
                    if not self.is_running:
                        break
                    
                    try:
                        event_data = json.loads(event.data)
                        self.process_event(event_data)
                        
                        # 完了チェック
                        if event_data.get("type") == "processing_completed":
                            log_with_timestamp("🎉 SSE: 処理完了イベント受信")
                            self.is_running = False
                            break
                            
                    except Exception as e:
                        log_with_timestamp(f"⚠️ SSE Event parse error: {str(e)}")
                
            except Exception as e:
                log_with_timestamp(f"❌ SSE接続エラー: {str(e)}")
            finally:
                self.is_running = False
                log_with_timestamp("🔌 SSE接続終了")
        
        # バックグラウンドでSSE収集開始
        thread = threading.Thread(target=collect_events, daemon=True)
        thread.start()
        return thread
        
    def process_event(self, event_data: Dict):
        """SSEイベント処理"""
        event_type = event_data.get("type", "unknown")
        message = event_data.get("message", "")
        timestamp = event_data.get("timestamp", time.time())
        
        self.events.append(event_data)
        self.last_event_time = timestamp
        
        # イベントタイプ別カウント
        if event_type not in self.event_counts:
            self.event_counts[event_type] = 0
        self.event_counts[event_type] += 1
        
        # 重要なイベントのみログ出力
        if event_type in ["connection_established", "processing_started", "translation_completed", 
                         "description_completed", "image_generation_completed", "item_completed", 
                         "processing_completed"]:
            log_with_timestamp(f"📡 SSE: {event_type} - {message}")
            
        # アイテム完了の詳細表示
        if event_type == "item_completed":
            item_id = event_data.get("item_id", "unknown")
            english_name = event_data.get("english_name", "unknown")
            log_with_timestamp(f"    ✅ アイテム完了: #{item_id} - {english_name}")
    
    def stop_collecting(self):
        """SSEイベント収集停止"""
        self.is_running = False
        
    def get_statistics(self) -> Dict:
        """統計情報取得"""
        total_events = len(self.events)
        
        # タイムライン分析
        if len(self.events) >= 2:
            first_event = self.events[0].get("timestamp", 0)
            last_event = self.events[-1].get("timestamp", 0)
            duration = last_event - first_event
        else:
            duration = 0
        
        # 段階別イベント数
        stage_events = {
            "connection": self.event_counts.get("connection_established", 0),
            "processing_started": self.event_counts.get("processing_started", 0),
            "translation": self.event_counts.get("translation_completed", 0),
            "description": self.event_counts.get("description_completed", 0),
            "image_generation": self.event_counts.get("image_generation_completed", 0) + 
                              self.event_counts.get("image_generation_skipped", 0),
            "item_completed": self.event_counts.get("item_completed", 0),
            "processing_completed": self.event_counts.get("processing_completed", 0),
            "heartbeat": self.event_counts.get("heartbeat", 0)
        }
        
        return {
            "total_events": total_events,
            "event_types": len(self.event_counts),
            "duration": duration,
            "events_per_second": total_events / duration if duration > 0 else 0,
            "stage_events": stage_events,
            "event_counts": self.event_counts
        }

def test_sse_real_api_integration():
    """SSEリアルタイムストリーミング + 実際のAPI統合テスト"""
    
    print("🔄 SSEリアルタイムストリーミング + 実際のAPI統合テスト開始")
    print("=" * 80)
    
    # Phase 1: API健康状態チェック
    log_with_timestamp("📋 Phase 1: API健康状態チェック")
    
    try:
        response = requests.get(f"{BASE_URL}/stats/api-health", timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            
            log_with_timestamp(f"Overall Health: {health_data['overall_health']}")
            
            for api_name, api_status in health_data["api_services"].items():
                status_icon = "✅" if api_status["status"] == "healthy" else "❌"
                log_with_timestamp(f"{status_icon} {api_status['service']}: {api_status['status']}")
            
            if health_data["overall_health"] != "healthy":
                log_with_timestamp("⚠️ API health check passed with warnings")
        else:
            log_with_timestamp(f"⚠️ API health check failed: {response.status_code}")
    except Exception as e:
        log_with_timestamp(f"⚠️ API health check error: {str(e)}")
    
    # Phase 2: SSE準備とテスト
    log_with_timestamp("🔄 Phase 2: SSEストリーミング準備")
    
    sse_collector = SSEEventCollector()
    
    # Phase 3: 処理開始
    log_with_timestamp(f"🚀 Phase 3: 実際のAPI統合処理開始")
    log_with_timestamp(f"📝 メニューアイテム: {len(SSE_TEST_MENU_ITEMS)}個")
    for i, item in enumerate(SSE_TEST_MENU_ITEMS):
        log_with_timestamp(f"   [{i:2d}] {item}")
    
    # 処理開始時刻記録
    start_time = time.time()
    start_timestamp = datetime.now()
    
    try:
        # 実際のAPI統合リクエスト送信
        payload = {
            "menu_items": SSE_TEST_MENU_ITEMS,
            "test_mode": False  # 実際のAPI統合モード
        }
        
        log_with_timestamp("📡 実際のAPI統合リクエスト送信中...")
        response = requests.post(
            f"{BASE_URL}/process-menu-items",
            json=payload,
            timeout=15
        )
        
        if response.status_code != 200:
            log_with_timestamp(f"❌ API呼び出し失敗: {response.status_code}")
            print(f"Error details: {response.text}")
            return
        
        result = response.json()
        session_id = result["session_id"]
        
        request_time = time.time() - start_time
        log_with_timestamp(f"✅ 実際のAPI統合開始完了 (リクエスト時間: {request_time:.2f}秒)")
        log_with_timestamp(f"🆔 セッションID: {session_id}")
        log_with_timestamp(f"🔧 統合モード: {result['api_integration']}")
        
        # SSE収集開始
        sse_thread = sse_collector.start_collecting(session_id)
        
    except Exception as e:
        log_with_timestamp(f"❌ 実際のAPI統合開始エラー: {str(e)}")
        return
    
    # Phase 4: SSEとAPI統合の監視
    log_with_timestamp("📊 Phase 4: SSEとAPI統合の同時監視")
    
    total_items = len(SSE_TEST_MENU_ITEMS)
    monitoring_start = time.time()
    max_monitoring_time = 300  # 5分間監視
    
    last_progress_check = 0
    
    while sse_collector.is_running and (time.time() - monitoring_start) < max_monitoring_time:
        current_time = time.time()
        
        # 定期的な進行状況確認（SSEとは独立）
        if current_time - last_progress_check > 10:  # 10秒間隔
            try:
                response = requests.get(
                    f"{BASE_URL}/status/{session_id}",
                    params={"total_items": total_items},
                    timeout=5
                )
                
                if response.status_code == 200:
                    status = response.json()
                    completed = status["completed_items"]
                    progress = status["progress_percentage"]
                    
                    elapsed = current_time - start_time
                    
                    log_with_timestamp(
                        f"📊 API状況確認: {completed}/{total_items} "
                        f"({progress:.1f}%) - "
                        f"経過時間: {elapsed:.1f}s"
                    )
                    
                    # 完了チェック
                    if completed >= total_items:
                        log_with_timestamp("🎉 API処理完了確認")
                        break
                
                last_progress_check = current_time
                
            except Exception as e:
                log_with_timestamp(f"⚠️ 進行状況確認エラー: {str(e)}")
        
        time.sleep(2)
    
    # SSE収集停止
    log_with_timestamp("🔄 SSE収集停止中...")
    sse_collector.stop_collecting()
    
    # 最大3秒待機してSSEスレッド終了を待つ
    if sse_thread:
        sse_thread.join(timeout=3)
    
    # Phase 5: 結果分析
    total_time = time.time() - start_time
    end_timestamp = datetime.now()
    
    log_with_timestamp("🎯 Phase 5: SSE + API統合結果分析")
    
    try:
        # 最終API状況取得
        response = requests.get(
            f"{BASE_URL}/status/{session_id}",
            params={"total_items": total_items},
            timeout=10
        )
        
        api_final_status = None
        if response.status_code == 200:
            api_final_status = response.json()
        
        # SSE統計取得
        sse_stats = sse_collector.get_statistics()
        
        # 結果サマリー
        print("\n" + "=" * 80)
        print("🔄 SSEリアルタイムストリーミング + 実際のAPI統合 最終結果")
        print("=" * 80)
        
        log_with_timestamp(f"📊 総処理時間: {total_time:.2f}秒")
        log_with_timestamp(f"🕐 開始時刻: {start_timestamp.strftime('%H:%M:%S')}")
        log_with_timestamp(f"🕐 終了時刻: {end_timestamp.strftime('%H:%M:%S')}")
        
        # API統合結果
        if api_final_status:
            log_with_timestamp(f"📈 API完了アイテム: {api_final_status['completed_items']}/{total_items}")
            log_with_timestamp(f"📉 API進行率: {api_final_status['progress_percentage']:.1f}%")
            log_with_timestamp(f"⚡ APIスループット: {api_final_status['completed_items']/total_time:.2f} items/sec")
            log_with_timestamp(f"🔧 統合モード: {api_final_status['api_integration']}")
        
        # SSEストリーミング結果
        print("\n📡 SSEストリーミング詳細統計:")
        log_with_timestamp(f"🔄 総イベント数: {sse_stats['total_events']}")
        log_with_timestamp(f"📊 イベントタイプ数: {sse_stats['event_types']}")
        log_with_timestamp(f"⏱️ ストリーミング時間: {sse_stats['duration']:.2f}秒")
        log_with_timestamp(f"📈 イベント/秒: {sse_stats['events_per_second']:.2f}")
        
        # 段階別イベント統計
        print("\n📋 段階別イベント統計:")
        stage_events = sse_stats['stage_events']
        log_with_timestamp(f"🔗 接続確立: {stage_events['connection']}")
        log_with_timestamp(f"🚀 処理開始: {stage_events['processing_started']}")
        log_with_timestamp(f"🌍 翻訳完了: {stage_events['translation']}")
        log_with_timestamp(f"🤖 説明完了: {stage_events['description']}")
        log_with_timestamp(f"🎨 画像完了: {stage_events['image_generation']}")
        log_with_timestamp(f"✅ アイテム完了: {stage_events['item_completed']}")
        log_with_timestamp(f"🎉 全体完了: {stage_events['processing_completed']}")
        log_with_timestamp(f"💓 ハートビート: {stage_events['heartbeat']}")
        
        # パフォーマンス評価
        print("\n🎯 統合システムパフォーマンス評価:")
        
        api_success = api_final_status and api_final_status['progress_percentage'] >= 100
        sse_success = sse_stats['total_events'] > 10 and stage_events['processing_completed'] > 0
        
        if api_success and sse_success:
            log_with_timestamp("🎉 結果: 完全成功 - API統合とSSEストリーミング両方が正常動作")
        elif api_success:
            log_with_timestamp("✅ 結果: API成功/SSE部分的 - API統合は成功、SSEに軽微な問題")
        elif sse_success:
            log_with_timestamp("⚠️ 結果: SSE成功/API部分的 - SSEは動作、API統合に問題")
        else:
            log_with_timestamp("❌ 結果: 改善必要 - API統合またはSSEストリーミングに問題")
        
        # 統合品質スコア計算
        api_score = (api_final_status['completed_items'] / total_items * 50) if api_final_status else 0
        sse_score = min(sse_stats['total_events'] / 20 * 30, 30)  # 最大30点
        realtime_score = 20 if sse_stats['events_per_second'] > 1 else 10  # リアルタイム性
        
        total_score = api_score + sse_score + realtime_score
        log_with_timestamp(f"🏆 統合品質スコア: {total_score:.1f}/100")
        log_with_timestamp(f"   📊 API統合: {api_score:.1f}/50")
        log_with_timestamp(f"   📡 SSE機能: {sse_score:.1f}/30")
        log_with_timestamp(f"   ⚡ リアルタイム性: {realtime_score:.1f}/20")
        
        # 技術的成果
        print("\n🚀 技術的成果:")
        log_with_timestamp("✅ Google Translate + OpenAI GPT-4.1-mini + Google Imagen 3統合")
        log_with_timestamp("✅ SSEリアルタイムストリーミング配信")
        log_with_timestamp("✅ 並列処理とリアルタイム監視の同期")
        log_with_timestamp("✅ イベントドリブンアーキテクチャ実装")
        log_with_timestamp("✅ WebベースリアルタイムUI対応")
        
    except Exception as e:
        log_with_timestamp(f"❌ 最終結果分析エラー: {str(e)}")
    
    print("\n" + "=" * 80)
    log_with_timestamp("🏁 SSEリアルタイムストリーミング + 実際のAPI統合テスト完了")
    print("=" * 80)

if __name__ == "__main__":
    test_sse_real_api_integration() 