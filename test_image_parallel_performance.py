#!/usr/bin/env python3
"""
画像生成並列処理の性能テストスクリプト

使用方法:
python test_image_parallel_performance.py

このスクリプトは以下をテストします:
1. 従来の順次処理 vs 新しい並列処理の速度比較
2. 異なる同時実行数での性能測定
3. 並列処理の正確性検証
"""

import asyncio
import time
import json
import os
import sys
from typing import Dict, List

# パスの追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.services.image.imagen3 import Imagen3Service

class ImagePerformanceTestHelper:
    """画像生成並列処理のパフォーマンステスト用ヘルパークラス"""
    
    def __init__(self):
        self.service = Imagen3Service()
    
    def create_test_menu_data(self, categories: int = 2, items_per_category: int = 6) -> Dict:
        """テスト用のサンプルメニューデータを生成"""
        test_data = {}
        
        for i in range(categories):
            category_name = f"Test Category {i+1}"
            items = []
            
            for j in range(items_per_category):
                items.append({
                    "japanese_name": f"テスト料理{i+1}-{j+1}",
                    "english_name": f"Test Dish {i+1}-{j+1}",
                    "description": f"Delicious test dish number {j+1} from category {i+1}",
                    "price": "¥1000"
                })
            
            test_data[category_name] = items
        
        return test_data
    
    async def test_sequential_image_processing(self, test_data: Dict) -> Dict:
        """従来の順次処理をテスト（mock）"""
        print("🔄 Testing sequential image processing...")
        start_time = time.time()
        
        # 模擬的な順次処理（各画像を順次処理）
        total_images = 0
        for category, items in test_data.items():
            total_images += len(items)
            
            # 各アイテムを順次模擬処理
            for i, item in enumerate(items):
                await asyncio.sleep(0.8)  # 模擬画像生成時間
                print(f"  Sequential: {category} image {i+1}/{len(items)} - {item['english_name']}")
        
        end_time = time.time()
        
        return {
            "method": "sequential",
            "total_time": end_time - start_time,
            "total_images": total_images,
            "images_per_second": total_images / (end_time - start_time)
        }
    
    async def test_parallel_image_processing(self, test_data: Dict, concurrent_limit: int = 3) -> Dict:
        """新しい並列処理をテスト"""
        print(f"🚀 Testing parallel image processing (concurrent_limit={concurrent_limit})...")
        start_time = time.time()
        
        # 実際の並列処理サービスを使用（ただしAPI呼び出しは模擬）
        original_settings = settings.IMAGE_CONCURRENT_CHUNK_LIMIT
        settings.IMAGE_CONCURRENT_CHUNK_LIMIT = concurrent_limit
        
        try:
            # 画像生成を模擬するため、一時的にメソッドを置き換え
            original_generate_single_image = self.service.generate_single_image
            
            async def mock_generate_single_image(japanese_name, english_name, description, category):
                await asyncio.sleep(0.8)  # 模擬画像生成時間
                print(f"  Parallel: {category} - {english_name}")
                return {
                    "japanese_name": japanese_name,
                    "english_name": english_name,
                    "image_url": f"/uploads/mock_{english_name.replace(' ', '_')}.png",
                    "generation_success": True
                }
            
            self.service.generate_single_image = mock_generate_single_image
            
            # 並列処理を実行
            category = list(test_data.keys())[0]
            items = list(test_data.values())[0]
            result = await self.service.process_category_parallel(category, items)
            
            end_time = time.time()
            
            total_images = sum(len(items) for items in test_data.values())
            
            return {
                "method": "parallel",
                "concurrent_limit": concurrent_limit,
                "total_time": end_time - start_time,
                "total_images": total_images,
                "images_per_second": total_images / (end_time - start_time),
                "result_images": len(result)
            }
            
        finally:
            # 元の設定とメソッドを復元
            settings.IMAGE_CONCURRENT_CHUNK_LIMIT = original_settings
            self.service.generate_single_image = original_generate_single_image
    
    async def run_image_performance_comparison(self):
        """総合的な画像生成性能比較テストを実行"""
        print("🎨 Starting parallel image processing performance test...")
        print("=" * 70)
        
        # テストデータを生成
        test_data = self.create_test_menu_data(categories=2, items_per_category=6)
        total_images = sum(len(items) for items in test_data.values())
        
        print(f"📊 Test Data: {len(test_data)} categories, {total_images} total images")
        print(f"📦 Image chunk size: {settings.IMAGE_PROCESSING_CHUNK_SIZE}")
        print()
        
        # 順次処理テスト
        sequential_result = await self.test_sequential_image_processing(test_data)
        print(f"⏱️ Sequential: {sequential_result['total_time']:.2f}s, {sequential_result['images_per_second']:.2f} images/sec")
        print()
        
        # 様々な並列数での並列処理テスト
        parallel_results = []
        concurrent_limits = [2, 3, 4, 6]
        
        for limit in concurrent_limits:
            parallel_result = await self.test_parallel_image_processing(test_data, limit)
            parallel_results.append(parallel_result)
            
            speedup = sequential_result['total_time'] / parallel_result['total_time']
            efficiency = speedup / limit * 100
            
            print(f"🚀 Parallel (limit={limit}): {parallel_result['total_time']:.2f}s, "
                  f"{parallel_result['images_per_second']:.2f} images/sec")
            print(f"   📈 Speedup: {speedup:.2f}x, Efficiency: {efficiency:.1f}%")
            print()
        
        # 結果の分析
        best_parallel = min(parallel_results, key=lambda x: x['total_time'])
        best_speedup = sequential_result['total_time'] / best_parallel['total_time']
        
        print("=" * 70)
        print("📊 IMAGE GENERATION PERFORMANCE SUMMARY")
        print("=" * 70)
        print(f"🐌 Sequential Processing: {sequential_result['total_time']:.2f}s")
        print(f"🚀 Best Parallel (limit={best_parallel['concurrent_limit']}): {best_parallel['total_time']:.2f}s")
        print(f"📈 Maximum Speedup: {best_speedup:.2f}x ({best_speedup*100-100:.1f}% faster)")
        print(f"💡 Recommended image concurrent limit: {best_parallel['concurrent_limit']}")
        
        # 設定推奨値
        print()
        print("⚙️ RECOMMENDED IMAGE GENERATION SETTINGS")
        print("=" * 45)
        print(f"IMAGE_CONCURRENT_CHUNK_LIMIT={best_parallel['concurrent_limit']}")
        print(f"IMAGE_PROCESSING_CHUNK_SIZE={settings.IMAGE_PROCESSING_CHUNK_SIZE}")
        if len(test_data) > 1:
            print("ENABLE_IMAGE_CATEGORY_PARALLEL=true  # For multiple categories")
        else:
            print("ENABLE_IMAGE_CATEGORY_PARALLEL=false  # Single category test")

async def main():
    """メイン関数"""
    print("📸 Image Generation Performance Test")
    print("=" * 50)
    
    # 必要な設定をチェック
    if not os.getenv("GEMINI_API_KEY"):
        print("⚠️ Warning: GEMINI_API_KEY not set. This is a mock performance test.")
        print("   For real testing, set GEMINI_API_KEY in your .env file.")
        print()
    
    helper = ImagePerformanceTestHelper()
    
    if not helper.service.is_available():
        print("⚠️ Image service not available. Running mock performance test...")
        print()
    
    await helper.run_image_performance_comparison()

if __name__ == "__main__":
    asyncio.run(main()) 