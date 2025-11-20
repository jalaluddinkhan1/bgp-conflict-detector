"""
BGP Flap Prediction using XGBoost Classifier.

This module provides ML-based prediction of BGP session flapping
using features like CPU usage, memory, interface errors, and BGP metrics.
"""
import json
import os
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import onnx
import onnxruntime as ort
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import xgboost as xgb

from app.middleware.logging import logger


class BGPFlapPredictor:
    """
    BGP Flap Predictor using XGBoost Classifier.
    
    Features:
    - cpu_usage: CPU utilization percentage (0-100)
    - memory_usage: Memory utilization percentage (0-100)
    - interface_errors: Number of interface errors
    - hold_time: BGP hold time in seconds
    - peer_uptime_seconds: Peer uptime in seconds
    - as_path_length: AS path length
    - prefix_count: Number of prefixes received
    """

    MODEL_VERSION = "1.0.0"
    MODEL_DIR = Path("./models")
    MODEL_FILENAME = "bgp_flap_predictor_v{version}.pkl"
    ONNX_FILENAME = "bgp_flap_predictor_v{version}.onnx"
    SCALER_FILENAME = "bgp_flap_scaler_v{version}.pkl"

    def __init__(self, model_dir: Optional[str] = None):
        """
        Initialize BGP Flap Predictor.
        
        Args:
            model_dir: Directory to load/save models (default: ./models)
        """
        if model_dir:
            self.MODEL_DIR = Path(model_dir)
        else:
            self.MODEL_DIR = Path("./models")
        
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        self.model: Optional[xgb.XGBClassifier] = None
        self.scaler: Optional[StandardScaler] = None
        self.onnx_session: Optional[ort.InferenceSession] = None
        self.feature_names = [
            "cpu_usage",
            "memory_usage",
            "interface_errors",
            "hold_time",
            "peer_uptime_seconds",
            "as_path_length",
            "prefix_count",
        ]
        self.load_model()

    def generate_synthetic_data(self, n_samples: int = 10000, random_state: int = 42) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data for BGP flap prediction.
        
        Args:
            n_samples: Number of samples to generate
            random_state: Random seed for reproducibility
            
        Returns:
            Tuple of (features, labels) where labels are 0 (no flap) or 1 (flap)
        """
        np.random.seed(random_state)
        
        # Generate features with realistic distributions
        cpu_usage = np.random.beta(2, 5, n_samples) * 100  # Skewed towards lower CPU
        memory_usage = np.random.beta(2, 5, n_samples) * 100  # Skewed towards lower memory
        interface_errors = np.random.poisson(lam=2, size=n_samples)  # Poisson for errors
        hold_time = np.random.choice([90, 180, 240, 360], size=n_samples)  # Common hold times
        peer_uptime_seconds = np.random.exponential(scale=86400, size=n_samples)  # Exponential uptime
        as_path_length = np.random.poisson(lam=4, size=n_samples) + 1  # AS path length (min 1)
        prefix_count = np.random.lognormal(mean=8, sigma=2, size=n_samples).astype(int)  # Log-normal for prefixes
        
        # Combine features
        X = np.column_stack([
            cpu_usage,
            memory_usage,
            interface_errors,
            hold_time,
            peer_uptime_seconds,
            as_path_length,
            prefix_count,
        ])
        
        # Generate labels based on realistic patterns
        # Higher probability of flap with:
        # - High CPU (>80%) or memory (>90%)
        # - Many interface errors (>10)
        # - Short uptime (<3600 seconds)
        # - Long AS path (>6)
        flap_probability = (
            (cpu_usage > 80) * 0.3 +
            (memory_usage > 90) * 0.3 +
            (interface_errors > 10) * 0.4 +
            (peer_uptime_seconds < 3600) * 0.2 +
            (as_path_length > 6) * 0.1
        )
        # Add some noise
        flap_probability = np.clip(flap_probability + np.random.normal(0, 0.1, n_samples), 0, 1)
        y = (flap_probability > 0.3).astype(int)
        
        # Ensure some positive samples
        if y.sum() < n_samples * 0.1:
            y[:int(n_samples * 0.1)] = 1
        
        return X, y

    def train(self, X: Optional[np.ndarray] = None, y: Optional[np.ndarray] = None, 
              use_synthetic: bool = True, test_size: float = 0.2) -> Dict[str, float]:
        """
        Train the XGBoost classifier.
        
        Args:
            X: Training features (if None, generates synthetic data)
            y: Training labels (if None, generates synthetic data)
            use_synthetic: Whether to use synthetic data if X/y are None
            test_size: Proportion of data to use for testing
            
        Returns:
            Dictionary with training metrics (accuracy, precision, recall, f1)
        """
        if X is None or y is None:
            if use_synthetic:
                logger.info("Generating synthetic training data")
                X, y = self.generate_synthetic_data()
            else:
                raise ValueError("X and y must be provided if use_synthetic=False")
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=42, stratify=y
        )
        
        # Scale features
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Train XGBoost model
        logger.info("Training XGBoost classifier")
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss',
        )
        
        self.model.fit(
            X_train_scaled,
            y_train,
            eval_set=[(X_test_scaled, y_test)],
            verbose=False,
        )
        
        # Evaluate
        train_score = self.model.score(X_train_scaled, y_train)
        test_score = self.model.score(X_test_scaled, y_test)
        
        # Calculate additional metrics
        from sklearn.metrics import precision_score, recall_score, f1_score
        
        y_pred = self.model.predict(X_test_scaled)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        
        metrics = {
            "train_accuracy": float(train_score),
            "test_accuracy": float(test_score),
            "precision": float(precision),
            "recall": float(recall),
            "f1_score": float(f1),
        }
        
        logger.info(f"Training completed. Metrics: {metrics}")
        
        # Save model
        self.save_model()
        
        return metrics

    def predict(self, features: Dict[str, float], use_onnx: bool = False) -> Dict[str, float]:
        """
        Predict probability of BGP flap.
        
        Args:
            features: Dictionary with feature values
            use_onnx: Whether to use ONNX runtime for inference (faster)
            
        Returns:
            Dictionary with prediction results:
            - flap_probability: Probability of flap (0-1)
            - will_flap: Boolean prediction
            - confidence: Confidence in prediction
        """
        if self.model is None:
            raise ValueError("Model not loaded. Train or load a model first.")
        
        # Extract features in correct order
        feature_vector = np.array([[
            features.get("cpu_usage", 0.0),
            features.get("memory_usage", 0.0),
            features.get("interface_errors", 0.0),
            features.get("hold_time", 180.0),
            features.get("peer_uptime_seconds", 0.0),
            features.get("as_path_length", 1.0),
            features.get("prefix_count", 0.0),
        ]])
        
        # Scale features
        if self.scaler is None:
            raise ValueError("Scaler not loaded. Train or load a model first.")
        
        feature_vector_scaled = self.scaler.transform(feature_vector)
        
        # Predict
        if use_onnx and self.onnx_session is not None:
            # Use ONNX runtime
            input_name = self.onnx_session.get_inputs()[0].name
            output = self.onnx_session.run(None, {input_name: feature_vector_scaled.astype(np.float32)})
            flap_probability = float(output[0][0][1])  # Probability of class 1 (flap)
        else:
            # Use XGBoost directly
            flap_probability = float(self.model.predict_proba(feature_vector_scaled)[0][1])
        
        will_flap = flap_probability > 0.5
        confidence = abs(flap_probability - 0.5) * 2  # Confidence as distance from 0.5
        
        return {
            "flap_probability": flap_probability,
            "will_flap": will_flap,
            "confidence": confidence,
        }

    def save_model(self) -> None:
        """Save model, scaler, and metadata to disk."""
        if self.model is None or self.scaler is None:
            raise ValueError("Model and scaler must be trained before saving")
        
        version = self.MODEL_VERSION
        
        # Save XGBoost model
        model_path = self.MODEL_DIR / self.MODEL_FILENAME.format(version=version)
        with open(model_path, "wb") as f:
            pickle.dump(self.model, f)
        logger.info(f"Saved XGBoost model to {model_path}")
        
        # Save scaler
        scaler_path = self.MODEL_DIR / self.SCALER_FILENAME.format(version=version)
        with open(scaler_path, "wb") as f:
            pickle.dump(self.scaler, f)
        logger.info(f"Saved scaler to {scaler_path}")
        
        # Save metadata
        metadata = {
            "version": version,
            "feature_names": self.feature_names,
            "model_type": "XGBoost",
        }
        metadata_path = self.MODEL_DIR / f"bgp_flap_metadata_v{version}.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        logger.info(f"Saved metadata to {metadata_path}")
        
        # Export to ONNX
        self.export_to_onnx()

    def export_to_onnx(self) -> None:
        """Export XGBoost model to ONNX format for fast inference."""
        if self.model is None or self.scaler is None:
            raise ValueError("Model and scaler must be trained before exporting")
        
        try:
            from skl2onnx import convert_sklearn
            from skl2onnx.common.data_types import FloatTensorType
            
            # Create initial type for ONNX
            initial_type = [("float_input", FloatTensorType([None, len(self.feature_names)]))]
            
            # Convert to ONNX
            onnx_model = convert_sklearn(
                self.model,
                initial_types=initial_type,
                target_opset=13,
            )
            
            # Save ONNX model
            version = self.MODEL_VERSION
            onnx_path = self.MODEL_DIR / self.ONNX_FILENAME.format(version=version)
            with open(onnx_path, "wb") as f:
                f.write(onnx_model.SerializeToString())
            logger.info(f"Exported ONNX model to {onnx_path}")
            
            # Load ONNX session for inference
            self.onnx_session = ort.InferenceSession(str(onnx_path))
            logger.info("ONNX session loaded for inference")
            
        except ImportError:
            logger.warning("skl2onnx not installed. Skipping ONNX export.")
        except Exception as e:
            logger.error(f"Failed to export to ONNX: {e}")

    def load_model(self, version: Optional[str] = None) -> bool:
        """
        Load model, scaler, and ONNX session from disk.
        
        Args:
            version: Model version to load (default: latest/MODEL_VERSION)
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        if version is None:
            version = self.MODEL_VERSION
        
        model_path = self.MODEL_DIR / self.MODEL_FILENAME.format(version=version)
        scaler_path = self.MODEL_DIR / self.SCALER_FILENAME.format(version=version)
        
        if not model_path.exists() or not scaler_path.exists():
            logger.warning(f"Model files not found for version {version}. Train a model first.")
            return False
        
        try:
            # Load XGBoost model
            with open(model_path, "rb") as f:
                self.model = pickle.load(f)
            logger.info(f"Loaded XGBoost model from {model_path}")
            
            # Load scaler
            with open(scaler_path, "rb") as f:
                self.scaler = pickle.load(f)
            logger.info(f"Loaded scaler from {scaler_path}")
            
            # Try to load ONNX model
            onnx_path = self.MODEL_DIR / self.ONNX_FILENAME.format(version=version)
            if onnx_path.exists():
                try:
                    self.onnx_session = ort.InferenceSession(str(onnx_path))
                    logger.info(f"Loaded ONNX session from {onnx_path}")
                except Exception as e:
                    logger.warning(f"Failed to load ONNX session: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

    def get_model_info(self) -> Dict:
        """Get information about the loaded model."""
        if self.model is None:
            return {"status": "no_model_loaded"}
        
        return {
            "status": "loaded",
            "version": self.MODEL_VERSION,
            "feature_names": self.feature_names,
            "model_type": "XGBoost",
            "onnx_available": self.onnx_session is not None,
        }

