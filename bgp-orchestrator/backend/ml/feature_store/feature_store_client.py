"""
Feast Feature Store Client

Provides interface for reading and writing features to/from Feast feature store.
"""
import os
from pathlib import Path
from typing import Dict, List, Optional

from app.config import settings
from app.middleware.logging import logger


class FeatureStoreClient:
    """
    Client for interacting with Feast feature store.
    
    Provides methods for:
    - Reading features (online serving)
    - Writing features (materialization)
    - Managing feature definitions
    """
    
    def __init__(self, repo_path: Optional[str] = None):
        """
        Initialize Feast feature store client.
        
        Args:
            repo_path: Path to Feast feature store repository
        """
        self.repo_path = repo_path or getattr(settings, "FEATURE_STORE_REPO_PATH", None)
        self.store = None
        self._initialized = False
        
        if self.repo_path:
            self._initialize()
    
    def _initialize(self) -> None:
        """Initialize Feast feature store."""
        try:
            from feast import FeatureStore
            
            repo_path = Path(self.repo_path)
            if not repo_path.exists():
                logger.warning(f"Feature store repo path does not exist: {repo_path}")
                return
            
            self.store = FeatureStore(repo_path=str(repo_path))
            self._initialized = True
            
            logger.info(f"Feast feature store initialized: {repo_path}")
            
        except ImportError:
            logger.warning("Feast not installed. Install with: pip install feast[redis]")
        except Exception as e:
            logger.error(f"Failed to initialize Feast feature store: {e}", exc_info=True)
    
    async def get_features(
        self,
        entity_ids: List[str],
        feature_names: List[str],
    ) -> Dict[str, Dict]:
        """
        Get features for given entity IDs (online serving).
        
        Args:
            entity_ids: List of entity IDs (e.g., ["192.168.1.1:65000"])
            feature_names: List of feature names to retrieve
            
        Returns:
            Dictionary mapping entity IDs to feature dictionaries
        """
        if not self._initialized or not self.store:
            return {}
        
        try:
            # Feast online serving
            features = self.store.get_online_features(
                features=feature_names,
                entity_rows=[{"bgp_session": eid} for eid in entity_ids],
            ).to_dict()
            
            # Transform to expected format
            result = {}
            for i, entity_id in enumerate(entity_ids):
                result[entity_id] = {
                    name: features[name][i] for name in feature_names
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting features from feature store: {e}", exc_info=True)
            return {}
    
    async def write_features(
        self,
        entity_id: str,
        features: Dict,
    ) -> bool:
        """
        Write features to feature store (for materialization).
        
        Args:
            entity_id: Entity ID
            features: Feature dictionary
            
        Returns:
            True if successful, False otherwise
        """
        # Note: In production, features are typically written via batch jobs
        # This method is for real-time feature updates
        try:
            # For now, log the features
            # In production, you'd write to a staging table or Kafka topic
            logger.debug(
                f"Writing features to feature store",
                entity_id=entity_id,
                features=list(features.keys()),
            )
            return True
            
        except Exception as e:
            logger.error(f"Error writing features to feature store: {e}", exc_info=True)
            return False
    
    def materialize_features(
        self,
        start_date: str,
        end_date: str,
    ) -> bool:
        """
        Trigger feature materialization (batch job).
        
        Args:
            start_date: Start date for materialization (ISO format)
            end_date: End date for materialization (ISO format)
            
        Returns:
            True if successful, False otherwise
        """
        if not self._initialized or not self.store:
            return False
        
        try:
            self.store.materialize_incremental(end_date=end_date)
            logger.info(f"Feature materialization triggered: {start_date} to {end_date}")
            return True
            
        except Exception as e:
            logger.error(f"Error materializing features: {e}", exc_info=True)
            return False


# Global feature store client
_feature_store_client: Optional[FeatureStoreClient] = None


def get_feature_store_client() -> Optional[FeatureStoreClient]:
    """Get or create feature store client instance."""
    global _feature_store_client
    
    if not getattr(settings, "FEATURE_STORE_ENABLED", False):
        return None
    
    if _feature_store_client is None:
        _feature_store_client = FeatureStoreClient()
    
    return _feature_store_client

