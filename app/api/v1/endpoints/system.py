from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
import asyncio
import os

router = APIRouter()

@router.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    
    # インポートを移動 - 新しいサービス層から取得
    from app.services.auth import get_compatibility_variables
    from app.services.realtime import get_ping_pong_sessions
    from app.services.ocr import get_ocr_service_status
    from app.services.category import get_category_service_status
    from app.services.translation import get_translation_service_status
    from app.services.description import get_description_service_status
    from app.services.image import get_image_service_status
    
    # API認証情報を取得
    auth_vars = get_compatibility_variables()
    VISION_AVAILABLE = auth_vars["VISION_AVAILABLE"]
    TRANSLATE_AVAILABLE = auth_vars["TRANSLATE_AVAILABLE"]
    OPENAI_AVAILABLE = auth_vars["OPENAI_AVAILABLE"]
    GEMINI_AVAILABLE = auth_vars["GEMINI_AVAILABLE"]
    IMAGEN_AVAILABLE = auth_vars["IMAGEN_AVAILABLE"]
    google_credentials = auth_vars["google_credentials"]
    
    # リアルタイム通信情報を取得
    ping_pong_sessions = get_ping_pong_sessions()
    
    # サービス状態の詳細情報
    services_detail = {}
    
    if VISION_AVAILABLE:
        services_detail["vision_api"] = {"status": "available", "client": "initialized"}
    else:
        services_detail["vision_api"] = {"status": "unavailable", "reason": "initialization_failed"}
    
    if TRANSLATE_AVAILABLE:
        services_detail["translate_api"] = {"status": "available", "client": "initialized"}
    else:
        services_detail["translate_api"] = {"status": "unavailable", "reason": "initialization_failed"}
    
    if OPENAI_AVAILABLE:
        services_detail["openai_api"] = {"status": "available", "client": "initialized"}
    else:
        services_detail["openai_api"] = {"status": "unavailable", "reason": "missing_api_key"}
    
    if GEMINI_AVAILABLE:
        services_detail["gemini_api"] = {"status": "available", "model": "gemini-2.0-flash-exp"}
    else:
        services_detail["gemini_api"] = {"status": "unavailable", "reason": "missing_api_key_or_package"}
    
    if IMAGEN_AVAILABLE:
        services_detail["imagen_api"] = {"status": "available", "model": "imagen-3.0-generate-002"}
    else:
        services_detail["imagen_api"] = {"status": "unavailable", "reason": "missing_api_key_or_package"}
    
    # Gemini OCRサービスの状態（Gemini専用モード）
    try:
        ocr_status = get_ocr_service_status()
        gemini_available = ocr_status.get("gemini", {}).get("available", False)
        services_detail["gemini_ocr"] = {
            "status": "available" if gemini_available else "unavailable",
            "mode": "gemini_exclusive",
            "engine": "gemini-2.0-flash",
            "gemini_service": ocr_status.get("gemini", {}),
            "features": [
                "japanese_menu_optimization",
                "high_precision_extraction",
                "contextual_understanding"
            ] if gemini_available else []
        }
    except Exception as e:
        services_detail["gemini_ocr"] = {"status": "error", "error": str(e), "mode": "gemini_exclusive"}
    
    # OpenAI カテゴリ分類サービスの状態（OpenAI専用モード）
    try:
        category_status = get_category_service_status()
        openai_available = category_status.get("openai", {}).get("available", False)
        services_detail["openai_categorization"] = {
            "status": "available" if openai_available else "unavailable",
            "mode": "openai_exclusive",
            "engine": "openai-function-calling",
            "openai_service": category_status.get("openai", {}),
            "features": [
                "japanese_menu_categorization",
                "function_calling_support",
                "structured_output",
                "menu_item_extraction"
            ] if openai_available else []
        }
    except Exception as e:
        services_detail["openai_categorization"] = {"status": "error", "error": str(e), "mode": "openai_exclusive"}
    
    # Google Translate + OpenAI 翻訳サービスの状態
    try:
        translation_status = get_translation_service_status()
        google_translate_available = translation_status.get("google_translate", {}).get("available", False)
        openai_translate_available = translation_status.get("openai", {}).get("available", False)
        
        services_detail["google_translate_translation"] = {
            "status": "available" if google_translate_available else "unavailable",
            "role": "primary",
            "engine": "google-translate-api",
            "google_service": translation_status.get("google_translate", {}),
            "features": [
                "real_time_translation",
                "category_mapping",
                "html_entity_cleanup",
                "rate_limiting"
            ] if google_translate_available else []
        }
        
        services_detail["openai_translation"] = {
            "status": "available" if openai_translate_available else "unavailable",
            "role": "fallback",
            "engine": "openai-function-calling",
            "openai_service": translation_status.get("openai", {}),
            "features": [
                "function_calling_structured_output",
                "japanese_cuisine_terminology",
                "batch_translation",
                "category_mapping"
            ] if openai_translate_available else []
        }
    except Exception as e:
        services_detail["google_translate_translation"] = {"status": "error", "error": str(e), "role": "primary"}
        services_detail["openai_translation"] = {"status": "error", "error": str(e), "role": "fallback"}
    
    # OpenAI 詳細説明サービスの状態
    try:
        description_status = get_description_service_status()
        openai_description_available = description_status.get("openai", {}).get("available", False)
        
        services_detail["openai_description"] = {
            "status": "available" if openai_description_available else "unavailable",
            "role": "primary",
            "engine": "openai-chunked-processing",
            "openai_service": description_status.get("openai", {}),
            "features": [
                "detailed_description_generation",
                "japanese_cuisine_expertise",
                "cultural_context_explanation",
                "tourist_friendly_descriptions",
                "chunked_processing",
                "real_time_progress"
            ] if openai_description_available else []
        }
    except Exception as e:
        services_detail["openai_description"] = {"status": "error", "error": str(e), "role": "primary"}
    
    # Imagen 3 画像生成サービスの状態
    try:
        image_status = get_image_service_status()
        imagen3_available = image_status.get("imagen3", {}).get("available", False)
        
        services_detail["imagen3_image_generation"] = {
            "status": "available" if imagen3_available else "unavailable",
            "role": "primary",
            "engine": "imagen3-food-photography",
            "imagen3_service": image_status.get("imagen3", {}),
            "features": [
                "professional_food_photography",
                "japanese_cuisine_focus",
                "category_specific_styling",
                "high_quality_generation",
                "menu_item_visualization",
                "real_time_progress"
            ] if imagen3_available else []
        }
    except Exception as e:
        services_detail["imagen3_image_generation"] = {"status": "error", "error": str(e), "role": "primary"}
    
    # アプリケーション全体の状態
    overall_status = "healthy" if any([GEMINI_AVAILABLE, VISION_AVAILABLE, TRANSLATE_AVAILABLE, OPENAI_AVAILABLE, IMAGEN_AVAILABLE]) else "degraded"
    
    return {
        "status": overall_status,
        "version": "1.0.0",
        "timestamp": asyncio.get_event_loop().time(),
        "environment": {
            "port": os.getenv("PORT", "8000"),
            "google_credentials": "loaded" if google_credentials else "not_loaded"
        },
        "services": {
            "vision_api": VISION_AVAILABLE,
            "translate_api": TRANSLATE_AVAILABLE,
            "openai_api": OPENAI_AVAILABLE,
            "gemini_api": GEMINI_AVAILABLE,
            "imagen_api": IMAGEN_AVAILABLE
        },
        "services_detail": services_detail,
        "ping_pong_sessions": len(ping_pong_sessions)
    }

@router.get("/diagnostic")
async def diagnostic():
    """システム診断情報を返す"""
    
    # 統一認証システムと従来システムからデータを取得
    from app.services.auth import get_compatibility_variables, get_vision_client
    from app.services.auth.unified_auth import get_auth_status, get_auth_troubleshooting
    from app.core.config import settings
    
    # API認証情報を取得
    auth_vars = get_compatibility_variables()
    auth_status = get_auth_status()
    
    VISION_AVAILABLE = auth_vars["VISION_AVAILABLE"]
    TRANSLATE_AVAILABLE = auth_vars["TRANSLATE_AVAILABLE"]
    OPENAI_AVAILABLE = auth_vars["OPENAI_AVAILABLE"]
    vision_client = get_vision_client()
    
    diagnostic_info = {
        "vision_api": {
            "available": VISION_AVAILABLE,
            "error": None if VISION_AVAILABLE else "Google Vision API not available"
        },
        "translate_api": {
            "available": TRANSLATE_AVAILABLE,
            "error": None if TRANSLATE_AVAILABLE else "Google Translate API not available"
        },
        "openai_api": {
            "available": OPENAI_AVAILABLE,
            "error": None if OPENAI_AVAILABLE else "OpenAI API not available"
        },
        "environment": {
            "google_credentials_available": auth_status["available"],
            "google_credentials_json_env": "GOOGLE_CREDENTIALS_JSON" in os.environ,
            "openai_api_key_env": "OPENAI_API_KEY" in os.environ,
            "use_aws_secrets_manager": settings.USE_AWS_SECRETS_MANAGER,
            "aws_region": settings.AWS_REGION if settings.USE_AWS_SECRETS_MANAGER else None,
            "aws_secret_name": settings.AWS_SECRET_NAME if settings.USE_AWS_SECRETS_MANAGER else None
        },
        "authentication": {
            "method": auth_status["method"],
            "source": auth_status["source"],
            "available": auth_status["available"],
            "troubleshooting": get_auth_troubleshooting() if not auth_status["available"] else None
        }
    }
    
    # Google Vision APIのテスト
    if VISION_AVAILABLE and vision_client:
        try:
            from google.cloud import vision
            # テスト用の小さな画像でAPIを確認
            test_response = vision_client.text_detection(vision.Image(content=b''))
            diagnostic_info["vision_api"]["test_status"] = "connection_ok"
        except Exception as e:
            diagnostic_info["vision_api"]["test_status"] = f"connection_failed: {str(e)}"
            diagnostic_info["vision_api"]["available"] = False
    
    # AWS Secrets Managerのテスト（有効な場合のみ）
    if settings.USE_AWS_SECRETS_MANAGER:
        try:
            from app.services.auth.aws_secrets import test_aws_connection
            aws_test_result = test_aws_connection()
            diagnostic_info["aws_secrets_manager"] = {
                "enabled": True,
                "connection_test": "success" if aws_test_result else "failed",
                "secret_name": settings.AWS_SECRET_NAME,
                "region": settings.AWS_REGION
            }
        except Exception as e:
            diagnostic_info["aws_secrets_manager"] = {
                "enabled": True,
                "connection_test": f"error: {str(e)}",
                "secret_name": settings.AWS_SECRET_NAME,
                "region": settings.AWS_REGION
            }
    else:
        diagnostic_info["aws_secrets_manager"] = {
            "enabled": False,
            "message": "AWS Secrets Manager is disabled (USE_AWS_SECRETS_MANAGER=false)"
        }
    
    return JSONResponse(content=diagnostic_info)

@router.get("/mobile-diagnostic")
async def mobile_diagnostic(request: Request):
    """モバイル専用の詳細診断情報"""
    
    # インポートを移動 - 新しいサービス層から取得
    from app.services.auth import is_vision_available
    
    VISION_AVAILABLE = is_vision_available()
    
    # リクエスト情報の詳細分析
    headers = dict(request.headers)
    user_agent = headers.get("user-agent", "Unknown")
    is_mobile = any(mobile_indicator in user_agent.lower() for mobile_indicator in [
        "mobile", "android", "iphone", "ipad", "blackberry", "windows phone"
    ])
    
    # ネットワーク情報
    network_info = {
        "client_ip": request.client.host if request.client else "Unknown",
        "user_agent": user_agent,
        "is_mobile_detected": is_mobile,
        "request_headers": headers,
        "forwarded_for": headers.get("x-forwarded-for"),
        "real_ip": headers.get("x-real-ip")
    }
    
    # サービス状態の詳細確認
    services_status = {
        "vision_api": {
            "available": VISION_AVAILABLE,
            "mobile_compatibility": "good" if VISION_AVAILABLE else "unavailable",
            "error": None if VISION_AVAILABLE else "Google Vision API not available"
        },
        "backend_connectivity": {
            "cors_configured": True,
            "sse_support": True,
            "mobile_headers": True
        }
    }
    
    # モバイル特有の問題チェック
    mobile_issues = []
    
    if not VISION_AVAILABLE:
        mobile_issues.append("Vision API unavailable - this will cause Stage 1 failures")
    
    origin = headers.get("origin", "")
    if "vercel.app" not in origin and "localhost" not in origin:
        mobile_issues.append(f"Request from unexpected origin: {origin}")
    
    accept_header = headers.get("accept", "")
    if "text/event-stream" not in accept_header:
        mobile_issues.append("SSE support may be limited")
    
    return JSONResponse(content={
        "mobile_diagnostic": True,
        "timestamp": asyncio.get_event_loop().time(),
        "network_info": network_info,
        "services_status": services_status,
        "mobile_issues": mobile_issues,
        "recommendations": [
            "Use Wi-Fi instead of mobile data for better stability",
            "Ensure latest browser version for SSE support",
            "Clear browser cache if experiencing persistent issues"
        ]
    }) 