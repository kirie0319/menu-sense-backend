"""
Pipeline Runner - Menu Processor v2
メニュー処理の基本フロー実行: OCR → Mapping → Categorize → DB Save → SSE → Parallel Tasks
"""
import time
import json
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime

from app_2.services.ocr_service import get_ocr_service
from app_2.services.categorize_service import get_categorize_service
from app_2.services.mapping_service import get_menu_mapping_categorize_service
from app_2.services.menu_save_service import create_menu_save_service
from app_2.services.dependencies import get_menu_repository, get_session_repository
from app_2.infrastructure.integrations.redis.redis_publisher import RedisPublisher
from app_2.domain.entities.session_entity import SessionEntity, SessionStatus
from app_2.utils.logger import get_logger

logger = get_logger("pipeline_runner")


class MenuProcessingPipeline:
    """
    メニュー処理パイプライン
    
    責任:
    1. OCR → Mapping → Categorize → DB Save (4段階基本処理)
    2. SSE進捗配信
    3. 並列タスクのトリガー
    """
    
    def __init__(self):
        self.redis_publisher = RedisPublisher()
        self.ocr_service = get_ocr_service()
        self.categorize_service = get_categorize_service()
        self.mapping_service = get_menu_mapping_categorize_service()

    async def _update_session_stage_completion(
        self, 
        session_id: str, 
        stage: str, 
        stage_data: Dict[str, Any]
    ) -> bool:
        """
        段階完了時のセッション状態更新
        
        Args:
            session_id: セッションID
            stage: 完了した段階名
            stage_data: 段階データ
            
        Returns:
            bool: 更新が成功したか
        """
        try:
            from app_2.core.database import async_session_factory
            
            async with async_session_factory() as db_session:
                session_repo = get_session_repository(db_session)
                
                # セッションモデルを直接取得
                from sqlalchemy import select
                from app_2.infrastructure.models.session_model import SessionModel
                
                stmt = select(SessionModel).where(SessionModel.session_id == session_id)
                result = await db_session.execute(stmt)
                session_model = result.scalar_one_or_none()
                
                if session_model:
                    # 段階データを更新
                    session_model.update_stage_data(stage, stage_data)
                    await db_session.commit()
                    
                    logger.info(f"✅ Session {session_id} stage updated: {stage}")
                    return True
                else:
                    logger.error(f"❌ Session not found for stage update: {session_id}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Failed to update session stage {session_id}/{stage}: {e}")
            return False

    async def _execute_ocr_stage(self, session_id: str, image_data: bytes) -> List[Dict]:
        """
        Stage 1: OCR実行 → DB更新 → SSE配信
        
        Args:
            session_id: セッションID
            image_data: 画像データ
            
        Returns:
            List[Dict]: OCR結果リスト
        """
        logger.info(f"🔍 Starting OCR stage for session: {session_id}")
        
        # OCR処理開始通知
        await self._update_progress(session_id, "ocr", "processing", 10)
        
        try:
            # OCR実行
            ocr_results = await self.ocr_service.extract_text_with_positions(
                image_data, level="paragraph"
            )
            
            logger.info(f"📝 OCR completed: {len(ocr_results)} text elements extracted")
            
            # 🎯 DB更新: セッション状態にOCR結果を保存
            stage_data = {
                "ocr_elements_count": len(ocr_results),
                "ocr_results": ocr_results,
                "stage_completed_at": datetime.utcnow().isoformat(),
                "processing_duration": time.time() - time.time(),  # 実際の処理時間を計算する場合
                "image_analysis": {
                    "text_density": "high" if len(ocr_results) > 20 else "medium" if len(ocr_results) > 10 else "low",
                    "elements_extracted": len(ocr_results),
                    "preview_available": len(ocr_results) > 0
                }
            }
            
            # セッション状態更新
            db_update_success = await self._update_session_stage_completion(
                session_id, "ocr_completed", stage_data
            )
            
            if not db_update_success:
                logger.warning(f"⚠️ DB update failed for OCR stage, but continuing with SSE broadcast")
            
            # 🎯 SSE配信: OCR完了通知（汎用メソッド使用）
            sse_success = await self.redis_publisher.publish_ocr_completion(
                session_id=session_id,
                ocr_results=ocr_results,
                db_saved=db_update_success
            )
            
            if sse_success:
                logger.info(f"📡 OCR completion broadcasted successfully for session: {session_id}")
            else:
                logger.warning(f"⚠️ SSE broadcast failed for OCR completion: {session_id}")
            
            # 進捗更新
            await self._update_progress(session_id, "ocr", "completed", 25)
            
            return ocr_results
            
        except Exception as e:
            logger.error(f"❌ OCR stage failed for session {session_id}: {e}")
            
            # エラー時のSSE配信
            await self.redis_publisher.publish_error_message(
                session_id=session_id,
                error_type="ocr_processing_failed",
                error_message=str(e),
                task_name="ocr"
            )
            
            raise

    async def _execute_mapping_stage(self, session_id: str, ocr_results: List[Dict]) -> str:
        """
        Stage 2: Mapping実行 → DB更新 → SSE配信
        
        Args:
            session_id: セッションID
            ocr_results: OCR結果リスト
            
        Returns:
            str: フォーマット済みマッピングデータ
        """
        logger.info(f"🗺️ Starting Mapping stage for session: {session_id}")
        
        await self._update_progress(session_id, "mapping", "processing", 35)
        
        try:
            # マッピング処理実行
            formatted_mapping_data = self.mapping_service._format_mapping_data(ocr_results)
            
            logger.info("📋 Mapping completed: Position data formatted for categorization")
            
            # 🎯 DB更新: マッピング結果を保存
            stage_data = {
                "formatted_data_length": len(formatted_mapping_data),
                "mapping_preview": formatted_mapping_data[:500],
                "stage_completed_at": datetime.utcnow().isoformat(),
                "ocr_elements_processed": len(ocr_results),
                "mapping_analysis": {
                    "data_size": len(formatted_mapping_data),
                    "processing_successful": True,
                    "preview_available": True
                }
            }
            
            # セッション状態更新
            db_update_success = await self._update_session_stage_completion(
                session_id, "mapping_completed", stage_data
            )
            
            # 🎯 SSE配信: Mapping完了通知（汎用メソッド使用）
            sse_success = await self.redis_publisher.publish_mapping_completion(
                session_id=session_id,
                mapping_data=formatted_mapping_data,
                db_saved=db_update_success
            )
            
            if sse_success:
                logger.info(f"📡 Mapping completion broadcasted successfully for session: {session_id}")
            else:
                logger.warning(f"⚠️ SSE broadcast failed for mapping completion: {session_id}")
            
            await self._update_progress(session_id, "mapping", "completed", 45)
            
            return formatted_mapping_data
            
        except Exception as e:
            logger.error(f"❌ Mapping stage failed for session {session_id}: {e}")
            
            # エラー時のSSE配信
            await self.redis_publisher.publish_error_message(
                session_id=session_id,
                error_type="mapping_processing_failed",
                error_message=str(e),
                task_name="mapping"
            )
            
            raise

    async def _execute_categorize_stage(self, session_id: str, mapping_data: str) -> Dict[str, Any]:
        """
        Stage 3: Categorize実行 → DB更新 → SSE配信
        
        Args:
            session_id: セッションID
            mapping_data: フォーマット済みマッピングデータ
            
        Returns:
            Dict[str, Any]: カテゴライズ結果と保存されたエンティティ
        """
        logger.info(f"🗂️ Starting Categorize stage for session: {session_id}")
        
        await self._update_progress(session_id, "categorize", "processing", 55)
        
        try:
            # カテゴライズ処理実行
            categorized_results = await self.categorize_service.categorize_menu_structure(
                mapping_data, level="paragraph"
            )
            
            logger.info("🏷️ Categorization completed: Menu structure analyzed")
            
            # メニューアイテムを基本情報でDB保存
            saved_entities = await self._save_basic_menu_items(session_id, categorized_results)
            
            # 保存されたエンティティを辞書形式に変換
            saved_menu_items = [self._entity_to_dict(entity) for entity in saved_entities]
            
            # 🎯 DB更新: カテゴライズ結果とメニューアイテム保存
            stage_data = {
                "categories_found": self._extract_categories(categorized_results),
                "menu_items_saved": len(saved_entities),
                "saved_menu_items": saved_menu_items,
                "stage_completed_at": datetime.utcnow().isoformat(),
                "categorization_analysis": {
                    "categories_detected": len(self._extract_categories(categorized_results)),
                    "items_categorized": len(saved_entities),
                    "processing_successful": True
                }
            }
            
            # セッション状態更新
            db_update_success = await self._update_session_stage_completion(
                session_id, "categorize_completed", stage_data
            )
            
            # 🎯 SSE配信: Categorize完了通知（汎用メソッド使用）
            sse_success = await self.redis_publisher.publish_categorize_completion(
                session_id=session_id,
                categorize_results=categorized_results,
                saved_menu_items=saved_menu_items,
                db_saved=db_update_success
            )
            
            if sse_success:
                logger.info(f"📡 Categorize completion broadcasted successfully for session: {session_id}")
            else:
                logger.warning(f"⚠️ SSE broadcast failed for categorize completion: {session_id}")
            
            await self._update_progress(session_id, "categorize", "completed", 65)
            
            return {
                "categorized_results": categorized_results,
                "saved_entities": saved_entities,
                "saved_menu_items": saved_menu_items,
                "sse_broadcast_success": sse_success  # SSE送信結果を追加
            }
            
        except Exception as e:
            logger.error(f"❌ Categorize stage failed for session {session_id}: {e}")
            
            # エラー時のSSE配信
            await self.redis_publisher.publish_error_message(
                session_id=session_id,
                error_type="categorize_processing_failed",
                error_message=str(e),
                task_name="categorize"
            )
            
            raise

    async def _save_basic_menu_items(self, session_id: str, categorized_results: Dict) -> List:
        """基本メニューアイテムをDBに保存"""
        try:
            from app_2.core.database import async_session_factory
            
            async with async_session_factory() as db_session:
                menu_repository = get_menu_repository(db_session)
                menu_save_service = create_menu_save_service(menu_repository)
                
                saved_entities = await menu_save_service.save_categorized_menu_with_session_id(
                    categorized_results, session_id
                )
                
                logger.info(f"💾 Database save completed: {len(saved_entities)} menu items saved")
                return saved_entities
                
        except Exception as e:
            logger.error(f"❌ Database save failed: {e}")
            return []

    def _entity_to_dict(self, entity) -> Dict[str, Any]:
        """エンティティを辞書形式に変換"""
        return {
            "id": entity.id,
            "name": entity.name,
            "category": entity.category,
            "category_translation": entity.category_translation,
            "price": entity.price,
            "translation": entity.translation,
            "description": entity.description,
            "allergy": entity.allergy,
            "ingredient": entity.ingredient
        }
        
    async def process_menu_image(
        self, 
        session_id: str, 
        image_data: bytes,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        メニュー画像の完全処理フロー（段階別DB更新+SSE配信対応）
        
        Args:
            session_id: セッションID
            image_data: 画像バイナリデータ
            filename: ファイル名（オプション）
            
        Returns:
            Dict[str, Any]: 処理結果
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting enhanced menu processing pipeline: session={session_id}")
            
            # 🔄 重複実行チェック：同じセッションIDで既に処理中/完了していないかを確認
            from app_2.core.database import async_session_factory
            async with async_session_factory() as db_session:
                session_repo = get_session_repository(db_session)
                existing_session = await session_repo.get_by_id(session_id)
                
                if existing_session:
                    # セッションが既に存在する場合の詳細チェック
                    if existing_session.status == SessionStatus.PROCESSING:
                        logger.warning(f"🔄 Session {session_id} is already being processed - rejecting duplicate request")
                        return {
                            "status": "error",
                            "session_id": session_id,
                            "error_type": "duplicate_processing",
                            "error_message": f"Session {session_id} is already being processed",
                            "existing_status": existing_session.status.value,
                            "existing_menu_count": len(existing_session.menu_ids or [])
                        }
                    elif existing_session.status == SessionStatus.COMPLETED:
                        logger.warning(f"🔄 Session {session_id} is already completed - rejecting duplicate request")
                        return {
                            "status": "error", 
                            "session_id": session_id,
                            "error_type": "already_completed",
                            "error_message": f"Session {session_id} is already completed",
                            "existing_status": existing_session.status.value,
                            "existing_menu_count": len(existing_session.menu_ids or [])
                        }
                    else:
                        logger.info(f"🔄 Session {session_id} exists with status {existing_session.status} - allowing reprocessing")
            
            # セッション作成または更新（UPSERT）
            async with async_session_factory() as db_session:
                session_repo = get_session_repository(db_session)
                session_entity = SessionEntity(
                    session_id=session_id,
                    status=SessionStatus.PROCESSING,
                    menu_ids=[],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                # 重複チェック付きでセッションを作成または更新
                await session_repo.upsert_session(session_entity)
                logger.info(f"✅ Session entity created/updated with PROCESSING status: {session_id}")
            
            # 開始通知
            await self.redis_publisher.publish_progress_update(
                session_id=session_id,
                task_name="initial_processing",
                status="started",
                progress_data={
                    "phase": "enhanced_pipeline",
                    "filename": filename or "uploaded_image",
                    "stages": ["ocr", "mapping", "categorize", "parallel_tasks"]
                }
            )
            
            # 🔄 Stage 1: OCR処理 - DB更新とSSE配信を含む
            ocr_results = await self._execute_ocr_stage(session_id, image_data)
            
            # 🔄 Stage 2: Mapping処理 - DB更新とSSE配信を含む
            formatted_mapping_data = await self._execute_mapping_stage(session_id, ocr_results)
            
            # 🔄 Stage 3: Categorize処理 - DB更新とSSE配信を含む
            categorize_data = await self._execute_categorize_stage(session_id, formatted_mapping_data)
            
            # セッション更新（メニューIDを追加）
            saved_entities = categorize_data["saved_entities"]
            if saved_entities:
                menu_ids = [entity.id for entity in saved_entities]
                async with async_session_factory() as db_session:
                    session_repo = get_session_repository(db_session)
                    session_entity = await session_repo.get_by_id(session_id)
                    if session_entity:
                        session_entity.menu_ids = menu_ids
                        session_entity.status = SessionStatus.PROCESSING
                        session_entity.updated_at = datetime.utcnow()
                        await session_repo.update(session_entity)
            
            # Phase 4: 並列タスクトリガー（SSE送信成功を条件とする）
            sse_broadcast_success = categorize_data.get("sse_broadcast_success", False)
            
            if sse_broadcast_success and saved_entities:
                logger.info(f"Phase 4: Triggering parallel tasks after successful SSE broadcast - session={session_id}")
                await self._update_progress(session_id, "parallel_tasks", "started", 90)
                
                # SSE送信が成功した時点でDBは確実にコミット済みなので、追加の確認は不要
                logger.info(f"✅ SSE broadcast confirmed DB commit, triggering parallel tasks with retry-enabled workers")
                await self._trigger_parallel_tasks(session_id, saved_entities)
                
                logger.info(f"🚀 Parallel tasks triggered successfully after SSE confirmation - session={session_id}")
            else:
                if not sse_broadcast_success:
                    logger.warning(f"⚠️ Skipping parallel tasks due to SSE broadcast failure - session={session_id}")
                    await self.redis_publisher.publish_error_message(
                        session_id=session_id,
                        error_type="sse_broadcast_failed",
                        error_message="Categorize SSE broadcast failed, parallel tasks not triggered",
                        task_name="parallel_tasks"
                    )
                elif not saved_entities:
                    logger.warning(f"⚠️ Skipping parallel tasks due to no saved entities - session={session_id}")
                else:
                    logger.warning(f"⚠️ Parallel tasks skipped for unknown reason - session={session_id}")
            
            # 初期処理完了通知
            await self._update_progress(session_id, "initial_processing", "completed", 100)
            
            # 処理時間計算
            processing_time = time.time() - start_time
            
            # レスポンス構築
            result = {
                "session_id": session_id,
                "status": "success",
                "filename": filename,
                "file_size": len(image_data),
                "processing_steps": {
                    "step1_ocr": {
                        "description": "Text extraction with position information and realtime broadcast",
                        "text_count": len(ocr_results),
                        "db_updated": True,
                        "sse_broadcasted": True
                    },
                    "step2_mapping": {
                        "description": "Position-based data formatting with realtime broadcast",
                        "formatted_data_length": len(formatted_mapping_data),
                        "db_updated": True,
                        "sse_broadcasted": True
                    },
                    "step3_categorize": {
                        "description": "Menu structure categorization with realtime broadcast",
                        "results": categorize_data["categorized_results"],
                        "saved_items_count": len(saved_entities),
                        "db_updated": True,
                        "sse_broadcasted": True
                    },
                    "step4_parallel_tasks": {
                        "description": "Triggering parallel processing tasks after SSE broadcast confirmation",
                        "sse_broadcast_success": sse_broadcast_success,
                        "parallel_tasks_triggered": sse_broadcast_success and len(saved_entities) > 0,
                        "trigger_condition": "sse_broadcast_confirmed" if sse_broadcast_success else "sse_broadcast_failed"
                    }
                },
                "final_results": categorize_data["categorized_results"],
                "saved_menu_items": categorize_data["saved_menu_items"],
                "categories": self._extract_categories(categorize_data["categorized_results"]),
                "ocr_elements": len(ocr_results),
                "processing_time": round(processing_time, 2),
                "message": f"Enhanced Pipeline: OCR → Mapping → Categorization with realtime DB updates and SSE broadcasts completed successfully. Parallel tasks {'triggered after SSE confirmation' if sse_broadcast_success else 'skipped due to SSE broadcast failure'}."
            }
            
            # 🔄 処理完了時：セッションステータスをCOMPLETEDに更新
            async with async_session_factory() as db_session:
                session_repo = get_session_repository(db_session)
                session_entity = await session_repo.get_by_id(session_id)
                if session_entity:
                    session_entity.status = SessionStatus.COMPLETED
                    session_entity.updated_at = datetime.utcnow()
                    await session_repo.update(session_entity)
                    logger.info(f"✅ Session {session_id} marked as COMPLETED")
            
            logger.info(f"Enhanced pipeline processing completed: session={session_id}, time={processing_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Enhanced pipeline processing failed: {e}", extra={
                "session_id": session_id,
                "image_size": len(image_data) if image_data else 0
            })
            
            # エラー通知
            await self.redis_publisher.publish_error_message(
                session_id=session_id,
                error_type="enhanced_pipeline_processing_failed",
                error_message=str(e),
                task_name="enhanced_initial_processing"
            )
            
            # セッション状態更新
            try:
                from app_2.core.database import async_session_factory
                async with async_session_factory() as db_session:
                    session_repo = get_session_repository(db_session)
                    session_entity = await session_repo.get_by_id(session_id)
                    if session_entity:
                        session_entity.status = SessionStatus.ERROR
                        session_entity.updated_at = datetime.utcnow()
                        await session_repo.update(session_entity)
            except Exception:
                pass
            
            raise
    
    async def _update_progress(
        self, 
        session_id: str, 
        task_name: str, 
        status: str, 
        progress: int
    ):
        """進捗更新のヘルパーメソッド"""
        await self.redis_publisher.publish_progress_update(
            session_id=session_id,
            task_name=task_name,
            status=status,
            progress_data={"progress": progress}
        )
    
    def _extract_categories(self, categorized_result: Dict[str, Any]) -> List[str]:
        """カテゴライズ結果からカテゴリ名を抽出"""
        try:
            if "menu" in categorized_result and "categories" in categorized_result["menu"]:
                return [
                    cat.get("name", "unknown") 
                    for cat in categorized_result["menu"]["categories"]
                ]
            return []
        except Exception:
            return []
    
    async def _trigger_parallel_tasks(self, session_id: str, menu_entities: List):
        """並列タスクのトリガー（翻訳 + 詳細説明 + アレルギー + 内容物を同時実行）"""
        try:
            # メニューアイテムデータを準備
            menu_items_data = [
                {
                    "id": entity.id,
                    "name": entity.name,
                    "category": entity.category,
                    "price": entity.price,
                    "translation": entity.translation,
                    "category_translation": entity.category_translation
                }
                for entity in menu_entities
            ]
            
            logger.info(f"Triggering parallel tasks with {len(menu_items_data)} menu items")
            
            # 🎯 並列タスクを同時実行：翻訳 + 詳細説明 + アレルギー + 内容物 + 画像検索
            
            # 翻訳タスクをトリガー
            from app_2.tasks.translate_task import translate_menu_task
            translate_task_result = translate_menu_task.delay(session_id, menu_items_data)
            
            # 詳細説明タスクをトリガー（同時実行）
            from app_2.tasks.describe_task import describe_menu_task
            describe_task_result = describe_menu_task.delay(session_id, menu_items_data)
            
            # アレルギー解析タスクをトリガー（同時実行）
            from app_2.tasks.allergen_task import allergen_menu_task
            allergen_task_result = allergen_menu_task.delay(session_id, menu_items_data)
            
            # 内容物解析タスクをトリガー（同時実行）
            from app_2.tasks.ingredient_task import ingredient_menu_task
            ingredient_task_result = ingredient_menu_task.delay(session_id, menu_items_data)
            
            # 画像検索タスクをトリガー（同時実行）
            from app_2.tasks.search_image_task import search_image_menu_task
            search_image_task_result = search_image_menu_task.delay(session_id, menu_items_data)
            
            logger.info(f"✅ Translation task triggered: task_id={translate_task_result.id}")
            logger.info(f"✅ Description task triggered: task_id={describe_task_result.id}")
            logger.info(f"✅ Allergen task triggered: task_id={allergen_task_result.id}")
            logger.info(f"✅ Ingredient task triggered: task_id={ingredient_task_result.id}")
            logger.info(f"✅ Search Image task triggered: task_id={search_image_task_result.id}")
            
            # 並列タスク開始の詳細通知
            await self.redis_publisher.publish_session_message(
                session_id=session_id,
                message_type="parallel_tasks_started",
                data={
                    "parallel_tasks": ["translation", "description", "allergen", "ingredient", "search_image"],
                    "task_ids": {
                        "translation": translate_task_result.id,
                        "description": describe_task_result.id,
                        "allergen": allergen_task_result.id,
                        "ingredient": ingredient_task_result.id,
                        "search_image": search_image_task_result.id
                    },
                    "total_items": len(menu_items_data),
                    "execution_mode": "parallel",
                    "message": f"Translation, description, allergen analysis, ingredient analysis, and image search started in parallel for {len(menu_items_data)} items"
                }
            )
            
            logger.info(f"🚀 All parallel tasks (translation + description + allergen + ingredient + search_image) triggered for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to trigger parallel tasks: {e}")
            
            await self.redis_publisher.publish_error_message(
                session_id=session_id,
                error_type="parallel_tasks_trigger_failed", 
                error_message=str(e),
                task_name="parallel_tasks"
            )


# シングルトンインスタンス
_pipeline_instance = None

def get_menu_processing_pipeline() -> MenuProcessingPipeline:
    """MenuProcessingPipelineのシングルトンインスタンスを取得"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = MenuProcessingPipeline()
    return _pipeline_instance 