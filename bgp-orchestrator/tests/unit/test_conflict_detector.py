"""
Unit tests for BGP conflict detector.
Target: 100% coverage of core.conflict_detector module.
"""
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_path))

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from core.conflict_detector import (
    ASNCollisionRule,
    BGPConflictDetector,
    Conflict,
    ConflictRule,
    ConflictSeverity,
    ConflictType,
    RPKIValidationRule,
    RoutingLoopRule,
    SessionOverlapRule,
)
from models.peering import BGPPeering, PeeringStatus


@pytest.fixture
def sample_peering():
    """Create sample BGP peering for tests."""
    return BGPPeering(
        id=1,
        name="test-peering",
        local_asn=65000,
        peer_asn=65001,
        peer_ip="10.0.0.1",
        hold_time=180,
        keepalive=60,
        device="router01",
        interface="eth0",
        status=PeeringStatus.ACTIVE.value,
        address_families=["ipv4"],
        routing_policy={},
    )


@pytest.fixture
def sample_peerings_list():
    """Create list of sample peerings for tests."""
    return [
        BGPPeering(
            id=1,
            name="peering-1",
            local_asn=65000,
            peer_asn=65001,
            peer_ip="10.0.0.1",
            hold_time=180,
            keepalive=60,
            device="router01",
            status=PeeringStatus.ACTIVE.value,
            address_families=["ipv4"],
            routing_policy={},
        ),
        BGPPeering(
            id=2,
            name="peering-2",
            local_asn=65000,
            peer_asn=65002,
            peer_ip="10.0.0.2",
            hold_time=180,
            keepalive=60,
            device="router02",
            status=PeeringStatus.ACTIVE.value,
            address_families=["ipv4"],
            routing_policy={},
        ),
    ]


class TestASNCollisionRule:
    """Tests for ASNCollisionRule."""

    @pytest.mark.asyncio
    async def test_no_collision(self, sample_peering, sample_peerings_list):
        """Test when no ASN collision exists."""
        rule = ASNCollisionRule()
        result = await rule.check(sample_peering, sample_peerings_list)
        assert result is None

    @pytest.mark.asyncio
    async def test_asn_collision_detected(self, sample_peering):
        """Test ASN collision detection."""
        rule = ASNCollisionRule()
        # Create peerings with same ASN but different IPs
        conflicting_peerings = [
            BGPPeering(
                id=2,
                name="conflicting-peering",
                local_asn=65000,
                peer_asn=sample_peering.peer_asn,  # Same ASN
                peer_ip="10.0.0.2",  # Different IP
                hold_time=180,
                keepalive=60,
                device="router02",
                status=PeeringStatus.ACTIVE.value,
                address_families=["ipv4"],
                routing_policy={},
            )
        ]

        result = await rule.check(sample_peering, conflicting_peerings)
        assert result is not None
        assert result.type == ConflictType.ASN_COLLISION
        assert result.severity == ConflictSeverity.HIGH
        assert sample_peering.id in result.affected_peers
        assert 2 in result.affected_peers

    @pytest.mark.asyncio
    async def test_no_collision_with_pending_status(self, sample_peering):
        """Test that pending peerings don't cause collisions."""
        rule = ASNCollisionRule()
        conflicting_peerings = [
            BGPPeering(
                id=2,
                name="pending-peering",
                local_asn=65000,
                peer_asn=sample_peering.peer_asn,
                peer_ip="10.0.0.2",
                hold_time=180,
                keepalive=60,
                device="router02",
                status=PeeringStatus.PENDING.value,  # Not active
                address_families=["ipv4"],
                routing_policy={},
            )
        ]

        result = await rule.check(sample_peering, conflicting_peerings)
        assert result is None


class TestRPKIValidationRule:
    """Tests for RPKIValidationRule."""

    @pytest.mark.asyncio
    async def test_private_asn_skipped(self, sample_peering, sample_peerings_list):
        """Test that private ASNs skip RPKI validation."""
        rule = RPKIValidationRule()
        # Use private ASN
        sample_peering.peer_asn = 64512  # Private ASN range
        result = await rule.check(sample_peering, sample_peerings_list)
        assert result is None

    @pytest.mark.asyncio
    async def test_public_asn_validation(self, sample_peering, sample_peerings_list):
        """Test RPKI validation for public ASNs (placeholder)."""
        rule = RPKIValidationRule()
        sample_peering.peer_asn = 15169  # Google ASN
        result = await rule.check(sample_peering, sample_peerings_list)
        # Currently returns None (placeholder implementation)
        assert result is None


class TestSessionOverlapRule:
    """Tests for SessionOverlapRule."""

    @pytest.mark.asyncio
    async def test_no_overlap(self, sample_peering, sample_peerings_list):
        """Test when no session overlap exists."""
        rule = SessionOverlapRule()
        result = await rule.check(sample_peering, sample_peerings_list)
        assert result is None

    @pytest.mark.asyncio
    async def test_overlap_detected(self, sample_peering):
        """Test session overlap detection."""
        rule = SessionOverlapRule()
        # Create overlapping peering (same device, IP, ASN)
        overlapping_peerings = [
            BGPPeering(
                id=2,
                name="overlapping-peering",
                local_asn=sample_peering.local_asn,
                peer_asn=sample_peering.peer_asn,
                peer_ip=sample_peering.peer_ip,  # Same IP
                hold_time=180,
                keepalive=60,
                device=sample_peering.device,  # Same device
                status=PeeringStatus.ACTIVE.value,
                address_families=["ipv4"],
                routing_policy={},
            )
        ]

        result = await rule.check(sample_peering, overlapping_peerings)
        assert result is not None
        assert result.type == ConflictType.SESSION_OVERLAP
        assert result.severity == ConflictSeverity.CRITICAL
        assert sample_peering.id in result.affected_peers

    @pytest.mark.asyncio
    async def test_ipv6_overlap(self):
        """Test IPv6 address overlap detection."""
        rule = SessionOverlapRule()
        peering1 = BGPPeering(
            id=1,
            name="ipv6-peering-1",
            local_asn=65000,
            peer_asn=65001,
            peer_ip="2001:db8::1",  # IPv6
            hold_time=180,
            keepalive=60,
            device="router01",
            status=PeeringStatus.ACTIVE.value,
            address_families=["ipv6"],
            routing_policy={},
        )
        peering2 = BGPPeering(
            id=2,
            name="ipv6-peering-2",
            local_asn=65000,
            peer_asn=65001,
            peer_ip="2001:db8::1",  # Same IPv6
            hold_time=180,
            keepalive=60,
            device="router01",  # Same device
            status=PeeringStatus.ACTIVE.value,
            address_families=["ipv6"],
            routing_policy={},
        )

        result = await rule.check(peering1, [peering2])
        assert result is not None
        assert result.type == ConflictType.SESSION_OVERLAP


class TestRoutingLoopRule:
    """Tests for RoutingLoopRule."""

    @pytest.mark.asyncio
    async def test_no_loop(self, sample_peering, sample_peerings_list):
        """Test when no routing loop exists."""
        rule = RoutingLoopRule()
        result = await rule.check(sample_peering, sample_peerings_list)
        assert result is None

    @pytest.mark.asyncio
    async def test_routing_loop_detected(self, sample_peering):
        """Test routing loop detection."""
        rule = RoutingLoopRule()
        # Set routing policy with local ASN in import path
        sample_peering.routing_policy = {
            "import": {
                "as_path": [65000, 65001, 65000],  # Loop detected
            }
        }

        result = await rule.check(sample_peering, [])
        assert result is not None
        assert result.type == ConflictType.ROUTING_LOOP
        assert result.severity == ConflictSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_no_loop_with_valid_path(self, sample_peering):
        """Test that valid AS paths don't cause loops."""
        rule = RoutingLoopRule()
        sample_peering.routing_policy = {
            "import": {
                "as_path": [65001, 65002],  # No loop
            }
        }

        result = await rule.check(sample_peering, [])
        assert result is None

    @pytest.mark.asyncio
    async def test_no_loop_without_import_policy(self, sample_peering):
        """Test that missing import policy doesn't cause issues."""
        rule = RoutingLoopRule()
        sample_peering.routing_policy = {}

        result = await rule.check(sample_peering, [])
        assert result is None


class TestBGPConflictDetector:
    """Tests for BGPConflictDetector orchestrator."""

    @pytest.mark.asyncio
    async def test_detect_conflicts_no_conflicts(self, sample_peering, sample_peerings_list):
        """Test conflict detection when no conflicts exist."""
        detector = BGPConflictDetector()
        conflicts = await detector.detect_conflicts(sample_peering, sample_peerings_list)
        assert len(conflicts) == 0

    @pytest.mark.asyncio
    async def test_detect_conflicts_with_overlap(self, sample_peering):
        """Test conflict detection with session overlap."""
        detector = BGPConflictDetector()
        overlapping_peerings = [
            BGPPeering(
                id=2,
                name="overlapping",
                local_asn=sample_peering.local_asn,
                peer_asn=sample_peering.peer_asn,
                peer_ip=sample_peering.peer_ip,
                hold_time=180,
                keepalive=60,
                device=sample_peering.device,
                status=PeeringStatus.ACTIVE.value,
                address_families=["ipv4"],
                routing_policy={},
            )
        ]

        conflicts = await detector.detect_conflicts(sample_peering, overlapping_peerings)
        assert len(conflicts) > 0
        assert any(c.type == ConflictType.SESSION_OVERLAP for c in conflicts)

    @pytest.mark.asyncio
    async def test_detect_conflicts_multiple_rules(self, sample_peering):
        """Test that multiple rules can detect conflicts."""
        detector = BGPConflictDetector()
        # Create peering with both overlap and routing loop
        sample_peering.routing_policy = {
            "import": {
                "as_path": [sample_peering.local_asn, 65001],
            }
        }
        overlapping_peerings = [
            BGPPeering(
                id=2,
                name="overlapping",
                local_asn=sample_peering.local_asn,
                peer_asn=sample_peering.peer_asn,
                peer_ip=sample_peering.peer_ip,
                hold_time=180,
                keepalive=60,
                device=sample_peering.device,
                status=PeeringStatus.ACTIVE.value,
                address_families=["ipv4"],
                routing_policy={},
            )
        ]

        conflicts = await detector.detect_conflicts(sample_peering, overlapping_peerings)
        assert len(conflicts) >= 2  # Should detect both overlap and loop

    @pytest.mark.asyncio
    async def test_detect_conflicts_with_rule_failure(self, sample_peering, sample_peerings_list):
        """Test that rule failures don't crash the detector."""
        detector = BGPConflictDetector()

        # Add a rule that will fail
        failing_rule = MagicMock(spec=ConflictRule)
        failing_rule.check = AsyncMock(side_effect=Exception("Rule failed"))
        failing_rule.rule_name = "FailingRule"
        detector.add_rule(failing_rule)

        # Should still work with other rules
        conflicts = await detector.detect_conflicts(sample_peering, sample_peerings_list)
        # Should not crash, may or may not have conflicts from other rules
        assert isinstance(conflicts, list)

    @pytest.mark.asyncio
    async def test_add_remove_rules(self):
        """Test adding and removing rules."""
        detector = BGPConflictDetector()
        initial_rule_count = len(detector.rules)

        # Add custom rule
        custom_rule = MagicMock(spec=ConflictRule)
        custom_rule.rule_name = "CustomRule"
        detector.add_rule(custom_rule)
        assert len(detector.rules) == initial_rule_count + 1

        # Remove rule
        detector.remove_rule("CustomRule")
        assert len(detector.rules) == initial_rule_count

    @pytest.mark.asyncio
    async def test_four_byte_asn(self):
        """Test with 4-byte ASN (ASN > 65535)."""
        detector = BGPConflictDetector()
        peering = BGPPeering(
            id=1,
            name="4byte-asn-peering",
            local_asn=4200000000,  # 4-byte ASN
            peer_asn=4200000001,
            peer_ip="10.0.0.1",
            hold_time=180,
            keepalive=60,
            device="router01",
            status=PeeringStatus.ACTIVE.value,
            address_families=["ipv4"],
            routing_policy={},
        )

        conflicts = await detector.detect_conflicts(peering, [])
        assert isinstance(conflicts, list)


class TestConflictDataClass:
    """Tests for Conflict dataclass."""

    def test_conflict_creation(self):
        """Test creating a Conflict object."""
        conflict = Conflict(
            type=ConflictType.ASN_COLLISION,
            severity=ConflictSeverity.HIGH,
            description="Test conflict",
            affected_peers=[1, 2],
            recommended_action="Fix it",
            metadata={"key": "value"},
        )
        assert conflict.type == ConflictType.ASN_COLLISION
        assert conflict.severity == ConflictSeverity.HIGH
        assert conflict.description == "Test conflict"
        assert conflict.affected_peers == [1, 2]
        assert conflict.metadata == {"key": "value"}

    def test_conflict_repr(self):
        """Test Conflict string representation."""
        conflict = Conflict(
            type=ConflictType.SESSION_OVERLAP,
            severity=ConflictSeverity.CRITICAL,
            description="Test",
            affected_peers=[1],
            recommended_action="Remove duplicate",
        )
        repr_str = repr(conflict)
        assert "SESSION_OVERLAP" in repr_str
        assert "CRITICAL" in repr_str
        assert "[1]" in repr_str

