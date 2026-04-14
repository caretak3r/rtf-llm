#!/usr/bin/env python3
"""
Data Exfiltration Module
Keylogger and screenshot simulation for red team testing

⚠️ LAB SANDBOX USE ONLY ⚠️
⚠️ USER WARNING REQUIRED ⚠️
"""

import time
import json
import base64
import platform
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from colorama import Fore, Style

class DataExfiltrationModule:
    """Data exfiltration capabilities for red team testing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('data_exfiltration', {}).get('enabled', False)
        self.keylogger_enabled = config.get('data_exfiltration', {}).get('keylogger', False)
        self.screenshot_enabled = config.get('data_exfiltration', {}).get('screenshot', False)
        self.file_exfiltration_enabled = config.get('data_exfiltration', {}).get('file_exfiltration', False)
        self.warning_shown = False
        
        if self.enabled:
            self._show_warning()
    
    def _show_warning(self):
        """Show warning about data exfiltration capabilities"""
        if not self.warning_shown:
            print(f"\n{Fore.RED}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.RED}⚠️  WARNING: DATA EXFILTRATION CAPABILITIES ⚠️{Style.RESET_ALL}")
            print(f"{Fore.RED}{'='*80}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}This module simulates data exfiltration capabilities including:{Style.RESET_ALL}")
            print(f"  - Keylogger simulation")
            print(f"  - Screenshot capture simulation")
            print(f"  - File exfiltration simulation")
            print(f"\n{Fore.RED}LAB SANDBOX USE ONLY{Style.RESET_ALL}")
            print(f"{Fore.RED}AUTHORIZED SECURITY TESTING ONLY{Style.RESET_ALL}")
            print(f"{Fore.RED}{'='*80}{Style.RESET_ALL}\n")
            self.warning_shown = True
    
    def simulate_keylogger(self, duration: int = 10, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulate keylogger functionality
        
        Args:
            duration: Duration in seconds to simulate logging
            output_file: Optional file to save keylog data
        
        Returns:
            Dictionary with simulated keylog data
        """
        if not self.enabled or not self.keylogger_enabled:
            print(f"{Fore.YELLOW}[!] Keylogger disabled - simulation skipped{Style.RESET_ALL}")
            return {'enabled': False}
        
        self._show_warning()
        
        print(f"{Fore.CYAN}[*] Simulating keylogger for {duration} seconds...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
        
        # Simulate key capture (in real scenario, would use keyboard hooks)
        simulated_keys = []
        start_time = time.time()
        
        # Generate simulated keystrokes
        sample_text = "This is a simulated keylog for testing purposes only."
        for char in sample_text:
            if time.time() - start_time > duration:
                break
            
            simulated_keys.append({
                'key': char,
                'timestamp': datetime.now().isoformat(),
                'modifiers': []
            })
            time.sleep(0.1)  # Simulate typing delay
        
        keylog_data = {
            'start_time': datetime.fromtimestamp(start_time).isoformat(),
            'end_time': datetime.now().isoformat(),
            'duration': duration,
            'keys_captured': len(simulated_keys),
            'keys': simulated_keys,
            'warning': 'LAB SANDBOX USE ONLY - Simulated data'
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(keylog_data, f, indent=2)
            print(f"{Fore.GREEN}[+] Keylog data saved: {output_file}{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}[+] Simulated capture of {len(simulated_keys)} keystrokes{Style.RESET_ALL}")
        
        return keylog_data
    
    def simulate_screenshot(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulate screenshot capture
        
        Args:
            output_file: Optional file to save screenshot metadata
        
        Returns:
            Dictionary with screenshot metadata
        """
        if not self.enabled or not self.screenshot_enabled:
            print(f"{Fore.YELLOW}[!] Screenshot disabled - simulation skipped{Style.RESET_ALL}")
            return {'enabled': False}
        
        self._show_warning()
        
        print(f"{Fore.CYAN}[*] Simulating screenshot capture...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
        
        # In real scenario, would use PIL/Pillow or similar
        # For simulation, we'll create metadata only
        screenshot_data = {
            'timestamp': datetime.now().isoformat(),
            'format': 'PNG',
            'resolution': '1920x1080',  # Simulated
            'size_bytes': 1024000,  # Simulated
            'file_path': output_file or 'screenshot_simulated.png',
            'warning': 'LAB SANDBOX USE ONLY - Simulated screenshot',
            'note': 'In real scenario, this would contain actual screenshot data'
        }
        
        if output_file:
            # Create a placeholder file with metadata
            with open(output_file + '.meta', 'w') as f:
                json.dump(screenshot_data, f, indent=2)
            print(f"{Fore.GREEN}[+] Screenshot metadata saved: {output_file}.meta{Style.RESET_ALL}")
        
        print(f"{Fore.GREEN}[+] Screenshot simulation complete{Style.RESET_ALL}")
        
        return screenshot_data
    
    def simulate_file_exfiltration(self, file_path: str, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulate file exfiltration
        
        Args:
            file_path: Path to file to exfiltrate
            output_file: Optional file to save exfiltrated data
        
        Returns:
            Dictionary with exfiltration metadata
        """
        if not self.enabled or not self.file_exfiltration_enabled:
            print(f"{Fore.YELLOW}[!] File exfiltration disabled - simulation skipped{Style.RESET_ALL}")
            return {'enabled': False}
        
        self._show_warning()
        
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            print(f"{Fore.RED}[!] File not found: {file_path}{Style.RESET_ALL}")
            return {'error': 'file_not_found'}
        
        print(f"{Fore.CYAN}[*] Simulating file exfiltration: {file_path}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY{Style.RESET_ALL}")
        
        # Read file (in real scenario, would encrypt before exfiltration)
        try:
            file_size = file_path_obj.stat().st_size
            
            # For simulation, we'll just read metadata
            # In real scenario, would read full file content
            with open(file_path, 'rb') as f:
                # Only read first 1KB for simulation
                file_content = f.read(min(1024, file_size))
            
            exfiltration_data = {
                'timestamp': datetime.now().isoformat(),
                'file_path': str(file_path),
                'file_name': file_path_obj.name,
                'file_size': file_size,
                'file_hash': 'simulated_hash',  # In real scenario, would compute hash
                'content_preview': base64.b64encode(file_content[:100]).decode('utf-8'),
                'exfiltrated': True,
                'warning': 'LAB SANDBOX USE ONLY - Simulated exfiltration'
            }
            
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(exfiltration_data, f, indent=2)
                print(f"{Fore.GREEN}[+] Exfiltration metadata saved: {output_file}{Style.RESET_ALL}")
            
            print(f"{Fore.GREEN}[+] Simulated exfiltration of {file_size} bytes{Style.RESET_ALL}")
            
            return exfiltration_data
            
        except Exception as e:
            print(f"{Fore.RED}[!] File exfiltration simulation failed: {e}{Style.RESET_ALL}")
            return {'error': str(e)}
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for exfiltration"""
        import platform
        
        return {
            'hostname': platform.node(),
            'platform': platform.system(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'timestamp': datetime.now().isoformat()
        }
    
    def simulate_data_collection(self, duration: int = 30) -> Dict[str, Any]:
        """
        Simulate comprehensive data collection session
        
        Args:
            duration: Duration in seconds
        
        Returns:
            Dictionary with collected data
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] Data exfiltration disabled{Style.RESET_ALL}")
            return {'enabled': False}
        
        self._show_warning()
        
        print(f"{Fore.CYAN}[*] Simulating data collection session...{Style.RESET_ALL}")
        
        collected_data = {
            'session_start': datetime.now().isoformat(),
            'system_info': self.get_system_info(),
            'keylogs': [],
            'screenshots': [],
            'files': []
        }
        
        # Simulate keylogger
        if self.keylogger_enabled:
            keylog = self.simulate_keylogger(duration=min(5, duration))
            collected_data['keylogs'].append(keylog)
        
        # Simulate screenshots
        if self.screenshot_enabled:
            screenshot = self.simulate_screenshot()
            collected_data['screenshots'].append(screenshot)
        
        collected_data['session_end'] = datetime.now().isoformat()
        
        print(f"{Fore.GREEN}[+] Data collection simulation complete{Style.RESET_ALL}")
        
        return collected_data

