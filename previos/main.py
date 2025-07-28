from app.core.app_setup import create_app
from app.core.config.base import base_settings

app = create_app()

if __name__ == "__main__":
    import uvicorn
    # 注意: これは開発環境でのみ実行される
    # 本番環境では適切なWSGIサーバー（Gunicorn等）を使用する
    uvicorn.run(app, host=base_settings.host, port=base_settings.port) 