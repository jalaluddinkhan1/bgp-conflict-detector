"""
Pyroscope Integration for Continuous Profiling

Pyroscope provides continuous profiling to identify performance bottlenecks
and optimize application performance.
"""
import os
from typing import Optional

from app.config import settings
from app.middleware.logging import logger


def setup_pyroscope() -> bool:
    """
    Setup Pyroscope for continuous profiling.
    
    Returns:
        True if Pyroscope is configured, False otherwise
    """
    pyroscope_enabled = getattr(settings, "PYROSCOPE_ENABLED", False)
    pyroscope_url = getattr(settings, "PYROSCOPE_URL", None)
    
    if not pyroscope_enabled or not pyroscope_url:
        logger.info("Pyroscope profiling disabled")
        return False
    
    try:
        import pyroscope
        
        pyroscope.configure(
            application_name=os.getenv("PYROSCOPE_APP_NAME", "bgp-orchestrator"),
            server_address=pyroscope_url,
            sample_rate=100,  # Sample 100% of requests
            detect_subprocesses=True,
            enable_logging=True,
            tags={
                "environment": os.getenv("ENVIRONMENT", "production"),
                "version": os.getenv("APP_VERSION", "1.0.0"),
            },
        )
        
        logger.info(f"Pyroscope profiling enabled: {pyroscope_url}")
        return True
        
    except ImportError:
        logger.warning("Pyroscope not installed. Install with: pip install pyroscope-io")
        return False
    except Exception as e:
        logger.error(f"Failed to setup Pyroscope: {e}")
        return False


def start_pyroscope_profiling() -> None:
    """Start Pyroscope profiling (call during application startup)."""
    setup_pyroscope()


# Profiling decorators
def profile_function(func):
    """Decorator to profile a specific function."""
    try:
        import pyroscope
        
        def wrapper(*args, **kwargs):
            with pyroscope.tag_wrapper({"function": func.__name__}):
                return func(*args, **kwargs)
        
        return wrapper
    except ImportError:
        # Pyroscope not available, return function as-is
        return func


def profile_async_function(func):
    """Decorator to profile an async function."""
    try:
        import pyroscope
        import asyncio
        
        async def wrapper(*args, **kwargs):
            with pyroscope.tag_wrapper({"function": func.__name__}):
                return await func(*args, **kwargs)
        
        return wrapper
    except ImportError:
        # Pyroscope not available, return function as-is
        return func

