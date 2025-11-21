"""
BGPStream implementation for real-time BGP updates.
"""
import asyncio
from typing import Any, AsyncGenerator, Optional

try:
    import pybgpstream
except ImportError:
    pybgpstream = None

from .sources import BGPDataSource


class BGPStreamSource(BGPDataSource):
    """
    BGPStream data source for real-time BGP updates.
    
    Uses pybgpstream to fetch BGP updates from RIPE RIS,
    RouteViews, and other collectors.
    """

    def __init__(self, collectors: Optional[list[str]] = None):
        """
        Initialize BGPStream source.
        
        Args:
            collectors: List of collector names (e.g., ["rrc00", "route-views2"])
        """
        if pybgpstream is None:
            raise ImportError("pybgpstream is not installed. Install with: pip install pybgpstream")

        self.collectors = collectors or ["rrc00"]
        self.stream = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to BGPStream."""
        if self._connected:
            return

        try:
            # Create BGPStream instance
            self.stream = pybgpstream.BGPStream(
                record_type="updates",
                collectors=self.collectors,
            )
            self._connected = True
        except Exception as e:
            raise ConnectionError(f"Failed to connect to BGPStream: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from BGPStream."""
        self.stream = None
        self._connected = False

    async def fetch_updates(
        self, filters: Optional[dict[str, Any]] = None
    ) -> AsyncGenerator[dict[str, Any], None]:
        """
        Fetch BGP updates from BGPStream.
        
        Args:
            filters: Optional filters (e.g., {"prefix": "192.0.2.0/24"})
            
        Yields:
            BGP update dictionaries
        """
        if not self._connected:
            await self.connect()

        if filters:
            # Apply filters
            if "prefix" in filters:
                self.stream.add_filter("prefix", filters["prefix"])
            if "peer_asn" in filters:
                self.stream.add_filter("peer", f"peer AS {filters['peer_asn']}")
            if "project" in filters:
                self.stream.add_filter("project", filters["project"])

        # Process stream in background thread
        loop = asyncio.get_event_loop()
        
        def process_stream():
            for elem in self.stream:
                if elem.type == "R" and elem.time:  # Record with timestamp
                    for rec in elem:
                        if rec.type == "A":  # Announcement
                            yield {
                                "type": "announce",
                                "timestamp": elem.time,
                                "peer_ip": elem.peer_address,
                                "peer_asn": elem.peer_asn,
                                "prefix": rec.fields.get("prefix", ""),
                                "as_path": rec.fields.get("as-path", "").split(),
                                "origin": rec.fields.get("origin", ""),
                                "next_hop": rec.fields.get("next-hop", ""),
                                "communities": rec.fields.get("communities", []),
                            }
                        elif rec.type == "W":  # Withdrawal
                            yield {
                                "type": "withdraw",
                                "timestamp": elem.time,
                                "peer_ip": elem.peer_address,
                                "peer_asn": elem.peer_asn,
                                "prefix": rec.fields.get("prefix", ""),
                            }

        # Run in executor to avoid blocking
        executor = loop.run_in_executor(None, process_stream)
        
        try:
            while True:
                batch = await asyncio.wait_for(executor, timeout=1.0)
                for update in batch:
                    yield update
        except asyncio.TimeoutError:
            pass

    def is_connected(self) -> bool:
        """Check if connected to BGPStream."""
        return self._connected

