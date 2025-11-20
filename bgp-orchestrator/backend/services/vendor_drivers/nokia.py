"""
Nokia SR OS vendor driver using pysros.
"""
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any

import pysros.management as pysros_mgmt
from pysros.exceptions import ModelProcessingError, SrosMgmtError


class ConnectionState(str, Enum):
    """Connection states."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    ERROR = "error"


@dataclass
class BGPSession:
    """BGP session information from Nokia SR OS."""

    session_name: str
    peer_address: str
    peer_asn: int
    local_asn: int
    state: str
    family: str
    prefix_count: int | None = None


@dataclass
class Credentials:
    """Device credentials."""

    username: str
    password: str
    port: int = 830  # NETCONF port


class NokiaSROSDriver:
    """Nokia SR OS driver using pysros."""

    def __init__(self, max_connections: int = 5):
        """Initialize Nokia SR OS driver."""
        self.max_connections = max_connections
        self._connections: dict[str, Any] = {}  # device -> connection
        self._connection_states: dict[str, ConnectionState] = {}
        self._semaphore = asyncio.Semaphore(max_connections)
        self._rollback_configs: dict[str, str] = {}  # device -> previous config

    async def _get_connection(self, device: str, credentials: Credentials) -> Any:
        """Get or create connection to device."""
        if device in self._connections and self._connection_states.get(device) == ConnectionState.CONNECTED:
            return self._connections[device]

        async with self._semaphore:
            try:
                self._connection_states[device] = ConnectionState.CONNECTING

                # Create connection (pysros is synchronous, so run in executor)
                def _connect() -> Any:
                    connection = pysros_mgmt.sros(
                        host=device,
                        username=credentials.username,
                        password=credentials.password,
                        port=credentials.port,
                    )
                    return connection

                loop = asyncio.get_event_loop()
                connection = await loop.run_in_executor(None, _connect)

                self._connections[device] = connection
                self._connection_states[device] = ConnectionState.CONNECTED
                return connection

            except SrosMgmtError as e:
                self._connection_states[device] = ConnectionState.ERROR
                raise Exception(f"Failed to connect to {device}: {str(e)}") from e
            except Exception as e:
                self._connection_states[device] = ConnectionState.ERROR
                raise Exception(f"Connection error to {device}: {str(e)}") from e

    async def validate_credentials(self, device: str, credentials: Credentials) -> bool:
        """
        Validate device credentials.

        Args:
            device: Device hostname/IP
            credentials: Device credentials

        Returns:
            True if credentials are valid
        """
        try:
            connection = await self._get_connection(device, credentials)
            if connection:
                return True
            return False
        except Exception:
            return False

    async def get_bgp_sessions(self, device: str, credentials: Credentials) -> list[BGPSession]:
        """
        Get BGP sessions from Nokia SR OS device.

        Args:
            device: Device hostname/IP
            credentials: Device credentials

        Returns:
            List of BGP sessions
        """
        connection = await self._get_connection(device, credentials)

        def _get_sessions() -> list[BGPSession]:
            """Get BGP sessions (synchronous)."""
            try:
                # Navigate to BGP configuration
                # This is a simplified example - actual implementation would use proper YANG paths
                bgp_path = "/nokia-conf:configure/router[router-name='Base']/bgp"

                # Get BGP neighbor configuration
                config = connection.running.get(bgp_path)

                sessions: list[BGPSession] = []
                if config and "neighbor" in config:
                    for neighbor in config["neighbor"]:
                        peer_address = neighbor.get("ip-address", "")
                        peer_asn = neighbor.get("peer-as", 0)

                        # Get session state
                        operational_path = f"/nokia-state:state/router[router-name='Base']/bgp/neighbor[ip-address='{peer_address}']"
                        try:
                            operational = connection.running.get(operational_path)
                            state = operational.get("oper-state", "unknown") if operational else "unknown"
                        except Exception:
                            state = "unknown"

                        sessions.append(
                            BGPSession(
                                session_name=f"{device}-{peer_address}",
                                peer_address=peer_address,
                                peer_asn=peer_asn,
                                local_asn=config.get("autonomous-system", 0),
                                state=state,
                                family="ipv4",  # Could be determined from config
                            )
                        )

                return sessions

            except (ModelProcessingError, SrosMgmtError) as e:
                raise Exception(f"Failed to get BGP sessions: {str(e)}") from e

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_sessions)

    async def update_bgp_config(
        self, device: str, credentials: Credentials, config: dict[str, Any]
    ) -> bool:
        """
        Update BGP configuration on Nokia SR OS device.

        Args:
            device: Device hostname/IP
            credentials: Device credentials
            config: Configuration dictionary

        Returns:
            True if update was successful
        """
        connection = await self._get_connection(device, credentials)

        # Store current config for rollback
        def _save_config() -> str:
            """Save current configuration."""
            try:
                bgp_path = "/nokia-conf:configure/router[router-name='Base']/bgp"
                return str(connection.running.get(bgp_path))
            except Exception:
                return ""

        loop = asyncio.get_event_loop()
        previous_config = await loop.run_in_executor(None, _save_config)
        self._rollback_configs[device] = previous_config

        def _update_config() -> bool:
            """Update configuration (synchronous)."""
            try:
                bgp_path = "/nokia-conf:configure/router[router-name='Base']/bgp"

                # Apply configuration changes
                # This is simplified - actual implementation would properly map config dict to YANG
                connection.running.set(bgp_path, config)

                # Commit configuration
                connection.candidate.commit()

                return True

            except (ModelProcessingError, SrosMgmtError) as e:
                # Rollback on failure
                try:
                    if previous_config:
                        connection.running.set(bgp_path, previous_config)
                        connection.candidate.commit()
                except Exception:
                    pass  # Rollback failed

                raise Exception(f"Failed to update BGP config: {str(e)}") from e

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, _update_config)

            # Clear rollback config on success
            if result and device in self._rollback_configs:
                del self._rollback_configs[device]

            return result

        except Exception as e:
            # Attempt rollback
            await self.rollback_config(device, credentials)
            raise

    async def rollback_config(self, device: str, credentials: Credentials) -> bool:
        """
        Rollback to previous configuration.

        Args:
            device: Device hostname/IP
            credentials: Device credentials

        Returns:
            True if rollback was successful
        """
        if device not in self._rollback_configs:
            return False

        previous_config = self._rollback_configs[device]
        if not previous_config:
            return False

        connection = await self._get_connection(device, credentials)

        def _rollback() -> bool:
            """Perform rollback (synchronous)."""
            try:
                bgp_path = "/nokia-conf:configure/router[router-name='Base']/bgp"
                connection.running.set(bgp_path, previous_config)
                connection.candidate.commit()
                return True
            except Exception:
                return False

        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _rollback)

        if result:
            del self._rollback_configs[device]

        return result

    async def close_connection(self, device: str) -> None:
        """Close connection to a device."""
        if device in self._connections:
            try:
                connection = self._connections[device]
                # pysros connections are typically closed automatically
                # but we can clean up our reference
                del self._connections[device]
                self._connection_states[device] = ConnectionState.DISCONNECTED
            except Exception:
                pass

    async def close_all(self) -> None:
        """Close all connections."""
        devices = list(self._connections.keys())
        for device in devices:
            await self.close_connection(device)

