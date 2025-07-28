"""
SSE Client Test Script
SSEエンドポイントの動作テスト用スクリプト
"""

import asyncio
import httpx
import json
from typing import AsyncGenerator

# ==========================================
# Python SSE Client Example
# ==========================================

class SSEClient:
    """Python SSE クライアント"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        
    async def listen_to_session(self, session_id: str, duration: int = 60):
        """
        セッションのSSEストリームを受信
        
        Args:
            session_id: セッションID
            duration: 受信時間（秒）
        """
        url = f"{self.base_url}/api/v1/sse/stream/{session_id}"
        
        print(f"🚀 SSE接続開始: {url}")
        print(f"⏰ 受信時間: {duration}秒")
        print("-" * 60)
        
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as response:
                    if response.status_code != 200:
                        print(f"❌ 接続失敗: {response.status_code}")
                        return
                    
                    print("✅ SSE接続成功")
                    
                    # タイムアウト付きでメッセージ受信
                    try:
                        async for chunk in response.aiter_bytes():
                            chunk_str = chunk.decode('utf-8')
                            
                            # SSEメッセージをパース
                            for message in self._parse_sse_message(chunk_str):
                                await self._handle_message(message)
                                
                    except asyncio.TimeoutError:
                        print(f"⏰ {duration}秒経過、接続終了")
                        
        except Exception as e:
            print(f"❌ SSE接続エラー: {e}")
    
    def _parse_sse_message(self, chunk: str) -> list:
        """SSEメッセージをパース"""
        messages = []
        
        if not chunk.strip():
            return messages
            
        # SSE形式のパース
        lines = chunk.strip().split('\n')
        current_message = {}
        
        for line in lines:
            if line.startswith('event:'):
                current_message['event'] = line[6:].strip()
            elif line.startswith('data:'):
                try:
                    data_str = line[5:].strip()
                    current_message['data'] = json.loads(data_str)
                    messages.append(current_message)
                    current_message = {}
                except json.JSONDecodeError:
                    current_message['data'] = data_str
                    
        return messages
    
    async def _handle_message(self, message: dict):
        """受信メッセージの処理"""
        event_type = message.get('event', 'unknown')
        data = message.get('data', {})
        
        print(f"\n📨 {event_type.upper()}")
        
        if event_type == 'connection_established':
            print(f"   ✅ 接続確立: {data.get('connection_id', 'unknown')}")
            print(f"   📊 アクティブ接続数: {data.get('active_connections', 0)}")
            
        elif event_type == 'stage_completed':
            stage_data = data.get('data', {})
            stage = stage_data.get('stage', 'unknown')
            print(f"   🎯 段階完了: {stage}")
            
            # 段階別詳細表示
            if stage == 'ocr':
                completion_data = stage_data.get('completion_data', {})
                print(f"   📝 抽出要素数: {completion_data.get('elements_extracted', 0)}")
            elif stage == 'mapping':
                completion_data = stage_data.get('completion_data', {})
                print(f"   🗺️ データサイズ: {completion_data.get('formatted_data_length', 0)}")
            elif stage == 'categorize':
                completion_data = stage_data.get('completion_data', {})
                print(f"   📂 カテゴリ数: {completion_data.get('total_categories', 0)}")
                print(f"   🍽️ メニュー数: {completion_data.get('total_menu_items', 0)}")
                
        elif event_type == 'menu_update':
            menu_data = data.get('data', {})
            print(f"   🍽️ メニュー更新: {menu_data.get('item_id', 'unknown')}")
            print(f"   📝 名前: {menu_data.get('original_name', 'unknown')}")
            
            # タスク別詳細表示
            task_type = menu_data.get('task_type', 'unknown')
            if task_type == 'translation':
                print(f"   🌍 翻訳: {menu_data.get('translation', 'N/A')}")
            elif task_type == 'description':
                print(f"   📄 説明: {menu_data.get('description', 'N/A')[:50]}...")
            elif task_type == 'allergen':
                print(f"   🛡️ アレルギー: {menu_data.get('allergen_info', 'N/A')}")
            elif task_type == 'ingredient':
                print(f"   🥬 成分: {menu_data.get('ingredient_info', 'N/A')}")
                
        elif event_type == 'progress_update':
            progress_data = data.get('data', {})
            task_name = progress_data.get('task_name', 'unknown')
            status = progress_data.get('status', 'unknown')
            print(f"   ⏳ 進捗: {task_name} - {status}")
            
            if 'progress_data' in progress_data:
                progress = progress_data['progress_data'].get('progress', 0)
                print(f"   📊 完了率: {progress}%")
                
        elif 'batch_completed' in event_type:
            batch_data = data.get('data', {})
            task_type = batch_data.get('task_type', 'unknown')
            completed = batch_data.get('completed_items', 0)
            total = batch_data.get('total_items', 0)
            success_rate = batch_data.get('success_rate', 0)
            
            print(f"   ✅ {task_type}バッチ完了")
            print(f"   📊 成功率: {completed}/{total} ({success_rate}%)")
            
        elif event_type == 'error':
            error_data = data.get('data', {})
            print(f"   ❌ エラー: {error_data.get('error_message', 'unknown')}")
            
        else:
            print(f"   📋 データ: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        print("-" * 40)


# ==========================================
# Test Functions
# ==========================================

async def test_sse_connection(session_id: str = "test-session-123"):
    """SSE接続テスト"""
    client = SSEClient()
    await client.listen_to_session(session_id, duration=30)


async def test_sse_with_pipeline():
    """Pipeline + SSE統合テスト"""
    import uuid
    from pathlib import Path
    
    # セッションID生成
    session_id = str(uuid.uuid4())
    print(f"🆔 テストセッションID: {session_id}")
    
    # SSE受信を別タスクで開始
    client = SSEClient()
    sse_task = asyncio.create_task(
        client.listen_to_session(session_id, duration=120)
    )
    
    # 少し待ってからPipeline実行をシミュレート
    await asyncio.sleep(2)
    
    try:
        # テスト画像のパスを確認
        test_image_path = Path(__file__).parent.parent / "tests" / "data" / "menu_test.webp"
        
        if test_image_path.exists():
            print(f"🚀 Pipeline実行シミュレーション...")
            
            # Pipeline APIを呼び出し
            async with httpx.AsyncClient() as http_client:
                with open(test_image_path, 'rb') as f:
                    files = {"file": (test_image_path.name, f, "image/webp")}
                    
                    response = await http_client.post(
                        "http://localhost:8000/api/v1/pipeline/process",
                        files=files,
                        timeout=300
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        print(f"✅ Pipeline実行成功: {result['status']}")
                        print(f"📊 セッションID: {result['session_id']}")
                    else:
                        print(f"❌ Pipeline実行失敗: {response.status_code}")
        else:
            print(f"⚠️ テスト画像が見つかりません: {test_image_path}")
            
        # SSEメッセージをさらに待機
        print("📡 SSEメッセージを60秒待機...")
        await asyncio.sleep(60)
        
    except Exception as e:
        print(f"❌ 統合テスト失敗: {e}")
    
    finally:
        # SSEタスクをキャンセル
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass


# ==========================================
# JavaScript Example (for Frontend)
# ==========================================

javascript_example = '''
// JavaScript SSE Client Example

class SSEMenuProcessor {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.eventSource = null;
        this.callbacks = {};
    }
    
    // セッションのSSEストリームに接続
    connect(sessionId) {
        const url = `${this.baseUrl}/api/v1/sse/stream/${sessionId}`;
        
        this.eventSource = new EventSource(url);
        
        // 接続確立
        this.eventSource.addEventListener('connection_established', (event) => {
            const data = JSON.parse(event.data);
            console.log('✅ SSE接続確立:', data);
            this.trigger('connected', data);
        });
        
        // 段階完了
        this.eventSource.addEventListener('stage_completed', (event) => {
            const data = JSON.parse(event.data);
            const stage = data.data.stage;
            console.log(`🎯 ${stage}段階完了:`, data);
            this.trigger('stage_completed', { stage, data: data.data });
        });
        
        // メニュー更新
        this.eventSource.addEventListener('menu_update', (event) => {
            const data = JSON.parse(event.data);
            const menuData = data.data;
            console.log('🍽️ メニュー更新:', menuData);
            this.trigger('menu_updated', menuData);
        });
        
        // 進捗更新
        this.eventSource.addEventListener('progress_update', (event) => {
            const data = JSON.parse(event.data);
            console.log('⏳ 進捗更新:', data);
            this.trigger('progress', data.data);
        });
        
        // バッチ完了通知
        ['translation_batch_completed', 'description_batch_completed', 
         'allergen_batch_completed', 'ingredient_batch_completed',
         'search_image_batch_completed'].forEach(eventType => {
            this.eventSource.addEventListener(eventType, (event) => {
                const data = JSON.parse(event.data);
                console.log(`✅ ${eventType}:`, data);
                this.trigger('batch_completed', { type: eventType, data: data.data });
            });
        });
        
        // エラー処理
        this.eventSource.addEventListener('error', (event) => {
            const data = JSON.parse(event.data);
            console.error('❌ SSEエラー:', data);
            this.trigger('error', data.data);
        });
        
        this.eventSource.onerror = (error) => {
            console.error('❌ SSE接続エラー:', error);
            this.trigger('connection_error', error);
        };
    }
    
    // イベントリスナー登録
    on(event, callback) {
        if (!this.callbacks[event]) {
            this.callbacks[event] = [];
        }
        this.callbacks[event].push(callback);
    }
    
    // イベント発火
    trigger(event, data) {
        if (this.callbacks[event]) {
            this.callbacks[event].forEach(callback => callback(data));
        }
    }
    
    // 接続終了
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
}

// 使用例
const processor = new SSEMenuProcessor();

// イベントリスナー設定
processor.on('connected', (data) => {
    console.log('接続確立:', data);
});

processor.on('stage_completed', ({ stage, data }) => {
    console.log(`${stage}段階完了:`, data);
    // UIを更新
    updateStageProgress(stage, data);
});

processor.on('menu_updated', (menuData) => {
    console.log('メニュー更新:', menuData);
    // メニューリストを更新
    updateMenuList(menuData);
});

processor.on('batch_completed', ({ type, data }) => {
    console.log('バッチ完了:', type, data);
    // 完了通知を表示
    showCompletionNotification(type, data);
});

// 接続開始
processor.connect('your-session-id-here');

// ページ離脱時に接続終了
window.addEventListener('beforeunload', () => {
    processor.disconnect();
});
'''


# ==========================================
# Main Test Runner
# ==========================================

async def main():
    """メインテスト実行"""
    import sys
    
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        print(f"📡 SSE接続テスト - セッションID: {session_id}")
        await test_sse_connection(session_id)
    else:
        print("📋 利用可能なテスト:")
        print("1. SSE接続テスト: python test_sse_client.py <session_id>")
        print("2. Pipeline統合テスト: 以下のコードで実行")
        print("")
        print("await test_sse_with_pipeline()")
        print("")
        print("📝 JavaScript使用例:")
        print(javascript_example)


if __name__ == "__main__":
    asyncio.run(main()) 