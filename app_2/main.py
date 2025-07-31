from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app_2.core.config import settings
from app_2.core.cors import get_cors_settings
from app_2.core.database import init_database, shutdown_database
from app_2.api.v1.endpoints.pipeline import router as pipeline_router
from app_2.api.v1.endpoints.menu_images import router as menu_images_router
from app_2.api.v1.endpoints.sse import router as sse_router
from app_2.api.v1.endpoints.service import router as service_router

async def shutdown_redis():
    """Redisリソースのグローバルクリーンアップ"""
    try:
        from app_2.services.dependencies import get_redis_client
        redis_client = get_redis_client()
        await redis_client.cleanup()
    except Exception as e:
        print(f"Redis cleanup error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # アプリケーション起動時
    await init_database()
    yield
    # アプリケーション終了時
    await shutdown_database()
    await shutdown_redis()

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.base.app_title,
        version=settings.base.app_version,
        description=settings.base.app_description,
        lifespan=lifespan
    )
    
    # CORS設定を追加
    app.add_middleware(
        CORSMiddleware,
        **get_cors_settings().get_cors_config()
    )
    
    # ルーターを追加
    app.include_router(pipeline_router, prefix="/api/v1")
    app.include_router(menu_images_router, prefix="/api/v1")
    app.include_router(sse_router, prefix="/api/v1")  # SSEエンドポイント
    app.include_router(service_router, prefix="/api/v1")  # サービステストエンドポイント
    
    return app

app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app_2.main:app",
        host=settings.base.host,
        port=settings.base.port,
        log_level="info"
    ) 