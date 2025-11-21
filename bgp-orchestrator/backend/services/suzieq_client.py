"""
SuzieQ client for live device polling and network observability.
"""
import asyncio
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import httpx

from app.config import settings
from utils.circuit_breaker import circuit_breaker


class BGPSessionState(str, Enum):
    """BGP session states."""

    ESTABLISHED = "Established"
    IDLE = "Idle"
    ACTIVE = "Active"
    CONNECT = "Connect"
    OPENSENT = "OpenSent"
    OPENCONFIRM = "OpenConfirm"


@dataclass
class BGPSession:
    """BGP session from live device."""

    device: str
    peer: str
    peer_asn: int
    state: BGPSessionState
    uptime: str | None = None
    prefix_count: int | None = None
    hold_time: int | None = None
    keepalive: int | None = None
    last_update: datetime | None = None


@dataclass
class Device:
    """Network device information."""

    name: str
    hostname: str
    vendor: str
    model: str | None = None
    os_version: str | None = None
    status: str = "up"
    last_polled: datetime | None = None


class SuzieQClient:
    """SuzieQ client for network device polling."""

    def __init__(self, endpoint: str | None = None, max_connections: int = 10):
        """Initialize SuzieQ client."""
        self.endpoint = endpoint or settings.SUZIEQ_ENDPOINT or "http://localhost:8000"
        self.max_connections = max_connections
        self.timeout = 30.0
        self.max_retries = 3
        self.retry_delay = 1.0
        self._connection_pool: list[httpx.AsyncClient] = []
        self._semaphore = asyncio.Semaphore(max_connections)

    async def _get_client(self) -> httpx.AsyncClient:
        """Get HTTP client from connection pool."""
        if not self._connection_pool:
            client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                limits=httpx.Limits(max_connections=self.max_connections),
            )
            self._connection_pool.append(client)
            return client

        return self._connection_pool[0]

    async def _request_with_retry(
        self, method: str, url: str, **kwargs: Any
    ) -> httpx.Response:
        """Make HTTP request with retry logic."""
        client = await self._get_client()
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with self._semaphore:
                    response = await client.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response
            except (httpx.RequestError, httpx.HTTPStatusError) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise Exception(f"Request failed after {self.max_retries} attempts: {str(e)}") from last_exception

        raise Exception("Request failed") from last_exception

    @circuit_breaker(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exception=(httpx.HTTPError, httpx.TimeoutException, Exception),
        name="suzieq_poll_bgp_sessions",
    )
    async def poll_bgp_sessions(self, device: str) -> list[BGPSession]:
        """
        Poll BGP sessions from a specific device.

        Args:
            device: Device name or hostname

        Returns:
            List of BGP sessions from the device
        """
        try:
            # SuzieQ REST API endpoint for BGP sessions
            url = f"{self.endpoint}/api/v2/bgp/session"
            params = {"hostname": device}

            response = await self._request_with_retry("GET", url, params=params)
            data = response.json()

            sessions: list[BGPSession] = []
            for item in data.get("data", []):
                # Map SuzieQ response to BGPSession
                state_str = item.get("state", "Idle")
                try:
                    state = BGPSessionState(state_str)
                except ValueError:
                    state = BGPSessionState.IDLE

                sessions.append(
                    BGPSession(
                        device=device,
                        peer=item.get("peer", ""),
                        peer_asn=int(item.get("peerAsn", 0)),
                        state=state,
                        uptime=item.get("uptime"),
                        prefix_count=int(item.get("prefixCount", 0)) if item.get("prefixCount") else None,
                        hold_time=int(item.get("holdTime", 0)) if item.get("holdTime") else None,
                        keepalive=int(item.get("keepaliveTime", 0)) if item.get("keepaliveTime") else None,
                        last_update=datetime.fromisoformat(item["lastUpdate"].replace("Z", "+00:00"))
                        if item.get("lastUpdate")
                        else None,
                    )
                )

            return sessions

        except Exception as e:
            # Return empty list on error (could also raise)
            return []

    @circuit_breaker(
        failure_threshold=5,
        recovery_timeout=60.0,
        expected_exception=(httpx.HTTPError, httpx.TimeoutException, Exception),
        name="suzieq_get_device_inventory",
    )
    async def get_device_inventory(self) -> list[Device]:
        """
        Get inventory of all devices.

        Returns:
            List of Device objects
        """
        try:
            # SuzieQ REST API endpoint for device inventory
            url = f"{self.endpoint}/api/v2/inventory/device"

            response = await self._request_with_retry("GET", url)
            data = response.json()

            devices: list[Device] = []
            for item in data.get("data", []):
                devices.append(
                    Device(
                        name=item.get("hostname", ""),
                        hostname=item.get("hostname", ""),
                        vendor=item.get("vendor", "unknown"),
                        model=item.get("model"),
                        os_version=item.get("version"),
                        status=item.get("status", "up"),
                        last_polled=datetime.fromisoformat(item["lastUpdate"].replace("Z", "+00:00"))
                        if item.get("lastUpdate")
                        else None,
                    )
                )

            return devices

        except Exception as e:
            # Return empty list on error
            return []

    async def close(self) -> None:
        """Close all connections."""
        for client in self._connection_pool:
            await client.aclose()
        self._connection_pool.clear()

