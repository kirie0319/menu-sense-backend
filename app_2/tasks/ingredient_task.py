"""
Ingredient Task - Menu Processor v2 (Refactored with BatchProcessor)
内容物解析処理を担当するCeleryワーカー（BatchProcessor使用版）
"""
import asyncio
import uuid
from typing import Dict, List, Any
import redis.asyncio as redis

from app_2.core.celery_app import celery_app
from app_2.tasks.batch_processor import BatchProcessor, BatchConfig
from app_2.services.ingredient_service import get_ingredient_service
from app_2.infrastructure.repositories.menu_repository_impl import MenuRepositoryImpl
from app_2.core.database import async_session_factory
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("ingredient_task")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3}, queue='ingredient_queue')
def ingredient_menu_task(
    self, 
    session_id: str, 
    menu_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    メニュー項目の内容物解析処理タスク（BatchProcessor使用版）
    
    Args:
        session_id: セッションID
        menu_items: 内容物解析対象のメニューアイテムリスト（実際のentityから変換されたdict）
        
    Returns:
        Dict[str, Any]: 処理結果
    """
    # 非同期処理をラップして実行
    return asyncio.run(_ingredient_menu_task_async(self, session_id, menu_items))


async def _ingredient_menu_task_async(
    task_instance,
    session_id: str, 
    menu_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    メニュー項目の内容物解析処理タスク（BatchProcessor使用版）
    
    Args:
        session_id: セッションID
        menu_items: 内容物解析対象のメニューアイテムリスト
        
    Returns:
        Dict[str, Any]: 処理結果
    """
    task_id = task_instance.request.id
    total_items = len(menu_items)
    
    logger.info(f"Ingredient task started: session={session_id}, items={total_items}, task_id={task_id}")
    
    try:
        # バッチプロセッサー設定
        config = BatchConfig(
            batch_size=8,
            max_concurrent_batches=3, 
            task_name="ingredient"
        )
        
        processor = BatchProcessor(config)
        ingredient_service = get_ingredient_service()
        
        # 内容物解析処理関数（タスク固有ロジック）
        async def ingredient_processor(item: Dict[str, Any]) -> Dict[str, Any]:
            """内容物解析固有の処理ロジック"""
            menu_name = item.get("name", "")
            category = item.get("category", "")
            
            # 翻訳済みの名前があれば、それも併用
            translation = item.get("translation", "")
            if translation:
                # 翻訳と原文の両方を使って内容物解析を実行
                ingredient_input = f"{menu_name} ({translation})"
            else:
                ingredient_input = menu_name
            
            return await ingredient_service.analyze_ingredients(
                menu_item=ingredient_input, 
                category=category
            )
        
        # 🔥 完全分離型DB更新関数（タスク専用Redis接続）
        async def ingredient_db_updater(item_id: str, ingredient_data: Dict[str, Any]) -> bool:
            """内容物解析結果をDBに更新（完全分離型Redis）"""
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
                lock_key = f"lock:menu_update:ingredient:{item_id}"
                lock_value = str(uuid.uuid4())
                
                # ロック取得試行（10秒タイムアウト）
                acquired = await task_redis.set(lock_key, lock_value, ex=10, nx=True)
                if not acquired:
                    logger.error(f"Failed to acquire lock for ingredient update: {item_id}")
                    return False
                
                try:
                    # リトライ機構付きDB更新
                    for retry_count in range(3):
                        try:
                            async with async_session_factory() as db_session:
                                menu_repository = MenuRepositoryImpl(db_session)
                                
                                # 内容物解析データを準備
                                main_ingredients = ingredient_data.get("main_ingredients", [])
                                if main_ingredients:
                                    # 主要材料リストを文字列に変換
                                    ingredient_text = ", ".join([ing.get("ingredient", ing) if isinstance(ing, dict) else str(ing) for ing in main_ingredients])
                                else:
                                    # 内容物情報がない場合の対応
                                    cuisine_category = ingredient_data.get("cuisine_category", "")
                                    cooking_method = ingredient_data.get("cooking_method", [])
                                    if cuisine_category != "unknown":
                                        ingredient_text = f"料理タイプ: {cuisine_category}"
                                    elif cooking_method:
                                        ingredient_text = f"調理法: {', '.join(cooking_method)}"
                                    else:
                                        ingredient_text = "材料情報不明"
                                
                                # 部分更新を使用（内容物フィールドのみ更新）
                                update_fields = {
                                    "ingredient": ingredient_text
                                }
                                
                                updated_entity = await menu_repository.update_partial(item_id, update_fields)
                                
                                if updated_entity:
                                    logger.info(f"Ingredient DB update successful: {item_id}")
                                    return True
                                else:
                                    if retry_count < 2:
                                        # エンティティが見つからない場合、少し待ってリトライ
                                        logger.warning(f"Menu entity not found for {item_id}, retrying... ({retry_count + 1}/3)")
                                        await asyncio.sleep(0.5 * (retry_count + 1))
                                        continue
                                    else:
                                        logger.error(f"Menu entity not found for ingredient update after 3 retries: {item_id}")
                                        return False
                            
                        except Exception as e:
                            if retry_count < 2:
                                logger.warning(f"Ingredient DB update failed for {item_id}, retrying... ({retry_count + 1}/3): {e}")
                                await asyncio.sleep(0.5 * (retry_count + 1))
                                continue
                            else:
                                logger.error(f"Ingredient DB update failed for {item_id} after 3 retries: {e}")
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
                logger.error(f"Redis connection error for ingredient update {item_id}: {e}")
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
            processor_func=ingredient_processor,
            db_updater_func=ingredient_db_updater
        )
        
        # タスクIDを結果に追加
        result["task_id"] = task_id
        
        # 🎯 内容物解析タスク完了後の詳細SSE送信
        if result.get("status") == "success":
            from app_2.infrastructure.integrations.redis.redis_publisher import RedisPublisher
            redis_publisher = RedisPublisher()
            
            # 内容物解析完了の詳細通知を送信
            await redis_publisher.publish_session_message(
                session_id=session_id,
                message_type="ingredient_batch_completed",
                data={
                    "task_type": "ingredient",
                    "batch_status": "completed",
                    "completed_items": result.get("completed_items", 0),
                    "total_items": result.get("total_items", 0),
                    "success_rate": result.get("success_rate", 0),
                    "task_id": task_id,
                    "processing_summary": {
                        "items_processed": len(menu_items),
                        "analysis_language": "Japanese/English",
                        "batch_completed_at": "now",
                        "nutrition_info": "ingredient_analysis_completed"
                    },
                    "message": f"Ingredient analysis completed: {result.get('completed_items', 0)}/{result.get('total_items', 0)} items now have ingredient information"
                }
            )
            
            logger.info(f"🥬 Ingredient batch completion broadcasted for session: {session_id}")
        
        logger.info(f"Ingredient task completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Ingredient task failed: {e}", extra={
            "session_id": session_id,
            "task_id": task_id,
            "input_count": total_items
        })
        raise 