"""
RIPE RIS client with BGPStream integration for live and historical BGP data.
"""
import asyncio
import ipaddress
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, AsyncGenerator, Generator

import httpx
from pybgpstream import BGPStream
from redis import Redis

from app.config import settings
from app.dependencies import get_redis


class BGPEventType(str, Enum):
    """BGP event types."""

    ANNOUNCEMENT = "announcement"
    WITHDRAWAL = "withdrawal"
    RIB = "rib"


@dataclass
class BGPEvent:
    """BGP event from RIPE RIS."""

    timestamp: datetime
    peer_ip: str
    peer_asn: int
    prefix: str
    as_path: list[int]
    origin_as: int | None = None
    next_hop: str | None = None
    event_type: BGPEventType = BGPEventType.ANNOUNCEMENT
    communities: list[str] | None = None


class CircuitBreaker:
    """Circuit breaker pattern for handling failures."""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: callable, *args: Any, **kwargs: Any) -> Any:
        """Call function with circuit breaker protection."""
        if self.state == "open":
            if self.last_failure_time and (
                datetime.now(timezone.utc) - self.last_failure_time
            ).total_seconds() > self.timeout:
                self.state = "half_open"
            else:
                raise Exception("Circuit breaker is OPEN - service unavailable")

        try:
            result = func(*args, **kwargs)
            if self.state == "half_open":
                self.state = "closed"
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now(timezone.utc)

            if self.failure_count >= self.failure_threshold:
                self.state = "open"

            raise e


class RIPEClient:
    """RIPE RIS client with connection pooling and caching."""

    def __init__(self, redis_client: Redis | None = None, max_connections: int = 5):
        """Initialize RIPE RIS client."""
        self.redis_client = redis_client or get_redis()
        self.max_connections = max_connections
        self.cache_ttl = 300  # 5 minutes
        self.circuit_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        self._connection_pool: list[httpx.AsyncClient] = []
        self._semaphore = asyncio.Semaphore(max_connections)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client from pool."""
        if not self._connection_pool:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_connections=self.max_connections),
            )
            self._connection_pool.append(client)
            return client

        return self._connection_pool[0]

    async def _cache_key(self, key: str) -> str:
        """Generate cache key."""
        return f"ripe_ris:{key}"

    async def _get_from_cache(self, key: str) -> Any | None:
        """Get value from Redis cache."""
        try:
            cached = self.redis_client.get(await self._cache_key(key))
            if cached:
                import json

                return json.loads(cached)
        except Exception:
            pass
        return None

    async def _set_cache(self, key: str, value: Any) -> None:
        """Set value in Redis cache."""
        try:
            import json

            self.redis_client.setex(
                await self._cache_key(key),
                self.cache_ttl,
                json.dumps(value, default=str),
            )
        except Exception:
            pass

    async def get_live_updates(
        self,
        collectors: list[str] | None = None,
        record_types: list[str] | None = None,
    ) -> AsyncGenerator[BGPEvent, None]:
        """
        Get live BGP updates from RIPE RIS.

        Args:
            collectors: List of RIS collectors (e.g., ['rrc00', 'rrc01'])
            record_types: List of record types (e.g., ['updates', 'ribs'])

        Yields:
            BGPEvent objects
        """
        if not settings.RIPE_RIS_ENABLED:
            return

        collectors = collectors or ["rrc00", "rrc01", "rrc02"]
        record_types = record_types or ["updates"]

        def _get_stream_events() -> Generator[BGPEvent, None, None]:
            """Get events from BGPStream (synchronous)."""
            stream = BGPStream(
                from_time=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                collectors=collectors,
                record_type="updates",
            )

            for elem in stream:
                if elem.type == "update":
                    # Extract prefix
                    prefix = elem.fields.get("prefix", "")

                    # Extract AS path
                    as_path_str = elem.fields.get("as-path", "")
                    as_path = [
                        int(asn.strip()) for asn in as_path_str.split() if asn.strip().isdigit()
                    ] if as_path_str else []

                    # Extract origin AS (last AS in path)
                    origin_as = as_path[-1] if as_path else None

                    # Determine event type
                    event_type = (
                        BGPEventType.ANNOUNCEMENT if prefix else BGPEventType.WITHDRAWAL
                    )

                    yield BGPEvent(
                        timestamp=datetime.fromtimestamp(elem.time, tz=timezone.utc),
                        peer_ip=elem.peer_address,
                        peer_asn=elem.peer_asn,
                        prefix=prefix,
                        as_path=as_path,
                        origin_as=origin_as,
                        next_hop=elem.fields.get("next-hop"),
                        event_type=event_type,
                        communities=elem.fields.get("communities", "").split() if elem.fields.get("communities") else None,
                    )

        # Run synchronous BGPStream in thread pool
        loop = asyncio.get_event_loop()
        while True:
            try:
                events = await loop.run_in_executor(None, lambda: list(_get_stream_events()))
                for event in events:
                    yield event
            except Exception as e:
                # Handle errors with circuit breaker
                self.circuit_breaker.call(lambda: None)  # Track failure
                await asyncio.sleep(5)  # Wait before retry

    async def get_historical_data(
        self,
        start_time: datetime,
        end_time: datetime,
        collectors: list[str] | None = None,
    ) -> list[BGPEvent]:
        """
        Get historical BGP data from RIPE RIS.

        Args:
            start_time: Start timestamp
            end_time: End timestamp
            collectors: List of RIS collectors

        Returns:
            List of BGPEvent objects
        """
        if not settings.RIPE_RIS_ENABLED:
            return []

        collectors = collectors or ["rrc00"]

        # Check cache
        cache_key = f"historical:{start_time.isoformat()}:{end_time.isoformat()}:{':'.join(collectors)}"
        cached = await self._get_from_cache(cache_key)
        if cached:
            return [
                BGPEvent(**event) if isinstance(event, dict) else event
                for event in cached
            ]

        events: list[BGPEvent] = []

        def _get_historical_events() -> list[BGPEvent]:
            """Get historical events from BGPStream (synchronous)."""
            stream = BGPStream(
                from_time=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                until_time=end_time.strftime("%Y-%m-%d %H:%M:%S"),
                collectors=collectors,
                record_type="updates",
            )

            result = []
            for elem in stream:
                if elem.type == "update":
                    prefix = elem.fields.get("prefix", "")
                    as_path_str = elem.fields.get("as-path", "")
                    as_path = [
                        int(asn.strip())
                        for asn in as_path_str.split()
                        if asn.strip().isdigit()
                    ] if as_path_str else []

                    result.append(
                        BGPEvent(
                            timestamp=datetime.fromtimestamp(elem.time, tz=timezone.utc),
                            peer_ip=elem.peer_address,
                            peer_asn=elem.peer_asn,
                            prefix=prefix,
                            as_path=as_path,
                            origin_as=as_path[-1] if as_path else None,
                            next_hop=elem.fields.get("next-hop"),
                            event_type=BGPEventType.ANNOUNCEMENT if prefix else BGPEventType.WITHDRAWAL,
                        )
                    )

            return result

        try:
            loop = asyncio.get_event_loop()
            events = await loop.run_in_executor(None, _get_historical_events)
            await self._set_cache(cache_key, [event.__dict__ for event in events])
        except Exception as e:
            self.circuit_breaker.call(lambda: None)  # Track failure
            raise Exception(f"Failed to get historical data: {str(e)}") from e

        return events

    async def validate_prefix_origin(self, prefix: str, origin_as: int) -> bool:
        """
        Validate if a prefix is correctly announced by an origin AS.

        Args:
            prefix: IP prefix (e.g., '8.8.8.0/24')
            origin_as: Expected origin ASN

        Returns:
            True if prefix is correctly originated by the AS
        """
        # Check cache
        cache_key = f"validate:{prefix}:{origin_as}"
        cached = await self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        try:
            # Get recent historical data (last 24 hours)
            end_time = datetime.now(timezone.utc)
            start_time = end_time - timedelta(hours=24)

            events = await self.get_historical_data(start_time, end_time)

            # Check if any event shows this prefix with the correct origin
            for event in events:
                if event.prefix == prefix and event.origin_as == origin_as:
                    await self._set_cache(cache_key, True)
                    return True

            # No matching announcement found
            await self._set_cache(cache_key, False)
            return False

        except Exception as e:
            # On error, check cache with fallback
            cached = await self._get_from_cache(cache_key)
            if cached is not None:
                return cached
            raise Exception(f"Failed to validate prefix origin: {str(e)}") from e

