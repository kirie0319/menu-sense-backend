"""
Menu Images API - Menu Processor v2
メニュー画像URL取得用API エンドポイント
"""
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app_2.infrastructure.repositories.menu_repository_impl import MenuRepositoryImpl
from app_2.domain.repositories.menu_repository import MenuRepositoryInterface
from app_2.core.database import get_db_session
from app_2.utils.logger import get_logger

logger = get_logger("menu_images_api")

router = APIRouter(prefix="/menu-images", tags=["menu-images"])


def get_menu_repository(
    db_session: AsyncSession = Depends(get_db_session)
) -> MenuRepositoryInterface:
    """Menu Repository依存性インジェクション（修正版）"""
    return MenuRepositoryImpl(db_session)


@router.get("/menus/{session_id}")
async def get_session_menus(
    session_id: str,
    repo: MenuRepositoryInterface = Depends(get_menu_repository)
) -> Dict[str, Any]:
    """
    セッション内の全メニューデータを取得
    
    Args:
        session_id: セッションID
        repo: メニューリポジトリ
        
    Returns:
        Dict: セッション内全メニューデータ
    """
    try:
        logger.info(f"Getting menus for session: {session_id}")
        
        # セッション内の全メニューを取得
        menu_entities = await repo.get_by_session_id(session_id)
        
        if not menu_entities:
            return {
                "session_id": session_id,
                "menus": [],
                "total_count": 0,
                "status": "success",
                "message": "No menus found for this session"
            }
        
        # メニューデータをレスポンス形式に変換
        menus = []
        for entity in menu_entities:
            menu_data = {
                "id": entity.id,
                "name": entity.name,
                "translation": entity.translation,
                "category": entity.category,
                "category_translation": entity.category_translation,
                "price": entity.price,
                "description": entity.description,
                "allergy": entity.allergy,
                "ingredient": entity.ingredient,
                "search_engine": entity.search_engine,
                "gen_image": entity.gen_image
                # Note: created_at, updated_atはMenuEntityに存在しないため除外
            }
            menus.append(menu_data)
        
        return {
            "session_id": session_id,
            "menus": menus,
            "total_count": len(menus),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get menus for session {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{menu_id}")
async def get_menu_images(
    menu_id: str,
    repo: MenuRepositoryInterface = Depends(get_menu_repository)
) -> Dict[str, Any]:
    """
    個別メニューの画像URLリストを取得
    
    Args:
        menu_id: メニューID
        repo: メニューリポジトリ
        
    Returns:
        Dict: メニューの画像URLリスト
    """
    try:
        logger.info(f"Getting images for menu: {menu_id}")
        
        # 画像URLリストを取得
        image_urls = await repo.get_menu_image_urls(menu_id)
        
        if image_urls is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Images not found for menu: {menu_id}"
            )
        
        # メニュー基本情報も取得
        menu_entity = await repo.get_by_id(menu_id)
        if not menu_entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Menu not found: {menu_id}"
            )
        
        return {
            "menu_id": menu_id,
            "menu_name": menu_entity.name,
            "category": menu_entity.category,
            "image_urls": image_urls,
            "image_count": len(image_urls),
            "status": "success"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get images for menu {menu_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/session/{session_id}")
async def get_session_menu_images(
    session_id: str,
    repo: MenuRepositoryInterface = Depends(get_menu_repository)
) -> Dict[str, Any]:
    """
    セッション内の全メニューの画像URLリストを取得
    
    Args:
        session_id: セッションID
        repo: メニューリポジトリ
        
    Returns:
        Dict: セッション内全メニューの画像URLリスト
    """
    try:
        logger.info(f"Getting images for session: {session_id}")
        
        # セッション内の全メニュー画像データを取得
        menu_images = await repo.get_session_menu_images(session_id)
        
        if not menu_images:
            return {
                "session_id": session_id,
                "menus": [],
                "total_menus": 0,
                "total_images": 0,
                "status": "success",
                "message": "No menus found for this session"
            }
        
        # 統計情報を計算
        total_images = sum(menu["image_count"] for menu in menu_images)
        menus_with_images = len([menu for menu in menu_images if menu["image_count"] > 0])
        
        return {
            "session_id": session_id,
            "menus": menu_images,
            "total_menus": len(menu_images),
            "menus_with_images": menus_with_images,
            "total_images": total_images,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get session menu images for {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/session/{session_id}/gallery")
async def get_session_image_gallery(
    session_id: str,
    repo: MenuRepositoryInterface = Depends(get_menu_repository)
) -> Dict[str, Any]:
    """
    セッション内の全画像をギャラリー形式で取得
    
    Args:
        session_id: セッションID
        repo: メニューリポジトリ
        
    Returns:
        Dict: ギャラリー形式の画像データ
    """
    try:
        logger.info(f"Getting image gallery for session: {session_id}")
        
        # セッション内の全メニュー画像データを取得
        menu_images = await repo.get_session_menu_images(session_id)
        
        # ギャラリー用データを構築
        gallery_items = []
        for menu in menu_images:
            for idx, image_url in enumerate(menu["image_urls"]):
                gallery_items.append({
                    "image_url": image_url,
                    "menu_id": menu["menu_id"],
                    "menu_name": menu["menu_name"],
                    "image_index": idx + 1,
                    "total_images_for_menu": len(menu["image_urls"])
                })
        
        return {
            "session_id": session_id,
            "gallery": gallery_items,
            "total_images": len(gallery_items),
            "total_menus": len(menu_images),
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"Failed to get image gallery for {session_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        ) 