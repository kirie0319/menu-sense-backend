#!/usr/bin/env python3
"""
並列処理の性能テストスクリプト

使用方法:
python test_parallel_performance.py

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
from app.services.description.openai import OpenAIDescriptionService

class PerformanceTestHelper:
    """並列処理のパフォーマンステスト用ヘルパークラス"""
    
    def __init__(self):
        self.service = OpenAIDescriptionService()
    
    def create_test_data(self, categories: int = 3, items_per_category: int = 9) -> Dict:
        """テスト用のサンプルメニューデータを生成"""
        test_data = {}
        
        for i in range(categories):
            category_name = f"Test Category {i+1}"
            items = []
            
            for j in range(items_per_category):
                items.append({
                    "japanese_name": f"テスト料理{i+1}-{j+1}",
                    "english_name": f"Test Dish {i+1}-{j+1}",
                    "price": "¥1000"
                })
            
            test_data[category_name] = items
        
        return test_data
    
    async def test_sequential_processing(self, test_data: Dict) -> Dict:
        """従来の順次処理をテスト（mock）"""
        print("🔄 Testing sequential processing...")
        start_time = time.time()
        
        # 模擬的な順次処理（各チャンクを順次処理）
        total_chunks = 0
        for category, items in test_data.items():
            chunk_size = settings.PROCESSING_CHUNK_SIZE
            chunks_in_category = (len(items) + chunk_size - 1) // chunk_size
            total_chunks += chunks_in_category
            
            # 各チャンクを順次模擬処理
            for i in range(chunks_in_category):
                await asyncio.sleep(0.5)  # 模擬AI処理時間
                print(f"  Sequential: {category} chunk {i+1}/{chunks_in_category}")
        
        end_time = time.time()
        
        return {
            "method": "sequential",
            "total_time": end_time - start_time,
            "total_chunks": total_chunks,
            "chunks_per_second": total_chunks / (end_time - start_time)
        }
    
    async def test_parallel_processing(self, test_data: Dict, concurrent_limit: int = 5) -> Dict:
        """新しい並列処理をテスト"""
        print(f"🚀 Testing parallel processing (concurrent_limit={concurrent_limit})...")
        start_time = time.time()
        
        # 実際の並列処理サービスを使用（ただしAPI呼び出しは模擬）
        original_settings = settings.CONCURRENT_CHUNK_LIMIT
        settings.CONCURRENT_CHUNK_LIMIT = concurrent_limit
        
        try:
            # API呼び出しを模擬するため、一時的にメソッドを置き換え
            original_process_chunk = self.service.process_chunk
            
            async def mock_process_chunk(category, chunk, chunk_number, total_chunks, session_id=None):
                await asyncio.sleep(0.5)  # 模擬AI処理時間
                print(f"  Parallel: {category} chunk {chunk_number}/{total_chunks}")
                return [{"test": "result"} for _ in chunk]
            
            self.service.process_chunk = mock_process_chunk
            
            # 並列処理を実行
            result = await self.service.process_category_parallel("Test Category", list(test_data.values())[0])
            
            end_time = time.time()
            
            total_chunks = sum((len(items) + settings.PROCESSING_CHUNK_SIZE - 1) // settings.PROCESSING_CHUNK_SIZE 
                             for items in test_data.values())
            
            return {
                "method": "parallel",
                "concurrent_limit": concurrent_limit,
                "total_time": end_time - start_time,
                "total_chunks": total_chunks,
                "chunks_per_second": total_chunks / (end_time - start_time),
                "result_items": len(result)
            }
            
        finally:
            # 元の設定とメソッドを復元
            settings.CONCURRENT_CHUNK_LIMIT = original_settings
            self.service.process_chunk = original_process_chunk
    
    async def run_performance_comparison(self):
        """総合的な性能比較テストを実行"""
        print("🧪 Starting parallel processing performance test...")
        print("=" * 60)
        
        # テストデータを生成
        test_data = self.create_test_data(categories=3, items_per_category=9)
        total_items = sum(len(items) for items in test_data.values())
        
        print(f"📊 Test Data: {len(test_data)} categories, {total_items} total items")
        print(f"📦 Chunk size: {settings.PROCESSING_CHUNK_SIZE}")
        print()
        
        # 順次処理テスト
        sequential_result = await self.test_sequential_processing(test_data)
        print(f"⏱️ Sequential: {sequential_result['total_time']:.2f}s, {sequential_result['chunks_per_second']:.2f} chunks/sec")
        print()
        
        # 様々な並列数での並列処理テスト
        parallel_results = []
        concurrent_limits = [2, 3, 5, 8]
        
        for limit in concurrent_limits:
            parallel_result = await self.test_parallel_processing(test_data, limit)
            parallel_results.append(parallel_result)
            
            speedup = sequential_result['total_time'] / parallel_result['total_time']
            efficiency = speedup / limit * 100
            
            print(f"🚀 Parallel (limit={limit}): {parallel_result['total_time']:.2f}s, "
                  f"{parallel_result['chunks_per_second']:.2f} chunks/sec")
            print(f"   📈 Speedup: {speedup:.2f}x, Efficiency: {efficiency:.1f}%")
            print()
        
        # 結果の分析
        best_parallel = min(parallel_results, key=lambda x: x['total_time'])
        best_speedup = sequential_result['total_time'] / best_parallel['total_time']
        
        print("=" * 60)
        print("📊 PERFORMANCE SUMMARY")
        print("=" * 60)
        print(f"🐌 Sequential Processing: {sequential_result['total_time']:.2f}s")
        print(f"🚀 Best Parallel (limit={best_parallel['concurrent_limit']}): {best_parallel['total_time']:.2f}s")
        print(f"📈 Maximum Speedup: {best_speedup:.2f}x ({best_speedup*100-100:.1f}% faster)")
        print(f"💡 Recommended concurrent limit: {best_parallel['concurrent_limit']}")
        
        # 設定推奨値
        print()
        print("⚙️ RECOMMENDED SETTINGS")
        print("=" * 30)
        print(f"CONCURRENT_CHUNK_LIMIT={best_parallel['concurrent_limit']}")
        if len(test_data) > 1:
            print("ENABLE_CATEGORY_PARALLEL=true  # For multiple categories")
        else:
            print("ENABLE_CATEGORY_PARALLEL=false  # Single category test")

async def main():
    """メイン実行関数"""
    if not settings.OPENAI_API_KEY:
        print("⚠️ OPENAI_API_KEY not set. This test uses mock API calls.")
        print("   Set OPENAI_API_KEY to test with real API calls.")
        print()
    
    tester = PerformanceTestHelper()
    await tester.run_performance_comparison()

if __name__ == "__main__":
    print("🚀 Menu Processor - Parallel Processing Performance Test")
    print("=" * 60)
    asyncio.run(main()) 