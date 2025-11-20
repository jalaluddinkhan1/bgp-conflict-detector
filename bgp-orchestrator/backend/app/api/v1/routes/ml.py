"""
Machine Learning API endpoints for BGP Orchestrator.
"""
import time
from typing import Dict

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.dependencies import CurrentUser, DbSession
from app.middleware.logging import logger
from ml.bgp_flap_predictor import BGPFlapPredictor
from observability.metrics import Histogram, registry

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/ml", tags=["Machine Learning"])

# ML prediction latency metric
ml_prediction_latency = Histogram(
    "ml_prediction_latency_seconds",
    "ML prediction latency in seconds",
    ["model_type", "endpoint"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
    registry=registry,
)

# Global predictor instance
_predictor: BGPFlapPredictor | None = None


def get_predictor() -> BGPFlapPredictor:
    """Get or create BGP flap predictor instance."""
    global _predictor
    if _predictor is None:
        _predictor = BGPFlapPredictor()
        # If no model exists, train one with synthetic data
        if not _predictor.model:
            logger.info("No model found. Training with synthetic data...")
            _predictor.train(use_synthetic=True)
    return _predictor


class FlapPredictionRequest(BaseModel):
    """Request model for BGP flap prediction."""
    
    cpu_usage: float = Field(..., ge=0, le=100, description="CPU utilization percentage")
    memory_usage: float = Field(..., ge=0, le=100, description="Memory utilization percentage")
    interface_errors: int = Field(..., ge=0, description="Number of interface errors")
    hold_time: int = Field(default=180, ge=0, description="BGP hold time in seconds")
    peer_uptime_seconds: float = Field(..., ge=0, description="Peer uptime in seconds")
    as_path_length: int = Field(..., ge=1, description="AS path length")
    prefix_count: int = Field(..., ge=0, description="Number of prefixes received")
    use_onnx: bool = Field(default=False, description="Use ONNX runtime for faster inference")


class FlapPredictionResponse(BaseModel):
    """Response model for BGP flap prediction."""
    
    flap_probability: float = Field(..., description="Probability of BGP flap (0-1)")
    will_flap: bool = Field(..., description="Prediction: will flap or not")
    confidence: float = Field(..., description="Confidence in prediction (0-1)")
    model_version: str = Field(..., description="Model version used")
    inference_time_ms: float = Field(..., description="Inference time in milliseconds")


@router.post("/predict", response_model=FlapPredictionResponse)
@limiter.limit("10/second")
async def predict_flap(
    request: Request,
    prediction_request: FlapPredictionRequest,
    user: CurrentUser,
) -> FlapPredictionResponse:
    """
    Predict probability of BGP session flapping.
    
    Uses XGBoost classifier trained on BGP telemetry data to predict
    the likelihood of a BGP session experiencing flapping.
    
    Features:
    - CPU and memory usage
    - Interface error counts
    - BGP session metrics (hold time, uptime)
    - Routing metrics (AS path length, prefix count)
    """
    start_time = time.time()
    
    try:
        predictor = get_predictor()
        
        # Prepare features
        features = {
            "cpu_usage": prediction_request.cpu_usage,
            "memory_usage": prediction_request.memory_usage,
            "interface_errors": prediction_request.interface_errors,
            "hold_time": prediction_request.hold_time,
            "peer_uptime_seconds": prediction_request.peer_uptime_seconds,
            "as_path_length": prediction_request.as_path_length,
            "prefix_count": prediction_request.prefix_count,
        }
        
        # Make prediction
        result = predictor.predict(features, use_onnx=prediction_request.use_onnx)
        
        # Calculate inference time
        inference_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        # Record metric
        ml_prediction_latency.labels(
            model_type="xgboost",
            endpoint="predict_flap"
        ).observe(time.time() - start_time)
        
        logger.info(
            f"BGP flap prediction completed",
            user=user.email,
            flap_probability=result["flap_probability"],
            inference_time_ms=inference_time,
        )
        
        return FlapPredictionResponse(
            flap_probability=result["flap_probability"],
            will_flap=result["will_flap"],
            confidence=result["confidence"],
            model_version=predictor.MODEL_VERSION,
            inference_time_ms=inference_time,
        )
        
    except ValueError as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Unexpected error during prediction: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during prediction",
        )


@router.get("/model/info")
@limiter.limit("10/second")
async def get_model_info(
    request: Request,
    user: CurrentUser,
) -> Dict:
    """
    Get information about the loaded ML model.
    
    Returns model version, feature names, and status.
    """
    try:
        predictor = get_predictor()
        return predictor.get_model_info()
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving model information",
        )


@router.post("/model/train")
@limiter.limit("1/minute")  # Limit training to once per minute
async def train_model(
    request: Request,
    user: CurrentUser,
    n_samples: int = Query(10000, ge=1000, le=100000),
) -> Dict:
    """
    Train or retrain the BGP flap prediction model.
    
    Uses synthetic data generation for training.
    Requires appropriate permissions.
    """
    try:
        predictor = get_predictor()
        logger.info(f"Training model with {n_samples} samples", user=user.email)
        
        # Generate synthetic data and train
        X, y = predictor.generate_synthetic_data(n_samples=n_samples)
        metrics = predictor.train(X=X, y=y, use_synthetic=False)
        
        logger.info(f"Model training completed", user=user.email, metrics=metrics)
        
        return {
            "status": "success",
            "metrics": metrics,
            "model_version": predictor.MODEL_VERSION,
        }
        
    except Exception as e:
        logger.error(f"Error training model: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error training model: {str(e)}",
        )

