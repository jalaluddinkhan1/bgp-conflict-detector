"""
Audit logging module with append-only audit trail and HMAC signatures.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.ext.declarative import declarative_base

from app.config import settings
from models.peering import Base as ModelBase


class AuditAction(str, Enum):
    """Audit action types."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    READ = "read"  # For sensitive data access


class AuditLog(ModelBase):
    """Append-only audit log table."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True, comment="User who performed the action")
    timestamp = Column(DateTime(timezone=True), nullable=False, default=func.now(), index=True)
    action = Column(String(50), nullable=False, index=True, comment="Action type (create/update/delete)")
    table_name = Column(String(255), nullable=False, index=True, comment="Table/entity name")
    record_id = Column(Integer, nullable=False, index=True, comment="ID of the affected record")
    old_values = Column(JSON, nullable=True, comment="Previous values (for updates)")
    new_values = Column(JSON, nullable=True, comment="New values")
    ip_address = Column(String(45), nullable=True, comment="Client IP address")
    user_agent = Column(String(500), nullable=True, comment="Client user agent")
    request_id = Column(String(36), nullable=True, index=True, comment="Request ID for correlation")
    hmac_signature = Column(Text, nullable=False, comment="HMAC signature for tamper detection")

    def __repr__(self) -> str:
        """String representation."""
        return f"<AuditLog(id={self.id}, action={self.action}, table={self.table_name}, record_id={self.record_id})>"


class AuditLogger:
    """Audit logging service with HMAC signing."""

    def __init__(self, secret_key: str | None = None):
        """Initialize audit logger."""
        self.secret_key = secret_key or settings.SECRET_KEY.encode("utf-8")

    def _generate_hmac(self, log_data: dict[str, Any]) -> str:
        """
        Generate HMAC signature for audit log entry.

        Args:
            log_data: Dictionary containing log data (excluding signature)

        Returns:
            HMAC signature as hex string
        """
        # Create a deterministic string from log data
        # Exclude timestamp and id for signature calculation
        signature_data = {
            "user_id": log_data.get("user_id"),
            "action": log_data.get("action"),
            "table_name": log_data.get("table_name"),
            "record_id": log_data.get("record_id"),
            "old_values": json.dumps(log_data.get("old_values"), sort_keys=True) if log_data.get("old_values") else None,
            "new_values": json.dumps(log_data.get("new_values"), sort_keys=True) if log_data.get("new_values") else None,
        }

        # Create canonical JSON string
        canonical_json = json.dumps(signature_data, sort_keys=True, separators=(",", ":"))

        # Generate HMAC
        signature = hmac.new(
            self.secret_key,
            canonical_json.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return signature

    def create_audit_entry(
        self,
        user_id: str,
        action: AuditAction,
        table_name: str,
        record_id: int,
        old_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Create an audit log entry with HMAC signature.

        Args:
            user_id: User who performed the action
            action: Action type
            table_name: Table/entity name
            record_id: ID of affected record
            old_values: Previous values (for updates)
            new_values: New values
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request ID for correlation

        Returns:
            Dictionary ready to be inserted into audit log
        """
        log_entry = {
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc),
            "action": action.value,
            "table_name": table_name,
            "record_id": record_id,
            "old_values": old_values,
            "new_values": new_values,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "request_id": request_id,
        }

        # Generate HMAC signature
        signature = self._generate_hmac(log_entry)
        log_entry["hmac_signature"] = signature

        return log_entry

    def verify_signature(self, log_entry: AuditLog) -> bool:
        """
        Verify HMAC signature of an audit log entry.

        Args:
            log_entry: AuditLog database record

        Returns:
            True if signature is valid, False otherwise
        """
        # Reconstruct log data dictionary
        log_data = {
            "user_id": log_entry.user_id,
            "action": log_entry.action,
            "table_name": log_entry.table_name,
            "record_id": log_entry.record_id,
            "old_values": log_entry.old_values,
            "new_values": log_entry.new_values,
        }

        # Generate expected signature
        expected_signature = self._generate_hmac(log_data)

        # Compare signatures (use constant-time comparison)
        return hmac.compare_digest(expected_signature, log_entry.hmac_signature)


# Global audit logger instance
audit_logger = AuditLogger()


async def log_audit_event(
    db_session: Any,
    user_id: str,
    action: AuditAction,
    table_name: str,
    record_id: int,
    old_values: dict[str, Any] | None = None,
    new_values: dict[str, Any] | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    request_id: str | None = None,
) -> AuditLog:
    """
    Log an audit event to the database.

    Args:
        db_session: SQLAlchemy database session
        user_id: User who performed the action
        action: Action type
        table_name: Table/entity name
        record_id: ID of affected record
        old_values: Previous values
        new_values: New values
        ip_address: Client IP address
        user_agent: Client user agent
        request_id: Request ID

    Returns:
        Created AuditLog record
    """
    log_entry_dict = audit_logger.create_audit_entry(
        user_id=user_id,
        action=action,
        table_name=table_name,
        record_id=record_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )

    audit_log = AuditLog(**log_entry_dict)
    db_session.add(audit_log)
    db_session.commit()
    db_session.refresh(audit_log)

    return audit_log


def verify_audit_log_integrity(db_session: Any, log_id: int) -> bool:
    """
    Verify the integrity of a specific audit log entry.

    Args:
        db_session: SQLAlchemy database session
        log_id: Audit log ID

    Returns:
        True if signature is valid, False otherwise
    """
    log_entry = db_session.query(AuditLog).filter(AuditLog.id == log_id).first()
    if log_entry is None:
        return False

    return audit_logger.verify_signature(log_entry)

