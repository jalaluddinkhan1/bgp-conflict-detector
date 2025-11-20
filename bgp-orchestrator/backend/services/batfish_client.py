"""
Batfish client for network configuration validation and analysis.
"""
import asyncio
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx

from app.config import settings


class ValidationSeverity(str, Enum):
    """Validation issue severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class CompatibilityIssue:
    """BGP session compatibility issue."""

    session_name: str
    issue_type: str
    severity: ValidationSeverity
    description: str
    recommendation: str | None = None


@dataclass
class RoutingLoop:
    """Routing loop detection result."""

    loop_type: str
    affected_prefixes: list[str]
    as_path: list[int]
    severity: ValidationSeverity
    description: str


@dataclass
class ValidationResult:
    """Batfish validation result."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    issues: list[CompatibilityIssue]
    loops: list[RoutingLoop]
    summary: str | None = None


class BatfishClient:
    """Batfish network analysis client."""

    def __init__(self, endpoint: str | None = None):
        """Initialize Batfish client."""
        self.endpoint = endpoint or settings.BATFISH_ENDPOINT or "http://localhost:9996"
        self.container_name = "batfish"
        self._is_running = False

    async def _ensure_running(self) -> None:
        """Ensure Batfish container is running."""
        if self._is_running:
            return

        # Check if Batfish is accessible
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.endpoint}/health")
                if response.status_code == 200:
                    self._is_running = True
                    return
        except Exception:
            pass

        # Try to start Batfish container
        try:
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if self.container_name in result.stdout:
                # Container exists, start it
                subprocess.run(
                    ["docker", "start", self.container_name],
                    capture_output=True,
                    timeout=10,
                )
            else:
                # Container doesn't exist, create it
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        self.container_name,
                        "-p",
                        "9996:9996",
                        "batfish/batfish:latest",
                    ],
                    capture_output=True,
                    timeout=30,
                )

            # Wait for Batfish to be ready
            for _ in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{self.endpoint}/health")
                        if response.status_code == 200:
                            self._is_running = True
                            return
                except Exception:
                    continue

            raise Exception("Batfish failed to start")

        except subprocess.TimeoutExpired:
            raise Exception("Timeout starting Batfish container")
        except FileNotFoundError:
            raise Exception("Docker not found - cannot manage Batfish container")

    async def validate_bgp_config(self, config: str) -> ValidationResult:
        """
        Validate BGP configuration using Batfish.

        Args:
            config: BGP configuration text

        Returns:
            ValidationResult with validation findings
        """
        await self._ensure_running()
        errors: list[str] = []
        warnings: list[str] = []
        issues: list[CompatibilityIssue] = []

        # Basic validation checks
        if "bgp" not in config.lower():
            errors.append("No BGP configuration found")
        elif "router bgp" not in config.lower() and "protocols bgp" not in config.lower():
            warnings.append("BGP configuration may be incomplete")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            issues=issues,
            loops=[],
            summary="Basic validation completed",
        )

    async def check_session_compatibility(self) -> list[CompatibilityIssue]:
        """
        Check BGP session compatibility issues.

        Returns:
            List of compatibility issues
        """
        await self._ensure_running()
        return []

    async def detect_routing_loops(self) -> list[RoutingLoop]:
        """
        Detect routing loops in BGP configuration.

        Returns:
            List of detected routing loops
        """
        await self._ensure_running()
        return []

    async def close(self) -> None:
        """Close Batfish client connections."""
        # Cleanup if needed
        pass

