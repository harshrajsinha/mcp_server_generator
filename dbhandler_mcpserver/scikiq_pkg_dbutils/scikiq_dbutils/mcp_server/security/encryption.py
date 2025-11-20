"""
Credential Encryption Manager

Provides secure encryption and decryption of database credentials using Fernet symmetric encryption.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import logging
from typing import Dict, Any, Optional


class CredentialManager:
    """
    Manages encryption and decryption of database credentials
    
    Uses Fernet symmetric encryption with PBKDF2 key derivation for secure credential storage.
    """
    
    def __init__(self, master_password: Optional[str] = None):
        """
        Initialize the credential manager
        
        Args:
            master_password: Master password for encryption. If None, uses environment variable.
        """
        self.logger = logging.getLogger(__name__)
        self.master_password = master_password or os.getenv("DBHANDLER_MASTER_PASSWORD", "change-me-in-production")
        
        if self.master_password == "change-me-in-production":
            self.logger.warning("Using default master password. Change DBHANDLER_MASTER_PASSWORD for production!")
        
        self.key = self._derive_key(self.master_password)
        self.cipher = Fernet(self.key)
        
    def _derive_key(self, password: str) -> bytes:
        """
        Derive encryption key from password using PBKDF2
        
        Args:
            password: Master password
            
        Returns:
            Derived key suitable for Fernet encryption
        """
        # Use a fixed salt for consistency (in production, store salt securely)
        salt = b'dbhandler_salt_2024_secure'
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def encrypt_password(self, password: str) -> str:
        """
        Encrypt a database password
        
        Args:
            password: Plain text password
            
        Returns:
            Base64 encoded encrypted password
        """
        try:
            encrypted_bytes = self.cipher.encrypt(password.encode())
            return base64.urlsafe_b64encode(encrypted_bytes).decode()
        except Exception as e:
            self.logger.error(f"Failed to encrypt password: {str(e)}")
            raise ValueError("Password encryption failed")
    
    def decrypt_password(self, encrypted_password: str) -> str:
        """
        Decrypt a database password
        
        Args:
            encrypted_password: Base64 encoded encrypted password
            
        Returns:
            Plain text password
        """
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_password.encode())
            decrypted_bytes = self.cipher.decrypt(encrypted_bytes)
            return decrypted_bytes.decode()
        except Exception as e:
            self.logger.error(f"Failed to decrypt password: {str(e)}")
            raise ValueError("Password decryption failed")
    
    def encrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in configuration
        
        Args:
            config: Database configuration dictionary
            
        Returns:
            Configuration with encrypted sensitive fields
        """
        encrypted_config = config.copy()
        
        # Encrypt password if present
        if "dbpassword" in encrypted_config:
            encrypted_config["dbpassword"] = self.encrypt_password(
                encrypted_config["dbpassword"]
            )
            encrypted_config["password_encrypted"] = 1
        
        # Encrypt SSH password if present
        if "ssh_password" in encrypted_config:
            encrypted_config["ssh_password"] = self.encrypt_password(
                encrypted_config["ssh_password"]
            )
        
        return encrypted_config
    
    def decrypt_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in configuration
        
        Args:
            config: Configuration with encrypted sensitive fields
            
        Returns:
            Configuration with decrypted plain text passwords
        """
        decrypted_config = config.copy()
        
        # Check if password is encrypted
        password_encrypted = config.get("password_encrypted", 0)
        
        if password_encrypted == 1 and "dbpassword" in decrypted_config:
            decrypted_config["dbpassword"] = self.decrypt_password(
                decrypted_config["dbpassword"]
            )
        
        # Decrypt SSH password if present and encrypted
        if password_encrypted == 1 and "ssh_password" in decrypted_config:
            decrypted_config["ssh_password"] = self.decrypt_password(
                decrypted_config["ssh_password"]
            )
        
        return decrypted_config
    
    def is_password_encrypted(self, password: str) -> bool:
        """
        Check if a password appears to be encrypted
        
        Args:
            password: Password string to check
            
        Returns:
            True if password appears to be encrypted
        """
        try:
            # Try to decode as base64
            base64.urlsafe_b64decode(password.encode())
            # If successful, likely encrypted (not foolproof but good heuristic)
            return len(password) > 20 and password.isalnum() or '-' in password or '_' in password
        except Exception:
            return False
    
    def generate_master_password(self, length: int = 32) -> str:
        """
        Generate a secure random master password
        
        Args:
            length: Length of the password to generate
            
        Returns:
            Cryptographically secure random password
        """
        return base64.urlsafe_b64encode(os.urandom(length)).decode()[:length]