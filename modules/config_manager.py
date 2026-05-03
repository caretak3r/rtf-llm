#!/usr/bin/env python3
"""
Enhanced Configuration Manager
Handles API keys, model configuration, and environment variables
"""

import json
import os
import getpass
from typing import Dict, Any, Optional
from pathlib import Path
from colorama import Fore, Style

class ConfigManager:
    """Enhanced configuration manager with secure key handling"""
    
    def __init__(self, config_path: str = 'config.json'):
        self.config_path = config_path
        self.config = self._load_config()
        self._load_environment_variables()
        self._validate_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                return config
            else:
                return self._get_default_config()
        except json.JSONDecodeError as e:
            print(f"{Fore.RED}[!] Error parsing config.json: {e}{Style.RESET_ALL}")
            return self._get_default_config()
        except Exception as e:
            print(f"{Fore.YELLOW}[!] Error loading config: {e}, using defaults{Style.RESET_ALL}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "llm": {
                "provider": "openai",
                "api_key": None,
                "model": "gpt-4",
                "base_url": None,
                "temperature": 0.7,
                "max_tokens": 2000,
                "timeout": 60
            },
            "providers": {
                "openai": {
                    "api_key": None,
                    "default_model": "gpt-4",
                    "base_url": "https://api.openai.com/v1"
                },
                "anthropic": {
                    "api_key": None,
                    "default_model": "claude-3-opus",
                    "base_url": "https://api.anthropic.com/v1"
                },
                "google": {
                    "api_key": None,
                    "default_model": "gemini-pro",
                    "base_url": "https://generativelanguage.googleapis.com/v1beta"
                },
                "cohere": {
                    "api_key": None,
                    "default_model": "command",
                    "base_url": "https://api.cohere.ai/v1"
                },
                "custom": {
                    "api_key": None,
                    "default_model": "custom-model",
                    "base_url": None
                }
            },
            "local_models": {
                "enabled": False,
                "model_path": None,
                "framework": "auto",  # auto, transformers, llama.cpp, vllm
                "device": "auto",  # auto, cpu, cuda, mps
                "weight_modification": {
                    "enabled": False,
                    "backup_weights": True,
                    "modification_dir": "modified_weights"
                }
            },
            "attacks": {
                "enable_all": True,
                "enable_prompt_injection": True,
                "enable_jailbreak": True,
                "enable_data_extraction": True,
                "enable_system_prompt_extraction": True,
                "enable_adversarial_inputs": True,
                "enable_role_confusion": True,
                "enable_context_injection": True,
                "enable_weight_manipulation": True
            },
            "adversarial": {
                "advanced_techniques": {
                    "gradient_based": False,  # Requires local model
                    "token_manipulation": True,
                    "semantic_perturbation": True,
                    "multi_modal_attacks": False,
                    "transfer_attacks": True
                },
                "attack_combinations": True,
                "adaptive_attacks": True,
                "ensemble_attacks": False
            },
            "reporting": {
                "output_dir": "reports",
                "format": "json",
                "include_responses": True,
                "severity_threshold": "medium",
                "detailed_analysis": True
            },
            "rate_limiting": {
                "enabled": True,
                "delay_between_requests": 0.5,
                "max_requests_per_minute": 60,
                "backoff_strategy": "exponential"
            },
            "logging": {
                "level": "INFO",
                "file": "llm_redteam.log",
                "console_output": True
            }
        }
    
    def _load_environment_variables(self):
        """Load configuration from environment variables"""
        # 3-level mappings: (section, key, subkey) -> nested dict assignment
        nested_mappings = {
            'OPENAI_API_KEY': ('providers', 'openai', 'api_key'),
            'ANTHROPIC_API_KEY': ('providers', 'anthropic', 'api_key'),
            'GOOGLE_API_KEY': ('providers', 'google', 'api_key'),
            'COHERE_API_KEY': ('providers', 'cohere', 'api_key'),
            'GROQ_API_KEY': ('providers', 'groq', 'api_key'),
            'TOGETHER_API_KEY': ('providers', 'together', 'api_key'),
            'PERPLEXITY_API_KEY': ('providers', 'perplexity', 'api_key'),
            'MISTRAL_API_KEY': ('providers', 'mistral', 'api_key'),
            'FIREWORKS_API_KEY': ('providers', 'fireworks', 'api_key'),
            'OPENROUTER_API_KEY': ('providers', 'openrouter', 'api_key'),
        }

        # 2-level mappings: (section, key) -> direct assignment
        flat_mappings = {
            'LLM_API_KEY': ('llm', 'api_key'),
            'LLM_PROVIDER': ('llm', 'provider'),
            'LLM_MODEL': ('llm', 'model'),
            'LLM_BASE_URL': ('llm', 'base_url'),
            'LOCAL_MODEL_PATH': ('local_models', 'model_path'),
            'JUDGE_API_KEY': ('judge', 'api_key'),
        }

        for env_var, path in nested_mappings.items():
            value = os.getenv(env_var)
            if value:
                section, key, subkey = path
                self.config.setdefault(section, {}).setdefault(key, {})[subkey] = value

        for env_var, path in flat_mappings.items():
            value = os.getenv(env_var)
            if value:
                section, key = path
                self.config.setdefault(section, {})[key] = value
        
        # Use provider-specific key if main key is not set
        if not self.config.get('llm', {}).get('api_key'):
            provider = self.config.get('llm', {}).get('provider', 'openai')
            provider_key = self.config.get('providers', {}).get(provider, {}).get('api_key')
            if provider_key:
                self.config['llm']['api_key'] = provider_key
    
    def _validate_config(self):
        """Validate configuration"""
        # Ensure required sections exist
        required_sections = ['llm', 'attacks', 'reporting']
        for section in required_sections:
            if section not in self.config:
                self.config[section] = {}
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration"""
        llm_config = self.config.get('llm', {}).copy()
        
        # Merge provider-specific config
        provider = llm_config.get('provider', 'openai')
        provider_config = self.config.get('providers', {}).get(provider, {})
        
        # Use provider defaults if not set
        if not llm_config.get('api_key') and provider_config.get('api_key'):
            llm_config['api_key'] = provider_config['api_key']
        if not llm_config.get('model') and provider_config.get('default_model'):
            llm_config['model'] = provider_config['default_model']
        if not llm_config.get('base_url') and provider_config.get('base_url'):
            llm_config['base_url'] = provider_config['base_url']
        
        return llm_config
    
    def get_provider_config(self, provider: str) -> Dict[str, Any]:
        """Get configuration for specific provider"""
        return self.config.get('providers', {}).get(provider, {})
    
    def get_local_model_config(self) -> Dict[str, Any]:
        """Get local model configuration"""
        return self.config.get('local_models', {})
    
    def get_adversarial_config(self) -> Dict[str, Any]:
        """Get adversarial attack configuration"""
        return self.config.get('adversarial', {})
    
    def prompt_for_api_key(self, provider: str = None) -> str:
        """Prompt user for API key securely"""
        if provider:
            prompt = f"Enter API key for {provider}: "
        else:
            prompt = "Enter API key: "
        
        api_key = getpass.getpass(prompt)
        return api_key
    
    def save_config(self, path: str = None):
        """Save configuration to file"""
        save_path = path or self.config_path
        
        # Don't save API keys to file
        config_to_save = json.loads(json.dumps(self.config))
        
        # Remove API keys from saved config
        if 'llm' in config_to_save:
            config_to_save['llm']['api_key'] = None
        
        if 'providers' in config_to_save:
            for provider in config_to_save['providers']:
                config_to_save['providers'][provider]['api_key'] = None
        
        with open(save_path, 'w') as f:
            json.dump(config_to_save, f, indent=2)
        
        print(f"{Fore.GREEN}[+] Configuration saved to {save_path}{Style.RESET_ALL}")
    
    def update_config(self, updates: Dict[str, Any]):
        """Update configuration with new values"""
        def deep_update(base_dict, update_dict):
            for key, value in update_dict.items():
                if isinstance(value, dict) and key in base_dict and isinstance(base_dict[key], dict):
                    deep_update(base_dict[key], value)
                else:
                    base_dict[key] = value
        
        deep_update(self.config, updates)
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """Get configuration value by dot-separated path"""
        keys = key_path.split('.')
        value = self.config
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def set(self, key_path: str, value: Any):
        """Set configuration value by dot-separated path"""
        keys = key_path.split('.')
        config = self.config
        
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        config[keys[-1]] = value

