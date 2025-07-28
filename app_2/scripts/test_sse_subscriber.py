"""
SSE Subscriber Test Script
Pipeline RunnerからのSSEメッセージ受信をテストする
"""
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import json
from app_2.infrastructure.integrations.redis.redis_subscriber import RedisSubscriber
from app_2.utils.logger import get_logger

logger = get_logger("sse_test")


async def test_sse_subscription(session_id: str, duration: int = 60):
    """
    指定セッションのSSEメッセージを受信テスト
    
    Args:
        session_id: 監視するセッションID
        duration: 監視時間（秒）
    """
    print(f"📡 SSE受信テスト開始")
    print(f"🆔 セッションID: {session_id}")
    print(f"⏰ 監視時間: {duration}秒")
    print("-" * 50)
    
    subscriber = RedisSubscriber()
    message_count = 0
    
    try:
        # セッション専用チャンネルを購読
        await subscriber.subscribe_to_session(session_id)
        print(f"✅ セッションチャンネル購読開始")
        
        # メッセージ受信ループ
        async def listen_with_timeout():
            nonlocal message_count
            async for message in subscriber.listen_for_messages():
                message_count += 1
                print(f"\n📨 メッセージ #{message_count} 受信:")
                print(f"   タイプ: {message.get('type', 'unknown')}")
                print(f"   セッション: {message.get('session_id', 'unknown')}")
                
                # メッセージタイプ別の詳細表示
                if message.get('type') == 'progress_update':
                    data = message.get('data', {})
                    print(f"   タスク: {data.get('task_name', 'unknown')}")
                    print(f"   ステータス: {data.get('status', 'unknown')}")
                    if 'progress' in data.get('progress_data', {}):
                        print(f"   進捗: {data['progress_data']['progress']}%")
                
                elif message.get('type') == 'menu_update':
                    data = message.get('data', {})
                    print(f"   メニューID: {data.get('menu_id', 'unknown')}")
                    if 'menu_data' in data:
                        menu_data = data['menu_data']
                        if 'menu_items_count' in menu_data:
                            print(f"   アイテム数: {menu_data['menu_items_count']}")
                        if 'categories_found' in menu_data:
                            print(f"   カテゴリ: {menu_data['categories_found']}")
                
                elif message.get('type') == 'error':
                    data = message.get('data', {})
                    print(f"   エラー: {data.get('error_message', 'unknown')}")
                
                print(f"   タイムスタンプ: {message.get('timestamp', 'unknown')}")
                print("-" * 30)
        
        # タイムアウト付きでメッセージ受信
        try:
            await asyncio.wait_for(listen_with_timeout(), timeout=duration)
        except asyncio.TimeoutError:
            print(f"⏰ {duration}秒経過、監視終了")
        
    except Exception as e:
        logger.error(f"SSE subscription test failed: {e}")
        print(f"❌ SSE受信テスト失敗: {e}")
    
    finally:
        await subscriber.cleanup()
        print(f"\n📊 受信結果:")
        print(f"   総メッセージ数: {message_count}")
        print(f"   購読終了")


async def test_sse_manual_mode():
    """手動モード：セッションIDを手動入力"""
    print("🔧 手動SSEテストモード")
    session_id = input("セッションID を入力してください: ").strip()
    
    if not session_id:
        print("❌ セッションIDが入力されていません")
        return
    
    duration = input("監視時間（秒、デフォルト60秒）: ").strip()
    try:
        duration = int(duration) if duration else 60
    except ValueError:
        duration = 60
    
    await test_sse_subscription(session_id, duration)


async def test_pipeline_and_sse():
    """Pipeline実行 + SSE受信の統合テスト"""
    import uuid
    from pathlib import Path
    from app_2.pipelines.pipeline_runner import get_menu_processing_pipeline
    
    print("🔄 Pipeline + SSE統合テスト")
    
    # テスト用画像確認
    test_image_path = Path(__file__).parent.parent / "tests" / "data" / "menu_test.webp"
    if not test_image_path.exists():
        print(f"❌ テスト画像が見つかりません: {test_image_path}")
        return
    
    # セッションID生成
    session_id = str(uuid.uuid4())
    print(f"🆔 生成セッションID: {session_id}")
    
    # SSE受信を別タスクで開始
    sse_task = asyncio.create_task(
        test_sse_subscription(session_id, duration=120)  # 2分間監視
    )
    
    # 少し待ってからPipeline実行
    await asyncio.sleep(2)
    
    try:
        # 画像データ読み込み
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"\n🚀 Pipeline実行開始...")
        
        # パイプライン実行
        pipeline = get_menu_processing_pipeline()
        result = await pipeline.process_menu_image(
            session_id=session_id,
            image_data=image_data,
            filename=test_image_path.name
        )
        
        print(f"✅ Pipeline実行完了: {result['status']}")
        
        # SSEメッセージをさらに待機
        print("📡 SSEメッセージをさらに30秒待機...")
        await asyncio.sleep(30)
        
    except Exception as e:
        print(f"❌ 統合テスト失敗: {e}")
    
    finally:
        # SSEタスクをキャンセル
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    print("=" * 60)
    print("📡 SSE Subscriber テストスイート")
    print("=" * 60)
    
    print("\n選択してください:")
    print("1. 手動SSEテスト（セッションID入力）")
    print("2. Pipeline + SSE統合テスト")
    
    choice = input("\n選択 (1/2): ").strip()
    
    async def run_sse_tests():
        if choice == "1":
            await test_sse_manual_mode()
        elif choice == "2":
            await test_pipeline_and_sse()
        else:
            print("❌ 無効な選択です")
    
    try:
        asyncio.run(run_sse_tests())
        print("\n🎉 SSEテスト完了!")
    except KeyboardInterrupt:
        print("\n⏹️ テスト中断")
    except Exception as e:
        print(f"\n�� SSEテストエラー: {e}") 