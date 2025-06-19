#!/usr/bin/env python3
"""
Stage 1 OCR並列化テストスクリプト

段階的なOCR並列処理のテスト
- 基本機能テスト
- マルチエンジン並列OCRテスト
- 統合テスト
- パフォーマンス検証
"""

import asyncio
import time
import os
import sys

# プロジェクトルートをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

async def test_ocr_service_availability():
    """OCRサービスの利用可能性をテスト"""
    print("=== Stage 1 OCRサービス利用可能性テスト ===")
    
    try:
        from app.services.ocr.parallel import ParallelOCRService
        
        parallel_service = ParallelOCRService()
        is_available = parallel_service.is_available()
        
        print(f"✅ 並列OCRサービス: {'利用可能' if is_available else '利用不可'}")
        
        if is_available:
            print("   🎯 Gemini 2.0 Flash: OK")
            print("   🚀 並列処理準備: OK")
        else:
            print("   ❌ Gemini API接続エラーまたは設定不備")
        
        # 個別サービス確認
        from app.services.ocr.gemini import GeminiOCRService
        from app.services.ocr.google_vision import GoogleVisionOCRService
        
        gemini_service = GeminiOCRService()
        vision_service = GoogleVisionOCRService()
        
        print(f"   🎯 Gemini単体: {'利用可能' if gemini_service.is_available() else '利用不可'}")
        print(f"   👁️ Google Vision: {'利用可能' if vision_service.is_available() else '利用不可'}")
        
        return is_available
        
    except Exception as e:
        print(f"❌ サービス利用可能性テスト失敗: {e}")
        return False

def test_single_engine_workers():
    """単一エンジンOCRワーカーをテスト"""
    print("\n=== 単一エンジンOCRワーカーテスト ===")
    
    # テスト用の画像ファイルが必要
    test_image_path = "uploads/test_menu.jpg"  # 実際のテスト画像パスに変更
    
    if not os.path.exists(test_image_path):
        print(f"⚠️ テスト画像が見つかりません: {test_image_path}")
        print("   テスト用メニュー画像をuploadsフォルダに配置してください")
        return False
    
    try:
        from app.tasks.ocr_tasks import ocr_with_gemini, ocr_with_google_vision
        
        print(f"🔄 単一エンジンOCRワーカーテスト開始")
        print(f"   テスト画像: {test_image_path}")
        
        start_time = time.time()
        
        # Geminiワーカータスクをテスト
        print("   🎯 Gemini OCRワーカーテスト...")
        gemini_task = ocr_with_gemini.delay(test_image_path, "test-session")
        gemini_result = gemini_task.get(timeout=60)
        
        processing_time = time.time() - start_time
        
        if gemini_result['success']:
            print(f"   ✅ Gemini OCRワーカー成功!")
            print(f"      ⏱️  処理時間: {processing_time:.2f}秒")
            print(f"      📝 抽出文字数: {gemini_result['text_length']}")
            print(f"      🎯 エンジン: {gemini_result['engine']}")
            
            # 抽出テキストのサンプル表示
            extracted_text = gemini_result['extracted_text']
            preview = extracted_text[:100] + "..." if len(extracted_text) > 100 else extracted_text
            print(f"      📄 テキストプレビュー: {preview}")
            
            return True
        else:
            print(f"   ❌ Gemini OCRワーカー失敗: {gemini_result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ 単一エンジンワーカーテスト失敗: {e}")
        return False

async def test_parallel_ocr_basic():
    """基本的な並列OCRテスト"""
    print("\n=== 基本並列OCRテスト ===")
    
    # テスト用の画像ファイルが必要
    test_image_path = "uploads/test_menu.jpg"  # 実際のテスト画像パスに変更
    
    if not os.path.exists(test_image_path):
        print(f"⚠️ テスト画像が見つかりません: {test_image_path}")
        print("   テスト用メニュー画像をuploadsフォルダに配置してください")
        return False
    
    try:
        from app.services.ocr.parallel import extract_text_with_parallel
        
        print(f"🔄 並列OCRテスト開始")
        print(f"   テスト画像: {test_image_path}")
        
        start_time = time.time()
        
        # 並列OCRを実行
        result = await extract_text_with_parallel(test_image_path, "test-session")
        
        processing_time = time.time() - start_time
        
        if result.success:
            print(f"✅ 並列OCR基本テスト成功!")
            print(f"   ⏱️  処理時間: {processing_time:.2f}秒")
            print(f"   📝 抽出文字数: {len(result.extracted_text)}")
            print(f"   🎯 処理モード: {result.metadata.get('processing_mode', 'unknown')}")
            print(f"   🚀 並列処理: {'有効' if result.metadata.get('parallel_enabled', False) else '無効'}")
            
            # 使用されたエンジン情報
            if result.metadata.get('parallel_enabled'):
                selected_engine = result.metadata.get('selected_engine', 'unknown')
                engines_used = result.metadata.get('engines_used', [])
                print(f"   🎭 使用エンジン: {engines_used}")
                print(f"   🏆 選択エンジン: {selected_engine}")
                
                # 全結果の比較
                all_results = result.metadata.get('all_results', {})
                print(f"   📊 エンジン結果比較:")
                for engine, engine_result in all_results.items():
                    status = "✅ 成功" if engine_result['success'] else "❌ 失敗"
                    text_len = engine_result['text_length']
                    print(f"      {engine}: {status} ({text_len}文字)")
            
            # 抽出テキストのサンプル表示
            preview = result.extracted_text[:150] + "..." if len(result.extracted_text) > 150 else result.extracted_text
            print(f"   📄 テキストプレビュー: {preview}")
            
            return True
        else:
            print(f"❌ 並列OCR基本テスト失敗: {result.error}")
            return False
        
    except Exception as e:
        print(f"❌ 基本並列OCRテスト失敗: {e}")
        return False

def test_multi_engine_worker():
    """マルチエンジン並列OCRワーカーをテスト"""
    print("\n=== マルチエンジン並列OCRワーカーテスト ===")
    
    # テスト用の画像ファイルが必要
    test_image_path = "uploads/test_menu.jpg"  # 実際のテスト画像パスに変更
    
    if not os.path.exists(test_image_path):
        print(f"⚠️ テスト画像が見つかりません: {test_image_path}")
        return False
    
    try:
        from app.tasks.ocr_tasks import ocr_parallel_multi_engine
        
        print(f"🔄 マルチエンジン並列OCRワーカーテスト開始")
        
        start_time = time.time()
        
        # マルチエンジン並列OCRワーカーを実行
        task = ocr_parallel_multi_engine.delay(test_image_path, "test-session")
        
        # 結果を取得（タイムアウト120秒）
        result = task.get(timeout=120)
        
        processing_time = time.time() - start_time
        
        if result['success']:
            print(f"✅ マルチエンジン並列OCRワーカーテスト成功!")
            print(f"   ⏱️  処理時間: {processing_time:.2f}秒")
            print(f"   📝 抽出文字数: {result['text_length']}")
            print(f"   🏆 選択エンジン: {result.get('engine', 'unknown')}")
            print(f"   🚀 並列処理: {'有効' if result.get('parallel_processing', False) else '無効'}")
            
            # エンジン結果比較
            all_results = result.get('all_results', {})
            if all_results:
                print(f"   📊 エンジン結果比較:")
                for engine, engine_result in all_results.items():
                    status = "✅ 成功" if engine_result['success'] else "❌ 失敗"
                    text_len = engine_result['text_length']
                    error_info = f" ({engine_result.get('error', '')})" if not engine_result['success'] else ""
                    print(f"      {engine}: {status} ({text_len}文字){error_info}")
            
            # 選択理由
            selection_reason = result.get('selection_reason', '')
            if selection_reason:
                print(f"   🎯 選択理由: {selection_reason}")
            
            return True
        else:
            print(f"❌ マルチエンジン並列OCRワーカーテスト失敗: {result.get('error', 'Unknown error')}")
            return False
        
    except Exception as e:
        print(f"❌ マルチエンジン並列OCRワーカーテスト失敗: {e}")
        return False

async def run_all_stage1_tests():
    """全Stage 1 OCR並列化テストを実行"""
    print("🎯 Stage 1 OCR並列化テスト開始")
    print("=" * 60)
    
    # テスト結果追跡
    test_results = {}
    
    # 1. サービス利用可能性テスト
    test_results['service_availability'] = await test_ocr_service_availability()
    
    if not test_results['service_availability']:
        print("\n❌ OCRサービスが利用できないため、テストを中止します")
        return
    
    # 2. 単一エンジンワーカーテスト
    test_results['single_engine_worker'] = test_single_engine_workers()
    
    # 3. 基本並列OCRテスト
    test_results['parallel_ocr_basic'] = await test_parallel_ocr_basic()
    
    # 4. マルチエンジン並列OCRワーカーテスト
    test_results['multi_engine_worker'] = test_multi_engine_worker()
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("🎯 Stage 1 OCR並列化テスト結果サマリー")
    print("=" * 60)
    
    total_tests = len(test_results)
    passed_tests = sum(1 for result in test_results.values() if result)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        test_display_name = test_name.replace('_', ' ').title()
        print(f"{status} {test_display_name}")
    
    print(f"\n📊 テスト結果: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
    
    if passed_tests == total_tests:
        print("🎉 全テスト成功! Stage 1 OCR並列化は正常に動作しています")
    else:
        print("❌ 一部テスト失敗。設定やシステムを確認してください")
    
    return test_results

if __name__ == "__main__":
    # 設定情報表示
    print("🔧 Stage 1 OCR並列化設定:")
    print(f"   ENABLE_PARALLEL_OCR: {getattr(settings, 'ENABLE_PARALLEL_OCR', 'Not set')}")
    print(f"   PARALLEL_OCR_TIMEOUT: {getattr(settings, 'PARALLEL_OCR_TIMEOUT', 'Not set')}")
    print(f"   OCR_FALLBACK_ENABLED: {getattr(settings, 'OCR_FALLBACK_ENABLED', 'Not set')}")
    
    # テスト画像の確認
    test_image_path = "uploads/test_menu.jpg"
    if os.path.exists(test_image_path):
        print(f"   📁 テスト画像: {test_image_path} ✅")
    else:
        print(f"   📁 テスト画像: {test_image_path} ❌（見つかりません）")
        print("   📝 Note: テスト用メニュー画像をuploadsフォルダに配置してください")
    
    print()
    
    # 非同期テスト実行
    asyncio.run(run_all_stage1_tests()) 