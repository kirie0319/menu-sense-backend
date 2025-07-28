"""
Pipeline Runner Test Script
基本フロー（OCR → Categorize → DB Save → SSE）の動作確認用
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import uuid

from app_2.pipelines.pipeline_runner import get_menu_processing_pipeline
from app_2.utils.logger import get_logger

logger = get_logger("pipeline_test")


async def test_pipeline_with_image():
    """実画像を使ったパイプラインテスト"""
    
    # テスト用画像パス
    test_image_path = Path(__file__).parent.parent / "tests" / "data" / "menu_test.webp"
    
    if not test_image_path.exists():
        logger.error(f"Test image not found: {test_image_path}")
        print(f"❌ テスト画像が見つかりません: {test_image_path}")
        return
    
    print("🚀 Pipeline Runner テスト開始")
    print(f"📸 使用画像: {test_image_path.name}")
    
    # セッションID生成
    session_id = str(uuid.uuid4())
    print(f"🆔 セッションID: {session_id}")
    
    try:
        # 画像データ読み込み
        with open(test_image_path, 'rb') as f:
            image_data = f.read()
        
        print(f"📊 画像サイズ: {len(image_data)} bytes")
        
        # パイプライン実行
        pipeline = get_menu_processing_pipeline()
        result = await pipeline.process_menu_image(
            session_id=session_id,
            image_data=image_data,
            filename=test_image_path.name
        )
        
        # 結果表示
        print("\n✅ パイプライン実行完了!")
        print(f"📋 処理結果:")
        print(f"   - ステータス: {result['status']}")
        print(f"   - メニューアイテム数: {result['menu_items_count']}")
        print(f"   - OCR要素数: {result['ocr_elements']}")
        print(f"   - カテゴリ: {result['categories']}")
        print(f"   - 並列タスク開始: {result['parallel_tasks_triggered']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}")
        print(f"❌ パイプラインテスト失敗: {e}")
        raise


async def test_pipeline_simple():
    """シンプルなパイプラインテスト（ダミーデータ使用）"""
    
    print("🧪 シンプルパイプラインテスト開始")
    
    # ダミー画像データ（小さなサイズ）
    dummy_image_data = b"dummy_image_data_for_testing"
    session_id = str(uuid.uuid4())
    
    print(f"🆔 セッションID: {session_id}")
    
    try:
        pipeline = get_menu_processing_pipeline()
        
        # 注意: これは実際のOCR/Categorizeサービスを呼び出すので
        # Google Vision API/OpenAI APIが利用可能である必要があります
        result = await pipeline.process_menu_image(
            session_id=session_id,
            image_data=dummy_image_data,
            filename="test_dummy.jpg"
        )
        
        print("✅ シンプルテスト完了")
        return result
        
    except Exception as e:
        print(f"⚠️ シンプルテスト失敗（予想される）: {e}")
        # ダミーデータでは失敗が予想されます
        return None


if __name__ == "__main__":
    print("=" * 60)
    print("🔬 Pipeline Runner テストスイート")
    print("=" * 60)
    
    # テストメニュー
    print("\n選択してください:")
    print("1. 実画像テスト (menu_test.webp)")
    print("2. シンプルテスト (ダミーデータ)")
    print("3. 両方実行")
    
    choice = input("\n選択 (1/2/3): ").strip()
    
    async def run_tests():
        if choice == "1":
            await test_pipeline_with_image()
        elif choice == "2":
            await test_pipeline_simple()
        elif choice == "3":
            print("\n--- 実画像テスト ---")
            await test_pipeline_with_image()
            print("\n--- シンプルテスト ---")
            await test_pipeline_simple()
        else:
            print("❌ 無効な選択です")
    
    try:
        asyncio.run(run_tests())
        print("\n🎉 テスト完了!")
    except KeyboardInterrupt:
        print("\n⏹️ テスト中断")
    except Exception as e:
        print(f"\n💥 テストエラー: {e}") 