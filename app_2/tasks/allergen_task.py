"""
Allergen Task - Menu Processor v2 (Refactored with BatchProcessor)
アレルギー解析処理を担当するCeleryワーカー（BatchProcessor使用版）
"""
import asyncio
import uuid
from typing import Dict, List, Any
import redis.asyncio as redis

from app_2.core.celery_app import celery_app
from app_2.tasks.batch_processor import BatchProcessor, BatchConfig
from app_2.services.allergen_service import get_allergen_service
from app_2.infrastructure.repositories.menu_repository_impl import MenuRepositoryImpl
from app_2.core.database import async_session_factory
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("allergen_task")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3}, queue='allergen_queue')
def allergen_menu_task(
    self, 
    session_id: str, 
    menu_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    メニュー項目のアレルギー解析処理タスク（BatchProcessor使用版）
    
    Args:
        session_id: セッションID
        menu_items: アレルギー解析対象のメニューアイテムリスト（実際のentityから変換されたdict）
        
    Returns:
        Dict[str, Any]: 処理結果
    """
    # 非同期処理をラップして実行
    return asyncio.run(_allergen_menu_task_async(self, session_id, menu_items))


async def _allergen_menu_task_async(
    task_instance,
    session_id: str, 
    menu_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    メニュー項目のアレルギー解析処理タスク（BatchProcessor使用版）
    
    Args:
        session_id: セッションID
        menu_items: アレルギー解析対象のメニューアイテムリスト
        
    Returns:
        Dict[str, Any]: 処理結果
    """
    task_id = task_instance.request.id
    total_items = len(menu_items)
    
    logger.info(f"Allergen task started: session={session_id}, items={total_items}, task_id={task_id}")
    
    try:
        # バッチプロセッサー設定
        config = BatchConfig(
            batch_size=8,
            max_concurrent_batches=3, 
            task_name="allergen"
        )
        
        processor = BatchProcessor(config)
        allergen_service = get_allergen_service()
        
        # アレルギー解析処理関数（タスク固有ロジック）
        async def allergen_processor(item: Dict[str, Any]) -> Dict[str, Any]:
            """アレルギー解析固有の処理ロジック"""
            menu_name = item.get("name", "")
            category = item.get("category", "")
            
            # 翻訳済みの名前があれば、それも併用
            translation = item.get("translation", "")
            if translation:
                # 翻訳と原文の両方を使ってアレルギー解析を実行
                allergen_input = f"{menu_name} ({translation})"
            else:
                allergen_input = menu_name
            
            return await allergen_service.analyze_allergens(
                menu_item=allergen_input, 
                category=category
            )
        
        # 🔥 完全分離型DB更新関数（タスク専用Redis接続）
        async def allergen_db_updater(item_id: str, allergen_data: Dict[str, Any]) -> bool:
            """アレルギー解析結果をDBに更新（完全分離型Redis）"""
            # 🔥 タスク専用Redis接続を作成（シングルトンなし）
            task_redis = None
            try:
                task_redis = redis.from_url(
                    settings.celery.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5
                )
                
                # 分散ロック処理
                lock_key = f"lock:menu_update:allergen:{item_id}"
                lock_value = str(uuid.uuid4())
                
                # ロック取得試行（10秒タイムアウト）
                acquired = await task_redis.set(lock_key, lock_value, ex=10, nx=True)
                if not acquired:
                    logger.error(f"Failed to acquire lock for allergen update: {item_id}")
                    return False
                
                try:
                    # リトライ機構付きDB更新
                    for retry_count in range(3):
                        try:
                            async with async_session_factory() as db_session:
                                menu_repository = MenuRepositoryImpl(db_session)
                                
                                # 🔥 Simple allergen list conversion to string format
                                allergen_list = allergen_data.get("allergens", [])
                                allergen_free = allergen_data.get("allergen_free", False)
                                
                                if allergen_list and len(allergen_list) > 0:
                                    # Convert simple string list to comma-separated format
                                    allergen_text = ", ".join(allergen_list)
                                elif allergen_free:
                                    # No allergens present
                                    allergen_text = "None"
                                else:
                                    # Unable to determine allergens
                                    notes = allergen_data.get("notes", "")
                                    allergen_text = notes if notes else "Unable to determine"
                                
                                # 部分更新を使用（アレルギーフィールドのみ更新）
                                update_fields = {
                                    "allergy": allergen_text
                                }
                                
                                updated_entity = await menu_repository.update_partial(item_id, update_fields)
                                
                                if updated_entity:
                                    logger.info(f"Allergen DB update successful: {item_id}")
                                    return True
                                else:
                                    if retry_count < 2:
                                        # エンティティが見つからない場合、少し待ってリトライ
                                        logger.warning(f"Menu entity not found for {item_id}, retrying... ({retry_count + 1}/3)")
                                        await asyncio.sleep(0.5 * (retry_count + 1))
                                        continue
                                    else:
                                        logger.error(f"Menu entity not found for allergen update after 3 retries: {item_id}")
                                        return False
                            
                        except Exception as e:
                            if retry_count < 2:
                                logger.warning(f"Allergen DB update failed for {item_id}, retrying... ({retry_count + 1}/3): {e}")
                                await asyncio.sleep(0.5 * (retry_count + 1))
                                continue
                            else:
                                logger.error(f"Allergen DB update failed for {item_id} after 3 retries: {e}")
                                return False
                    
                    return False
                    
                finally:
                    # 🔥 原子的ロック解放（Luaスクリプト）
                    lua_script = """
                    if redis.call("get", KEYS[1]) == ARGV[1] then
                        return redis.call("del", KEYS[1])
                    else
                        return 0
                    end
                    """
                    try:
                        await task_redis.eval(lua_script, 1, lock_key, lock_value)
                    except Exception as e:
                        logger.warning(f"Failed to release lock {lock_key}: {e}")
                
            except Exception as e:
                logger.error(f"Redis connection error for allergen update {item_id}: {e}")
                return False
            finally:
                # 🔥 確実にRedis接続をクリーンアップ
                if task_redis:
                    try:
                        await task_redis.aclose()
                    except Exception as e:
                        logger.warning(f"Redis cleanup error: {e}")
        
        # バッチ処理実行
        result = await processor.process_items(
            session_id=session_id,
            items=menu_items,
            processor_func=allergen_processor,
            db_updater_func=allergen_db_updater
        )
        
        # タスクIDを結果に追加
        result["task_id"] = task_id
        
        # 🎯 アレルギー解析タスク完了後の詳細SSE送信
        if result.get("status") == "success":
            from app_2.infrastructure.integrations.redis.redis_publisher import RedisPublisher
            redis_publisher = RedisPublisher()
            
            # アレルギー解析完了の詳細通知を送信
            await redis_publisher.publish_session_message(
                session_id=session_id,
                message_type="allergen_batch_completed",
                data={
                    "task_type": "allergen",
                    "batch_status": "completed",
                    "completed_items": result.get("completed_items", 0),
                    "total_items": result.get("total_items", 0),
                    "success_rate": result.get("success_rate", 0),
                    "task_id": task_id,
                    "processing_summary": {
                        "items_processed": len(menu_items),
                        "analysis_language": "Japanese/English",
                        "batch_completed_at": "now",
                        "safety_info": "allergen_warnings_identified"
                    },
                    "message": f"Allergen analysis completed: {result.get('completed_items', 0)}/{result.get('total_items', 0)} items now have allergen information"
                }
            )
            
            logger.info(f"🛡️ Allergen batch completion broadcasted for session: {session_id}")
        
        logger.info(f"Allergen task completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Allergen task failed: {e}", extra={
            "session_id": session_id,
            "task_id": task_id,
            "input_count": total_items
        })
        raise 