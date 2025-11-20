"""
Anomaly Detection for BGP and Network Metrics using Prophet.

This module provides time-series anomaly detection for:
- BGP session flaps
- CPU temperature
- Interface errors

Uses Prophet for seasonality detection and 3-sigma rule for anomaly detection.
"""
import json
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from prophet import Prophet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.logging import logger
from models.anomaly import Anomaly, AnomalyType, AnomalySeverity


class AnomalyDetector:
    """
    Anomaly detector using Prophet for seasonality detection and 3-sigma rule.
    
    Detects anomalies in:
    - bgp_session_flaps: Number of BGP session flaps per time period
    - cpu_temp: CPU temperature readings
    - interface_errors: Interface error counts
    """

    def __init__(self, sigma_threshold: float = 3.0):
        """
        Initialize anomaly detector.
        
        Args:
            sigma_threshold: Number of standard deviations for anomaly detection (default: 3.0)
        """
        self.sigma_threshold = sigma_threshold
        self.models: Dict[str, Prophet] = {}

    def detect_anomalies(
        self,
        metric_name: str,
        timestamps: List[datetime],
        values: List[float],
        seasonality_mode: str = "multiplicative",
    ) -> List[Dict]:
        """
        Detect anomalies in time-series data using Prophet and 3-sigma rule.
        
        Args:
            metric_name: Name of the metric (e.g., "bgp_session_flaps")
            timestamps: List of timestamps
            values: List of metric values
            seasonality_mode: Prophet seasonality mode ("additive" or "multiplicative")
            
        Returns:
            List of detected anomalies with metadata
        """
        if len(timestamps) < 10:
            logger.warning(f"Insufficient data for anomaly detection: {len(timestamps)} points")
            return []
        
        # Prepare DataFrame for Prophet
        df = pd.DataFrame({
            "ds": pd.to_datetime(timestamps),
            "y": values,
        })
        df = df.sort_values("ds").reset_index(drop=True)
        
        # Fit Prophet model
        try:
            model = Prophet(
                seasonality_mode=seasonality_mode,
                daily_seasonality=True,
                weekly_seasonality=True,
                yearly_seasonality=False,
                changepoint_prior_scale=0.05,
            )
            model.fit(df)
            
            # Make predictions
            future = model.make_future_dataframe(periods=0)
            forecast = model.predict(future)
            
            # Calculate residuals
            df["yhat"] = forecast["yhat"].values
            df["yhat_lower"] = forecast["yhat_lower"].values
            df["yhat_upper"] = forecast["yhat_upper"].values
            df["residual"] = df["y"] - df["yhat"]
            
            # Calculate rolling statistics for 3-sigma rule
            window_size = min(30, len(df) // 2)  # Adaptive window size
            df["residual_mean"] = df["residual"].rolling(window=window_size, center=True).mean()
            df["residual_std"] = df["residual"].rolling(window=window_size, center=True).std()
            
            # Fill NaN values with overall statistics
            overall_mean = df["residual"].mean()
            overall_std = df["residual"].std()
            df["residual_mean"] = df["residual_mean"].fillna(overall_mean)
            df["residual_std"] = df["residual_std"].fillna(overall_std)
            
            # Detect anomalies using 3-sigma rule
            df["is_anomaly"] = (
                (df["residual"] > df["residual_mean"] + self.sigma_threshold * df["residual_std"]) |
                (df["residual"] < df["residual_mean"] - self.sigma_threshold * df["residual_std"])
            )
            
            # Extract anomalies
            anomalies = []
            for idx, row in df[df["is_anomaly"]].iterrows():
                deviation = abs(row["residual"])
                severity = self._calculate_severity(deviation, row["residual_std"])
                
                anomalies.append({
                    "metric_name": metric_name,
                    "timestamp": row["ds"].to_pydatetime(),
                    "value": float(row["y"]),
                    "expected_value": float(row["yhat"]),
                    "deviation": float(deviation),
                    "severity": severity,
                    "metadata": {
                        "residual_std": float(row["residual_std"]),
                        "sigma_threshold": self.sigma_threshold,
                        "lower_bound": float(row["yhat_lower"]),
                        "upper_bound": float(row["yhat_upper"]),
                    },
                })
            
            logger.info(
                f"Detected {len(anomalies)} anomalies in {metric_name}",
                metric=metric_name,
                total_points=len(df),
                anomalies=len(anomalies),
            )
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies for {metric_name}: {e}", exc_info=True)
            return []

    def _calculate_severity(self, deviation: float, std: float) -> str:
        """
        Calculate anomaly severity based on deviation.
        
        Args:
            deviation: Absolute deviation from expected value
            std: Standard deviation of residuals
            
        Returns:
            Severity level: "low", "medium", "high", "critical"
        """
        if std == 0:
            return "medium"
        
        sigma_ratio = deviation / std if std > 0 else 0
        
        if sigma_ratio >= 5.0:
            return "critical"
        elif sigma_ratio >= 4.0:
            return "high"
        elif sigma_ratio >= 3.0:
            return "medium"
        else:
            return "low"

    async def detect_and_store_anomalies(
        self,
        db: AsyncSession,
        metric_name: str,
        timestamps: List[datetime],
        values: List[float],
        device: Optional[str] = None,
    ) -> List[Anomaly]:
        """
        Detect anomalies and store them in the database.
        
        Args:
            db: Database session
            metric_name: Name of the metric
            timestamps: List of timestamps
            values: List of metric values
            device: Optional device name for context
            
        Returns:
            List of created Anomaly objects
        """
        # Detect anomalies
        anomaly_data = self.detect_anomalies(metric_name, timestamps, values)
        
        if not anomaly_data:
            return []
        
        # Map metric name to anomaly type
        anomaly_type_map = {
            "bgp_session_flaps": AnomalyType.BGP_FLAP,
            "cpu_temp": AnomalyType.CPU_TEMPERATURE,
            "interface_errors": AnomalyType.INTERFACE_ERROR,
        }
        
        anomaly_type = anomaly_type_map.get(metric_name, AnomalyType.OTHER)
        
        # Map severity string to enum
        severity_map = {
            "low": AnomalySeverity.LOW,
            "medium": AnomalySeverity.MEDIUM,
            "high": AnomalySeverity.HIGH,
            "critical": AnomalySeverity.CRITICAL,
        }
        
        # Create anomaly records
        anomalies = []
        for data in anomaly_data:
            anomaly = Anomaly(
                metric_name=metric_name,
                anomaly_type=anomaly_type,
                timestamp=data["timestamp"],
                value=data["value"],
                expected_value=data["expected_value"],
                deviation=data["deviation"],
                severity=severity_map.get(data["severity"], AnomalySeverity.MEDIUM),
                device=device,
                metadata=data["metadata"],
            )
            db.add(anomaly)
            anomalies.append(anomaly)
        
        await db.commit()
        
        # Refresh to get IDs
        for anomaly in anomalies:
            await db.refresh(anomaly)
        
        logger.info(
            f"Stored {len(anomalies)} anomalies in database",
            metric=metric_name,
            count=len(anomalies),
        )
        
        return anomalies

    async def get_recent_anomalies(
        self,
        db: AsyncSession,
        metric_name: Optional[str] = None,
        device: Optional[str] = None,
        severity: Optional[AnomalySeverity] = None,
        hours: int = 24,
    ) -> List[Anomaly]:
        """
        Retrieve recent anomalies from database.
        
        Args:
            db: Database session
            metric_name: Filter by metric name
            device: Filter by device
            severity: Filter by severity
            hours: Number of hours to look back
            
        Returns:
            List of Anomaly objects
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = select(Anomaly).where(Anomaly.timestamp >= cutoff_time)
        
        if metric_name:
            query = query.where(Anomaly.metric_name == metric_name)
        if device:
            query = query.where(Anomaly.device == device)
        if severity:
            query = query.where(Anomaly.severity == severity)
        
        query = query.order_by(Anomaly.timestamp.desc())
        
        result = await db.execute(query)
        return list(result.scalars().all())

    def generate_synthetic_metrics(
        self,
        metric_name: str,
        n_points: int = 1000,
        start_time: Optional[datetime] = None,
        include_anomalies: bool = True,
    ) -> Tuple[List[datetime], List[float]]:
        """
        Generate synthetic time-series data for testing.
        
        Args:
            metric_name: Name of the metric
            n_points: Number of data points
            start_time: Start timestamp (default: now - n_points hours)
            include_anomalies: Whether to include synthetic anomalies
            
        Returns:
            Tuple of (timestamps, values)
        """
        if start_time is None:
            start_time = datetime.now(timezone.utc) - timedelta(hours=n_points)
        
        timestamps = [start_time + timedelta(hours=i) for i in range(n_points)]
        
        # Generate base signal with seasonality
        t = np.arange(n_points)
        base = 50 + 20 * np.sin(2 * np.pi * t / 24)  # Daily seasonality
        base += 10 * np.sin(2 * np.pi * t / (24 * 7))  # Weekly seasonality
        base += np.random.normal(0, 5, n_points)  # Noise
        
        # Add metric-specific characteristics
        if metric_name == "bgp_session_flaps":
            values = np.maximum(0, base / 10).astype(int).tolist()  # Non-negative integers
        elif metric_name == "cpu_temp":
            values = (base + 30).tolist()  # Temperature in Celsius
        elif metric_name == "interface_errors":
            values = np.maximum(0, base / 5).astype(int).tolist()  # Non-negative integers
        else:
            values = base.tolist()
        
        # Inject anomalies if requested
        if include_anomalies:
            n_anomalies = max(1, n_points // 100)  # ~1% anomalies
            anomaly_indices = np.random.choice(n_points, size=n_anomalies, replace=False)
            for idx in anomaly_indices:
                # Make values significantly higher or lower
                if np.random.random() > 0.5:
                    values[idx] *= 3  # Spike
                else:
                    values[idx] *= 0.1  # Drop
        
        return timestamps, values

