"""
Search Image Task - Menu Processor v2 (Refactored with BatchProcessor)
画像検索処理を担当するCeleryワーカー（BatchProcessor使用版）
"""
import asyncio
import uuid
from typing import Dict, List, Any
import redis.asyncio as redis

from app_2.core.celery_app import celery_app
from app_2.tasks.batch_processor import BatchProcessor, BatchConfig
from app_2.services.search_image_service import get_search_image_service
from app_2.infrastructure.repositories.menu_repository_impl import MenuRepositoryImpl
from app_2.core.database import async_session_factory
from app_2.core.config import settings
from app_2.utils.logger import get_logger

logger = get_logger("search_image_task")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3}, queue='search_image_queue')
def search_image_menu_task(
    self, 
    session_id: str, 
    menu_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    メニュー項目の画像検索処理タスク（BatchProcessor使用版）
    
    Args:
        session_id: セッションID
        menu_items: 画像検索対象のメニューアイテムリスト（実際のentityから変換されたdict）
        
    Returns:
        Dict[str, Any]: 処理結果
    """
    # 非同期処理をラップして実行
    return asyncio.run(_search_image_menu_task_async(self, session_id, menu_items))


async def _search_image_menu_task_async(
    task_instance,
    session_id: str, 
    menu_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    メニュー項目の画像検索処理タスク（BatchProcessor使用版）
    
    Args:
        session_id: セッションID
        menu_items: 画像検索対象のメニューアイテムリスト
        
    Returns:
        Dict[str, Any]: 処理結果
    """
    task_id = task_instance.request.id
    total_items = len(menu_items)
    
    logger.info(f"Search image task started: session={session_id}, items={total_items}, task_id={task_id}")
    
    try:
        # バッチプロセッサー設定
        config = BatchConfig(
            batch_size=5,
            max_concurrent_batches=2, 
            task_name="search_image"
        )
        
        processor = BatchProcessor(config)
        search_image_service = get_search_image_service()
        
        # 画像検索処理関数（画像URLリスト版）
        async def search_image_processor(item: Dict[str, Any]) -> Dict[str, Any]:
            """画像検索処理 - 画像URLリストのみ抽出"""
            menu_name = item.get("name", "")
            category = item.get("category", "")
            
            # シンプルな画像検索実行
            image_results = await search_image_service.search_menu_images(
                menu_item=menu_name,
                category=category,
                num_results=3  # 3件の画像を検索
            )
            
            # 画像URLリストのみ抽出
            image_urls = []
            if image_results:
                for img in image_results:
                    if isinstance(img, dict) and 'link' in img:
                        image_urls.append(img['link'])
                logger.info(f"✅ Found {len(image_urls)} image URLs for: {menu_name}")
            else:
                logger.warning(f"⚠️ No images found for: {menu_name}")
            
            # 画像URLリストをJSON文字列として保存
            image_urls_json = None
            if image_urls:
                import json
                image_urls_json = json.dumps(image_urls, ensure_ascii=False)
            
            return {
                "search_engine": image_urls_json,
                "images_found": len(image_urls)
            }
        
        # 🔥 完全分離型DB更新関数（タスク専用Redis接続）
        async def search_image_db_updater(item_id: str, search_data: Dict[str, Any]) -> bool:
            """画像検索結果をDBに更新（完全分離型Redis）"""
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
                lock_key = f"lock:menu_update:search_image:{item_id}"
                lock_value = str(uuid.uuid4())
                
                # ロック取得試行（10秒タイムアウト）
                acquired = await task_redis.set(lock_key, lock_value, ex=10, nx=True)
                if not acquired:
                    logger.error(f"Failed to acquire lock for search image update: {item_id}")
                    return False
                
                try:
                    # リトライ機構付きDB更新
                    for retry_count in range(3):
                        try:
                            async with async_session_factory() as db_session:
                                menu_repository = MenuRepositoryImpl(db_session)
                                
                                # 画像検索データを準備
                                search_result_json = search_data.get("search_engine")
                                
                                # search_engine フィールドを更新
                                updated_entity = await menu_repository.update_search_engine_result(
                                    item_id, search_result_json
                                )
                                
                                if updated_entity:
                                    logger.info(f"Search image DB update successful: {item_id}")
                                    return True
                                else:
                                    if retry_count < 2:
                                        # エンティティが見つからない場合、少し待ってリトライ
                                        logger.warning(f"Menu entity not found for {item_id}, retrying... ({retry_count + 1}/3)")
                                        await asyncio.sleep(0.5 * (retry_count + 1))
                                        continue
                                    else:
                                        logger.error(f"Menu entity not found for search image update after 3 retries: {item_id}")
                                        return False
                            
                        except Exception as e:
                            if retry_count < 2:
                                logger.warning(f"Search image DB update failed for {item_id}, retrying... ({retry_count + 1}/3): {e}")
                                await asyncio.sleep(0.5 * (retry_count + 1))
                                continue
                            else:
                                logger.error(f"Search image DB update failed for {item_id} after 3 retries: {e}")
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
                logger.error(f"Redis connection error for search image update {item_id}: {e}")
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
            processor_func=search_image_processor,
            db_updater_func=search_image_db_updater
        )
        
        # タスクIDを結果に追加
        result["task_id"] = task_id
        
        # 🎯 画像検索タスク完了後のSSE送信（簡略化版）
        if result.get("status") == "success":
            from app_2.infrastructure.integrations.redis.redis_publisher import RedisPublisher
            redis_publisher = RedisPublisher()
            
            # 画像検索完了の簡潔な通知を送信
            await redis_publisher.publish_session_message(
                session_id=session_id,
                message_type="search_image_completed",
                data={
                    "task_type": "search_image",
                    "completed_items": result.get("completed_items", 0),
                    "total_items": result.get("total_items", 0),
                    "task_id": task_id,
                    "message": f"Image search completed: {result.get('completed_items', 0)}/{result.get('total_items', 0)} items"
                }
            )
            
            logger.info(f"🔍 Search image completion broadcasted for session: {session_id}")
        
        logger.info(f"Search image task completed successfully: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Search image task failed: {e}", extra={
            "session_id": session_id,
            "task_id": task_id,
            "input_count": total_items
        })
        raise


# 単体アイテム用のヘルパー関数（簡略化版）
async def search_image_single_menu_item(
    menu_id: str,
    menu_name: str,
    category: str = ""
) -> Dict[str, Any]:
    """
    単一メニューアイテムの画像検索処理（簡略化版）
    
    Args:
        menu_id: メニューID
        menu_name: メニュー名
        category: カテゴリ
        
    Returns:
        Dict[str, Any]: 検索結果
    """
    try:
        search_image_service = get_search_image_service()
        
        # 画像検索実行
        image_results = await search_image_service.search_menu_images(
            menu_item=menu_name,
            category=category,
            num_results=3  # 固定で3件
        )
        
        # 結果をフォーマット
        return {
            "menu_id": menu_id,
            "menu_name": menu_name,
            "images_found": len(image_results),
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Failed to search images for {menu_name}: {e}")
        return {
            "menu_id": menu_id,
            "menu_name": menu_name,
            "images_found": 0,
            "status": "failed",
            "error": str(e)
        } 