"""
Feature Store API endpoints for ML model inference.
"""
from typing import List

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import CurrentUser
from app.middleware.logging import logger
from ml.feature_store.feature_store_client import get_feature_store_client

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/features", tags=["Feature Store"])


class FeatureRequest(BaseModel):
    """Request model for feature serving."""
    
    entity_ids: List[str] = Field(..., description="List of entity IDs (e.g., peer IP:ASN)")
    feature_names: List[str] = Field(
        ...,
        description="List of feature names to retrieve",
        examples=[["peer_uptime_seconds", "prefix_count", "as_path_length"]],
    )


class FeatureResponse(BaseModel):
    """Response model for feature serving."""
    
    entity_id: str
    features: dict
    timestamp: str


@router.post("/serve", response_model=List[FeatureResponse])
@limiter.limit("100/second")
async def serve_features(
    request: Request,
    feature_request: FeatureRequest,
    user: CurrentUser,
) -> List[FeatureResponse]:
    """
    Serve features from feature store for ML model inference.
    
    Retrieves features for given entity IDs (e.g., BGP sessions) from
    the online feature store for use in ML model predictions.
    
    Example:
        POST /api/v1/features/serve
        {
            "entity_ids": ["192.168.1.1:65000", "192.168.1.2:65001"],
            "feature_names": ["peer_uptime_seconds", "prefix_count", "as_path_length"]
        }
    """
    from datetime import datetime, timezone
    
    try:
        feature_store = get_feature_store_client()
        
        if not feature_store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Feature store is not enabled or configured",
            )
        
        # Get features from feature store
        features_dict = await feature_store.get_features(
            entity_ids=feature_request.entity_ids,
            feature_names=feature_request.feature_names,
        )
        
        # Format response
        responses = []
        for entity_id in feature_request.entity_ids:
            entity_features = features_dict.get(entity_id, {})
            responses.append(
                FeatureResponse(
                    entity_id=entity_id,
                    features=entity_features,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
            )
        
        logger.info(
            f"Features served",
            user=user.email,
            entity_count=len(feature_request.entity_ids),
            feature_count=len(feature_request.feature_names),
        )
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving features: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error serving features: {str(e)}",
        )


@router.post("/materialize")
@limiter.limit("1/minute")  # Limit materialization to once per minute
async def trigger_materialization(
    request: Request,
    user: CurrentUser,
    start_date: str = Query(..., description="Start date (ISO format)"),
    end_date: str = Query(..., description="End date (ISO format)"),
) -> dict:
    """
    Trigger feature materialization (batch job).
    
    Materializes features from offline store to online store for the
    specified date range. Typically run as a scheduled job.
    """
    try:
        feature_store = get_feature_store_client()
        
        if not feature_store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Feature store is not enabled or configured",
            )
        
        success = feature_store.materialize_features(
            start_date=start_date,
            end_date=end_date,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to trigger materialization",
            )
        
        logger.info(
            f"Feature materialization triggered",
            user=user.email,
            start_date=start_date,
            end_date=end_date,
        )
        
        return {
            "status": "success",
            "message": "Materialization triggered",
            "start_date": start_date,
            "end_date": end_date,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering materialization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering materialization: {str(e)}",
        )


@router.get("/health")
@limiter.limit("10/second")
async def feature_store_health(
    request: Request,
    user: CurrentUser,
) -> dict:
    """
    Check feature store health.
    
    Returns status of feature store connection and configuration.
    """
    feature_store = get_feature_store_client()
    
    if not feature_store:
        return {
            "status": "disabled",
            "message": "Feature store is not enabled",
        }
    
    return {
        "status": "enabled",
        "initialized": feature_store._initialized,
        "repo_path": feature_store.repo_path,
    }

