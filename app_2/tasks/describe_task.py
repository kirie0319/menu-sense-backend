"""
Description Task - Menu Processor v2 (Refactored with BatchProcessor)
詳細説明処理を担当するCeleryワーカー（BatchProcessor使用版）
"""
import asyncio
import uuid
from typing import Dict, List, Any
import redis.asyncio as redis

from app_2.core.celery_app import celery_app
from app_2.tasks.batch_processor import BatchProcessor, BatchConfig
from app_2.services.describe_service import get_describe_service
from app_2.infrastructure.repositories.menu_repository_impl import MenuRepositoryImpl
from app_2.core.database import async_session_factory
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("describe_task")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3}, queue='describe_queue')
def describe_menu_task(
    self, 
    session_id: str, 
    menu_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    メニュー項目の詳細説明処理タスク（BatchProcessor使用版）
    
    Args:
        session_id: セッションID
        menu_items: 詳細説明対象のメニューアイテムリスト（実際のentityから変換されたdict）
        
    Returns:
        Dict[str, Any]: 処理結果
    """
    # 非同期処理をラップして実行
    return asyncio.run(_describe_menu_task_async(self, session_id, menu_items))


async def _describe_menu_task_async(
    task_instance,
    session_id: str, 
    menu_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    メニュー項目の詳細説明処理タスク（BatchProcessor使用版）
    
    Args:
        session_id: セッションID
        menu_items: 詳細説明対象のメニューアイテムリスト
        
    Returns:
        Dict[str, Any]: 処理結果
    """
    task_id = task_instance.request.id
    total_items = len(menu_items)
    
    logger.info(f"Description task started: session={session_id}, items={total_items}, task_id={task_id}")
    
    try:
        # バッチプロセッサー設定
        config = BatchConfig(
            batch_size=6,
            max_concurrent_batches=2, 
            task_name="description"
        )
        
        processor = BatchProcessor(config)
        describe_service = get_describe_service()
        
        # 詳細説明処理関数（タスク固有ロジック）
        async def description_processor(item: Dict[str, Any]) -> Dict[str, Any]:
            """詳細説明固有の処理ロジック"""
            menu_name = item.get("name", "")
            category = item.get("category", "")
            
            # 翻訳済みの名前があれば、それも併用
            translation = item.get("translation", "")
            if translation:
                # 翻訳と原文の両方を使って詳細説明を生成
                description_input = f"{menu_name} ({translation})"
            else:
                description_input = menu_name
            
            return await describe_service.generate_menu_description(
                menu_item=description_input, 
                category=category
            )
        
        # 🔥 完全分離型DB更新関数（タスク専用Redis接続）
        async def description_db_updater(item_id: str, description_data: Dict[str, Any]) -> bool:
            """詳細説明結果をDBに更新（完全分離型Redis）"""
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
                lock_key = f"lock:menu_update:description:{item_id}"
                lock_value = str(uuid.uuid4())
                
                # ロック取得試行（10秒タイムアウト）
                acquired = await task_redis.set(lock_key, lock_value, ex=10, nx=True)
                if not acquired:
                    logger.error(f"Failed to acquire lock for description update: {item_id}")
                    return False
                
                try:
                    # リトライ機構付きDB更新
                    for retry_count in range(3):
                        try:
                            async with async_session_factory() as db_session:
                                menu_repository = MenuRepositoryImpl(db_session)
                                
                                # 説明データを準備
                                description_text = description_data.get("description", "")
                                if not description_text:
                                    # フォールバック用の説明
                                    description_text = description_data.get("summary", "説明情報を生成できませんでした")
                                
                                # 部分更新を使用（説明フィールドのみ更新）
                                update_fields = {
                                    "description": description_text
                                }
                                
                                updated_entity = await menu_repository.update_partial(item_id, update_fields)
                                
                                if updated_entity:
                                    logger.info(f"Description DB update successful: {item_id}")
                                    return True
                                else:
                                    if retry_count < 2:
                                        # エンティティが見つからない場合、少し待ってリトライ
                                        logger.warning(f"Menu entity not found for {item_id}, retrying... ({retry_count + 1}/3)")
                                        await asyncio.sleep(0.5 * (retry_count + 1))
                                        continue
                                    else:
                                        logger.error(f"Menu entity not found for description update after 3 retries: {item_id}")
                                        return False
                            
                        except Exception as e:
                            if retry_count < 2:
                                logger.warning(f"Description DB update failed for {item_id}, retrying... ({retry_count + 1}/3): {e}")
                                await asyncio.sleep(0.5 * (retry_count + 1))
                                continue
                            else:
                                logger.error(f"Description DB update failed for {item_id} after 3 retries: {e}")
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
                logger.error(f"Redis connection error for description update {item_id}: {e}")
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
            processor_func=description_processor,
            db_updater_func=description_db_updater
        )
        
        # タスクIDを結果に追加
        result["task_id"] = task_id
        
        # 🎯 詳細説明タスク完了後の詳細SSE送信
        if result.get("status") == "success":
            from app_2.infrastructure.integrations.redis.redis_publisher import RedisPublisher
            redis_publisher = RedisPublisher()
            
            # 詳細説明完了の詳細通知を送信
            await redis_publisher.publish_session_message(
                session_id=session_id,
                message_type="description_batch_completed",
                data={
                    "task_type": "description",
                    "batch_status": "completed",
                    "completed_items": result.get("completed_items", 0),
                    "total_items": result.get("total_items", 0),
                    "success_rate": result.get("success_rate", 0),
                    "task_id": task_id,
                    "processing_summary": {
                        "items_processed": len(menu_items),
                        "description_language": "Japanese",
                        "batch_completed_at": "now",
                        "content_type": "detailed_menu_descriptions"
                    },
                    "message": f"Description generation completed: {result.get('completed_items', 0)}/{result.get('total_items', 0)} items now have detailed descriptions"
                }
            )
            
            logger.info(f"📝 Description batch completion broadcasted for session: {session_id}")
        
        logger.info(f"Description task completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Description task failed: {e}", extra={
            "session_id": session_id,
            "task_id": task_id,
            "input_count": total_items
        })
        raise 