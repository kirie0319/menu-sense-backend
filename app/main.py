import uvicorn

# アプリケーション設定統合サービス
from app.core.app_setup import create_configured_app
from app.core.config import settings

# FastAPIアプリと後方互換性変数の設定
app, compatibility_vars = create_configured_app()

# 後方互換性のためのグローバル変数設定
google_credentials = compatibility_vars['google_credentials']
vision_client = compatibility_vars['vision_client']
translate_client = compatibility_vars['translate_client']
openai_client = compatibility_vars['openai_client']
gemini_model = compatibility_vars['gemini_model']
imagen_client = compatibility_vars['imagen_client']
VISION_AVAILABLE = compatibility_vars['VISION_AVAILABLE']
TRANSLATE_AVAILABLE = compatibility_vars['TRANSLATE_AVAILABLE']
OPENAI_AVAILABLE = compatibility_vars['OPENAI_AVAILABLE']
GEMINI_AVAILABLE = compatibility_vars['GEMINI_AVAILABLE']
IMAGEN_AVAILABLE = compatibility_vars['IMAGEN_AVAILABLE']
call_openai_with_retry = compatibility_vars['call_openai_with_retry']

if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT) 