"""
Test Runner for Pipeline and SSE
実行用シンプルスクリプト
"""
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加
current_dir = Path(__file__).parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

# 環境変数も設定
os.environ.setdefault('PYTHONPATH', str(project_root))

def main():
    print("🧪 Menu Processor v2 テストランナー")
    print("=" * 50)
    
    print("\n選択してください:")
    print("1. Pipeline テスト")
    print("2. SSE受信テスト") 
    print("3. Pipeline + SSE統合テスト")
    
    choice = input("\n選択 (1/2/3): ").strip()
    
    try:
        if choice == "1":
            print("\n🚀 Pipeline テスト開始...")
            from scripts.test_pipeline import test_pipeline_with_image
            import asyncio
            asyncio.run(test_pipeline_with_image())
            
        elif choice == "2":
            print("\n📡 SSE受信テスト開始...")
            from scripts.test_sse_subscriber import test_sse_manual_mode
            import asyncio
            asyncio.run(test_sse_manual_mode())
            
        elif choice == "3":
            print("\n🔄 統合テスト開始...")
            from scripts.test_sse_subscriber import test_pipeline_and_sse
            import asyncio
            asyncio.run(test_pipeline_and_sse())
            
        else:
            print("❌ 無効な選択です")
            
    except ImportError as e:
        print(f"❌ インポートエラー: {e}")
        print("💡 必要な依存関係がインストールされていることを確認してください")
    except Exception as e:
        print(f"❌ テスト実行エラー: {e}")

if __name__ == "__main__":
    main() 