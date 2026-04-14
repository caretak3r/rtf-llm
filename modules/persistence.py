#!/usr/bin/env python3
"""
Persistence Module
Registry and startup script persistence simulation for red team testing

⚠️ LAB SANDBOX USE ONLY ⚠️
"""

import os
import platform
import json
from typing import Dict, Any, List
from pathlib import Path
from colorama import Fore, Style

class PersistenceModule:
    """Persistence mechanisms for red team testing"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled = config.get('persistence', {}).get('enabled', False)
        self.system = platform.system().lower()
        self.persistence_methods = []
    
    def simulate_registry_persistence(self, key_path: str, value_name: str, payload_path: str) -> Dict[str, Any]:
        """
        Simulate Windows registry persistence
        
        Args:
            key_path: Registry key path (e.g., "HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run")
            value_name: Registry value name
            payload_path: Path to payload executable
        
        Returns:
            Dictionary with persistence details
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] Persistence disabled - simulation skipped{Style.RESET_ALL}")
            return {'enabled': False, 'method': 'registry'}
        
        if self.system != 'windows':
            print(f"{Fore.YELLOW}[!] Registry persistence only available on Windows{Style.RESET_ALL}")
            return {'enabled': False, 'method': 'registry', 'reason': 'not_windows'}
        
        persistence_info = {
            'method': 'registry',
            'key_path': key_path,
            'value_name': value_name,
            'payload_path': payload_path,
            'simulated': True,
            'command': f'reg add "{key_path}" /v "{value_name}" /t REG_SZ /d "{payload_path}" /f'
        }
        
        self.persistence_methods.append(persistence_info)
        
        print(f"{Fore.CYAN}[*] Simulated registry persistence:{Style.RESET_ALL}")
        print(f"  Key: {key_path}")
        print(f"  Value: {value_name}")
        print(f"  Payload: {payload_path}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY - Not actually executed{Style.RESET_ALL}")
        
        return persistence_info
    
    def simulate_startup_script(self, script_path: str, payload_path: str) -> Dict[str, Any]:
        """
        Simulate startup script persistence (Linux/macOS)
        
        Args:
            script_path: Path where startup script would be placed
            payload_path: Path to payload executable
        
        Returns:
            Dictionary with persistence details
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] Persistence disabled - simulation skipped{Style.RESET_ALL}")
            return {'enabled': False, 'method': 'startup_script'}
        
        persistence_info = {
            'method': 'startup_script',
            'script_path': script_path,
            'payload_path': payload_path,
            'simulated': True
        }
        
        # Determine script location based on OS
        if self.system == 'linux':
            common_locations = [
                '~/.bashrc',
                '~/.bash_profile',
                '~/.profile',
                '/etc/rc.local',
                '~/.config/autostart/'
            ]
        elif self.system == 'darwin':  # macOS
            common_locations = [
                '~/Library/LaunchAgents/',
                '~/Library/LaunchDaemons/',
                '~/.zshrc',
                '~/.bash_profile'
            ]
        else:
            common_locations = [script_path]
        
        persistence_info['common_locations'] = common_locations
        
        # Generate example script content
        script_content = f'''#!/bin/bash
# LAB SANDBOX USE ONLY
# Simulated persistence script

# Execute payload
{payload_path} &
'''
        
        persistence_info['script_content'] = script_content
        persistence_info['command'] = f'echo "{script_content}" > {script_path} && chmod +x {script_path}'
        
        self.persistence_methods.append(persistence_info)
        
        print(f"{Fore.CYAN}[*] Simulated startup script persistence:{Style.RESET_ALL}")
        print(f"  Script path: {script_path}")
        print(f"  Payload: {payload_path}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY - Not actually executed{Style.RESET_ALL}")
        
        return persistence_info
    
    def simulate_cron_job(self, schedule: str, payload_path: str) -> Dict[str, Any]:
        """
        Simulate cron job persistence (Linux/macOS)
        
        Args:
            schedule: Cron schedule (e.g., "@reboot" or "0 * * * *")
            payload_path: Path to payload executable
        
        Returns:
            Dictionary with persistence details
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] Persistence disabled - simulation skipped{Style.RESET_ALL}")
            return {'enabled': False, 'method': 'cron'}
        
        persistence_info = {
            'method': 'cron',
            'schedule': schedule,
            'payload_path': payload_path,
            'simulated': True,
            'command': f'(crontab -l 2>/dev/null; echo "{schedule} {payload_path}") | crontab -'
        }
        
        self.persistence_methods.append(persistence_info)
        
        print(f"{Fore.CYAN}[*] Simulated cron job persistence:{Style.RESET_ALL}")
        print(f"  Schedule: {schedule}")
        print(f"  Payload: {payload_path}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY - Not actually executed{Style.RESET_ALL}")
        
        return persistence_info
    
    def simulate_systemd_service(self, service_name: str, payload_path: str) -> Dict[str, Any]:
        """
        Simulate systemd service persistence (Linux)
        
        Args:
            service_name: Name of systemd service
            payload_path: Path to payload executable
        
        Returns:
            Dictionary with persistence details
        """
        if not self.enabled:
            print(f"{Fore.YELLOW}[!] Persistence disabled - simulation skipped{Style.RESET_ALL}")
            return {'enabled': False, 'method': 'systemd'}
        
        if self.system != 'linux':
            print(f"{Fore.YELLOW}[!] Systemd persistence only available on Linux{Style.RESET_ALL}")
            return {'enabled': False, 'method': 'systemd', 'reason': 'not_linux'}
        
        service_file_content = f'''[Unit]
Description=Simulated Service - LAB SANDBOX USE ONLY
After=network.target

[Service]
Type=simple
ExecStart={payload_path}
Restart=always

[Install]
WantedBy=multi-user.target
'''
        
        service_file_path = f'/etc/systemd/system/{service_name}.service'
        
        persistence_info = {
            'method': 'systemd',
            'service_name': service_name,
            'service_file_path': service_file_path,
            'payload_path': payload_path,
            'service_content': service_file_content,
            'simulated': True,
            'commands': [
                f'echo "{service_file_content}" > {service_file_path}',
                f'systemctl daemon-reload',
                f'systemctl enable {service_name}',
                f'systemctl start {service_name}'
            ]
        }
        
        self.persistence_methods.append(persistence_info)
        
        print(f"{Fore.CYAN}[*] Simulated systemd service persistence:{Style.RESET_ALL}")
        print(f"  Service: {service_name}")
        print(f"  Payload: {payload_path}")
        print(f"{Fore.YELLOW}[!] LAB SANDBOX USE ONLY - Not actually executed{Style.RESET_ALL}")
        
        return persistence_info
    
    def get_all_persistence_methods(self) -> List[Dict[str, Any]]:
        """Get all simulated persistence methods"""
        return self.persistence_methods
    
    def save_persistence_report(self, output_path: str = "persistence_report.json"):
        """Save persistence simulation report"""
        report = {
            'system': self.system,
            'enabled': self.enabled,
            'methods': self.persistence_methods,
            'warning': 'LAB SANDBOX USE ONLY - These are simulations, not actual persistence'
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"{Fore.GREEN}[+] Persistence report saved: {output_path}{Style.RESET_ALL}")

