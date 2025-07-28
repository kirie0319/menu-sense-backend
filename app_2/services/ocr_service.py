"""
OCR Service - Menu Processor v2
Google Vision API を使用したテキスト抽出サービス

処理フロー:
1. 画像からOCRでテキスト抽出のみ
2. 一切のフィルタリング・判定は行わない
3. 生のOCR結果をCategorizeServiceに渡す

責任:
- 画像からのテキスト抽出のみ
- テキストの判定・フィルタリングは一切行わない
- OpenAI Categorizeサービスがすべての判定を担当
"""
from functools import lru_cache
from typing import List, Optional, Dict, Union
from app_2.infrastructure.integrations.google import GoogleVisionClient, get_google_vision_client
from app_2.utils.logger import get_logger

logger = get_logger("ocr_service")


class OCRService:
    """
    OCR処理サービス
    
    Google Vision APIを使用してメニュー画像からテキストを抽出。
    一切のフィルタリング・判定は行わず、純粋にテキスト抽出のみに特化。
    すべての判定ロジックはCategorizeServiceに委譲。
    """
    
    def __init__(self, vision_client: Optional[GoogleVisionClient] = None):
        """
        OCRサービスを初期化
        
        Args:
            vision_client: GoogleVisionClientインスタンス（テスト用）
                         Noneの場合はシングルトンクライアントを使用
        """
        self.vision_client = vision_client or get_google_vision_client()
        logger.info("OCRService initialized with enhanced error handling")

    async def extract_text_with_positions(
        self, 
        image_data: bytes, 
        level: str = "paragraph", 
        max_retries: int = 2
    ) -> List[Dict[str, Union[str, float]]]:
        """
        テキストとその位置情報を抽出（エラーハンドリング強化版）
        
        Args:
            image_data: 画像バイナリデータ
            level: 抽出レベル ("word" または "paragraph")
            max_retries: 最大リトライ回数（デフォルト: 2回）
            
        Returns:
            List[Dict]: テキストと位置情報の辞書リスト
            例: [{"text": "ブレンド", "x_center": 120.0, "y_center": 240.0}, ...]
            
        Raises:
            Exception: Vision API呼び出しがmax_retries回失敗した場合
        """
        try:
            logger.info(f"Starting OCR text extraction (level: {level}, max_retries: {max_retries})")
            
            # Vision APIクライアントの新しいリトライ機能を使用
            result = await self.vision_client.extract_text_with_positions(
                image_data=image_data,
                level=level,
                max_retries=max_retries
            )
            
            logger.info(f"OCR extraction completed successfully: {len(result)} text elements extracted")
            return result
            
        except Exception as e:
            logger.error(f"OCR extraction failed after all retries: {e}")
            raise Exception(f"OCR processing failed: {str(e)}")


@lru_cache(maxsize=1)
def get_ocr_service() -> OCRService:
    """
    OCRサービスのシングルトンインスタンスを取得
    
    Returns:
        OCRService: OCRサービスインスタンス
    """
    return OCRService() 