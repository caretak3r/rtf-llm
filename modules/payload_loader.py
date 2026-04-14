#!/usr/bin/env python3
"""
Payload Loader Module
AES-encrypted payload loading and decoding for red team testing

⚠️ LAB SANDBOX USE ONLY ⚠️
"""

import base64
import os
from typing import Optional, Dict, Any
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad
from colorama import Fore, Style

class PayloadLoader:
    """Payload loader with AES encryption/decryption"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('payload_loader', {}).get('enabled', False)
        self.key = None
        self._load_or_generate_key()
    
    def _load_or_generate_key(self):
        """Load encryption key from config or generate new one"""
        key_config = self.config.get('payload_loader', {}).get('encryption_key')
        
        if key_config:
            # Decode from base64 if stored as string
            if isinstance(key_config, str):
                self.key = base64.b64decode(key_config)
            else:
                self.key = key_config
        else:
            # Generate new 32-byte key for AES-256
            self.key = get_random_bytes(32)
            print(f"{Fore.YELLOW}[!] Generated new encryption key{Style.RESET_ALL}")
    
    def encrypt_payload(self, payload: bytes, key: Optional[bytes] = None) -> Dict[str, str]:
        """
        Encrypt payload using AES-256-CBC
        
        Args:
            payload: Raw payload bytes to encrypt
            key: Encryption key (uses instance key if not provided)
        
        Returns:
            Dictionary with encrypted data, IV, and key (base64 encoded)
        """
        if not self.enabled:
            raise RuntimeError("Payload loader is disabled in configuration")
        
        encryption_key = key or self.key
        
        # Generate random IV
        iv = get_random_bytes(16)
        
        # Create cipher
        cipher = AES.new(encryption_key, AES.MODE_CBC, iv)
        
        # Pad and encrypt
        padded_payload = pad(payload, AES.block_size)
        ciphertext = cipher.encrypt(padded_payload)
        
        return {
            'encrypted_data': base64.b64encode(ciphertext).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'key': base64.b64encode(encryption_key).decode('utf-8')
        }
    
    def decrypt_payload(self, encrypted_data: str, iv: str, key: Optional[bytes] = None) -> bytes:
        """
        Decrypt payload using AES-256-CBC
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            iv: Base64-encoded initialization vector
            key: Decryption key (uses instance key if not provided)
        
        Returns:
            Decrypted payload bytes
        """
        if not self.enabled:
            raise RuntimeError("Payload loader is disabled in configuration")
        
        decryption_key = key or self.key
        
        # Decode from base64
        ciphertext = base64.b64decode(encrypted_data)
        iv_bytes = base64.b64decode(iv)
        
        # Create cipher and decrypt
        cipher = AES.new(decryption_key, AES.MODE_CBC, iv_bytes)
        padded_plaintext = cipher.decrypt(ciphertext)
        
        # Unpad
        plaintext = unpad(padded_plaintext, AES.block_size)
        
        return plaintext
    
    def load_encrypted_payload(self, file_path: str) -> bytes:
        """
        Load and decrypt payload from file
        
        Args:
            file_path: Path to encrypted payload file
        
        Returns:
            Decrypted payload bytes
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Payload file not found: {file_path}")
        
        # Read encrypted payload (format: JSON with encrypted_data, iv, key)
        import json
        with open(file_path, 'r') as f:
            payload_data = json.load(f)
        
        encrypted_data = payload_data['encrypted_data']
        iv = payload_data['iv']
        key_b64 = payload_data.get('key')
        
        # Use provided key or instance key
        key = base64.b64decode(key_b64) if key_b64 else None
        
        return self.decrypt_payload(encrypted_data, iv, key)
    
    def save_encrypted_payload(self, payload: bytes, output_path: str) -> Dict[str, str]:
        """
        Encrypt and save payload to file
        
        Args:
            payload: Raw payload bytes
            output_path: Path to save encrypted payload
        
        Returns:
            Dictionary with encryption metadata
        """
        encrypted = self.encrypt_payload(payload)
        
        # Save to file
        import json
        with open(output_path, 'w') as f:
            json.dump(encrypted, f, indent=2)
        
        print(f"{Fore.GREEN}[+] Encrypted payload saved to: {output_path}{Style.RESET_ALL}")
        return encrypted
    
    def create_stub_loader(self, payload_path: str, output_path: str = "loader_stub.py"):
        """
        Create a stub loader script that decrypts and executes payload
        
        Args:
            payload_path: Path to encrypted payload
            output_path: Path to save loader stub
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] Payload loader disabled - stub not created{Style.RESET_ALL}")
            return
        
        # Read encrypted payload to get metadata
        import json
        with open(payload_path, 'r') as f:
            payload_data = json.load(f)
        
        key_b64 = payload_data['key']
        iv_b64 = payload_data['iv']
        encrypted_b64 = payload_data['encrypted_data']
        
        # Generate loader stub
        stub_code = f'''#!/usr/bin/env python3
"""
Payload Loader Stub - LAB SANDBOX USE ONLY
⚠️ AUTHORIZED SECURITY TESTING ONLY ⚠️
"""

import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# Encrypted payload data
ENCRYPTED_PAYLOAD = "{encrypted_b64}"
IV = "{iv_b64}"
KEY = "{key_b64}"

def decrypt_and_load():
    """Decrypt and load payload"""
    try:
        # Decode from base64
        ciphertext = base64.b64decode(ENCRYPTED_PAYLOAD)
        iv = base64.b64decode(IV)
        key = base64.b64decode(KEY)
        
        # Decrypt
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_plaintext = cipher.decrypt(ciphertext)
        payload = unpad(padded_plaintext, AES.block_size)
        
        # Execute payload (in real scenario, this would be more sophisticated)
        # For testing purposes, we'll just return the decrypted data
        return payload
        
    except Exception as e:
        print(f"Decryption error: {{e}}")
        return None

if __name__ == '__main__':
    # LAB SANDBOX USE ONLY
    payload = decrypt_and_load()
    if payload:
        print("Payload decrypted successfully")
        # In real scenario: exec(payload) or similar
'''
        
        with open(output_path, 'w') as f:
            f.write(stub_code)
        
        # Make executable on Unix systems
        try:
            os.chmod(output_path, 0o755)
        except:
            pass
        
        print(f"{Fore.GREEN}[+] Loader stub created: {output_path}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")

