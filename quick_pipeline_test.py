#!/usr/bin/env python3
"""
パイプライン統合サービス簡単テスト
"""
import asyncio
import time

async def test_pipeline_service():
    print('🔄 パイプライン統合サービス直接テスト開始...')
    
    try:
        from app.services.pipeline import PipelineProcessingService
        
        service = PipelineProcessingService()
        
        print(f'✅ パイプライン統合サービス: 利用可能 = {service.is_available()}')
        print(f'📋 パイプラインモード: {service.pipeline_mode}')
        print(f'⚡ 最大ワーカー数: {service.max_workers}')
        print(f'📊 カテゴリ閾値: {service.category_threshold}')
        print(f'📈 アイテム閾値: {service.item_threshold}')
        
        # パイプライン戦略のテスト
        print('\n🧪 パイプライン戦略テスト:')
        strategies = [
            {'force_worker_pipeline': True},
            {'force_category_pipeline': True},
            {}
        ]
        
        for i, options in enumerate(strategies):
            strategy = service._determine_pipeline_strategy(options)
            print(f'  戦略 {i+1}: {strategy}')
        
        print('\n🎉 パイプライン統合サービス直接テスト完了！')
        return True
        
    except Exception as e:
        print(f'❌ テスト失敗: {e}')
        return False

if __name__ == "__main__":
    success = asyncio.run(test_pipeline_service())
    exit(0 if success else 1) 