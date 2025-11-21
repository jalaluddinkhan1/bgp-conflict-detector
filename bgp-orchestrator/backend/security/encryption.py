"""
Encryption module for sensitive data.
Supports Fernet encryption with key rotation and cloud KMS integration.
"""
import base64
import json
from datetime import datetime, timezone
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionKeyManager:
    """Manages encryption keys with rotation support."""

    def __init__(self, primary_key: bytes | None = None):
        """Initialize key manager."""
        if primary_key is None:
            # Generate a new key if none provided
            primary_key = Fernet.generate_key()
        self.primary_key = primary_key
        self.key_version = "v1"
        self.rotation_history: list[tuple[bytes, str]] = []

    def rotate_key(self) -> bytes:
        """Rotate to a new encryption key."""
        # Add old key to rotation history
        self.rotation_history.append((self.primary_key, self.key_version))
        # Generate new key
        self.primary_key = Fernet.generate_key()
        # Update version
        version_num = int(self.key_version.replace("v", "")) + 1
        self.key_version = f"v{version_num}"
        return self.primary_key

    def get_key_for_version(self, version: str) -> bytes | None:
        """Get encryption key for a specific version."""
        if version == self.key_version:
            return self.primary_key
        # Search in rotation history
        for key, key_version in self.rotation_history:
            if key_version == version:
                return key
        return None

    @staticmethod
    async def derive_key_from_password_async(password: str, redis_client: Any = None) -> bytes:
        """
        Derive a Fernet key from a password using PBKDF2 with dynamic salt from Redis.
        
        Args:
            password: Password to derive key from
            redis_client: Redis client instance (optional, will generate new salt if None)
        
        Returns:
            Derived encryption key
        """
        import secrets
        
        salt_key = "encryption_salt"
        salt: bytes | None = None
        
        # Try to get salt from Redis if available
        if redis_client:
            try:
                stored_salt = redis_client.get(salt_key)
                if stored_salt:
                    if isinstance(stored_salt, str):
                        salt = base64.b64decode(stored_salt)
                    else:
                        salt = stored_salt
            except Exception:
                pass  # Fall through to generate new salt
        
        # Generate new salt if not found
        if salt is None:
            salt = secrets.token_bytes(16)
            # Store in Redis if available
            if redis_client:
                try:
                    redis_client.set(salt_key, base64.b64encode(salt).decode("utf-8"))
                except Exception:
                    pass  # Continue even if Redis write fails
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
    
    @staticmethod
    def derive_key_from_password(password: str, salt: bytes | None = None) -> bytes:
        """
        Derive a Fernet key from a password using PBKDF2.
        
        WARNING: This method uses a static salt if none provided. 
        Use derive_key_from_password_async() for production with Redis-backed salt.
        """
        if salt is None:
            # Generate a random salt as fallback (not stored, so not ideal)
            import secrets
            salt = secrets.token_bytes(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key


class EncryptionService:
    """Service for encrypting and decrypting sensitive data."""

    def __init__(self, key_manager: EncryptionKeyManager | None = None):
        """Initialize encryption service."""
        if key_manager is None:
            key_manager = EncryptionKeyManager()
        self.key_manager = key_manager
        self.fernet = Fernet(self.key_manager.primary_key)

    def encrypt_data(self, data: dict[str, Any]) -> bytes:
        """
        Encrypt a dictionary of sensitive data.

        Returns:
            Encrypted bytes with metadata (version, timestamp)
        """
        # Serialize data to JSON
        json_data = json.dumps(data, default=str).encode("utf-8")

        # Encrypt the data
        encrypted = self.fernet.encrypt(json_data)

        # Create metadata
        metadata = {
            "version": self.key_manager.key_version,
            "encrypted_at": datetime.now(timezone.utc).isoformat(),
        }

        # Combine metadata and encrypted data
        result = {
            "metadata": metadata,
            "data": base64.b64encode(encrypted).decode("utf-8"),
        }

        return json.dumps(result).encode("utf-8")

    def decrypt_data(self, encrypted_bytes: bytes) -> dict[str, Any]:
        """
        Decrypt encrypted data.

        Args:
            encrypted_bytes: Encrypted data with metadata

        Returns:
            Decrypted dictionary

        Raises:
            ValueError: If decryption fails
        """
        try:
            # Parse the encrypted data structure
            encrypted_obj = json.loads(encrypted_bytes.decode("utf-8"))
            metadata = encrypted_obj.get("metadata", {})
            encrypted_data = base64.b64decode(encrypted_obj.get("data", ""))

            # Get the key version from metadata
            version = metadata.get("version", self.key_manager.key_version)

            # Get the appropriate key for this version
            key = self.key_manager.get_key_for_version(version)
            if key is None:
                raise ValueError(f"Cannot find key for version {version}")

            # Decrypt using the appropriate key
            fernet = Fernet(key)
            decrypted_bytes = fernet.decrypt(encrypted_data)

            # Deserialize JSON
            return json.loads(decrypted_bytes.decode("utf-8"))
        except (json.JSONDecodeError, InvalidToken, ValueError) as e:
            raise ValueError(f"Decryption failed: {str(e)}") from e


_encryption_service: EncryptionService | None = None


def get_encryption_service() -> EncryptionService:
    """Get the global encryption service instance."""
    global _encryption_service
    if _encryption_service is None:
        key_manager = EncryptionKeyManager()
        _encryption_service = EncryptionService(key_manager)
    return _encryption_service


def encrypt_peer_config(config: dict[str, Any]) -> bytes:
    """
    Encrypt BGP peer configuration data (passwords, SNMP communities, etc.).

    Args:
        config: Dictionary containing sensitive configuration data

    Returns:
        Encrypted bytes
    """
    service = get_encryption_service()
    return service.encrypt_data(config)


def decrypt_peer_config(encrypted_bytes: bytes) -> dict[str, Any]:
    """
    Decrypt BGP peer configuration data.

    Args:
        encrypted_bytes: Encrypted configuration data

    Returns:
        Decrypted configuration dictionary
    """
    service = get_encryption_service()
    return service.decrypt_data(encrypted_bytes)


class CloudKMSIntegration:
    """Base class for cloud KMS integration (Azure Key Vault, AWS KMS)."""

    def get_key(self, key_id: str) -> bytes:
        """Retrieve encryption key from cloud KMS."""
        raise NotImplementedError("Subclasses must implement get_key")

    def encrypt_with_kms(self, data: bytes, key_id: str) -> bytes:
        """Encrypt data using cloud KMS."""
        raise NotImplementedError("Subclasses must implement encrypt_with_kms")

    def decrypt_with_kms(self, encrypted_data: bytes, key_id: str) -> bytes:
        """Decrypt data using cloud KMS."""
        raise NotImplementedError("Subclasses must implement decrypt_with_kms")


class AzureKeyVaultIntegration(CloudKMSIntegration):
    """Azure Key Vault integration."""

    def __init__(self, vault_url: str, credential: Any):
        """Initialize Azure Key Vault client."""
        self.vault_url = vault_url
        self.credential = credential

    def get_key(self, key_id: str) -> bytes:
        """Retrieve key from Azure Key Vault."""
        raise NotImplementedError("Azure Key Vault integration not yet implemented")


class AWSKMSIntegration(CloudKMSIntegration):
    """AWS KMS integration."""

    def __init__(self, kms_client: Any):
        """Initialize AWS KMS client."""
        self.kms_client = kms_client

    def get_key(self, key_id: str) -> bytes:
        """Retrieve key from AWS KMS."""
        raise NotImplementedError("AWS KMS integration not yet implemented")

