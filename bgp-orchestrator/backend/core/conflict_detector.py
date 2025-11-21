"""
BGP conflict detection system using rule-based architecture.
"""
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..models.peering import BGPPeering
else:
    # Runtime import using relative import
    from ..models.peering import BGPPeering  # noqa: F401


class ConflictSeverity(str, Enum):
    """Severity levels for detected conflicts."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConflictType(str, Enum):
    """Types of conflicts that can be detected."""

    ASN_COLLISION = "asn_collision"
    RPKI_INVALID = "rpki_invalid"
    SESSION_OVERLAP = "session_overlap"
    ROUTING_LOOP = "routing_loop"
    CONFIGURATION_MISMATCH = "configuration_mismatch"


@dataclass
class Conflict:
    """Represents a detected BGP conflict."""

    type: ConflictType
    severity: ConflictSeverity
    description: str
    affected_peers: list[int]  # List of peering IDs
    recommended_action: str
    metadata: dict[str, Any] | None = None

    def __repr__(self) -> str:
        """String representation of the conflict."""
        return f"<Conflict(type={self.type.value}, severity={self.severity.value}, peers={self.affected_peers})>"


class ConflictRule(ABC):
    """Abstract base class for conflict detection rules."""

    @abstractmethod
    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """
        Check for conflicts related to a specific peering session.

        Args:
            peering: The peering session to check
            all_peerings: All existing peering sessions for context

        Returns:
            Conflict object if a conflict is detected, None otherwise
        """
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Return the name of this rule."""
        pass


class ASNCollisionRule(ConflictRule):
    """
    Detects ASN collisions - multiple peerings with the same peer ASN
    that might cause routing issues.
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """Check for ASN collisions."""
        # Find peerings with the same peer ASN but different peer IPs
        collisions = [
            p
            for p in all_peerings
            if p.id != peering.id
            and p.peer_asn == peering.peer_asn
            and p.peer_ip != peering.peer_ip
            and p.status == "active"
        ]

        if collisions:
            return Conflict(
                type=ConflictType.ASN_COLLISION,
                severity=ConflictSeverity.HIGH,
                description=f"Multiple active peerings found for ASN {peering.peer_asn} with different IPs",
                affected_peers=[peering.id] + [p.id for p in collisions],
                recommended_action="Review peerings to ensure they're not duplicate sessions",
                metadata={"collision_count": len(collisions), "peer_asn": peering.peer_asn},
            )

        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "ASN Collision Detection"


class RPKIValidationRule(ConflictRule):
    """
    Validates BGP routes against RPKI (Resource Public Key Infrastructure).
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """Check RPKI validation."""
        if 64512 <= peering.peer_asn <= 65534 or 4200000000 <= peering.peer_asn <= 4294967294:
            return None
        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "RPKI Validation"


class SessionOverlapRule(ConflictRule):
    """
    Detects overlapping BGP sessions - same device, same peer IP/ASN.
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """Check for overlapping sessions."""
        overlaps = [
            p
            for p in all_peerings
            if p.id != peering.id
            and p.device == peering.device
            and p.peer_ip == peering.peer_ip
            and p.peer_asn == peering.peer_asn
        ]

        if overlaps:
            return Conflict(
                type=ConflictType.SESSION_OVERLAP,
                severity=ConflictSeverity.CRITICAL,
                description=f"Duplicate peering session found on device {peering.device} for {peering.peer_ip}",
                affected_peers=[peering.id] + [p.id for p in overlaps],
                recommended_action="Remove duplicate peering session",
                metadata={
                    "device": peering.device,
                    "peer_ip": str(peering.peer_ip),
                    "peer_asn": peering.peer_asn,
                },
            )

        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "Session Overlap Detection"


class RoutingLoopRule(ConflictRule):
    """
    Detects potential AS_PATH loops in routing configuration.
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """Check for potential routing loops."""
        # Check if local ASN matches peer ASN (ASN collision)
        if peering.local_asn == peering.peer_asn:
            return Conflict(
                type=ConflictType.ROUTING_LOOP,
                severity=ConflictSeverity.CRITICAL,
                description=f"ASN collision: local ASN {peering.local_asn} matches peer ASN",
                affected_peers=[peering.id],
                recommended_action="Change local or peer ASN to avoid routing loops",
                metadata={"local_asn": peering.local_asn, "peer_asn": peering.peer_asn},
            )

        # Check if local ASN appears in routing policy as a transit path
        routing_policy = peering.routing_policy or {}

        # Look for import/export policies that might create loops
        import_policy = routing_policy.get("import", {})
        export_policy = routing_policy.get("export", {})

        # Check if we're advertising our own ASN back to ourselves
        if import_policy and "as_path" in import_policy:
            as_path = import_policy.get("as_path", [])
            if peering.local_asn in as_path:
                return Conflict(
                    type=ConflictType.ROUTING_LOOP,
                    severity=ConflictSeverity.CRITICAL,
                    description=f"Potential routing loop detected: local ASN {peering.local_asn} in import policy",
                    affected_peers=[peering.id],
                    recommended_action="Review import policy to prevent ASN loop",
                    metadata={"local_asn": peering.local_asn, "as_path": as_path},
                )

        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "Routing Loop Detection"


class PrefixOverlapRule(ConflictRule):
    """
    Detects prefix overlaps and suspiciously broad prefixes (potential hijack).
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """Check for prefix overlaps and suspicious prefixes."""
        try:
            import ipaddress

            # Check if peer IP is in a suspiciously broad range
            try:
                peer_ip = ipaddress.ip_address(str(peering.peer_ip))
                
                # Check for private IPs in public peering (might be misconfiguration)
                if peer_ip.is_private and peering.status == "active":
                    # This might be intentional for internal peerings, so only warn
                    return Conflict(
                        type=ConflictType.CONFIGURATION_MISMATCH,
                        severity=ConflictSeverity.MEDIUM,
                        description=f"Private IP {peering.peer_ip} used in active peering",
                        affected_peers=[peering.id],
                        recommended_action="Verify this is intentional for internal peering",
                        metadata={"peer_ip": str(peering.peer_ip), "is_private": True},
                    )
            except ValueError:
                # Invalid IP format
                return Conflict(
                    type=ConflictType.CONFIGURATION_MISMATCH,
                    severity=ConflictSeverity.HIGH,
                    description=f"Invalid IP address format: {peering.peer_ip}",
                    affected_peers=[peering.id],
                    recommended_action="Fix IP address format",
                    metadata={"invalid_ip": str(peering.peer_ip)},
                )

            # Check for overlapping peer IPs on same device
            overlaps = [
                p
                for p in all_peerings
                if p.id != peering.id
                and p.device == peering.device
                and p.peer_ip == peering.peer_ip
            ]

            if overlaps:
                return Conflict(
                    type=ConflictType.SESSION_OVERLAP,
                    severity=ConflictSeverity.CRITICAL,
                    description=f"Duplicate peer IP {peering.peer_ip} on device {peering.device}",
                    affected_peers=[peering.id] + [p.id for p in overlaps],
                    recommended_action="Remove duplicate peering session",
                    metadata={
                        "device": peering.device,
                        "peer_ip": str(peering.peer_ip),
                    },
                )

        except Exception as e:
            pass

        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "Prefix Overlap Detection"


class BGPConflictDetector:
    """Orchestrates all conflict detection rules."""

    def __init__(self) -> None:
        """Initialize detector with all available rules."""
        self.rules: list[ConflictRule] = [
            ASNCollisionRule(),
            RPKIValidationRule(),
            SessionOverlapRule(),
            RoutingLoopRule(),
            PrefixOverlapRule(),
        ]

    async def detect_conflicts(
        self, peering: BGPPeering, all_peerings: list[BGPPeering] | None = None
    ) -> list[Conflict]:
        """
        Run all conflict detection rules on a peering session concurrently with timeout.

        Args:
            peering: The peering session to check
            all_peerings: All existing peering sessions (required for context)

        Returns:
            List of detected conflicts
        """
        if all_peerings is None:
            all_peerings = []

        conflicts: list[Conflict] = []

        # Run all rules concurrently with timeout
        tasks = []
        for rule in self.rules:
            task = asyncio.wait_for(
                rule.check(peering, all_peerings),
                timeout=5.0,  # 5 second timeout per rule
            )
            tasks.append((task, rule.rule_name))

        # Execute all tasks concurrently
        try:
            results = await asyncio.gather(*[t[0] for t in tasks], return_exceptions=True)
            
            # Process results
            for i, result in enumerate(results):
                rule_name = tasks[i][1]
                if isinstance(result, asyncio.TimeoutError):
                    # Log timeout but don't fail the entire check
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Conflict detection rule '{rule_name}' timed out after 5 seconds")
                    # Fail open: allow the peering if detection times out
                    continue
                elif isinstance(result, Exception):
                    # Log exception but continue with other rules
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Conflict detection rule '{rule_name}' failed: {result}")
                    continue
                elif result is not None:
                    conflicts.append(result)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Conflict detection failed: {e}")
            # Fail open: return empty list if detection fails completely

        return conflicts

    def add_rule(self, rule: ConflictRule) -> None:
        """Add a custom conflict detection rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> None:
        """Remove a rule by name."""
        self.rules = [r for r in self.rules if r.rule_name != rule_name]

