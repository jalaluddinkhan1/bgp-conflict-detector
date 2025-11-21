"""
BGP data source abstraction layer.
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Optional


class BGPDataSource(ABC):
    """
    Abstract base class for BGP data sources.
    
    Implementations should provide methods to fetch
    BGP updates from various sources (BGPStream, BMP, etc.)
    """

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the data source."""

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the data source."""

    @abstractmethod
    async def fetch_updates(
        self, filters: Optional[dict[str, Any]] = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Fetch BGP updates from the source.
        
        Args:
            filters: Optional filters for updates (e.g., ASN, prefix)
            
        Yields:
            BGP update dictionaries
        """

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to the data source."""

