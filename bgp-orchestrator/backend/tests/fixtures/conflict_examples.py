"""
Sample conflict examples for testing.
"""
from core.conflict_detector import Conflict, ConflictType, ConflictSeverity


# ASN Collision Example
ASN_COLLISION = Conflict(
    type=ConflictType.ASN_COLLISION,
    severity=ConflictSeverity.HIGH,
    description="ASN 65001 is used by multiple peers",
    affected_peers=[1, 2],
    recommended_action="Verify ASN ownership and resolve collision",
    metadata={"asn": 65001, "peers": ["192.0.2.1", "192.0.2.2"]},
)

# RPKI Invalid Example
RPKI_INVALID = Conflict(
    type=ConflictType.RPKI_INVALID,
    severity=ConflictSeverity.CRITICAL,
    description="Prefix 192.0.2.0/24 is not valid in RPKI",
    affected_peers=[1],
    recommended_action="Validate prefix ownership in RPKI",
    metadata={
        "prefix": "192.0.2.0/24",
        "peer_asn": 65001,
        "rpki_status": "invalid",
    },
)

# Session Overlap Example
SESSION_OVERLAP = Conflict(
    type=ConflictType.SESSION_OVERLAP,
    severity=ConflictSeverity.MEDIUM,
    description="BGP sessions overlap with existing configuration",
    affected_peers=[1, 3],
    recommended_action="Review session configuration for overlaps",
    metadata={
        "overlapping_sessions": [
            {"peer_ip": "192.0.2.1", "peer_asn": 65001},
            {"peer_ip": "192.0.2.3", "peer_asn": 65001},
        ]
    },
)

# Routing Loop Example
ROUTING_LOOP = Conflict(
    type=ConflictType.ROUTING_LOOP,
    severity=ConflictSeverity.HIGH,
    description="Potential routing loop detected in AS path",
    affected_peers=[1],
    recommended_action="Review AS path filters",
    metadata={
        "prefix": "192.0.2.0/24",
        "as_path": [65001, 65002, 65001],
        "loop_detected_at": 65001,
    },
)

# Configuration Mismatch Example
CONFIGURATION_MISMATCH = Conflict(
    type=ConflictType.CONFIGURATION_MISMATCH,
    severity=ConflictSeverity.MEDIUM,
    description="BGP configuration mismatch between peers",
    affected_peers=[1, 2],
    recommended_action="Synchronize BGP configuration",
    metadata={
        "mismatch_type": "import_policy",
        "expected": "accept-all",
        "actual": "restrictive",
    },
)

ALL_CONFLICTS = [
    ASN_COLLISION,
    RPKI_INVALID,
    SESSION_OVERLAP,
    ROUTING_LOOP,
    CONFIGURATION_MISMATCH,
]

