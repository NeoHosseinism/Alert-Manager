"""
Encryption utilities using Fernet for API key encryption
"""
from cryptography.fernet import Fernet, InvalidToken
from core.exceptions import EncryptionException
from config import settings


class EncryptionService:
    """Service for encrypting and decrypting sensitive data"""

    def __init__(self, encryption_key: str):
        """
        Initialize encryption service

        Args:
            encryption_key: Base64-encoded Fernet key

        Raises:
            EncryptionException: If key is invalid
        """
        try:
            self._fernet = Fernet(encryption_key.encode())
        except Exception as e:
            raise EncryptionException(f"Invalid encryption key: {e}")

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext string

        Args:
            plaintext: String to encrypt

        Returns:
            Base64-encoded encrypted string

        Raises:
            EncryptionException: If encryption fails
        """
        if not plaintext:
            raise EncryptionException("Cannot encrypt empty string")

        try:
            encrypted_bytes = self._fernet.encrypt(plaintext.encode())
            return encrypted_bytes.decode()
        except Exception as e:
            raise EncryptionException(f"Encryption failed: {e}")

    def decrypt(self, encrypted: str) -> str:
        """
        Decrypt encrypted string

        Args:
            encrypted: Base64-encoded encrypted string

        Returns:
            Decrypted plaintext string

        Raises:
            EncryptionException: If decryption fails
        """
        if not encrypted:
            raise EncryptionException("Cannot decrypt empty string")

        try:
            decrypted_bytes = self._fernet.decrypt(encrypted.encode())
            return decrypted_bytes.decode()
        except InvalidToken:
            raise EncryptionException("Invalid token or corrupted data")
        except Exception as e:
            raise EncryptionException(f"Decryption failed: {e}")


# Global encryption service instance
_encryption_service: EncryptionService = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service instance"""
    global _encryption_service
    if _encryption_service is None:
        _encryption_service = EncryptionService(settings.encryption_key)
    return _encryption_service


def encrypt_api_key(api_key: str) -> str:
    """
    Encrypt an API key

    Args:
        api_key: Plaintext API key

    Returns:
        Encrypted API key
    """
    return get_encryption_service().encrypt(api_key)


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key

    Args:
        encrypted_key: Encrypted API key

    Returns:
        Plaintext API key
    """
    return get_encryption_service().decrypt(encrypted_key)


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key

    Returns:
        Base64-encoded Fernet key
    """
    return Fernet.generate_key().decode()
