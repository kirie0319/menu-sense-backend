"""
🔄 Migration Compatibility Layer

This module provides backward compatibility and gradual migration support
for transitioning from legacy task functions to the new pure task architecture.
"""

import logging
import os
from typing import Dict, Any, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


class MigrationConfig:
    """Migration configuration settings"""
    
    def __init__(self):
        # Environment variable to control migration mode
        self.use_pure_tasks = os.getenv("USE_PURE_TASKS", "true").lower() == "true"
        self.enable_fallback = os.getenv("ENABLE_TASK_FALLBACK", "true").lower() == "true"
        self.log_migration_events = os.getenv("LOG_MIGRATION_EVENTS", "true").lower() == "true"
    
    def should_use_pure_tasks(self) -> bool:
        """Check if pure tasks should be used"""
        return self.use_pure_tasks
    
    def should_enable_fallback(self) -> bool:
        """Check if fallback to legacy is enabled"""
        return self.enable_fallback
    
    def should_log_events(self) -> bool:
        """Check if migration events should be logged"""
        return self.log_migration_events


migration_config = MigrationConfig()


def migration_wrapper(pure_func: Callable, legacy_func: Optional[Callable] = None):
    """
    Decorator to wrap functions for migration compatibility
    
    Args:
        pure_func: The new pure function
        legacy_func: The legacy function (optional fallback)
    
    Returns:
        Wrapped function that can switch between pure and legacy
    """
    
    @wraps(pure_func)
    def wrapper(*args, **kwargs):
        func_name = pure_func.__name__
        
        try:
            # Try pure function first if enabled
            if migration_config.should_use_pure_tasks():
                if migration_config.should_log_events():
                    logger.info(f"🟢 Using pure function: {func_name}")
                return pure_func(*args, **kwargs)
            
            # Use legacy function if pure tasks are disabled
            if legacy_func is not None:
                if migration_config.should_log_events():
                    logger.info(f"🟡 Using legacy function: {func_name}")
                return legacy_func(*args, **kwargs)
            else:
                # No legacy function available, force pure
                if migration_config.should_log_events():
                    logger.warning(f"⚠️ No legacy function available, using pure: {func_name}")
                return pure_func(*args, **kwargs)
                
        except Exception as e:
            # Fallback to legacy if pure function fails
            if migration_config.should_enable_fallback() and legacy_func is not None:
                if migration_config.should_log_events():
                    logger.warning(f"🔴 Pure function failed, falling back to legacy: {func_name} - {e}")
                try:
                    return legacy_func(*args, **kwargs)
                except Exception as fallback_error:
                    logger.error(f"❌ Both pure and legacy functions failed: {func_name} - Pure: {e}, Legacy: {fallback_error}")
                    raise
            else:
                logger.error(f"❌ Pure function failed, no fallback available: {func_name} - {e}")
                raise
    
    return wrapper


class CompatibilityFunctionRegistry:
    """Registry for compatibility functions"""
    
    def __init__(self):
        self._functions: Dict[str, Dict[str, Callable]] = {}
    
    def register(self, name: str, pure_func: Callable, legacy_func: Optional[Callable] = None):
        """Register a compatibility function pair"""
        self._functions[name] = {
            "pure": pure_func,
            "legacy": legacy_func,
            "wrapper": migration_wrapper(pure_func, legacy_func)
        }
        
        if migration_config.should_log_events():
            logger.info(f"📝 Registered compatibility function: {name}")
    
    def get(self, name: str) -> Optional[Callable]:
        """Get the wrapped compatibility function"""
        if name in self._functions:
            return self._functions[name]["wrapper"]
        return None
    
    def get_pure(self, name: str) -> Optional[Callable]:
        """Get the pure function directly"""
        if name in self._functions:
            return self._functions[name]["pure"]
        return None
    
    def get_legacy(self, name: str) -> Optional[Callable]:
        """Get the legacy function directly"""
        if name in self._functions:
            return self._functions[name]["legacy"]
        return None
    
    def list_functions(self) -> Dict[str, Dict[str, bool]]:
        """List all registered functions and their availability"""
        result = {}
        for name, funcs in self._functions.items():
            result[name] = {
                "pure_available": funcs["pure"] is not None,
                "legacy_available": funcs["legacy"] is not None,
                "currently_using": "pure" if migration_config.should_use_pure_tasks() else "legacy"
            }
        return result


# Global registry instance
compatibility_registry = CompatibilityFunctionRegistry()


def register_task_functions():
    """Register all task function compatibility pairs"""
    
    try:
        # Import pure functions
        from app.tasks.pure_menu_tasks import (
            pure_real_translate_menu_item,
            pure_real_generate_menu_description,
            pure_real_generate_menu_image,
            pure_test_translate_menu_item,
            pure_test_generate_menu_description,
            pure_get_real_status
        )
        
        # Import legacy functions
        try:
            from app.tasks.menu_item_parallel_tasks import (
                real_translate_menu_item,
                real_generate_menu_description,
                real_generate_menu_image,
                test_translate_menu_item,
                test_generate_menu_description,
                get_real_status,
                test_redis_connection
            )
            legacy_available = True
        except ImportError:
            logger.warning("⚠️ Legacy task functions not available")
            legacy_available = False
            real_translate_menu_item = None
            real_generate_menu_description = None
            real_generate_menu_image = None
            test_translate_menu_item = None
            test_generate_menu_description = None
            get_real_status = None
            test_redis_connection = None
        
        # Register function pairs
        compatibility_registry.register(
            "real_translate_menu_item",
            pure_real_translate_menu_item,
            real_translate_menu_item if legacy_available else None
        )
        
        compatibility_registry.register(
            "real_generate_menu_description",
            pure_real_generate_menu_description,
            real_generate_menu_description if legacy_available else None
        )
        
        compatibility_registry.register(
            "real_generate_menu_image",
            pure_real_generate_menu_image,
            real_generate_menu_image if legacy_available else None
        )
        
        compatibility_registry.register(
            "test_translate_menu_item",
            pure_test_translate_menu_item,
            test_translate_menu_item if legacy_available else None
        )
        
        compatibility_registry.register(
            "test_generate_menu_description",
            pure_test_generate_menu_description,
            test_generate_menu_description if legacy_available else None
        )
        
        compatibility_registry.register(
            "get_real_status",
            pure_get_real_status,
            get_real_status if legacy_available else None
        )
        
        # Redis connection test function was removed - no longer needed
        # compatibility_registry.register(
        #     "test_redis_connection",
        #     pure_test_redis_connection,
        #     test_redis_connection if legacy_available else None
        # )
        
        logger.info("✅ Task function compatibility registry initialized")
        
    except Exception as e:
        logger.error(f"❌ Failed to register task functions: {e}")
        raise


# Auto-register functions on module import
try:
    register_task_functions()
except Exception as e:
    logger.warning(f"⚠️ Failed to auto-register task functions: {e}")


def get_migration_status() -> Dict[str, Any]:
    """Get current migration status and configuration"""
    return {
        "migration_config": {
            "use_pure_tasks": migration_config.should_use_pure_tasks(),
            "enable_fallback": migration_config.should_enable_fallback(),
            "log_migration_events": migration_config.should_log_events()
        },
        "registered_functions": compatibility_registry.list_functions(),
        "environment_variables": {
            "USE_PURE_TASKS": os.getenv("USE_PURE_TASKS", "true"),
            "ENABLE_TASK_FALLBACK": os.getenv("ENABLE_TASK_FALLBACK", "true"),
            "LOG_MIGRATION_EVENTS": os.getenv("LOG_MIGRATION_EVENTS", "true")
        }
    }


def set_migration_mode(use_pure_tasks: bool) -> None:
    """
    Dynamically set migration mode
    
    Args:
        use_pure_tasks: Whether to use pure tasks
    """
    migration_config.use_pure_tasks = use_pure_tasks
    mode = "pure" if use_pure_tasks else "legacy"
    logger.info(f"🔄 Migration mode changed to: {mode}")


def enable_fallback(enabled: bool) -> None:
    """
    Enable or disable fallback to legacy functions
    
    Args:
        enabled: Whether to enable fallback
    """
    migration_config.enable_fallback = enabled
    status = "enabled" if enabled else "disabled"
    logger.info(f"🔄 Fallback to legacy functions: {status}")


# Convenience functions for getting compatible task functions
def get_compatible_translate_function():
    """Get compatible translation function"""
    return compatibility_registry.get("real_translate_menu_item")


def get_compatible_description_function():
    """Get compatible description generation function"""
    return compatibility_registry.get("real_generate_menu_description")


def get_compatible_image_function():
    """Get compatible image generation function"""
    return compatibility_registry.get("real_generate_menu_image")


def get_compatible_status_function():
    """Get compatible status function"""
    return compatibility_registry.get("get_real_status")


def get_compatible_redis_test_function():
    """Get compatible Redis test function - deprecated, returns None"""
    # Redis connection test function was removed - no longer needed
    return None


# Export
__all__ = [
    "MigrationConfig",
    "migration_config",
    "migration_wrapper",
    "CompatibilityFunctionRegistry",
    "compatibility_registry",
    "register_task_functions",
    "get_migration_status",
    "set_migration_mode",
    "enable_fallback",
    "get_compatible_translate_function",
    "get_compatible_description_function", 
    "get_compatible_image_function",
    "get_compatible_status_function",
    "get_compatible_redis_test_function"
]