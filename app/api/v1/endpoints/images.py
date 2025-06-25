"""
S3画像管理のためのAPIエンドポイント
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

from app.services.s3_storage import s3_storage

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/list", response_model=Dict[str, Any])
async def list_images(
    prefix: Optional[str] = Query(None, description="フィルタリング用のプレフィックス"),
    max_keys: int = Query(100, description="最大取得件数", le=1000)
):
    """
    S3バケットから画像リストを取得
    """
    try:
        images = s3_storage.list_images(prefix=prefix, max_keys=max_keys)
        
        return {
            "success": True,
            "count": len(images),
            "images": images,
            "bucket": s3_storage.bucket_name,
            "prefix": prefix or s3_storage.image_prefix
        }
    except Exception as e:
        logger.error(f"❌ Error listing images: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list images: {str(e)}")

@router.get("/recent", response_model=Dict[str, Any])
async def get_recent_images(
    limit: int = Query(20, description="取得件数", le=100)
):
    """
    最新の画像を取得
    """
    try:
        images = s3_storage.get_recent_images(limit=limit)
        
        return {
            "success": True,
            "count": len(images),
            "images": images,
            "bucket": s3_storage.bucket_name,
            "limit": limit
        }
    except Exception as e:
        logger.error(f"❌ Error getting recent images: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get recent images: {str(e)}")

@router.get("/search", response_model=Dict[str, Any])
async def search_images(
    filename: str = Query(..., description="ファイル名検索パターン"),
):
    """
    ファイル名で画像を検索
    """
    try:
        images = s3_storage.search_images_by_filename(filename)
        
        return {
            "success": True,
            "count": len(images),
            "images": images,
            "search_pattern": filename,
            "bucket": s3_storage.bucket_name
        }
    except Exception as e:
        logger.error(f"❌ Error searching images: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to search images: {str(e)}")

@router.get("/by-date", response_model=Dict[str, Any])
async def get_images_by_date(
    date: str = Query(..., description="日付 (YYYY-MM-DD または YYYY/MM/DD)")
):
    """
    指定日付の画像を取得
    """
    try:
        images = s3_storage.list_images_by_date(date)
        
        return {
            "success": True,
            "count": len(images),
            "images": images,
            "date": date,
            "bucket": s3_storage.bucket_name
        }
    except Exception as e:
        logger.error(f"❌ Error getting images by date: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get images by date: {str(e)}")

@router.get("/info/{key:path}", response_model=Dict[str, Any])
async def get_image_info(key: str):
    """
    S3キーから画像情報を取得
    """
    try:
        image_info = s3_storage.get_image_by_key(key)
        
        if not image_info:
            raise HTTPException(status_code=404, detail="Image not found")
        
        return {
            "success": True,
            "image": image_info,
            "bucket": s3_storage.bucket_name
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting image info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get image info: {str(e)}")

@router.get("/gallery", response_model=Dict[str, Any])
async def get_image_gallery(
    page: int = Query(1, description="ページ番号", ge=1),
    per_page: int = Query(20, description="1ページあたりの件数", le=100),
    sort_by: str = Query("recent", description="ソート方法: recent, name, size")
):
    """
    画像ギャラリー用のページネーション付きリストを取得
    """
    try:
        if sort_by == "recent":
            # 最新順で多めに取得
            all_images = s3_storage.list_images(max_keys=per_page * 10)
            all_images.sort(key=lambda x: x['last_modified'], reverse=True)
        elif sort_by == "name":
            all_images = s3_storage.list_images()
            all_images.sort(key=lambda x: x['filename'])
        elif sort_by == "size":
            all_images = s3_storage.list_images()
            all_images.sort(key=lambda x: x['size'], reverse=True)
        else:
            all_images = s3_storage.get_recent_images(limit=per_page * 10)
        
        # ページネーション
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_images = all_images[start_idx:end_idx]
        
        total_pages = (len(all_images) + per_page - 1) // per_page
        
        return {
            "success": True,
            "images": paginated_images,
            "pagination": {
                "current_page": page,
                "per_page": per_page,
                "total_items": len(all_images),
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            },
            "sort_by": sort_by,
            "bucket": s3_storage.bucket_name
        }
    except Exception as e:
        logger.error(f"❌ Error getting image gallery: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get image gallery: {str(e)}")

@router.get("/stats", response_model=Dict[str, Any])
async def get_image_stats():
    """
    S3画像統計情報を取得
    """
    try:
        all_images = s3_storage.list_images()
        
        if not all_images:
            return {
                "success": True,
                "stats": {
                    "total_images": 0,
                    "total_size": 0,
                    "average_size": 0,
                    "dates": [],
                    "latest_upload": None
                },
                "bucket": s3_storage.bucket_name
            }
        
        # 統計計算
        total_size = sum(img['size'] for img in all_images)
        average_size = total_size // len(all_images) if all_images else 0
        
        # 日付統計
        dates = {}
        for img in all_images:
            date_key = img['date_path']
            if date_key not in dates:
                dates[date_key] = 0
            dates[date_key] += 1
        
        # 最新アップロード
        latest_image = max(all_images, key=lambda x: x['last_modified'])
        
        return {
            "success": True,
            "stats": {
                "total_images": len(all_images),
                "total_size": total_size,
                "average_size": average_size,
                "dates": dates,
                "latest_upload": {
                    "filename": latest_image['filename'],
                    "date": latest_image['last_modified'],
                    "url": latest_image['url']
                }
            },
            "bucket": s3_storage.bucket_name
        }
    except Exception as e:
        logger.error(f"❌ Error getting image stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get image stats: {str(e)}")

@router.get("/status", response_model=Dict[str, Any])
async def get_s3_status():
    """
    S3接続状態を確認
    """
    try:
        bucket_info = s3_storage.get_bucket_info()
        is_available = s3_storage.is_available()
        
        return {
            "success": True,
            "s3_available": is_available,
            "bucket_info": bucket_info,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"❌ Error getting S3 status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get S3 status: {str(e)}") 