"""
Feature Store Materialization Job

Runs periodically to materialize features from offline store to online store.
Typically runs every 5 minutes to keep online store up-to-date.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.config import settings
from app.middleware.logging import logger
from ml.feature_store.feature_store_client import get_feature_store_client


async def run_materialization_job() -> None:
    """
    Run feature materialization job.
    
    Materializes features from the last 5 minutes to keep online store updated.
    """
    if not getattr(settings, "FEATURE_STORE_ENABLED", False):
        return
    
    feature_store = get_feature_store_client()
    if not feature_store:
        return
    
    try:
        # Materialize features from last 5 minutes
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(minutes=5)
        
        success = feature_store.materialize_features(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        
        if success:
            logger.info(
                f"Feature materialization completed",
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat(),
            )
        else:
            logger.warning("Feature materialization failed")
            
    except Exception as e:
        logger.error(f"Error in materialization job: {e}", exc_info=True)


async def start_materialization_scheduler(interval_minutes: int = 5) -> None:
    """
    Start periodic materialization scheduler.
    
    Args:
        interval_minutes: Interval between materialization runs (default: 5 minutes)
    """
    if not getattr(settings, "FEATURE_STORE_ENABLED", False):
        logger.info("Feature store materialization disabled")
        return
    
    logger.info(f"Starting feature materialization scheduler (interval: {interval_minutes} minutes)")
    
    while True:
        try:
            await asyncio.sleep(interval_minutes * 60)
            await run_materialization_job()
        except asyncio.CancelledError:
            logger.info("Feature materialization scheduler stopped")
            break
        except Exception as e:
            logger.error(f"Error in materialization scheduler: {e}", exc_info=True)
            await asyncio.sleep(60)  # Wait 1 minute before retrying


# Background task reference
_materialization_task: Optional[asyncio.Task] = None


def start_background_materialization(interval_minutes: int = 5) -> None:
    """
    Start materialization scheduler as background task.
    
    Args:
        interval_minutes: Interval between materialization runs
    """
    global _materialization_task
    
    if not getattr(settings, "FEATURE_STORE_ENABLED", False):
        return
    
    if _materialization_task is None or _materialization_task.done():
        _materialization_task = asyncio.create_task(
            start_materialization_scheduler(interval_minutes)
        )
        logger.info("Feature materialization scheduler started")


def stop_background_materialization() -> None:
    """Stop the materialization scheduler."""
    global _materialization_task
    
    if _materialization_task and not _materialization_task.done():
        _materialization_task.cancel()
        logger.info("Feature materialization scheduler stopped")

