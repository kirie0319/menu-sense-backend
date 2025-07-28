"""
Menu Mapping Categorize Service - Menu Processor v2
位置情報付きマッピングデータを使用したカテゴライズサービス

処理フロー:
1. 位置情報付きテキストデータを受け取る
2. マッピングデータを整形
3. CategorizeServiceに委譲してカテゴライズ実行
4. 構造化されたカテゴライズ結果を返す
"""
from functools import lru_cache
from typing import List, Dict, Union, Any
from app_2.services.categorize_service import get_categorize_service
from app_2.utils.logger import get_logger

logger = get_logger("menu_mapping_categorize")


class MenuMappingCategorizeService:
    """
    位置情報付きメニューマッピングデータのカテゴライズサービス
    
    XY座標情報を含むOCRデータを受け取り、
    OpenAI APIを使用してメニュー構造を分析・カテゴライズ
    """
    
    def __init__(self):
        """サービスを初期化"""
        self.categorize_service = get_categorize_service()
        logger.info("MenuMappingCategorizeService initialized")
    
    async def categorize_mapping_data(
        self, 
        text_positions: List[Dict[str, Union[str, float]]], 
        level: str = "paragraph"
    ) -> Dict[str, Any]:
        """
        位置情報付きマッピングデータをカテゴライズ
        
        Args:
            text_positions: 位置情報付きテキストデータ
                例: [{"text": "ブレンド", "x_center": 209.0, "y_center": 732.0}, ...]
            level: データレベル ("word" または "paragraph")
            
        Returns:
            Dict[str, Any]: カテゴライズ結果
        """
        if not text_positions:
            raise ValueError("Text positions data is empty")
        
        try:
            logger.info(f"Starting categorization for {len(text_positions)} {level} elements")
            
            # マッピングデータを整形
            formatted_mapping_data = self._format_mapping_data(text_positions)
            
            # CategorizeServiceでカテゴライズ実行
            categorize_result = await self.categorize_service.categorize_menu_structure(formatted_mapping_data, level)
            
            logger.info(f"Categorization completed: {len(text_positions)} elements processed")
            return categorize_result
            
        except Exception as e:
            logger.error(f"Categorization failed: {e}")
            raise
    
    def _format_mapping_data(self, text_positions: List[Dict[str, Union[str, float]]]) -> str:
        """
        位置情報付きデータを読みやすい形式に整形
        
        Args:
            text_positions: 位置情報付きテキストデータ
            
        Returns:
            str: 整形済みマッピングデータ
        """
        # Y座標でソートして行を特定
        sorted_by_y = sorted(text_positions, key=lambda x: x['y_center'])
        
        # 行をグループ化（Y座標が近いものを同じ行とみなす）
        rows = []
        current_row = []
        tolerance = 20  # Y座標の許容差
        
        for item in sorted_by_y:
            if not current_row:
                current_row = [item]
            elif abs(item['y_center'] - current_row[0]['y_center']) <= tolerance:
                current_row.append(item)
            else:
                # 現在の行をX座標でソート
                current_row.sort(key=lambda x: x['x_center'])
                rows.append(current_row)
                current_row = [item]
        
        # 最後の行を追加
        if current_row:
            current_row.sort(key=lambda x: x['x_center'])
            rows.append(current_row)
        
        # 整形されたマッピングデータを構築
        formatted_lines = []
        formatted_lines.append("=== メニュー画像から抽出されたテキストマッピングデータ ===")
        formatted_lines.append(f"総要素数: {len(text_positions)}")
        formatted_lines.append(f"行数: {len(rows)}")
        formatted_lines.append("")
        
        for i, row in enumerate(rows, 1):
            avg_y = sum(item['y_center'] for item in row) / len(row)
            formatted_lines.append(f"Row {i} (Y座標: {avg_y:.1f}):")
            
            # 行内の各要素を表示
            row_elements = []
            for item in row:
                row_elements.append(f"'{item['text']}'(X:{item['x_center']:.0f})")
            
            formatted_lines.append(f"  要素: {' | '.join(row_elements)}")
            formatted_lines.append("")
        
        # 座標順の生データも追加
        formatted_lines.append("=== 座標順生データ ===")
        sorted_positions = sorted(text_positions, key=lambda x: (x['y_center'], x['x_center']))
        for i, pos in enumerate(sorted_positions, 1):
            formatted_lines.append(f"{i:2d}. '{pos['text']}' at ({pos['x_center']:4.0f}, {pos['y_center']:4.0f})")
        
        return '\n'.join(formatted_lines)
    


# ファクトリー関数（シングルトンパターン）
@lru_cache(maxsize=1)
def get_menu_mapping_categorize_service() -> MenuMappingCategorizeService:
    """
    MenuMappingCategorizeService のインスタンスを取得（シングルトン）
    
    Returns:
        MenuMappingCategorizeService: メニューマッピングカテゴライズサービス
    """
    return MenuMappingCategorizeService() 