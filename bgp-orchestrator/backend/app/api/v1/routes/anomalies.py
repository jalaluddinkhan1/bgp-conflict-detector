"""
Anomaly Detection API endpoints.
"""
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import CurrentUser, DbSession
from app.middleware.logging import logger
from models.anomaly import Anomaly, AnomalySeverity, AnomalyType
from observability.anomaly_detector import AnomalyDetector
from observability.metrics import track_anomaly

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/anomalies", tags=["Anomaly Detection"])

# Global detector instance
_detector: AnomalyDetector | None = None


def get_detector() -> AnomalyDetector:
    """Get or create anomaly detector instance."""
    global _detector
    if _detector is None:
        _detector = AnomalyDetector(sigma_threshold=3.0)
    return _detector


class AnomalyResponse(BaseModel):
    """Response model for anomaly."""
    
    id: int
    metric_name: str
    anomaly_type: str
    timestamp: datetime
    value: float
    expected_value: float
    deviation: float
    severity: str
    device: Optional[str] = None
    metadata: Optional[dict] = None


class AnomalyDetectionRequest(BaseModel):
    """Request model for anomaly detection."""
    
    metric_name: str = Field(..., description="Name of the metric to analyze")
    timestamps: List[datetime] = Field(..., description="List of timestamps")
    values: List[float] = Field(..., description="List of metric values")
    device: Optional[str] = Field(None, description="Device name (optional)")


@router.post("/detect", response_model=List[AnomalyResponse])
@limiter.limit("5/minute")  # Limit detection to 5 times per minute
async def detect_anomalies(
    request: Request,
    detection_request: AnomalyDetectionRequest,
    db: DbSession,
    user: CurrentUser,
) -> List[AnomalyResponse]:
    """
    Detect anomalies in time-series metric data.
    
    Uses Prophet for seasonality detection and 3-sigma rule for anomaly detection.
    Detected anomalies are stored in the database.
    """
    start_time = time.time()
    
    try:
        if len(detection_request.timestamps) != len(detection_request.values):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="timestamps and values must have the same length",
            )
        
        detector = get_detector()
        
        # Detect and store anomalies
        anomalies = await detector.detect_and_store_anomalies(
            db=db,
            metric_name=detection_request.metric_name,
            timestamps=detection_request.timestamps,
            values=detection_request.values,
            device=detection_request.device,
        )
        
        # Track metrics
        duration = time.time() - start_time
        for anomaly in anomalies:
            track_anomaly(
                metric_name=anomaly.metric_name,
                severity=anomaly.severity.value,
                anomaly_type=anomaly.anomaly_type.value,
                duration=duration,
            )
        
        logger.info(
            f"Anomaly detection completed",
            user=user.email,
            metric=detection_request.metric_name,
            anomalies_detected=len(anomalies),
            duration=duration,
        )
        
        return [
            AnomalyResponse(
                id=anomaly.id,
                metric_name=anomaly.metric_name,
                anomaly_type=anomaly.anomaly_type.value,
                timestamp=anomaly.timestamp,
                value=anomaly.value,
                expected_value=anomaly.expected_value,
                deviation=anomaly.deviation,
                severity=anomaly.severity.value,
                device=anomaly.device,
                metadata=anomaly.metadata,
            )
            for anomaly in anomalies
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error detecting anomalies: {str(e)}",
        )


@router.get("/", response_model=List[AnomalyResponse])
@limiter.limit("10/second")
async def list_anomalies(
    request: Request,
    db: DbSession,
    user: CurrentUser,
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    device: Optional[str] = Query(None, description="Filter by device"),
    severity: Optional[AnomalySeverity] = Query(None, description="Filter by severity"),
    hours: int = Query(24, ge=1, le=168, description="Number of hours to look back"),
) -> List[AnomalyResponse]:
    """
    List recent anomalies with optional filtering.
    """
    try:
        detector = get_detector()
        
        anomalies = await detector.get_recent_anomalies(
            db=db,
            metric_name=metric_name,
            device=device,
            severity=severity,
            hours=hours,
        )
        
        return [
            AnomalyResponse(
                id=anomaly.id,
                metric_name=anomaly.metric_name,
                anomaly_type=anomaly.anomaly_type.value,
                timestamp=anomaly.timestamp,
                value=anomaly.value,
                expected_value=anomaly.expected_value,
                deviation=anomaly.deviation,
                severity=anomaly.severity.value,
                device=anomaly.device,
                metadata=anomaly.metadata,
            )
            for anomaly in anomalies
        ]
        
    except Exception as e:
        logger.error(f"Error listing anomalies: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving anomalies",
        )


@router.get("/{anomaly_id}", response_model=AnomalyResponse)
@limiter.limit("10/second")
async def get_anomaly(
    request: Request,
    anomaly_id: int,
    db: DbSession,
    user: CurrentUser,
) -> AnomalyResponse:
    """
    Get a specific anomaly by ID.
    """
    from sqlalchemy import select
    
    try:
        result = await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
        anomaly = result.scalar_one_or_none()
        
        if anomaly is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Anomaly with ID {anomaly_id} not found",
            )
        
        return AnomalyResponse(
            id=anomaly.id,
            metric_name=anomaly.metric_name,
            anomaly_type=anomaly.anomaly_type.value,
            timestamp=anomaly.timestamp,
            value=anomaly.value,
            expected_value=anomaly.expected_value,
            deviation=anomaly.deviation,
            severity=anomaly.severity.value,
            device=anomaly.device,
            metadata=anomaly.metadata,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving anomaly: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving anomaly",
        )

