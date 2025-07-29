"""
Google Vision Client - Enhanced with Error Handling and Retry Logic
"""

import asyncio
from functools import lru_cache
from typing import List, Dict, Union
from google.cloud import vision
from google.api_core import exceptions as google_exceptions

from app_2.infrastructure.integrations.google.google_credential_manager import get_google_credential_manager
from app_2.utils.logger import get_logger

logger = get_logger("google_vision_client")


class GoogleVisionClient:
    def __init__(self):
        self.credential_manager = get_google_credential_manager()
        self.client = None

    async def _ensure_client(self):
        """認証済みクライアントを確保"""
        if self.client is None:
            self.client = await self.credential_manager.get_vision_client_async()
        return self.client

    async def extract_text_with_positions(self, image_data: bytes, level: str = "word", max_retries: int = 2) -> List[Dict[str, Union[str, float]]]:
        """
        テキストとその位置情報を抽出（リトライロジック付き）
        
        Args:
            image_data: 画像バイナリデータ
            level: 抽出レベル ("word" または "paragraph")
            max_retries: 最大リトライ回数（デフォルト: 2回）
            
        Returns:
            List[Dict]: テキストと位置情報の辞書リスト
            例: [{"text": "ブレンド", "x_center": 120.0, "y_center": 240.0}, ...]
        """
        for attempt in range(max_retries + 1):
            try:
                return await self._execute_vision_api_call(image_data, level)
                
            except Exception as e:
                error_message = str(e).lower()
                
                # GOAWAYエラーやセッションタイムアウトの検出
                is_connection_error = any(keyword in error_message for keyword in [
                    "goaway",
                    "session_timed_out", 
                    "connection reset",
                    "connection closed",
                    "deadline exceeded",
                    "unavailable"
                ])
                
                # 認証エラーの検出
                is_auth_error = any(keyword in error_message for keyword in [
                    "default credentials",
                    "authentication",
                    "credentials",
                    "permission denied",
                    "unauthorized"
                ])
                
                if (is_connection_error or is_auth_error) and attempt < max_retries:
                    wait_time = 2 ** attempt  # 指数バックオフ: 1秒, 2秒, 4秒...
                    logger.warning(
                        f"Vision API error detected (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Resetting client and retrying in {wait_time} seconds..."
                    )
                    
                    # クライアントを再作成
                    self.credential_manager.reset_vision_client()
                    self.client = None  # 次回の_ensure_client()で再作成される
                    
                    await asyncio.sleep(wait_time)
                    continue
                    
                elif attempt < max_retries:
                    # その他のエラー（Rate Limit等）
                    wait_time = 2 ** attempt
                    logger.warning(
                        f"Vision API error (attempt {attempt + 1}/{max_retries + 1}): {e}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    # 最大リトライ回数に達した場合
                    logger.error(f"Vision API call failed after {max_retries + 1} attempts: {e}")
                    raise Exception(f"Vision API error after {max_retries + 1} attempts: {str(e)}")
        
        # このコードには到達しないはずだが、念のため
        raise Exception("Unexpected error in Vision API retry logic")

    async def _execute_vision_api_call(self, image_data: bytes, level: str) -> List[Dict[str, Union[str, float]]]:
        """
        実際のVision API呼び出しを実行
        
        Args:
            image_data: 画像バイナリデータ
            level: 抽出レベル ("word" または "paragraph")
            
        Returns:
            List[Dict]: テキストと位置情報の辞書リスト
        """
        # 認証済みクライアントを確保
        client = await self._ensure_client()
        
        image = vision.Image(content=image_data)
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            raise Exception(f"Vision API error: {response.error.message}")
        
        text_positions = []
        
        if not response.full_text_annotation:
            return text_positions
            
        # 各ページをループ
        for page in response.full_text_annotation.pages:
            # 各ブロックをループ
            for block in page.blocks:
                # 各パラグラフをループ
                for paragraph in block.paragraphs:
                    if level == "paragraph":
                        # パラグラフレベルでテキストを抽出
                        paragraph_text = "".join([
                            "".join([symbol.text for symbol in word.symbols])
                            for word in paragraph.words
                        ])
                        
                        if paragraph_text.strip():
                            x_center, y_center = self._calculate_bounding_box_center(paragraph.bounding_box)
                            text_positions.append({
                                "text": paragraph_text.strip(),
                                "x_center": x_center,
                                "y_center": y_center
                            })
                    
                    elif level == "word":
                        # ワードレベルでテキストを抽出
                        for word in paragraph.words:
                            word_text = "".join([symbol.text for symbol in word.symbols])
                            
                            if word_text.strip():
                                x_center, y_center = self._calculate_bounding_box_center(word.bounding_box)
                                text_positions.append({
                                    "text": word_text.strip(),
                                    "x_center": x_center,
                                    "y_center": y_center
                                })
        
        logger.info(f"Vision API call successful: extracted {len(text_positions)} text elements")
        return text_positions
    
    def _calculate_bounding_box_center(self, bounding_box) -> tuple[float, float]:
        """
        バウンディングボックスの中心座標を計算
        
        Args:
            bounding_box: Vision APIのバウンディングボックス
            
        Returns:
            tuple: (x_center, y_center)
        """
        if not bounding_box or not bounding_box.vertices:
            return (0.0, 0.0)
        
        # 全ての頂点のx座標とy座標の平均を計算
        x_coords = [vertex.x for vertex in bounding_box.vertices if hasattr(vertex, 'x')]
        y_coords = [vertex.y for vertex in bounding_box.vertices if hasattr(vertex, 'y')]
        
        if not x_coords or not y_coords:
            return (0.0, 0.0)
        
        x_center = sum(x_coords) / len(x_coords)
        y_center = sum(y_coords) / len(y_coords)
        
        return (x_center, y_center)


@lru_cache(maxsize=1)
def get_google_vision_client():
    return GoogleVisionClient() 