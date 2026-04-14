#!/usr/bin/env python3
"""
Polymorphic Encoding Module
Variable name obfuscation and XOR encoding for red team testing

⚠️ LAB SANDBOX USE ONLY ⚠️
"""

import random
import string
import base64
from typing import Dict, Any, List, Optional
from colorama import Fore, Style

class PolymorphicEncoder:
    """Polymorphic encoding for payload obfuscation"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('polymorphic_encoding', {}).get('enabled', False)
        self.variable_name_pool = []
        self._generate_variable_pool()
    
    def _generate_variable_pool(self, size: int = 100):
        """Generate pool of random variable names"""
        # Generate random variable names
        for _ in range(size):
            # Random length between 5-15 characters
            length = random.randint(5, 15)
            var_name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))
            self.variable_name_pool.append(var_name)
    
    def generate_random_variable_name(self) -> str:
        """Get random variable name from pool"""
        return random.choice(self.variable_name_pool)
    
    def obfuscate_variable_names(self, code: str) -> str:
        """
        Obfuscate variable names in code
        
        Args:
            code: Source code string
        
        Returns:
            Code with obfuscated variable names
        """
        if not self.enabled:
            return code
        
        # Simple variable name obfuscation
        # In production, would use AST parsing for better results
        import re
        
        # Find common variable patterns
        variable_patterns = [
            r'\b(var|let|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b',  # JavaScript
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=',  # Python/General
            r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # Python functions
            r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)',  # Classes
        ]
        
        obfuscated_code = code
        variable_map = {}
        
        for pattern in variable_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                var_name = match.group(1) if match.groups() else match.group(0)
                if var_name not in variable_map and var_name not in ['def', 'class', 'var', 'let', 'const']:
                    new_name = self.generate_random_variable_name()
                    variable_map[var_name] = new_name
        
        # Replace variable names
        for old_name, new_name in variable_map.items():
            # Use word boundaries to avoid partial matches
            obfuscated_code = re.sub(r'\b' + re.escape(old_name) + r'\b', new_name, obfuscated_code)
        
        return obfuscated_code
    
    def xor_encode(self, data: bytes, key: Optional[bytes] = None) -> bytes:
        """
        XOR encode data
        
        Args:
            data: Data bytes to encode
            key: XOR key (generates random if not provided)
        
        Returns:
            XOR encoded data
        """
        if not self.enabled:
            return data
        
        if key is None:
            # Generate random key
            key_length = min(len(data), 32)  # Max 32 bytes
            key = bytes([random.randint(0, 255) for _ in range(key_length)])
        
        # XOR encode
        encoded = bytearray()
        key_len = len(key)
        
        for i, byte in enumerate(data):
            encoded.append(byte ^ key[i % key_len])
        
        return bytes(encoded), key
    
    def xor_decode(self, encoded_data: bytes, key: bytes) -> bytes:
        """
        XOR decode data
        
        Args:
            encoded_data: XOR encoded data
            key: XOR key
        
        Returns:
            Decoded data bytes
        """
        decoded = bytearray()
        key_len = len(key)
        
        for i, byte in enumerate(encoded_data):
            decoded.append(byte ^ key[i % key_len])
        
        return bytes(decoded)
    
    def base64_encode(self, data: bytes) -> str:
        """Base64 encode data"""
        return base64.b64encode(data).decode('utf-8')
    
    def base64_decode(self, encoded: str) -> bytes:
        """Base64 decode data"""
        return base64.b64decode(encoded)
    
    def polymorphic_encode_payload(self, payload: bytes, method: str = 'xor') -> Dict[str, Any]:
        """
        Apply polymorphic encoding to payload
        
        Args:
            payload: Raw payload bytes
            method: Encoding method ('xor', 'base64', 'combined')
        
        Returns:
            Dictionary with encoded payload and metadata
        """
        if not self.enabled:
            return {
                'encoded': base64.b64encode(payload).decode('utf-8'),
                'method': 'none',
                'key': None
            }
        
        result = {
            'original_size': len(payload),
            'method': method
        }
        
        if method == 'xor':
            encoded_result = self.xor_encode(payload)
            if isinstance(encoded_result, tuple):
                encoded, key = encoded_result
            else:
                encoded, key = encoded_result, None
            result['encoded'] = base64.b64encode(encoded).decode('utf-8')
            if key:
                result['key'] = base64.b64encode(key).decode('utf-8')
                result['key_length'] = len(key)
            else:
                result['key'] = None
        
        elif method == 'base64':
            result['encoded'] = self.base64_encode(payload)
            result['key'] = None
        
        elif method == 'combined':
            # XOR then base64
            encoded_result = self.xor_encode(payload)
            if isinstance(encoded_result, tuple):
                encoded, key = encoded_result
            else:
                encoded, key = encoded_result, None
            result['encoded'] = self.base64_encode(encoded)
            if key:
                result['key'] = base64.b64encode(key).decode('utf-8')
                result['key_length'] = len(key)
            else:
                result['key'] = None
        
        result['encoded_size'] = len(result['encoded'])
        
        return result
    
    def polymorphic_decode_payload(self, encoded_data: str, method: str, key: Optional[str] = None) -> bytes:
        """
        Decode polymorphically encoded payload
        
        Args:
            encoded_data: Encoded payload string
            method: Encoding method used
            key: Decryption key (if needed)
        
        Returns:
            Decoded payload bytes
        """
        if method == 'xor' or method == 'combined':
            if not key:
                raise ValueError("Key required for XOR decoding")
            
            key_bytes = base64.b64decode(key)
            
            if method == 'combined':
                # Base64 decode first
                xor_encoded = self.base64_decode(encoded_data)
                return self.xor_decode(xor_encoded, key_bytes)
            else:
                xor_encoded = self.base64_decode(encoded_data)
                return self.xor_decode(xor_encoded, key_bytes)
        
        elif method == 'base64':
            return self.base64_decode(encoded_data)
        
        else:
            raise ValueError(f"Unknown encoding method: {method}")
    
    def generate_obfuscated_stub(self, payload_data: Dict[str, Any], output_file: str = "obfuscated_stub.py"):
        """
        Generate obfuscated stub code
        
        Args:
            payload_data: Encoded payload data dictionary
            output_file: Output file path
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] Polymorphic encoding disabled{Style.RESET_ALL}")
            return
        
        # Generate obfuscated variable names
        var_encoded = self.generate_random_variable_name()
        var_key = self.generate_random_variable_name()
        var_data = self.generate_random_variable_name()
        var_result = self.generate_random_variable_name()
        
        stub_code = f'''#!/usr/bin/env python3
"""
Polymorphic Encoded Stub - LAB SANDBOX USE ONLY
⚠️ AUTHORIZED SECURITY TESTING ONLY ⚠️
"""

import base64

# Obfuscated variable names
{var_encoded} = "{payload_data['encoded']}"
{var_key} = "{payload_data.get('key', '')}"
{var_data} = base64.b64decode({var_encoded})

# XOR decode if needed
if {var_key}:
    {var_key}_bytes = base64.b64decode({var_key})
    {var_result} = bytearray()
    for i, byte in enumerate({var_data}):
        {var_result}.append(byte ^ {var_key}_bytes[i % len({var_key}_bytes)])
    {var_data} = bytes({var_result})

# Decoded payload ready
# In real scenario: exec({var_data}) or similar
payload = {var_data}
print("Payload decoded successfully")
'''
        
        # Obfuscate the stub code itself
        obfuscated_stub = self.obfuscate_variable_names(stub_code)
        
        with open(output_file, 'w') as f:
            f.write(obfuscated_stub)
        
        print(f"{Fore.GREEN}[+] Obfuscated stub generated: {output_file}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")

