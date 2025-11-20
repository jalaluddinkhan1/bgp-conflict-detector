"""Security package."""
from .auth import (
    AzureADHandler,
    GoogleHandler,
    JWTManager,
    OktaHandler,
    OAuth2ProviderHandler,
    PasswordHash,
    User,
    UserRole,
    get_current_user,
    get_oauth2_handler,
    jwt_manager,
    require_role,
)
from .audit import (
    AuditAction,
    AuditLog,
    AuditLogger,
    audit_logger,
    log_audit_event,
    verify_audit_log_integrity,
)
from .encryption import (
    AWSKMSIntegration,
    AzureKeyVaultIntegration,
    CloudKMSIntegration,
    EncryptionKeyManager,
    EncryptionService,
    decrypt_peer_config,
    encrypt_peer_config,
    get_encryption_service,
)

__all__ = [
    # Auth
    "User",
    "UserRole",
    "JWTManager",
    "PasswordHash",
    "OAuth2ProviderHandler",
    "AzureADHandler",
    "GoogleHandler",
    "OktaHandler",
    "get_current_user",
    "get_oauth2_handler",
    "require_role",
    "jwt_manager",
    # Encryption
    "EncryptionService",
    "EncryptionKeyManager",
    "encrypt_peer_config",
    "decrypt_peer_config",
    "get_encryption_service",
    "CloudKMSIntegration",
    "AzureKeyVaultIntegration",
    "AWSKMSIntegration",
    # Audit
    "AuditLog",
    "AuditAction",
    "AuditLogger",
    "audit_logger",
    "log_audit_event",
    "verify_audit_log_integrity",
]

