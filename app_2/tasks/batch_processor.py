"""
Batch Processor - 汎用バッチ処理エンジン (Simplified)
各タスク（翻訳、アレルゲン検出、成分分析など）で共通利用するバッチ処理ロジック
"""
import asyncio
from typing import Dict, List, Any, Callable
from dataclasses import dataclass

from app_2.infrastructure.integrations.redis.redis_publisher import RedisPublisher
from app_2.utils.logger import get_logger

logger = get_logger("batch_processor")


@dataclass
class BatchConfig:
    """バッチ処理設定"""
    batch_size: int = 8
    max_concurrent_batches: int = 3
    task_name: str = ""


class BatchProcessor:
    """
    汎用バッチ処理エンジン (Simplified)
    
    各タスクは processor_func と db_updater_func のみ実装すればよい
    """
    
    def __init__(self, config: BatchConfig):
        self.config = config
        self.redis_publisher = RedisPublisher()
        
    async def process_items(
        self,
        session_id: str,
        items: List[Dict[str, Any]],
        processor_func: Callable[[Dict[str, Any]], Dict[str, Any]],
        db_updater_func: Callable[[str, Dict[str, Any]], bool]
    ) -> Dict[str, Any]:
        """
        アイテムバッチ処理のメインエンジン
        
        Args:
            session_id: セッションID
            items: 処理対象アイテム
            processor_func: 各タスク固有の処理関数
            db_updater_func: DB更新関数
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        total_items = len(items)
        logger.info(f"{self.config.task_name} processing: {total_items} items")
        
        # 開始通知
        await self._notify_start(session_id, total_items)
        
        # バッチ分割
        batches = [
            items[i:i + self.config.batch_size] 
            for i in range(0, total_items, self.config.batch_size)
        ]
        
        # 並列バッチ処理
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        
        async def process_batch(batch_idx: int, batch_items: List[Dict]) -> Dict:
            async with semaphore:
                return await self._process_batch(
                    session_id, batch_idx, batch_items, processor_func, db_updater_func
                )
        
        # 全バッチ実行
        batch_results = await asyncio.gather(
            *[process_batch(i, batch) for i, batch in enumerate(batches)],
            return_exceptions=True
        )
        
        # 結果集計
        return await self._aggregate_and_notify(session_id, batch_results, total_items)
    
    async def _process_batch(
        self, 
        session_id: str, 
        batch_idx: int,
        batch_items: List[Dict],
        processor_func: Callable,
        db_updater_func: Callable
    ) -> Dict:
        """単一バッチの処理"""
        completed = 0
        errors = []
        
        # バッチ内並列処理
        async def process_item(item: Dict[str, Any]) -> bool:
            try:
                # 処理実行
                processed_data = await processor_func(item)
                
                # DB更新
                success = await db_updater_func(item["id"], processed_data)
                
                if success:
                    # 個別完了通知（実際の処理データを含む）
                    menu_update_data = {
                        "task_type": self.config.task_name,
                        "status": "completed",
                        "batch_idx": batch_idx,
                        "item_id": item["id"],
                        "original_name": item.get("name", ""),
                        "category": item.get("category", "")
                    }
                    
                    # 翻訳タスクの場合は翻訳結果を追加
                    if self.config.task_name == "translation" and processed_data:
                        menu_update_data.update({
                            "translation": processed_data.get("name", ""),
                            "category_translation": processed_data.get("category", ""),
                            "translation_language": "en"
                        })
                    # 詳細説明タスクの場合は説明を追加
                    elif self.config.task_name == "description" and processed_data:
                        menu_update_data.update({
                            "description": processed_data.get("description", ""),
                            "description_language": "ja",
                            "description_length": len(processed_data.get("description", ""))
                        })
                    # アレルギー解析タスクの場合はアレルギー情報を追加
                    elif self.config.task_name == "allergen" and processed_data:
                        allergen_list = processed_data.get("allergens", [])
                        # 辞書形式のアレルギー情報に対応
                        allergen_info_text = ", ".join([
                            allergen.get("name", allergen) if isinstance(allergen, dict) else str(allergen) 
                            for allergen in allergen_list
                        ]) if allergen_list else processed_data.get("notes", "アレルギー情報なし")
                        
                        menu_update_data.update({
                            "allergen_info": allergen_info_text,
                            "allergen_details": allergen_list,
                            "allergen_free": processed_data.get("allergen_free", False),
                            "safety_level": "safe" if processed_data.get("allergen_free", False) else "check_required"
                        })
                    # 内容物解析タスクの場合は内容物情報を追加
                    elif self.config.task_name == "ingredient" and processed_data:
                        main_ingredients = processed_data.get("main_ingredients", [])
                        dietary_info = processed_data.get("dietary_info", {})
                        menu_update_data.update({
                            "ingredient_info": ", ".join([ing.get("ingredient", ing) if isinstance(ing, dict) else str(ing) for ing in main_ingredients]),
                            "main_ingredients": main_ingredients,
                            "dietary_info": dietary_info,
                            "cuisine_category": processed_data.get("cuisine_category", "unknown")
                        })
                    # 画像検索タスクの場合は画像URL情報を追加
                    elif self.config.task_name == "search_image" and processed_data:
                        search_engine_data = processed_data.get("search_engine", "")
                        images_found = processed_data.get("images_found", 0)
                        
                        # JSONとして送信されたsearch_engineをそのまま転送
                        menu_update_data.update({
                            "search_engine": search_engine_data,
                            "images_found": images_found,
                            "image_search_status": "completed" if images_found > 0 else "no_results"
                        })
                    # その他のタスクの場合は該当するデータを追加
                    elif processed_data:
                        menu_update_data["processed_data"] = processed_data
                    
                    await self.redis_publisher.publish_menu_update(
                        session_id=session_id,
                        menu_id=item["id"],
                        menu_data=menu_update_data
                    )
                    return True
                else:
                    errors.append(f"DB update failed: {item['id']}")
                    return False
                    
            except Exception as e:
                error_msg = f"{item.get('name', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                
                # エラー通知
                await self.redis_publisher.publish_error_message(
                    session_id=session_id,
                    error_type=f"{self.config.task_name}_item_failed",
                    error_message=error_msg,
                    task_name=self.config.task_name
                )
                return False
        
        # バッチ内全アイテム並列処理
        results = await asyncio.gather(
            *[process_item(item) for item in batch_items],
            return_exceptions=True
        )
        
        # 成功数カウント
        for result in results:
            if result is True:
                completed += 1
            elif isinstance(result, Exception):
                errors.append(str(result))
        
        return {
            "completed": completed,
            "total": len(batch_items),
            "errors": errors
        }
    
    async def _notify_start(self, session_id: str, total_items: int):
        """開始通知"""
        await self.redis_publisher.publish_progress_update(
            session_id=session_id,
            task_name=self.config.task_name,
            status="started",
            progress_data={
                "total_items": total_items,
                "batch_size": self.config.batch_size
            }
        )
    
    async def _aggregate_and_notify(
        self, 
        session_id: str, 
        batch_results: List, 
        total_items: int
    ) -> Dict[str, Any]:
        """結果集計と最終通知"""
        total_completed = 0
        all_errors = []
        completed_batches = 0
        
        # 結果集計
        for result in batch_results:
            if isinstance(result, Exception):
                all_errors.append(str(result))
                continue
            
            completed_batches += 1
            total_completed += result.get("completed", 0)
            all_errors.extend(result.get("errors", []))
        
        # 成功率計算
        success_rate = round((total_completed / total_items) * 100, 1) if total_items > 0 else 0
        
        # 最終通知
        await self.redis_publisher.publish_progress_update(
            session_id=session_id,
            task_name=self.config.task_name,
            status="completed",
            progress_data={
                "progress": 100,
                "completed_items": total_completed,
                "total_items": total_items,
                "success_rate": success_rate
            }
        )
        
        logger.info(f"{self.config.task_name} completed: {total_completed}/{total_items} ({success_rate}%)")
        
        return {
            "status": "success",
            "session_id": session_id,
            "task_name": self.config.task_name,
            "completed_items": total_completed,
            "total_items": total_items,
            "success_rate": success_rate,
            "error_count": len(all_errors)
        }
