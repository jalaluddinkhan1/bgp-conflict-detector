"""
Border Gateway Protocol (BGP) Conflict Detection System

This module implements a rule-based conflict detection framework for BGP peering
sessions. The system employs multiple detection algorithms to identify potential
routing conflicts, misconfigurations, and security violations in BGP configurations.

The architecture follows a composable rule-based design where each detection rule
implements a specific conflict detection algorithm. Rules are executed concurrently
with timeout protection to ensure system responsiveness.

References:
    - RFC 4271: A Border Gateway Protocol 4 (BGP-4)
    - RFC 6811: BGP Prefix Origin Validation
    - RFC 8205: BGPsec Protocol Specification
"""
import asyncio
import logging
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

logger = logging.getLogger(__name__)


class ConflictSeverity(str, Enum):
    """
    Severity classification for detected BGP conflicts.
    
    Severity levels are assigned based on the potential impact on network
    stability, security, and routing correctness. Higher severity conflicts
    indicate conditions that may cause immediate routing failures or security
    violations.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ConflictType(str, Enum):
    """
    Classification of BGP conflict types.
    
    Each type represents a distinct category of routing conflict or
    misconfiguration that can be detected through algorithmic analysis
    of peering session configurations.
    """

    ASN_COLLISION = "asn_collision"
    RPKI_INVALID = "rpki_invalid"
    SESSION_OVERLAP = "session_overlap"
    ROUTING_LOOP = "routing_loop"
    CONFIGURATION_MISMATCH = "configuration_mismatch"


@dataclass
class Conflict:
    """
    Represents a detected BGP routing conflict.
    
    This data structure encapsulates all information related to a detected
    conflict, including its classification, severity assessment, affected
    peering sessions, and remediation recommendations.
    
    Attributes:
        type: Classification of the conflict according to ConflictType enum
        severity: Severity assessment according to ConflictSeverity enum
        description: Human-readable description of the conflict condition
        affected_peers: List of peering session identifiers affected by this conflict
        recommended_action: Suggested remediation steps to resolve the conflict
        metadata: Additional structured data relevant to the conflict detection
    """

    type: ConflictType
    severity: ConflictSeverity
    description: str
    affected_peers: list[int]
    recommended_action: str
    metadata: dict[str, Any] | None = None

    def __repr__(self) -> str:
        """Generate string representation for debugging and logging."""
        return f"<Conflict(type={self.type.value}, severity={self.severity.value}, peers={self.affected_peers})>"


class ConflictRule(ABC):
    """
    Abstract base class for BGP conflict detection rules.
    
    This class defines the interface that all conflict detection algorithms
    must implement. Each rule implements a specific detection algorithm that
    analyzes peering session configurations for potential conflicts.
    
    The rule-based architecture allows for modular, extensible conflict
    detection where new detection algorithms can be added without modifying
    existing code.
    """

    @abstractmethod
    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """
        Execute conflict detection algorithm for a peering session.
        
        This method implements the core detection logic for a specific type
        of conflict. The algorithm analyzes the target peering session in
        the context of all existing peering sessions to identify conflicts.
        
        Args:
            peering: The BGP peering session under analysis
            all_peerings: Complete set of existing peering sessions for
                         contextual analysis and cross-session conflict detection

        Returns:
            Conflict object if a conflict is detected, None if no conflict
            is found. The Conflict object contains full details of the
            detected condition including severity and remediation guidance.
        """
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """
        Return the canonical name of this detection rule.
        
        Returns:
            Human-readable name identifying this specific detection algorithm
        """
        pass


class ASNCollisionRule(ConflictRule):
    """
    Autonomous System Number (ASN) Collision Detection Rule.
    
    This rule detects cases where multiple active BGP peering sessions
    are configured with the same peer Autonomous System Number (ASN) but
    different peer IP addresses. Such configurations may indicate duplicate
    peering sessions or misconfiguration that could lead to routing
    inconsistencies.
    
    Algorithm:
        For the target peering session, identify all other active peering
        sessions that share the same peer ASN but have different peer IP
        addresses. If such sessions exist, a collision is detected.
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """
        Execute ASN collision detection algorithm.
        
        Implements the collision detection logic by comparing the target
        peering session against all existing peerings to identify ASN
        collisions with different IP addresses.
        """
        try:
            # Validate required attributes
            if not hasattr(peering, "peer_asn") or peering.peer_asn is None:
                return None
            
            peering_id = getattr(peering, "id", None)
            
            # Find peerings with the same peer ASN but different peer IPs
            collisions = [
                p
                for p in all_peerings
                if getattr(p, "id", None) != peering_id
                and getattr(p, "peer_asn", None) == peering.peer_asn
                and getattr(p, "peer_ip", None) != getattr(peering, "peer_ip", None)
                and getattr(p, "status", None) == "active"
            ]

            if collisions:
                affected_ids = [peering_id] if peering_id is not None else []
                affected_ids.extend([getattr(p, "id", None) for p in collisions if getattr(p, "id", None) is not None])
                
                return Conflict(
                    type=ConflictType.ASN_COLLISION,
                    severity=ConflictSeverity.HIGH,
                    description=f"Multiple active peerings found for ASN {peering.peer_asn} with different IPs",
                    affected_peers=affected_ids,
                    recommended_action="Review peerings to ensure they're not duplicate sessions",
                    metadata={"collision_count": len(collisions), "peer_asn": peering.peer_asn},
                )
        except Exception as e:
            logger.error(
                f"Error in ASNCollisionRule.check(): {e}",
                exc_info=True,
                extra={"rule_name": "ASN Collision Detection"},
            )

        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "ASN Collision Detection"


class RPKIValidationRule(ConflictRule):
    """
    Resource Public Key Infrastructure (RPKI) Validation Rule.
    
    This rule validates BGP route origin announcements against RPKI
    Route Origin Authorizations (ROAs). RPKI provides cryptographic
    validation of route origin to prevent route hijacking attacks.
    
    Implementation Note:
        Full RPKI validation requires integration with RPKI validators
        (e.g., RIPE RPKI Validator, Routinator). This implementation
        currently serves as a framework for future RPKI integration.
        
    References:
        - RFC 6811: BGP Prefix Origin Validation
        - RFC 6480: An Infrastructure to Support Secure Internet Routing
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """
        Execute RPKI validation algorithm.
        
        Validates the peering session's ASN and associated routes against
        RPKI ROAs. Private and reserved ASN ranges are excluded from validation
        as they are not part of the public RPKI infrastructure.
        """
        try:
            peer_asn = getattr(peering, "peer_asn", None)
            if peer_asn is None:
                return None
            
            # Exclude private ASN ranges from RPKI validation
            # Range 64512-65534: Private 16-bit ASNs (RFC 6996)
            # Range 4200000000-4294967294: Private 32-bit ASNs (RFC 6996)
            if 64512 <= peer_asn <= 65534 or 4200000000 <= peer_asn <= 4294967294:
                return None
            
            # RPKI validation requires integration with RPKI validator service
            # This is a placeholder for future implementation
            return None
        except Exception as e:
            logger.error(
                f"Error in RPKIValidationRule.check(): {e}",
                exc_info=True,
                extra={"rule_name": "RPKI Validation"},
            )
            return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "RPKI Validation"


class SessionOverlapRule(ConflictRule):
    """
    BGP Session Overlap Detection Rule.
    
    Detects duplicate BGP peering sessions where multiple sessions are
    configured with identical parameters (device, peer IP address, and
    peer ASN). Such overlaps indicate configuration errors that can cause
    routing instability and session establishment failures.
    
    Algorithm:
        Identify all peering sessions that share the same device identifier,
        peer IP address, and peer ASN as the target session. If duplicates
        exist, a critical overlap conflict is detected.
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """
        Execute session overlap detection algorithm.
        
        Compares the target peering session against all existing sessions
        to identify exact parameter matches indicating duplicate configurations.
        """
        try:
            # Validate required attributes
            peering_id = getattr(peering, "id", None)
            peering_device = getattr(peering, "device", None)
            peering_peer_ip = getattr(peering, "peer_ip", None)
            peering_peer_asn = getattr(peering, "peer_asn", None)
            
            if not all([peering_device, peering_peer_ip, peering_peer_asn]):
                return None
            
            overlaps = [
                p
                for p in all_peerings
                if getattr(p, "id", None) != peering_id
                and getattr(p, "device", None) == peering_device
                and getattr(p, "peer_ip", None) == peering_peer_ip
                and getattr(p, "peer_asn", None) == peering_peer_asn
            ]

            if overlaps:
                affected_ids = [peering_id] if peering_id is not None else []
                affected_ids.extend([getattr(p, "id", None) for p in overlaps if getattr(p, "id", None) is not None])
                
                return Conflict(
                    type=ConflictType.SESSION_OVERLAP,
                    severity=ConflictSeverity.CRITICAL,
                    description=f"Duplicate peering session found on device {peering_device} for {peering_peer_ip}",
                    affected_peers=affected_ids,
                    recommended_action="Remove duplicate peering session",
                    metadata={
                        "device": peering_device,
                        "peer_ip": str(peering_peer_ip),
                        "peer_asn": peering_peer_asn,
                    },
                )
        except Exception as e:
            logger.error(
                f"Error in SessionOverlapRule.check(): {e}",
                exc_info=True,
                extra={"rule_name": "Session Overlap Detection"},
            )

        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "Session Overlap Detection"


class RoutingLoopRule(ConflictRule):
    """
    BGP Routing Loop Detection Rule.
    
    Detects potential routing loops in BGP configurations by analyzing
    AS_PATH attributes and routing policies. Routing loops can cause
    route oscillation, increased convergence time, and network instability.
    
    Detection Methods:
        1. ASN Collision: Local ASN matches peer ASN (immediate loop condition)
        2. AS_PATH Analysis: Local ASN appears in import policy AS_PATH
           filters, indicating potential loop-back routing
    
    Algorithm:
        Analyzes the peering session's local ASN, peer ASN, and routing
        policy import filters to identify conditions that could create
        routing loops in the AS_PATH.
        
    References:
        - RFC 4271, Section 6.3: BGP AS_PATH Loop Detection
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """
        Execute routing loop detection algorithm.
        
        Analyzes ASN relationships and routing policy configurations to
        identify potential routing loop conditions.
        """
        try:
            peering_id = getattr(peering, "id", None)
            local_asn = getattr(peering, "local_asn", None)
            peer_asn = getattr(peering, "peer_asn", None)
            
            # Detection Method 1: Direct ASN collision
            # If local ASN equals peer ASN, this creates an immediate loop condition
            if local_asn is not None and peer_asn is not None and local_asn == peer_asn:
                return Conflict(
                    type=ConflictType.ROUTING_LOOP,
                    severity=ConflictSeverity.CRITICAL,
                    description=f"ASN collision detected: local ASN {local_asn} matches peer ASN",
                    affected_peers=[peering_id] if peering_id is not None else [],
                    recommended_action="Modify local ASN or peer ASN to eliminate collision",
                    metadata={"local_asn": local_asn, "peer_asn": peer_asn},
                )

            # Detection Method 2: AS_PATH loop analysis
            # Analyze routing policy import filters for AS_PATH loop conditions
            routing_policy = getattr(peering, "routing_policy", None) or {}

            if isinstance(routing_policy, dict):
                import_policy = routing_policy.get("import", {})
                export_policy = routing_policy.get("export", {})

                # Check if local ASN appears in import policy AS_PATH filter
                # This indicates potential loop-back where routes may be re-advertised
                if local_asn is not None and import_policy and "as_path" in import_policy:
                    as_path_filter = import_policy.get("as_path", [])
                    if isinstance(as_path_filter, list) and local_asn in as_path_filter:
                        return Conflict(
                            type=ConflictType.ROUTING_LOOP,
                            severity=ConflictSeverity.CRITICAL,
                            description=f"AS_PATH loop condition: local ASN {local_asn} present in import policy AS_PATH filter",
                            affected_peers=[peering_id] if peering_id is not None else [],
                            recommended_action="Review and modify import policy AS_PATH filter to prevent loop-back",
                            metadata={"local_asn": local_asn, "as_path": as_path_filter},
                        )
        except Exception as e:
            logger.error(
                f"Error in RoutingLoopRule.check(): {e}",
                exc_info=True,
                extra={"rule_name": "Routing Loop Detection"},
            )

        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "Routing Loop Detection"


class PrefixOverlapRule(ConflictRule):
    """
    IP Prefix Overlap and Misconfiguration Detection Rule.
    
    Detects configuration issues related to IP address prefixes in BGP
    peering sessions. This includes:
    
    1. Invalid IP address formats
    2. Private IP addresses used in active peering sessions (potential misconfiguration)
    3. Duplicate peer IP addresses on the same device
    
    Algorithm:
        Validates peer IP address format using standard IP address parsing.
        Checks for private address space usage in active sessions.
        Identifies duplicate peer IP configurations on the same network device.
        
    References:
        - RFC 1918: Address Allocation for Private Internets
        - RFC 4291: IP Version 6 Addressing Architecture
    """

    async def check(self, peering: BGPPeering, all_peerings: list[BGPPeering]) -> Conflict | None:
        """
        Execute prefix overlap and misconfiguration detection algorithm.
        
        Performs IP address validation and duplicate detection for peer
        IP addresses in BGP peering configurations.
        """
        try:
            import ipaddress

            # Get all required attributes upfront
            peering_id = getattr(peering, "id", None)
            peering_device = getattr(peering, "device", None)
            peering_peer_ip = getattr(peering, "peer_ip", None)
            peering_status = getattr(peering, "status", None)
            
            if peering_peer_ip is None:
                return None

            # IP Address Format Validation
            try:
                peer_ip = ipaddress.ip_address(str(peering_peer_ip))
                
                # Private Address Space Detection
                # RFC 1918 private addresses in active sessions may indicate misconfiguration
                # Note: This may be intentional for internal BGP (iBGP) sessions
                status_value = peering_status.value if hasattr(peering_status, "value") else peering_status
                if peer_ip.is_private and status_value == "active":
                    return Conflict(
                        type=ConflictType.CONFIGURATION_MISMATCH,
                        severity=ConflictSeverity.MEDIUM,
                        description=f"Private IP address space detected in active peering: {peering_peer_ip}",
                        affected_peers=[peering_id] if peering_id is not None else [],
                        recommended_action="Verify private IP usage is intentional for internal peering configuration",
                        metadata={"peer_ip": str(peering_peer_ip), "is_private": True},
                    )
            except ValueError:
                # Invalid IP address format detected
                return Conflict(
                    type=ConflictType.CONFIGURATION_MISMATCH,
                    severity=ConflictSeverity.HIGH,
                    description=f"Invalid IP address format: {peering_peer_ip}",
                    affected_peers=[peering_id] if peering_id is not None else [],
                    recommended_action="Correct IP address format to valid IPv4 or IPv6 address",
                    metadata={"invalid_ip": str(peering_peer_ip)},
                )

            # Duplicate Peer IP Detection
            # Identify multiple peering sessions with identical peer IP on same device
            
            if peering_device and peering_peer_ip:
                overlaps = [
                    p
                    for p in all_peerings
                    if getattr(p, "id", None) != peering_id
                    and getattr(p, "device", None) == peering_device
                    and getattr(p, "peer_ip", None) == peering_peer_ip
                ]

                if overlaps:
                    affected_ids = [peering_id] if peering_id is not None else []
                    affected_ids.extend([getattr(p, "id", None) for p in overlaps if getattr(p, "id", None) is not None])
                    
                    return Conflict(
                        type=ConflictType.SESSION_OVERLAP,
                        severity=ConflictSeverity.CRITICAL,
                        description=f"Duplicate peer IP {peering_peer_ip} on device {peering_device}",
                        affected_peers=affected_ids,
                        recommended_action="Remove duplicate peering session",
                        metadata={
                            "device": peering_device,
                            "peer_ip": str(peering_peer_ip),
                        },
                    )

        except Exception as e:
            # Error handling: Log exception but continue with other detection rules
            # Fail-open design ensures partial rule failures do not prevent overall conflict detection
            peering_id = getattr(peering, "id", None)
            peering_name = getattr(peering, "name", "unknown")
            logger.error(
                f"PrefixOverlapRule execution error for peering {peering_id}: {e}",
                exc_info=True,
                extra={
                    "peering_id": peering_id,
                    "peering_name": peering_name,
                    "rule_name": "Prefix Overlap Detection",
                },
            )

        return None

    @property
    def rule_name(self) -> str:
        """Return the rule name."""
        return "Prefix Overlap Detection"


class BGPConflictDetector:
    """
    BGP Conflict Detection Orchestrator.
    
    This class coordinates the execution of multiple conflict detection rules
    against BGP peering sessions. Rules are executed concurrently with timeout
    protection to ensure system responsiveness and prevent blocking operations.
    
    The orchestrator implements a fail-open design where individual rule failures
    do not prevent other rules from executing. This ensures maximum conflict
    detection coverage even when some rules encounter errors.
    
    Architecture:
        - Composable rule-based design
        - Concurrent rule execution with asyncio
        - Per-rule timeout protection (5 seconds default)
        - Comprehensive error handling and logging
    """

    def __init__(self) -> None:
        """
        Initialize conflict detector with all available detection rules.
        
        The rule set includes:
            - ASN Collision Detection
            - RPKI Validation (framework)
            - Session Overlap Detection
            - Routing Loop Detection
            - Prefix Overlap Detection
        """
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
        Execute all conflict detection rules against a peering session.
        
        This method orchestrates the concurrent execution of all registered
        conflict detection rules. Each rule runs independently with timeout
        protection. Results are aggregated and returned as a list of detected
        conflicts.
        
        Execution Model:
            - Concurrent execution using asyncio.gather()
            - Per-rule timeout: 5 seconds
            - Fail-open design: rule failures do not block other rules
            - Exception handling: all exceptions are logged and isolated
        
        Args:
            peering: The BGP peering session to analyze for conflicts
            all_peerings: Complete set of existing peering sessions required
                         for cross-session conflict analysis. If None, an empty
                         list is used.

        Returns:
            List of Conflict objects representing all detected conflicts.
            Empty list if no conflicts are detected or if all rules fail.
        """
        if all_peerings is None:
            all_peerings = []

        conflicts: list[Conflict] = []

        # Prepare concurrent execution tasks with timeout protection
        # Each rule executes independently with a 5-second timeout
        RULE_TIMEOUT_SECONDS = 5.0
        tasks = []
        for rule in self.rules:
            task = asyncio.wait_for(
                rule.check(peering, all_peerings),
                timeout=RULE_TIMEOUT_SECONDS,
            )
            tasks.append((task, rule.rule_name))

        # Execute all detection rules concurrently
        try:
            results = await asyncio.gather(*[t[0] for t in tasks], return_exceptions=True)
            
            # Process rule execution results
            peering_id = getattr(peering, "id", None)
            for i, result in enumerate(results):
                rule_name = tasks[i][1]
                
                if isinstance(result, asyncio.TimeoutError):
                    # Rule execution exceeded timeout threshold
                    logger.warning(
                        f"Conflict detection rule '{rule_name}' exceeded timeout threshold",
                        extra={
                            "rule_name": rule_name,
                            "peering_id": peering_id,
                            "timeout_seconds": RULE_TIMEOUT_SECONDS,
                        },
                    )
                    continue
                elif isinstance(result, Exception):
                    # Rule execution raised an exception
                    logger.error(
                        f"Conflict detection rule '{rule_name}' execution error: {result}",
                        exc_info=True,
                        extra={
                            "rule_name": rule_name,
                            "peering_id": peering_id,
                            "error_type": type(result).__name__,
                        },
                    )
                    continue
                elif result is not None:
                    # Rule detected a conflict
                    conflicts.append(result)
                    
        except Exception as e:
            # Catastrophic failure in rule orchestration
            peering_id = getattr(peering, "id", None)
            logger.error(
                f"Conflict detection orchestration failure: {e}",
                exc_info=True,
                extra={
                    "peering_id": peering_id,
                    "error_type": type(e).__name__,
                },
            )

        return conflicts

    def add_rule(self, rule: ConflictRule) -> None:
        """
        Register a custom conflict detection rule.
        
        This method allows dynamic extension of the conflict detection
        system by adding new detection algorithms at runtime.
        
        Args:
            rule: ConflictRule instance implementing the detection algorithm
        """
        self.rules.append(rule)

    def remove_rule(self, rule_name: str) -> None:
        """
        Unregister a conflict detection rule by name.
        
        Removes the specified rule from the active detection rule set.
        This operation is idempotent: removing a non-existent rule has no effect.
        
        Args:
            rule_name: Canonical name of the rule to remove
        """
        self.rules = [r for r in self.rules if r.rule_name != rule_name]

