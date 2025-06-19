"""
タスク共通処理ユーティリティ
"""

from typing import Dict, List, Any, Optional
import uuid
import logging
import json
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

# Redis接続
try:
    redis_client = redis.from_url(settings.REDIS_URL)
except Exception as e:
    logger.error(f"Redis connection failed: {e}")
    redis_client = None

def create_image_chunks(final_menu: Dict[str, List[Dict]], chunk_size: int = 3, min_chunks: int = None) -> List[Dict]:
    """
    メニューデータをチャンクに分割（ワーカー均等活用対応）
    
    Args:
        final_menu: カテゴリ別メニューデータ
        chunk_size: 基本チャンクサイズ
        min_chunks: 最小チャンク数（ワーカー均等活用用）
        
    Returns:
        チャンク情報のリスト
    """
    # 全アイテム数を計算
    total_items = sum(len(items) for items in final_menu.values() if items)
    
    if total_items == 0:
        return []
    
    # 最小チャンク数の設定（利用可能ワーカー数に基づく）
    if min_chunks is None:
        min_chunks = min(settings.IMAGE_CONCURRENT_CHUNK_LIMIT, total_items)
    
    # 強制的なワーカー均等活用モード
    if settings.FORCE_WORKER_UTILIZATION and settings.DYNAMIC_CHUNK_SIZING:
        # 理想的なチャンク数を計算（ワーカー数の最小倍数）
        ideal_chunks = max(
            settings.IMAGE_CONCURRENT_CHUNK_LIMIT,  # 最低でもワーカー数分
            int(settings.IMAGE_CONCURRENT_CHUNK_LIMIT * settings.MIN_CHUNKS_PER_WORKER)  # ワーカーあたりの最小チャンク数
        )
        
        # アイテム数が多い場合は効率性も考慮
        if total_items > settings.IMAGE_CONCURRENT_CHUNK_LIMIT * 2:
            ideal_chunks = min(ideal_chunks, total_items)
        
        # 最適なチャンクサイズを計算
        optimal_chunk_size = max(1, total_items // ideal_chunks)
        
        logger.info(f"Force worker utilization: {total_items} items → target {ideal_chunks} chunks (chunk_size={optimal_chunk_size})")
    else:
        # 従来のロジック
        if total_items <= settings.IMAGE_CONCURRENT_CHUNK_LIMIT:
            # アイテム数がワーカー数以下の場合：1アイテム1チャンク
            optimal_chunk_size = 1
        else:
            # 全ワーカーを均等に使用するためのチャンクサイズ
            optimal_chunk_size = max(1, total_items // settings.IMAGE_CONCURRENT_CHUNK_LIMIT)
            # 基本チャンクサイズも考慮
            optimal_chunk_size = min(optimal_chunk_size, chunk_size)
    
    chunks = []
    chunk_id = 1
    
    for category, items in final_menu.items():
        if not items:  # 空のカテゴリはスキップ
            continue
            
        # カテゴリ内のアイテムをチャンクに分割
        for i in range(0, len(items), optimal_chunk_size):
            chunk_items = items[i:i + optimal_chunk_size]
            
            chunk_info = {
                "chunk_id": chunk_id,
                "category": category,
                "items": chunk_items,
                "items_count": len(chunk_items),
                "category_chunk_index": (i // optimal_chunk_size) + 1,
                "total_category_chunks": (len(items) + optimal_chunk_size - 1) // optimal_chunk_size,
                "optimal_chunk_size": optimal_chunk_size,
                "worker_utilization_strategy": True,
                "force_utilization": settings.FORCE_WORKER_UTILIZATION
            }
            
            chunks.append(chunk_info)
            chunk_id += 1
    
    # 強制均等活用：チャンク数が不足している場合の追加分割
    if settings.FORCE_WORKER_UTILIZATION and len(chunks) < settings.IMAGE_CONCURRENT_CHUNK_LIMIT:
        original_chunks = chunks.copy()
        chunks = []
        chunk_id = 1
        
        # より細かく分割し直す
        micro_chunk_size = max(1, total_items // settings.IMAGE_CONCURRENT_CHUNK_LIMIT)
        
        for category, items in final_menu.items():
            if not items:
                continue
                
            for i in range(0, len(items), micro_chunk_size):
                chunk_items = items[i:i + micro_chunk_size]
                
                chunk_info = {
                    "chunk_id": chunk_id,
                    "category": category,
                    "items": chunk_items,
                    "items_count": len(chunk_items),
                    "category_chunk_index": (i // micro_chunk_size) + 1,
                    "total_category_chunks": (len(items) + micro_chunk_size - 1) // micro_chunk_size,
                    "optimal_chunk_size": micro_chunk_size,
                    "worker_utilization_strategy": True,
                    "force_utilization": True,
                    "micro_chunking": True
                }
                
                chunks.append(chunk_info)
                chunk_id += 1
        
        logger.info(f"Micro-chunking applied: {len(original_chunks)} → {len(chunks)} chunks for better worker utilization")
    
    # 全体の総チャンク数を各チャンクに設定
    total_chunks = len(chunks)
    for chunk in chunks:
        chunk["total_chunks"] = total_chunks
    
    # ワーカー活用情報をログ出力
    expected_workers = min(total_chunks, settings.IMAGE_CONCURRENT_CHUNK_LIMIT)
    utilization_rate = (expected_workers / settings.IMAGE_CONCURRENT_CHUNK_LIMIT) * 100
    
    logger.info(f"Chunk creation: {total_items} items → {total_chunks} chunks (chunk_size={optimal_chunk_size}, expected_workers={expected_workers}, utilization={utilization_rate:.1f}%)")
    
    return chunks

def validate_menu_data(final_menu: Dict[str, List[Dict]]) -> bool:
    """
    メニューデータの妥当性をチェック
    
    Args:
        final_menu: 検証対象のメニューデータ
        
    Returns:
        妥当性チェック結果
    """
    if not isinstance(final_menu, dict):
        logger.error("Menu data must be a dictionary")
        return False
    
    if not final_menu:
        logger.error("Menu data is empty")
        return False
    
    # 各カテゴリとアイテムの検証
    for category, items in final_menu.items():
        if not isinstance(items, list):
            logger.error(f"Category '{category}' items must be a list")
            return False
        
        for item in items:
            if not isinstance(item, dict):
                logger.error(f"Item in category '{category}' must be a dictionary")
                return False
            
            # 必須フィールドの確認
            required_fields = ["japanese_name", "english_name"]
            for field in required_fields:
                if field not in item:
                    logger.error(f"Item in category '{category}' missing required field: {field}")
                    return False
                    
                if not isinstance(item[field], str) or not item[field].strip():
                    logger.error(f"Field '{field}' in category '{category}' must be a non-empty string")
                    return False
    
    return True

def generate_job_id() -> str:
    """ユニークなジョブIDを生成"""
    return str(uuid.uuid4())

def calculate_estimated_time(final_menu: Dict[str, List[Dict]], seconds_per_item: float = 2.0) -> int:
    """
    推定処理時間を計算
    
    Args:
        final_menu: メニューデータ
        seconds_per_item: アイテム1つあたりの処理時間（秒）
        
    Returns:
        推定処理時間（秒）
    """
    total_items = sum(len(items) for items in final_menu.values())
    return int(total_items * seconds_per_item)

def create_chunk_summary(chunks: List[Dict]) -> Dict[str, Any]:
    """
    チャンク情報のサマリーを作成
    
    Args:
        chunks: チャンクリスト
        
    Returns:
        チャンクサマリー情報
    """
    if not chunks:
        return {
            "total_chunks": 0,
            "total_items": 0,
            "categories": [],
            "chunks_per_category": {}
        }
    
    categories = list(set(chunk["category"] for chunk in chunks))
    chunks_per_category = {}
    total_items = 0
    
    for category in categories:
        category_chunks = [c for c in chunks if c["category"] == category]
        chunks_per_category[category] = {
            "chunk_count": len(category_chunks),
            "items_count": sum(c["items_count"] for c in category_chunks)
        }
        total_items += chunks_per_category[category]["items_count"]
    
    return {
        "total_chunks": len(chunks),
        "total_items": total_items,
        "categories": categories,
        "chunks_per_category": chunks_per_category,
        "estimated_time": calculate_estimated_time(
            {cat: [{}] * info["items_count"] for cat, info in chunks_per_category.items()}
        )
    }

# ========== Redis進行状況管理 ==========

def save_job_info(job_id: str, job_data: Dict[str, Any]) -> bool:
    """
    ジョブ情報をRedisに保存
    
    Args:
        job_id: ジョブID
        job_data: ジョブデータ
        
    Returns:
        保存成功フラグ
    """
    if not redis_client:
        logger.error("Redis client not available")
        return False
    
    try:
        key = f"job:{job_id}"
        value = json.dumps(job_data, ensure_ascii=False)
        redis_client.setex(key, settings.IMAGE_JOB_TIMEOUT, value)
        logger.info(f"Job info saved: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save job info: {e}")
        return False

def get_job_info(job_id: str) -> Optional[Dict[str, Any]]:
    """
    ジョブ情報をRedisから取得
    
    Args:
        job_id: ジョブID
        
    Returns:
        ジョブデータ（存在しない場合はNone）
    """
    if not redis_client:
        logger.error("Redis client not available")
        return None
    
    try:
        key = f"job:{job_id}"
        value = redis_client.get(key)
        if value:
            return json.loads(value.decode('utf-8'))
        return None
    except Exception as e:
        logger.error(f"Failed to get job info: {e}")
        return None

def update_job_progress(job_id: str, progress_data: Dict[str, Any]) -> bool:
    """
    ジョブ進行状況を更新
    
    Args:
        job_id: ジョブID
        progress_data: 進行状況データ
        
    Returns:
        更新成功フラグ
    """
    if not redis_client:
        logger.error("Redis client not available")
        return False
    
    try:
        # 既存のジョブ情報を取得
        job_info = get_job_info(job_id)
        if not job_info:
            logger.warning(f"Job not found for progress update: {job_id}")
            return False
        
        # 進行状況を更新
        if "progress" not in job_info:
            job_info["progress"] = {}
        
        job_info["progress"].update(progress_data)
        job_info["last_updated"] = progress_data.get("timestamp", "unknown")
        
        # Redisに保存
        return save_job_info(job_id, job_info)
        
    except Exception as e:
        logger.error(f"Failed to update job progress: {e}")
        return False

def save_chunk_result(job_id: str, chunk_id: int, result_data: Dict[str, Any]) -> bool:
    """
    チャンク結果をRedisに保存
    
    Args:
        job_id: ジョブID
        chunk_id: チャンクID
        result_data: 結果データ
        
    Returns:
        保存成功フラグ
    """
    if not redis_client:
        logger.error("Redis client not available")
        return False
    
    try:
        key = f"job:{job_id}:chunk:{chunk_id}"
        value = json.dumps(result_data, ensure_ascii=False)
        redis_client.setex(key, settings.IMAGE_JOB_TIMEOUT, value)
        logger.info(f"Chunk result saved: {job_id}/chunk_{chunk_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to save chunk result: {e}")
        return False

def get_chunk_result(job_id: str, chunk_id: int) -> Optional[Dict[str, Any]]:
    """
    チャンク結果をRedisから取得
    
    Args:
        job_id: ジョブID
        chunk_id: チャンクID
        
    Returns:
        チャンク結果データ
    """
    if not redis_client:
        logger.error("Redis client not available")
        return None
    
    try:
        key = f"job:{job_id}:chunk:{chunk_id}"
        value = redis_client.get(key)
        if value:
            return json.loads(value.decode('utf-8'))
        return None
    except Exception as e:
        logger.error(f"Failed to get chunk result: {e}")
        return None

def get_all_chunk_results(job_id: str) -> Dict[int, Dict[str, Any]]:
    """
    ジョブの全チャンク結果を取得
    
    Args:
        job_id: ジョブID
        
    Returns:
        チャンクID別の結果辞書
    """
    if not redis_client:
        logger.error("Redis client not available")
        return {}
    
    try:
        pattern = f"job:{job_id}:chunk:*"
        keys = redis_client.keys(pattern)
        
        results = {}
        for key in keys:
            # キーからチャンクIDを抽出
            chunk_id = int(key.decode('utf-8').split(':')[-1])
            value = redis_client.get(key)
            if value:
                results[chunk_id] = json.loads(value.decode('utf-8'))
        
        return results
    except Exception as e:
        logger.error(f"Failed to get all chunk results: {e}")
        return {}

def calculate_job_progress(job_id: str) -> Dict[str, Any]:
    """
    ジョブ全体の進行状況を計算
    
    Args:
        job_id: ジョブID
        
    Returns:
        進行状況サマリー
    """
    try:
        job_info = get_job_info(job_id)
        if not job_info:
            return {"error": "Job not found"}
        
        chunk_results = get_all_chunk_results(job_id)
        total_chunks = job_info.get("total_chunks", 0)
        
        if total_chunks == 0:
            return {"progress_percent": 0, "status": "pending"}
        
        completed_chunks = len([r for r in chunk_results.values() if r.get("status") == "completed"])
        failed_chunks = len([r for r in chunk_results.values() if r.get("status") == "failed"])
        
        progress_percent = int((completed_chunks / total_chunks) * 100)
        
        if completed_chunks + failed_chunks == total_chunks:
            status = "completed" if failed_chunks == 0 else "partial_completed"
        elif failed_chunks > 0:
            status = "processing_with_errors"
        elif completed_chunks > 0:
            status = "processing"
        else:
            status = "pending"
        
        return {
            "progress_percent": progress_percent,
            "status": status,
            "total_chunks": total_chunks,
            "completed_chunks": completed_chunks,
            "failed_chunks": failed_chunks,
            "chunk_results": chunk_results
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate job progress: {e}")
        return {"error": str(e)}

def cleanup_job_data(job_id: str) -> bool:
    """
    ジョブ関連データを削除
    
    Args:
        job_id: ジョブID
        
    Returns:
        削除成功フラグ
    """
    if not redis_client:
        logger.error("Redis client not available")
        return False
    
    try:
        # ジョブ情報削除
        redis_client.delete(f"job:{job_id}")
        
        # チャンク結果削除
        pattern = f"job:{job_id}:chunk:*"
        keys = redis_client.keys(pattern)
        if keys:
            redis_client.delete(*keys)
        
        logger.info(f"Job data cleaned up: {job_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to cleanup job data: {e}")
        return False
