"""
後方互換性管理サービス
"""
from typing import Dict, Any

class CompatibilityManager:
    """後方互換性のための変数設定を管理するクラス"""
    
    @staticmethod
    def setup_global_variables() -> Dict[str, Any]:
        """後方互換性のためのグローバル変数を設定する"""
        
        # API認証サービスの初期化と変数設定
        from app.services.auth import get_compatibility_variables
        
        # 認証変数を取得
        auth_vars = get_compatibility_variables()
        
        # グローバルスコープに設定するための辞書を返す
        return {
            'google_credentials': auth_vars["google_credentials"],
            'vision_client': auth_vars["vision_client"],
            'translate_client': auth_vars["translate_client"],
            'openai_client': auth_vars["openai_client"],
            'gemini_model': auth_vars["gemini_model"],
            'imagen_client': auth_vars["imagen_client"],
            'VISION_AVAILABLE': auth_vars["VISION_AVAILABLE"],
            'TRANSLATE_AVAILABLE': auth_vars["TRANSLATE_AVAILABLE"],
            'OPENAI_AVAILABLE': auth_vars["OPENAI_AVAILABLE"],
            'GEMINI_AVAILABLE': auth_vars["GEMINI_AVAILABLE"],
            'IMAGEN_AVAILABLE': auth_vars["IMAGEN_AVAILABLE"]
        }
    
    @staticmethod
    def setup_compatibility_imports() -> Dict[str, Any]:
        """後方互換性のための関数インポートを設定する"""
        
        # OpenAI API リトライ関数（後方互換性）
        from app.services.auth import call_openai_with_retry
        
        return {
            'call_openai_with_retry': call_openai_with_retry
        }

# 便利な関数
def setup_compatibility_layer() -> Dict[str, Any]:
    """後方互換性レイヤーをセットアップする便利関数"""
    variables = CompatibilityManager.setup_global_variables()
    imports = CompatibilityManager.setup_compatibility_imports()
    
    # 両方を結合して返す
    return {**variables, **imports} 