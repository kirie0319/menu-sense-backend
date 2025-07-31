"""
Menu Repository Implementation - Infrastructure Layer
Concrete implementation of MenuRepositoryInterface using SQLAlchemy (MVP Simplified)
"""

from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app_2.domain.entities.menu_entity import MenuEntity
from app_2.domain.repositories.menu_repository import MenuRepositoryInterface
from app_2.infrastructure.models.menu_model import MenuModel
from app_2.utils.logger import get_logger

logger = get_logger("menu_repository")


class MenuRepositoryImpl(MenuRepositoryInterface):
    """
    メニューリポジトリ具体実装（MVP版）
    
    最小限のCRUD操作を実装
    """
    
    def __init__(self, session: AsyncSession):
        """
        Args:
            session: SQLAlchemy AsyncSession
        """
        self.session = session

    async def save(self, menu: MenuEntity) -> MenuEntity:
        """
        メニューを保存（従来のメソッド - 非推奨）
        
        Note: session_idが必要なため、save_with_sessionの使用を推奨
        
        Args:
            menu: 保存するメニューエンティティ
            
        Returns:
            MenuEntity: 保存されたメニューエンティティ
        """
        raise NotImplementedError("Use save_with_session instead. Session ID is required.")

    async def save_with_session(self, menu: MenuEntity, session_id: str) -> MenuEntity:
        """
        セッションID付きでメニューを保存
        
        Args:
            menu: 保存するメニューエンティティ
            session_id: セッションID
            
        Returns:
            MenuEntity: 保存されたメニューエンティティ
        """
        try:
            # EntityをSessionつきModelに変換
            menu_model = MenuModel.from_entity_with_session(menu, session_id)
            
            # データベースに追加
            self.session.add(menu_model)
            await self.session.commit()
            await self.session.refresh(menu_model)
            
            logger.info(f"Menu saved with session: {menu.id} -> {session_id}")
            return menu_model.to_entity()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to save menu {menu.id} with session {session_id}: {e}")
            raise

    async def bulk_save_with_session(self, menus: List[MenuEntity], session_id: str) -> List[MenuEntity]:
        """
        複数メニューの一括保存（パフォーマンス最適化版）
        
        37個のメニューを個別に保存すると37回のcommitが発生し31秒の遅延が発生します。
        一括保存により1回のcommitで処理時間を大幅に短縮します。
        
        Args:
            menus: 保存するメニューエンティティのリスト
            session_id: セッションID
            
        Returns:
            List[MenuEntity]: 保存されたメニューエンティティのリスト
        """
        if not menus:
            return []
        
        try:
            saved_entities = []
            menu_models = []
            
            # 全てのエンティティをモデルに変換
            for menu in menus:
                menu_model = MenuModel.from_entity_with_session(menu, session_id)
                menu_models.append(menu_model)
                self.session.add(menu_model)
            
            # 一括でコミット（1回のみ）
            await self.session.commit()
            
            # 一括でリフレッシュ
            for menu_model in menu_models:
                await self.session.refresh(menu_model)
                saved_entities.append(menu_model.to_entity())
            
            logger.info(f"Bulk saved {len(saved_entities)} menus with session: {session_id}")
            return saved_entities
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to bulk save {len(menus)} menus with session {session_id}: {e}")
            raise

    async def get_by_id(self, menu_id: str) -> Optional[MenuEntity]:
        """
        IDでメニューを取得
        
        Args:
            menu_id: メニューID
            
        Returns:
            Optional[MenuEntity]: 見つかったメニューエンティティ
        """
        try:
            stmt = select(MenuModel).where(MenuModel.id == menu_id)
            result = await self.session.execute(stmt)
            menu_model = result.scalar_one_or_none()
            
            return menu_model.to_entity() if menu_model else None
            
        except Exception as e:
            logger.error(f"Failed to get menu {menu_id}: {e}")
            raise

    async def get_by_session_id(self, session_id: str) -> List[MenuEntity]:
        """
        セッションIDでメニュー一覧を取得
        
        Args:
            session_id: セッションID
            
        Returns:
            List[MenuEntity]: 該当するメニューエンティティ一覧
        """
        try:
            stmt = select(MenuModel).where(MenuModel.session_id == session_id)
            result = await self.session.execute(stmt)
            menu_models = result.scalars().all()
            
            return [model.to_entity() for model in menu_models]
            
        except Exception as e:
            logger.error(f"Failed to get menus by session {session_id}: {e}")
            raise

    async def update(self, menu: MenuEntity) -> MenuEntity:
        """
        メニューを更新（統一メソッド）
        
        Args:
            menu: 更新するメニューエンティティ
            
        Returns:
            MenuEntity: 更新されたメニューエンティティ
        """
        try:
            stmt = select(MenuModel).where(MenuModel.id == menu.id)
            result = await self.session.execute(stmt)
            menu_model = result.scalar_one_or_none()
            
            if not menu_model:
                raise ValueError(f"Menu not found: {menu.id}")
            
            # 全フィールド一括更新
            menu_model.update_from_entity(menu)
            await self.session.commit()
            await self.session.refresh(menu_model)
            
            logger.info(f"Menu updated: {menu.id}")
            return menu_model.to_entity()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update menu {menu.id}: {e}")
            raise

    async def update_partial(self, menu_id: str, fields: dict) -> Optional[MenuEntity]:
        """
        メニューの部分更新（特定フィールドのみ更新）
        
        Args:
            menu_id: メニューID
            fields: 更新するフィールドの辞書
            
        Returns:
            Optional[MenuEntity]: 更新されたメニューエンティティ
        """
        try:
            stmt = select(MenuModel).where(MenuModel.id == menu_id)
            result = await self.session.execute(stmt)
            menu_model = result.scalar_one_or_none()
            
            if not menu_model:
                logger.warning(f"Menu not found for partial update: {menu_id}")
                return None
            
            # 指定されたフィールドのみ更新
            for field_name, field_value in fields.items():
                if hasattr(menu_model, field_name):
                    setattr(menu_model, field_name, field_value)
                    logger.debug(f"Updated field {field_name} for menu {menu_id}")
                else:
                    logger.warning(f"Unknown field {field_name} for menu {menu_id}")
            
            # updated_at は常に更新
            menu_model.updated_at = datetime.utcnow()
            
            await self.session.commit()
            await self.session.refresh(menu_model)
            
            logger.info(f"Menu partially updated: {menu_id}, fields: {list(fields.keys())}")
            return menu_model.to_entity()
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to partially update menu {menu_id}: {e}")
            raise

    async def delete(self, menu_id: str) -> bool:
        """
        メニューを削除
        
        Args:
            menu_id: 削除するメニューID
            
        Returns:
            bool: 削除が成功したか
        """
        try:
            stmt = delete(MenuModel).where(MenuModel.id == menu_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            
            deleted_count = result.rowcount
            success = deleted_count > 0
            
            if success:
                logger.info(f"Menu deleted: {menu_id}")
            else:
                logger.warning(f"Menu not found for deletion: {menu_id}")
            
            return success
            
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete menu {menu_id}: {e}")
            raise

    async def update_search_engine_result(self, menu_id: str, search_result_json: Optional[str]) -> Optional[MenuEntity]:
        """
        メニューの画像検索結果を更新
        
        Args:
            menu_id: メニューID
            search_result_json: 画像検索結果JSON文字列
            
        Returns:
            Optional[MenuEntity]: 更新されたメニューエンティティ
        """
        try:
            return await self.update_partial(menu_id, {"search_engine": search_result_json})
            
        except Exception as e:
            logger.error(f"Failed to update search engine result for menu {menu_id}: {e}")
            raise

    async def update_translation(self, menu_id: str, translation: str) -> Optional[MenuEntity]:
        """
        メニューの翻訳を更新
        
        Args:
            menu_id: メニューID
            translation: 翻訳結果
            
        Returns:
            Optional[MenuEntity]: 更新されたメニューエンティティ
        """
        try:
            return await self.update_partial(menu_id, {"translation": translation})
            
        except Exception as e:
            logger.error(f"Failed to update translation for menu {menu_id}: {e}")
            raise

    async def update_description(self, menu_id: str, description: str) -> Optional[MenuEntity]:
        """
        メニューの説明を更新
        
        Args:
            menu_id: メニューID
            description: 説明文
            
        Returns:
            Optional[MenuEntity]: 更新されたメニューエンティティ
        """
        try:
            return await self.update_partial(menu_id, {"description": description})
            
        except Exception as e:
            logger.error(f"Failed to update description for menu {menu_id}: {e}")
            raise

    async def update_allergy_info(self, menu_id: str, allergy_info: str) -> Optional[MenuEntity]:
        """
        メニューのアレルギー情報を更新
        
        Args:
            menu_id: メニューID
            allergy_info: アレルギー情報
            
        Returns:
            Optional[MenuEntity]: 更新されたメニューエンティティ
        """
        try:
            return await self.update_partial(menu_id, {"allergy": allergy_info})
            
        except Exception as e:
            logger.error(f"Failed to update allergy info for menu {menu_id}: {e}")
            raise

    async def update_ingredient_info(self, menu_id: str, ingredient_info: str) -> Optional[MenuEntity]:
        """
        メニューの成分情報を更新
        
        Args:
            menu_id: メニューID
            ingredient_info: 成分情報
            
        Returns:
            Optional[MenuEntity]: 更新されたメニューエンティティ
        """
        try:
            return await self.update_partial(menu_id, {"ingredient": ingredient_info})
            
        except Exception as e:
            logger.error(f"Failed to update ingredient info for menu {menu_id}: {e}")
            raise
    
    async def get_menu_image_urls(self, menu_id: str) -> Optional[List[str]]:
        """
        メニューの画像URLリストを取得
        
        Args:
            menu_id: メニューID
            
        Returns:
            Optional[List[str]]: 画像URLリスト（見つからない場合はNone）
        """
        try:
            stmt = select(MenuModel.search_engine).where(MenuModel.id == menu_id)
            result = await self.session.execute(stmt)
            search_engine_json = result.scalar_one_or_none()
            
            if not search_engine_json:
                logger.warning(f"No search engine data found for menu {menu_id}")
                return None
            
            # JSONからURLリストを抽出
            import json
            try:
                image_urls = json.loads(search_engine_json)
                if isinstance(image_urls, list):
                    return image_urls
                else:
                    logger.warning(f"Search engine data is not a list for menu {menu_id}")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse search engine JSON for menu {menu_id}: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to get image URLs for menu {menu_id}: {e}")
            return None
    
    async def get_session_menu_images(self, session_id: str) -> List[dict]:
        """
        セッション内の全メニューの画像URLリストを取得
        
        Args:
            session_id: セッションID
            
        Returns:
            List[dict]: メニューIDと画像URLリストのマッピング
        """
        try:
            stmt = select(
                MenuModel.id, 
                MenuModel.name, 
                MenuModel.search_engine
            ).where(MenuModel.session_id == session_id)
            
            result = await self.session.execute(stmt)
            rows = result.all()
            
            menu_images = []
            for row in rows:
                menu_id, menu_name, search_engine_json = row
                image_urls = []
                
                if search_engine_json:
                    try:
                        import json
                        parsed_urls = json.loads(search_engine_json)
                        if isinstance(parsed_urls, list):
                            image_urls = parsed_urls
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse search engine JSON for menu {menu_id}")
                
                menu_images.append({
                    "menu_id": menu_id,
                    "menu_name": menu_name,
                    "image_urls": image_urls,
                    "image_count": len(image_urls)
                })
            
            logger.info(f"Retrieved image data for {len(menu_images)} menus in session {session_id}")
            return menu_images
            
        except Exception as e:
            logger.error(f"Failed to get session menu images for {session_id}: {e}")
            return [] 