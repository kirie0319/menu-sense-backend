"""
Unified Monitoring Endpoints

All monitoring functions integrated into a single endpoint group
WITH FULL COMPATIBILITY for old system endpoints
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any

# Import unified monitoring services
from app.services.monitoring import (
    SystemMonitoringService,
    APIHealthService,
    SSEMonitoringService,
    DiagnosticsService
)

router = APIRouter()

# Service instance cache (singleton pattern)
_service_cache: Dict[str, Any] = {}

def get_service(service_class):
    """Get service instance with caching"""
    service_name = service_class.__name__
    if service_name not in _service_cache:
        _service_cache[service_name] = service_class()
    return _service_cache[service_name]

# ===============================
# OLD SYSTEM COMPATIBILITY ENDPOINTS
# ===============================

@router.get("/health")
async def old_system_health_compatibility():
    """
    🔄 FULL COMPATIBILITY: /api/v1/system/health replacement
    
    This endpoint provides EXACT same response format as old system
    """
    try:
        service = get_service(SystemMonitoringService)
        return await service.get_basic_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

@router.get("/diagnostic")
async def old_system_diagnostic_compatibility():
    """
    🔄 FULL COMPATIBILITY: /api/v1/system/diagnostic replacement
    
    This endpoint provides EXACT same response format as old system
    """
    try:
        service = get_service(DiagnosticsService)
        diagnostic_result = await service.get_system_diagnostics()
        return JSONResponse(content=diagnostic_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System diagnostic failed: {str(e)}")

@router.get("/mobile-diagnostic")
async def old_system_mobile_diagnostic_compatibility(request: Request):
    """
    🔄 FULL COMPATIBILITY: /api/v1/system/mobile-diagnostic replacement
    
    This endpoint provides EXACT same response format as old system
    """
    try:
        service = get_service(DiagnosticsService)
        
        # Extract request information (old system format)
        request_info = {
            "user_agent": request.headers.get("user-agent", "Unknown"),
            "client_ip": request.client.host if request.client else "Unknown",
            "headers": dict(request.headers)
        }
        
        mobile_result = await service.get_mobile_diagnostics(request_info)
        return JSONResponse(content=mobile_result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mobile diagnostic failed: {str(e)}")

# ===============================
# NEW SYSTEM ENHANCED ENDPOINTS
# ===============================

@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with additional new system features"""
    try:
        service = get_service(SystemMonitoringService)
        return await service.get_detailed_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detailed health check failed: {str(e)}")

@router.get("/health/apis")
async def api_health():
    """API-specific health check"""
    try:
        service = get_service(APIHealthService)
        return await service.get_comprehensive_health()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"API health check failed: {str(e)}")

# ===============================
# Statistics Endpoints
# ===============================

@router.get("/stats/system")
async def system_stats():
    """System statistics information"""
    try:
        # Combine system monitoring and API health checks
        system_service = get_service(SystemMonitoringService)
        api_service = get_service(APIHealthService)
        
        system_health = await system_service.get_basic_health()
        api_health = await api_service.get_comprehensive_health()
        
        return {
            "success": True,
            "system": system_health,
            "apis": api_health,
            "timestamp": system_health["timestamp"],
            "integration_mode": "unified_monitoring"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System stats failed: {str(e)}")

@router.get("/stats/sse")
async def sse_stats():
    """SSE statistics information"""
    try:
        service = get_service(SSEMonitoringService)
        return await service.get_sse_statistics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SSE stats failed: {str(e)}")

@router.get("/stats/performance")
async def performance_stats():
    """Performance statistics information"""
    try:
        service = get_service(SSEMonitoringService)
        return await service.get_performance_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Performance stats failed: {str(e)}")

# ===============================
# Unified Status Endpoint
# ===============================

@router.get("/status")
async def overall_status():
    """Overall system status"""
    try:
        # Get status from all services
        system_service = get_service(SystemMonitoringService)
        api_service = get_service(APIHealthService)
        sse_service = get_service(SSEMonitoringService)
        diagnostic_service = get_service(DiagnosticsService)
        
        # Get each service status
        system_status = await system_service.get_status()
        api_status = await api_service.get_status()
        sse_status = await sse_service.get_status()
        diagnostic_status = await diagnostic_service.get_status()
        
        # Determine overall status
        all_statuses = [system_status, api_status, sse_status, diagnostic_status]
        available_services = sum(1 for status in all_statuses if status.available)
        
        overall_available = available_services >= 3  # 3 out of 4 services must be available
        overall_status_str = "healthy" if overall_available else "degraded"
        
        return {
            "overall_status": overall_status_str,
            "available_services": available_services,
            "total_services": len(all_statuses),
            "services": {
                "system": system_status.to_dict(),
                "api_health": api_status.to_dict(),
                "sse": sse_status.to_dict(),
                "diagnostics": diagnostic_status.to_dict()
            },
            "timestamp": system_status.details.get("timestamp") if system_status.details else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Overall status failed: {str(e)}")

# ===============================
# Service Information Endpoint
# ===============================

@router.get("/info")
async def monitoring_info():
    """Information about monitoring capabilities"""
    return {
        "monitoring_version": "2.1.0-legacy-cleanup",
        "unified_monitoring": True,
        "old_system_compatibility": True,
        "compatibility_endpoints": [
            "/health",  # ✅ Replaces /api/v1/system/health
            "/diagnostic",  # ✅ Replaces /api/v1/system/diagnostic
            "/mobile-diagnostic",  # ✅ Replaces /api/v1/system/mobile-diagnostic
        ],
        "enhanced_endpoints": [
            "/health/detailed", 
            "/health/apis",
            "/stats/system",
            "/stats/sse",
            "/stats/performance",
            "/status",
            "/info"
        ],

        "features": [
            "full_old_system_compatibility",
            "unified_service_architecture",
            "safe_import_handling",
            "error_resilience",
            "mobile_device_detection",
            "performance_monitoring",
            "comprehensive_diagnostics",
            "exact_response_format_matching"
        ],
        "migration_notes": [
            "✅ /api/v1/system/health → /api/v1/monitoring/health (exact format)",
            "✅ /api/v1/system/diagnostic → /api/v1/monitoring/diagnostic (exact format)",
            "✅ /api/v1/system/mobile-diagnostic → /api/v1/monitoring/mobile-diagnostic (exact format)",
            "🆕 Enhanced features available via /health/detailed, /stats/*, etc."
        ]
    }