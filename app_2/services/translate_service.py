from functools import lru_cache
from typing import List, Optional, Dict, Any
from app_2.infrastructure.integrations.google import GoogleTranslateClient, get_google_translate_client
from app_2.utils.logger import get_logger

logger = get_logger("translate_service")


class TranslateService:
    """
    翻訳処理サービス
    
    Google Translate APIを使用してメニュー項目を多言語翻訳。
    単一項目から複数項目の一括処理まで対応。
    """
    
    def __init__(self, translate_client: Optional[GoogleTranslateClient] = None):
        """
        翻訳サービスを初期化
        
        Args:
            translate_client: GoogleTranslateClientインスタンス（テスト用）
                            Noneの場合はシングルトンクライアントを使用
        """
        self.translate_client = translate_client or get_google_translate_client()
        logger.info("TranslateService initialized")
    
    async def translate_menu_data(
        self, 
        menu_data: Dict[str, Any], 
        target_language: str = "en"
    ) -> Dict[str, Any]:
        """
        メニューデータ構造体を翻訳
        
        Args:
            menu_data: メニューデータ辞書
                      例: {"name": "Coffee", "description": "Hot coffee", "category": "Drinks"}
            target_language: 対象言語コード
            
        Returns:
            Dict[str, Any]: 翻訳済みメニューデータ
        """
        if not menu_data or not isinstance(menu_data, dict):
            logger.warning("Invalid menu data provided for translation")
            return menu_data or {}
        
        try:
            logger.debug(f"Translating menu data structure with {len(menu_data)} fields")
            translated_data = {}
            
            # 翻訳対象フィールドを定義
            translatable_fields = ["name", "category"]
            
            for key, value in menu_data.items():
                if key in translatable_fields and value and isinstance(value, str):
                    # 翻訳実行（直接translate_clientを呼び出し）
                    try:
                        translated_value = await self.translate_client.translate(value, target_language)
                        translated_data[key] = translated_value.strip() if translated_value else value
                        
                        # 元の値も保持（_originalサフィックス）
                        translated_data[f"{key}_original"] = value
                    except Exception as e:
                        logger.error(f"Failed to translate {key}: '{value}' - {e}")
                        translated_data[key] = value  # フォールバック
                        translated_data[f"{key}_original"] = value
                else:
                    # 翻訳対象外フィールドはそのまま保持
                    translated_data[key] = value
            
            logger.info("Menu data structure translation completed")
            return translated_data
            
        except Exception as e:
            logger.error(f"Menu data translation failed: {e}")
            return menu_data


@lru_cache(maxsize=1)
def get_translate_service() -> TranslateService:
    """
    TranslateServiceのシングルトンインスタンスを取得
    
    プロジェクト統一パターン: @lru_cache でシングルトン化
    
    Returns:
        TranslateService: 翻訳サービスシングルトンインスタンス
    """
    return TranslateService() 