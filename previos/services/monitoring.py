"""
Unified Monitoring Service

System monitoring, API health checks, SSE statistics integration

I will divide this file to multiple files cuz this file has a lot of responsiblitly about monitoring which include sse or something.
"""

import logging
import time
import asyncio
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


# ===============================
# Base Classes
# ===============================

@dataclass
class ServiceStatus:
    """Unified service status response"""
    name: str
    available: bool
    status: str
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Return as dictionary"""
        return {
            "name": self.name,
            "available": self.available,
            "status": self.status,
            "error": self.error,
            "details": self.details
        }


class MonitoringUtils:
    """Common monitoring utilities"""
    
    @staticmethod
    def get_current_timestamp() -> float:
        """Get current timestamp"""
        return time.time()
    
    @staticmethod
    def get_asyncio_timestamp() -> float:
        """Get asyncio timestamp (for compatibility with old system)"""
        try:
            return asyncio.get_event_loop().time()
        except RuntimeError:
            # No event loop running, fallback to regular timestamp
            return time.time()
    
    @staticmethod
    def format_uptime(start_time: float) -> float:
        """Calculate uptime"""
        return time.time() - start_time
    
    @staticmethod
    def safe_import(module_path: str, function_name: str = None):
        """Safe import with error handling"""
        try:
            module = __import__(module_path, fromlist=[function_name] if function_name else [])
            return getattr(module, function_name) if function_name else module
        except ImportError as e:
            return None
        except Exception as e:
            return None


class MonitoringServiceBase(ABC):
    """Base class for monitoring services"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def get_status(self) -> ServiceStatus:
        """Get service status"""
        pass
    
    def _handle_error(self, error: Exception, service_name: str) -> ServiceStatus:
        """Unified error handling"""
        self.logger.error(f"{service_name} error: {error}")
        return ServiceStatus(
            name=service_name,
            available=False,
            status="error",
            error=str(error)
        )


# ===============================
# System Monitoring Service
# ===============================

class SystemMonitoringService(MonitoringServiceBase):
    """System-wide monitoring service"""
    
    async def get_basic_health(self) -> Dict[str, Any]:
        """Basic health check - FULL COMPATIBILITY with old system"""
        try:
            # Safely import existing get_compatibility_variables
            get_compatibility_variables = MonitoringUtils.safe_import(
                'app.services.auth', 'get_compatibility_variables'
            )
            
            if not get_compatibility_variables:
                return self._get_fallback_health()
            
            auth_vars = get_compatibility_variables()
            
            # Basic health status determination
            VISION_AVAILABLE = auth_vars.get("VISION_AVAILABLE", False)
            TRANSLATE_AVAILABLE = auth_vars.get("TRANSLATE_AVAILABLE", False)
            OPENAI_AVAILABLE = auth_vars.get("OPENAI_AVAILABLE", False)
            GEMINI_AVAILABLE = auth_vars.get("GEMINI_AVAILABLE", False)
            IMAGEN_AVAILABLE = auth_vars.get("IMAGEN_AVAILABLE", False)
            google_credentials = auth_vars.get("google_credentials")
            
            # Basic services dict (old system format)
            services = {
                "vision_api": VISION_AVAILABLE,
                "translate_api": TRANSLATE_AVAILABLE,
                "openai_api": OPENAI_AVAILABLE,
                "gemini_api": GEMINI_AVAILABLE,
                "imagen_api": IMAGEN_AVAILABLE
            }
            
            # ===== MISSING FIELD 1: services_detail =====
            services_detail = await self._get_services_detail(
                VISION_AVAILABLE, TRANSLATE_AVAILABLE, OPENAI_AVAILABLE, 
                GEMINI_AVAILABLE, IMAGEN_AVAILABLE
            )
            
            # ===== MISSING FIELD 2: environment =====
            environment = {
                "port": os.getenv("PORT", "8000"),
                "google_credentials": "loaded" if google_credentials else "not_loaded"
            }
            
            # ===== MISSING FIELD 3: ping_pong_sessions =====
            ping_pong_sessions = await self._get_sse_session_count()
            
            # Overall health status determination
            overall_status = "healthy" if any([GEMINI_AVAILABLE, VISION_AVAILABLE, TRANSLATE_AVAILABLE, OPENAI_AVAILABLE, IMAGEN_AVAILABLE]) else "degraded"
            
            # ===== RETURN OLD SYSTEM COMPATIBLE FORMAT =====
            return {
                "status": overall_status,
                "version": "1.0.0",
                "timestamp": MonitoringUtils.get_asyncio_timestamp(),  # Use asyncio timestamp for compatibility
                "environment": environment,  # ✅ Added missing field
                "services": services,
                "services_detail": services_detail,  # ✅ Added missing field
                "ping_pong_sessions": ping_pong_sessions  # ✅ Added missing field
            }
        except Exception as e:
            return self._handle_error(e, "system_monitoring").to_dict()
    
    async def _get_services_detail(self, vision_available, translate_available, openai_available, gemini_available, imagen_available) -> Dict[str, Any]:
        """Get detailed service information (old system format)"""
        services_detail = {}
        
        # Vision API detail
        if vision_available:
            services_detail["vision_api"] = {"status": "available", "client": "initialized"}
        else:
            services_detail["vision_api"] = {"status": "unavailable", "reason": "initialization_failed"}
        
        # Translate API detail
        if translate_available:
            services_detail["translate_api"] = {"status": "available", "client": "initialized"}
        else:
            services_detail["translate_api"] = {"status": "unavailable", "reason": "initialization_failed"}
        
        # OpenAI API detail
        if openai_available:
            services_detail["openai_api"] = {"status": "available", "client": "initialized"}
        else:
            services_detail["openai_api"] = {"status": "unavailable", "reason": "missing_api_key"}
        
        # Gemini API detail
        if gemini_available:
            services_detail["gemini_api"] = {"status": "available", "model": "gemini-2.0-flash-exp"}
        else:
            services_detail["gemini_api"] = {"status": "unavailable", "reason": "missing_api_key_or_package"}
        
        # Imagen API detail
        if imagen_available:
            services_detail["imagen_api"] = {"status": "available", "model": "imagen-3.0-generate-002"}
        else:
            services_detail["imagen_api"] = {"status": "unavailable", "reason": "missing_api_key_or_package"}
        
        # Gemini OCR service detail (old system format)
        try:
            get_ocr_service_status = MonitoringUtils.safe_import('app.services.ocr', 'get_ocr_service_status')
            if get_ocr_service_status:
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
            else:
                services_detail["gemini_ocr"] = {"status": "import_error", "error": "Could not import get_ocr_service_status"}
        except Exception as e:
            services_detail["gemini_ocr"] = {"status": "error", "error": str(e), "mode": "gemini_exclusive"}
        
        # OpenAI categorization service detail (old system format)
        try:
            get_category_service_status = MonitoringUtils.safe_import('app.services.category', 'get_category_service_status')
            if get_category_service_status:
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
            else:
                services_detail["openai_categorization"] = {"status": "import_error", "error": "Could not import get_category_service_status"}
        except Exception as e:
            services_detail["openai_categorization"] = {"status": "error", "error": str(e), "mode": "openai_exclusive"}
        
        # Translation services detail (old system format)
        try:
            get_translation_service_status = MonitoringUtils.safe_import('app.services.translation', 'get_translation_service_status')
            if get_translation_service_status:
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
            else:
                services_detail["google_translate_translation"] = {"status": "import_error", "error": "Could not import get_translation_service_status"}
                services_detail["openai_translation"] = {"status": "import_error", "error": "Could not import get_translation_service_status"}
        except Exception as e:
            services_detail["google_translate_translation"] = {"status": "error", "error": str(e), "role": "primary"}
            services_detail["openai_translation"] = {"status": "error", "error": str(e), "role": "fallback"}
        
        # Description service detail (old system format)
        try:
            get_description_service_status = MonitoringUtils.safe_import('app.services.description', 'get_description_service_status')
            if get_description_service_status:
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
            else:
                services_detail["openai_description"] = {"status": "import_error", "error": "Could not import get_description_service_status"}
        except Exception as e:
            services_detail["openai_description"] = {"status": "error", "error": str(e), "role": "primary"}
        
        # Image service detail (old system format)
        try:
            get_image_service_status = MonitoringUtils.safe_import('app.services.image', 'get_image_service_status')
            if get_image_service_status:
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
            else:
                services_detail["imagen3_image_generation"] = {"status": "import_error", "error": "Could not import get_image_service_status"}
        except Exception as e:
            services_detail["imagen3_image_generation"] = {"status": "error", "error": str(e), "role": "primary"}
        
        return services_detail
    
    async def _get_sse_session_count(self) -> int:
        """Get SSE session count (old system format)"""
        try:
            get_active_sessions = MonitoringUtils.safe_import(
                'app.api.v1.endpoints.menu_parallel.shared_state', 'get_active_sessions'
            )
            if get_active_sessions:
                active_sessions = get_active_sessions()
                return len(active_sessions)
            else:
                return 0  # No SSE sessions if module not available
        except Exception as e:
            return 0  # Default to 0 on error
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Detailed health check"""
        try:
            # Get basic health status (which now has full compatibility)
            basic_health = await self.get_basic_health()
            
            # Add additional detailed information for new system
            basic_health["healthy_services_count"] = sum(1 for available in basic_health["services"].values() if available)
            basic_health["total_services"] = len(basic_health["services"])
            
            return basic_health
            
        except Exception as e:
            return self._handle_error(e, "system_monitoring_detailed").to_dict()
    
    def _get_fallback_health(self) -> Dict[str, Any]:
        """Fallback health status (old system format)"""
        return {
            "status": "degraded",
            "version": "1.0.0",
            "timestamp": MonitoringUtils.get_asyncio_timestamp(),
            "environment": {
                "port": os.getenv("PORT", "8000"),
                "google_credentials": "not_loaded"
            },
            "services": {},
            "services_detail": {},
            "ping_pong_sessions": 0
        }
    
    async def get_status(self) -> ServiceStatus:
        """Get service status"""
        health = await self.get_basic_health()
        return ServiceStatus(
            name="system_monitoring",
            available=health["status"] == "healthy",
            status=health["status"],
            details=health
        )


# ===============================
# API Health Service
# ===============================

class APIHealthService(MonitoringServiceBase):
    """API health monitoring service"""
    
    async def get_comprehensive_health(self) -> Dict[str, Any]:
        """Comprehensive API health check"""
        try:
            health_results = {}
            overall_health = True
            
            # Check health status of each API service
            apis_to_check = [
                ("google_translate", "app.services.translation.google_translate", "GoogleTranslateService"),
                ("openai_description", "app.services.description.openai", "OpenAIDescriptionService"),
                ("imagen3", "app.services.image.imagen3", "Imagen3Service"),
            ]
            
            for api_name, module_path, class_name in apis_to_check:
                try:
                    # Safely import service class
                    service_class = MonitoringUtils.safe_import(module_path, class_name)
                    
                    if service_class:
                        service = service_class()
                        available = service.is_available()
                        health_results[api_name] = {
                            "status": "healthy" if available else "unavailable",
                            "available": available,
                            "critical": api_name in ["google_translate"],  # Critical service setting
                            "service_class": class_name
                        }
                        
                        # If critical service is unavailable, mark overall health as degraded
                        if not available and health_results[api_name]["critical"]:
                            overall_health = False
                    else:
                        health_results[api_name] = {
                            "status": "import_error",
                            "available": False,
                            "error": f"Could not import {class_name}",
                            "critical": api_name in ["google_translate"]
                        }
                        if api_name in ["google_translate"]:
                            overall_health = False
                            
                except Exception as e:
                    health_results[api_name] = {
                        "status": "error",
                        "available": False,
                        "error": str(e),
                        "critical": api_name in ["google_translate"]
                    }
                    if api_name in ["google_translate"]:
                        overall_health = False
            
            # Redis health check
            redis_health = await self._check_redis_health()
            health_results["redis"] = redis_health
            if not redis_health["available"]:
                overall_health = False
            
            return {
                "overall_health": "healthy" if overall_health else "degraded",
                "api_services": health_results,
                "timestamp": MonitoringUtils.get_current_timestamp(),
                "integration_mode": "real_api_integration",
                "checked_apis": len(apis_to_check) + 1,  # +1 for Redis
                "healthy_apis": sum(1 for api in health_results.values() if api["available"])
            }
            
        except Exception as e:
            return self._handle_error(e, "api_health").to_dict()
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Redis health check"""
        try:
            test_redis_connection = MonitoringUtils.safe_import(
                'app.tasks.menu_item_parallel_tasks', 'test_redis_connection'
            )
            
            if test_redis_connection:
                redis_result = test_redis_connection()
                return {
                    "available": redis_result.get("success", False),
                    "status": "healthy" if redis_result.get("success", False) else "unavailable",
                    "details": redis_result,
                    "critical": True
                }
            else:
                return {
                    "available": False,
                    "status": "import_error",
                    "error": "Could not import test_redis_connection",
                    "critical": True
                }
        except Exception as e:
            return {
                "available": False,
                "status": "error",
                "error": str(e),
                "critical": True
            }
    
    async def get_status(self) -> ServiceStatus:
        """Get service status"""
        health = await self.get_comprehensive_health()
        return ServiceStatus(
            name="api_health",
            available=health["overall_health"] == "healthy",
            status=health["overall_health"],
            details=health
        )


# ===============================
# SSE Monitoring Service
# ===============================

class SSEMonitoringService(MonitoringServiceBase):
    """SSE streaming monitoring service"""
    
    async def get_sse_statistics(self) -> Dict[str, Any]:
        """Get SSE statistics"""
        try:
            # Safely import existing SSE statistics functions
            get_sse_statistics = MonitoringUtils.safe_import(
                'app.api.v1.endpoints.menu_parallel.shared_state', 'get_sse_statistics'
            )
            get_active_sessions = MonitoringUtils.safe_import(
                'app.api.v1.endpoints.menu_parallel.shared_state', 'get_active_sessions'
            )
            
            if not get_sse_statistics or not get_active_sessions:
                return self._get_fallback_sse_stats()
            
            # Basic statistics
            sse_stats = get_sse_statistics()
            active_sessions = get_active_sessions()
            
            # Detailed session information
            active_sessions_info = []
            current_time = MonitoringUtils.get_current_timestamp()
            
            for session_id, session_data in active_sessions.items():
                start_time = session_data.get("start_time", current_time)
                uptime = MonitoringUtils.format_uptime(start_time)
                
                session_info = {
                    "session_id": session_id,
                    "uptime": uptime,
                    "total_items": session_data.get("total_items", 0),
                    "connection_active": session_data.get("connection_active", False),
                    "events_queued": len(sse_stats.get("progress_streams", {}).get(session_id, []))
                }
                active_sessions_info.append(session_info)
            
            # Performance indicators
            performance_indicators = {
                "low_session_count": len(active_sessions) < 10,
                "manageable_queue_size": sse_stats.get("total_events_queued", 0) < 100,
                "healthy_memory_usage": True  # Memory usage check to be implemented later
            }
            
            return {
                "success": True,
                "sse_statistics": sse_stats,
                "active_sessions": active_sessions_info,
                "active_sessions_count": len(active_sessions),
                "total_events_queued": sse_stats.get("total_events_queued", 0),
                "performance_indicators": performance_indicators,
                "features": [
                    "real_time_progress_streaming",
                    "automatic_heartbeat",
                    "connection_management",
                    "event_queuing",
                    "memory_efficient_cleanup"
                ],
                "timestamp": current_time
            }
            
        except Exception as e:
            return self._handle_error(e, "sse_monitoring").to_dict()
    
    async def get_performance_stats(self) -> Dict[str, Any]:
        """Performance statistics"""
        try:
            # Get SSE statistics
            sse_stats = await self.get_sse_statistics()
            
            if not sse_stats["success"]:
                return sse_stats
            
            # Calculate performance metrics
            active_sessions = sse_stats["active_sessions"]
            
            # Session duration statistics
            session_durations = [session["uptime"] for session in active_sessions]
            
            if session_durations:
                avg_duration = sum(session_durations) / len(session_durations)
                max_duration = max(session_durations)
                min_duration = min(session_durations)
            else:
                avg_duration = max_duration = min_duration = 0
            
            # Total event count statistics
            total_events = sum(session["events_queued"] for session in active_sessions)
            
            return {
                "success": True,
                "current_load": {
                    "active_sessions": sse_stats["active_sessions_count"],
                    "total_events_queued": total_events,
                    "average_events_per_session": total_events / max(1, len(active_sessions))
                },
                "session_statistics": {
                    "total_active": len(active_sessions),
                    "average_duration": avg_duration,
                    "max_duration": max_duration,
                    "min_duration": min_duration
                },
                "performance_health": {
                    "low_load": len(active_sessions) < 10,
                    "manageable_queue": total_events < 100,
                    "reasonable_duration": avg_duration < 300  # Within 5 minutes
                },
                "timestamp": MonitoringUtils.get_current_timestamp()
            }
            
        except Exception as e:
            return self._handle_error(e, "sse_performance").to_dict()
    
    def _get_fallback_sse_stats(self) -> Dict[str, Any]:
        """Fallback SSE statistics"""
        return {
            "success": False,
            "error": "SSE statistics unavailable",
            "sse_statistics": {},
            "active_sessions": [],
            "active_sessions_count": 0,
            "total_events_queued": 0,
            "timestamp": MonitoringUtils.get_current_timestamp()
        }
    
    async def get_status(self) -> ServiceStatus:
        """Get service status"""
        stats = await self.get_sse_statistics()
        return ServiceStatus(
            name="sse_monitoring",
            available=stats["success"],
            status="healthy" if stats["success"] else "degraded",
            details=stats
        )


# ===============================
# Diagnostics Service
# ===============================

class DiagnosticsService(MonitoringServiceBase):
    """System diagnostics service"""
    
    async def get_system_diagnostics(self) -> Dict[str, Any]:
        """Get system diagnostic information - FULL COMPATIBILITY with old system"""
        try:
            # Get information from unified auth system
            get_compatibility_variables = MonitoringUtils.safe_import('app.services.auth', 'get_compatibility_variables')
            get_vision_client = MonitoringUtils.safe_import('app.services.auth', 'get_vision_client')
            get_auth_status = MonitoringUtils.safe_import('app.services.auth.unified_auth', 'get_auth_status')
            get_auth_troubleshooting = MonitoringUtils.safe_import('app.services.auth.unified_auth', 'get_auth_troubleshooting')
            
            if not get_compatibility_variables or not get_auth_status:
                return self._get_fallback_diagnostics()
            
            # API authentication info
            auth_vars = get_compatibility_variables()
            auth_status = get_auth_status()
            
            VISION_AVAILABLE = auth_vars.get("VISION_AVAILABLE", False)
            TRANSLATE_AVAILABLE = auth_vars.get("TRANSLATE_AVAILABLE", False)
            OPENAI_AVAILABLE = auth_vars.get("OPENAI_AVAILABLE", False)
            vision_client = get_vision_client() if get_vision_client else None
            
            # OLD SYSTEM FORMAT
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
                "environment": await self._get_environment_diagnostics(),
                "authentication": {
                    "method": auth_status.get("method", "unknown"),
                    "source": auth_status.get("source", "unknown"),
                    "available": auth_status.get("available", False),
                    "troubleshooting": get_auth_troubleshooting() if get_auth_troubleshooting and not auth_status.get("available", False) else None
                }
            }
            
            # ===== MISSING FEATURE: Google Vision API connection test =====
            if VISION_AVAILABLE and vision_client:
                try:
                    google_vision = MonitoringUtils.safe_import('google.cloud', 'vision')
                    if google_vision:
                        # Test connection with empty image
                        test_response = vision_client.text_detection(google_vision.Image(content=b''))
                        diagnostic_info["vision_api"]["test_status"] = "connection_ok"
                except Exception as e:
                    diagnostic_info["vision_api"]["test_status"] = f"connection_failed: {str(e)}"
                    diagnostic_info["vision_api"]["available"] = False
            
            # ===== MISSING FEATURE: AWS Secrets Manager test =====
            aws_settings = MonitoringUtils.safe_import('app.core.config.aws', 'aws_settings')
            if aws_settings and aws_settings.use_secrets_manager:
                try:
                    aws_status = {
                        "use_aws_secrets_manager": aws_settings.use_secrets_manager,
                        "aws_region": aws_settings.region,
                        "aws_secret_name": aws_settings.secret_name
                    }
                    diagnostic_info["aws_secrets_manager"] = aws_status
                except Exception as e:
                    diagnostic_info["aws_secrets_manager"] = {"error": str(e)}
            else:
                diagnostic_info["aws_secrets_manager"] = {
                    "message": "AWS Secrets Manager is disabled (USE_AWS_SECRETS_MANAGER=false)"
                }
            
            return diagnostic_info
            
        except Exception as e:
            return self._handle_error(e, "system_diagnostics").to_dict()
    
    async def get_mobile_diagnostics(self, request_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Mobile-specific diagnostic information - FULL COMPATIBILITY"""
        try:
            # Get Vision API status
            is_vision_available = MonitoringUtils.safe_import('app.services.auth', 'is_vision_available')
            VISION_AVAILABLE = is_vision_available() if is_vision_available else False
            
            # ===== OLD SYSTEM FORMAT: Request information analysis =====
            network_info = {
                "client_ip": "Unknown",
                "user_agent": "Unknown", 
                "is_mobile_detected": False,
                "request_headers": {},
                "forwarded_for": None,
                "real_ip": None
            }
            
            if request_info:
                headers = request_info.get("headers", {})
                user_agent = request_info.get("user_agent", "Unknown")
                
                network_info.update({
                    "client_ip": request_info.get("client_ip", "Unknown"),
                    "user_agent": user_agent,
                    "is_mobile_detected": self._detect_mobile(user_agent),
                    "request_headers": headers,
                    "forwarded_for": headers.get("x-forwarded-for"),
                    "real_ip": headers.get("x-real-ip")
                })
            
            # Service status detailed confirmation
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
            
            # ===== MISSING FEATURE: Mobile-specific issue checks =====
            mobile_issues = []
            
            if not VISION_AVAILABLE:
                mobile_issues.append("Vision API unavailable - this will cause Stage 1 failures")
            
            if request_info:
                headers = request_info.get("headers", {})
                origin = headers.get("origin", "")
                if "vercel.app" not in origin and "localhost" not in origin:
                    mobile_issues.append(f"Request from unexpected origin: {origin}")
                
                accept_header = headers.get("accept", "")
                if "text/event-stream" not in accept_header:
                    mobile_issues.append("SSE support may be limited")
            
            # OLD SYSTEM FORMAT
            return {
                "mobile_diagnostic": True,
                "timestamp": MonitoringUtils.get_asyncio_timestamp(),  # Use asyncio timestamp for compatibility
                "network_info": network_info,
                "services_status": services_status,
                "mobile_issues": mobile_issues,
                "recommendations": [
                    "Use Wi-Fi instead of mobile data for better stability",
                    "Ensure latest browser version for SSE support",
                    "Clear browser cache if experiencing persistent issues"
                ]
            }
            
        except Exception as e:
            return self._handle_error(e, "mobile_diagnostics").to_dict()
    
    async def _get_environment_diagnostics(self) -> Dict[str, Any]:
        """Environment configuration diagnostics (old system format)"""
        try:
            aws_settings = MonitoringUtils.safe_import('app.core.config.aws', 'aws_settings')
            
            env_vars = {
                "google_credentials_available": "GOOGLE_CREDENTIALS_JSON" in os.environ,
                "google_credentials_json_env": "GOOGLE_CREDENTIALS_JSON" in os.environ,
                "openai_api_key_env": "OPENAI_API_KEY" in os.environ,
                "use_aws_secrets_manager": aws_settings.use_secrets_manager if aws_settings else False,
                "aws_region": aws_settings.region if aws_settings and aws_settings.use_secrets_manager else None,
                "aws_secret_name": aws_settings.secret_name if aws_settings and aws_settings.use_secrets_manager else None
            }
            
            return env_vars
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_fallback_diagnostics(self) -> Dict[str, Any]:
        """Fallback diagnostics (old system format)"""
        return {
            "vision_api": {"available": False, "error": "Auth service unavailable"},
            "translate_api": {"available": False, "error": "Auth service unavailable"},
            "openai_api": {"available": False, "error": "Auth service unavailable"},
            "environment": {"error": "Environment diagnostics unavailable"},
            "authentication": {"available": False, "error": "Auth diagnostics unavailable"}
        }
    
    def _detect_mobile(self, user_agent: str) -> bool:
        """Detect mobile devices"""
        mobile_indicators = [
            "mobile", "android", "iphone", "ipad", 
            "blackberry", "windows phone", "opera mini"
        ]
        return any(indicator in user_agent.lower() for indicator in mobile_indicators)
    
    async def get_status(self) -> ServiceStatus:
        """Get service status"""
        diagnostics = await self.get_system_diagnostics()
        return ServiceStatus(
            name="diagnostics",
            available=True,  # Diagnostics are always available
            status="healthy",
            details=diagnostics
        )