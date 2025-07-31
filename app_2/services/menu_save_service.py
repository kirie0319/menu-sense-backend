"""
Menu Save Service - OCRカテゴライズ結果をDBに保存
"""
import uuid
from typing import List, Dict, Any
from app_2.domain.entities.menu_entity import MenuEntity
from app_2.domain.repositories.menu_repository import MenuRepositoryInterface
from app_2.utils.logger import get_logger

logger = get_logger("menu_save_service")


class MenuSaveService:
    """
    メニューカテゴライズ結果をDBに保存するサービス
    """
    
    def __init__(self, menu_repository: MenuRepositoryInterface):
        """
        MenuSaveServiceを初期化
        
        Args:
            menu_repository: メニューリポジトリ
        """
        self.menu_repository = menu_repository
        logger.info("MenuSaveService initialized")
    
    async def save_categorized_menu(self, categorize_result: Dict[str, Any], session_id: str = None) -> List[MenuEntity]:
        """
        カテゴライズ結果をmenuテーブルに保存（重複チェック機能付き）
        
        Args:
            categorize_result: OCRカテゴライズ結果
            session_id: セッションID（重複チェック用）
            
        Returns:
            List[MenuEntity]: 保存されたメニューエンティティのリスト
        """
        try:
            # 🔍 デバッグ：受信したカテゴライズ結果を詳細ログ出力
            logger.info(f"🔍 [DEBUG] Received categorize_result for session {session_id}:")
            if "menu" in categorize_result and "categories" in categorize_result["menu"]:
                categories = categorize_result["menu"]["categories"]
                logger.info(f"🔍 [DEBUG] Found {len(categories)} categories:")
                for i, category in enumerate(categories):
                    cat_name = category.get("name", f"Unknown_{i}")
                    items = category.get("items", [])
                    logger.info(f"🔍 [DEBUG]   Category {i+1}: {cat_name} with {len(items)} items")
                    for j, item in enumerate(items):
                        item_name = item.get("name", "").strip()
                        item_price = item.get("price", "")
                        logger.info(f"🔍 [DEBUG]     Item {j+1}: '{item_name}' - {item_price}")
            
            saved_entities = []
            
            if "menu" not in categorize_result:
                logger.warning("No menu data found in categorize result")
                return saved_entities
            
            menu_data = categorize_result["menu"]
            categories = menu_data.get("categories", [])
            
            logger.info(f"Starting to save {len(categories)} categories to menu table")
            
            # 🔄 重複チェック用セット（name + category の組み合わせ）
            saved_items_set = set()
            
            # 🚀 一括保存用のエンティティリストを準備
            entities_to_save = []
            
            # カテゴリごとに商品を処理
            for category in categories:
                category_name = category.get("name", "")
                category_japanese = category.get("japanese_name", "")
                items = category.get("items", [])
                
                logger.info(f"Processing category: {category_japanese} ({category_name}) with {len(items)} items")
                
                # カテゴリ内の各商品をエンティティに変換
                for item in items:
                    try:
                        item_name = item.get("name", "").strip()
                        
                        # 🔄 重複チェック：名前とカテゴリの組み合わせをチェック
                        item_key = f"{item_name}||{category_name}".lower()
                        
                        if item_key in saved_items_set:
                            logger.warning(f"🔄 Duplicate item skipped: '{item_name}' in category '{category_name}'")
                            continue
                        
                        # 名前が空の場合もスキップ
                        if not item_name:
                            logger.warning("🔄 Empty item name skipped")
                            continue
                        
                        # 重複チェック用セットに追加
                        saved_items_set.add(item_key)
                        
                        menu_entity = MenuEntity(
                            id=str(uuid.uuid4()),  # 新しいUUIDを生成
                            name=item_name,
                            translation=None,  # 翻訳は後で翻訳タスクで更新
                            category=category_name,
                            category_translation=None,
                            price=item.get("price", ""),
                            description=None,  # 説明は後で説明タスクで更新
                            allergy=None,  # アレルギー情報は後でアレルギータスクで更新
                            ingredient=None,  # 原材料は後で原材料タスクで更新
                            search_engine=None,  # 検索結果は後で検索タスクで更新
                            gen_image=None  # 生成画像は後で画像生成タスクで更新
                        )
                        
                        # 一括保存用リストに追加
                        entities_to_save.append(menu_entity)
                        
                        logger.debug(f"✅ Prepared menu item for bulk save: {menu_entity.name} - {menu_entity.price}")
                        
                    except Exception as e:
                        logger.error(f"Failed to prepare menu item {item}: {e}")
                        continue
            
            # 🚀 一括保存実行（パフォーマンス最適化）
            if entities_to_save:
                if session_id:
                    saved_entities = await self.menu_repository.bulk_save_with_session(entities_to_save, session_id)
                    logger.info(f"🚀 Bulk save completed: {len(saved_entities)} items in single transaction")
                else:
                    # session_idがない場合は個別保存にフォールバック
                    for entity in entities_to_save:
                        saved_entity = await self.menu_repository.save(entity)
                        saved_entities.append(saved_entity)
                    logger.info(f"Individual save completed: {len(saved_entities)} items")
            else:
                logger.warning("No items to save after duplicate filtering")
            
            # 🔄 重複除去結果をログ出力
            total_items_processed = sum(len(cat.get("items", [])) for cat in categories)
            duplicates_removed = total_items_processed - len(saved_entities)
            
            logger.info(f"✅ Save completed: {len(saved_entities)} unique items saved (removed {duplicates_removed} duplicates)")
            return saved_entities
            
        except Exception as e:
            logger.error(f"Failed to save categorized menu: {e}")
            raise
    
    async def save_categorized_menu_with_session_id(
        self, 
        categorize_result: Dict[str, Any], 
        session_id: str
    ) -> List[MenuEntity]:
        """
        セッションIDを含むカテゴライズ結果をmenuテーブルに保存
        
        Args:
            categorize_result: OCRカテゴライズ結果
            session_id: 分析セッションID（識別用）
            
        Returns:
            List[MenuEntity]: 保存されたメニューエンティティのリスト
        """
        try:
            logger.info(f"Saving categorized menu with session_id: {session_id}")
            saved_entities = await self.save_categorized_menu(categorize_result, session_id)
            
            # セッションIDを商品名やカテゴリに含める場合の処理
            # （必要に応じて後で拡張）
            
            return saved_entities
            
        except Exception as e:
            logger.error(f"Failed to save categorized menu with session_id {session_id}: {e}")
            raise


# ファクトリー関数
def create_menu_save_service(menu_repository: MenuRepositoryInterface) -> MenuSaveService:
    """
    MenuSaveServiceのインスタンスを作成
    
    Args:
        menu_repository: メニューリポジトリ
        
    Returns:
        MenuSaveService: メニュー保存サービス
    """
    return MenuSaveService(menu_repository) 