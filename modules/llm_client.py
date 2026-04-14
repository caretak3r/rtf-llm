#!/usr/bin/env python3
"""
LLM Client Adapter Module
Unified interface for interacting with various LLM providers.

Features:
  - Multi-provider support (OpenAI, Anthropic, Google, Cohere, custom)
  - Automatic retry with configurable exponential backoff
  - Response metadata tracking (latency, token usage, status codes)
  - Rate-limit awareness (respects Retry-After headers)
"""

import requests
import json
import time
import random
from typing import Dict, List, Optional, Any
from colorama import Fore, Style


class LLMClient:
    """Unified LLM client adapter supporting multiple providers."""

    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get('provider', 'openai').lower()
        self.api_key = config.get('api_key')
        self.model = config.get('model', 'gpt-4')
        self.base_url = config.get('base_url')
        self.temperature = config.get('temperature', 0.7)
        self.max_tokens = config.get('max_tokens', 2000)
        self.timeout = config.get('timeout', 60)

        # Retry configuration
        self.max_retries = config.get('max_retries', 3)
        self.retry_base_delay = config.get('retry_base_delay', 1.0)
        self.retry_max_delay = config.get('retry_max_delay', 30.0)

        # Telemetry
        self.request_count = 0
        self.total_latency = 0.0
        self.error_count = 0

        if not self.api_key:
            raise ValueError("API key is required")

        self._setup_endpoints()
    
    def _setup_endpoints(self):
        """Setup provider-specific endpoints"""
        endpoints = {
            'openai': {
                'base': self.base_url or 'https://api.openai.com/v1',
                'chat': '/chat/completions'
            },
            'anthropic': {
                'base': self.base_url or 'https://api.anthropic.com/v1',
                'chat': '/messages'
            },
            'google': {
                'base': self.base_url or 'https://generativelanguage.googleapis.com/v1beta',
                'chat': '/models/{model}:generateContent'
            },
            'cohere': {
                'base': self.base_url or 'https://api.cohere.ai/v1',
                'chat': '/generate'
            }
        }
        
        if self.provider not in endpoints:
            # Custom provider - assume OpenAI-compatible format
            endpoints[self.provider] = {
                'base': self.base_url or 'http://localhost:8000/v1',
                'chat': '/chat/completions'
            }
        
        self.endpoint_config = endpoints[self.provider]
        self.chat_url = f"{self.endpoint_config['base']}{self.endpoint_config['chat']}"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers based on provider"""
        headers = {
            'Content-Type': 'application/json'
        }
        
        if self.provider == 'openai' or self.provider == 'custom':
            headers['Authorization'] = f'Bearer {self.api_key}'
        elif self.provider == 'anthropic':
            headers['x-api-key'] = self.api_key
            headers['anthropic-version'] = '2023-06-01'
        elif self.provider == 'google':
            headers['Authorization'] = f'Bearer {self.api_key}'
        elif self.provider == 'cohere':
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
    
    def _format_openai_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Format request for OpenAI-compatible APIs"""
        return {
            'model': self.model,
            'messages': messages,
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            **kwargs
        }
    
    def _format_anthropic_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Format request for Anthropic API"""
        # Convert messages format
        system_prompt = None
        formatted_messages = []
        
        for msg in messages:
            if msg['role'] == 'system':
                system_prompt = msg['content']
            else:
                formatted_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
        
        request = {
            'model': self.model,
            'messages': formatted_messages,
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            'temperature': kwargs.get('temperature', self.temperature),
            **kwargs
        }
        
        if system_prompt:
            request['system'] = system_prompt
        
        return request
    
    def _format_google_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Format request for Google Gemini API"""
        # Convert messages to Google format
        contents = []
        system_instruction = None
        
        for msg in messages:
            if msg['role'] == 'system':
                system_instruction = msg['content']
            else:
                contents.append({
                    'role': 'user' if msg['role'] == 'user' else 'model',
                    'parts': [{'text': msg['content']}]
                })
        
        request = {
            'contents': contents,
            'generationConfig': {
                'temperature': kwargs.get('temperature', self.temperature),
                'maxOutputTokens': kwargs.get('max_tokens', self.max_tokens),
            }
        }
        
        if system_instruction:
            request['systemInstruction'] = {
                'parts': [{'text': system_instruction}]
            }
        
        return request
    
    def _format_cohere_request(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Format request for Cohere API"""
        # Extract prompt from last user message
        prompt = ""
        for msg in messages:
            if msg['role'] == 'user':
                prompt += msg['content'] + "\n"
        
        return {
            'model': self.model,
            'prompt': prompt.strip(),
            'temperature': kwargs.get('temperature', self.temperature),
            'max_tokens': kwargs.get('max_tokens', self.max_tokens),
            **kwargs
        }
    
    def _parse_openai_response(self, response: requests.Response) -> str:
        """Parse OpenAI-compatible response"""
        data = response.json()
        if 'choices' in data and len(data['choices']) > 0:
            return data['choices'][0]['message']['content']
        raise ValueError(f"Unexpected response format: {data}")
    
    def _parse_anthropic_response(self, response: requests.Response) -> str:
        """Parse Anthropic response"""
        data = response.json()
        if 'content' in data and len(data['content']) > 0:
            return data['content'][0]['text']
        raise ValueError(f"Unexpected response format: {data}")
    
    def _parse_google_response(self, response: requests.Response) -> str:
        """Parse Google Gemini response"""
        data = response.json()
        if 'candidates' in data and len(data['candidates']) > 0:
            if 'content' in data['candidates'][0]:
                parts = data['candidates'][0]['content'].get('parts', [])
                if parts:
                    return parts[0].get('text', '')
        raise ValueError(f"Unexpected response format: {data}")
    
    def _parse_cohere_response(self, response: requests.Response) -> str:
        """Parse Cohere response"""
        data = response.json()
        if 'generations' in data and len(data['generations']) > 0:
            return data['generations'][0]['text']
        raise ValueError(f"Unexpected response format: {data}")
    
    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Send chat request to LLM with automatic retry and telemetry.

        Args:
            messages: List of message dicts with 'role' and 'content'
            **kwargs: Additional parameters (temperature, max_tokens, etc.)

        Returns:
            Response text from LLM
        """
        # Format request based on provider
        if self.provider in ('openai', 'custom'):
            payload = self._format_openai_request(messages, **kwargs)
            parse_func = self._parse_openai_response
        elif self.provider == 'anthropic':
            payload = self._format_anthropic_request(messages, **kwargs)
            parse_func = self._parse_anthropic_response
        elif self.provider == 'google':
            payload = self._format_google_request(messages, **kwargs)
            parse_func = self._parse_google_response
        elif self.provider == 'cohere':
            payload = self._format_cohere_request(messages, **kwargs)
            parse_func = self._parse_cohere_response
        else:
            payload = self._format_openai_request(messages, **kwargs)
            parse_func = self._parse_openai_response

        headers = self._get_headers()
        url = self.chat_url.replace('{model}', self.model) if self.provider == 'google' else self.chat_url

        return self._request_with_retry(url, headers, payload, parse_func)

    def _request_with_retry(self, url: str, headers: Dict, payload: Dict,
                            parse_func, attempt: int = 0) -> str:
        """Execute HTTP request with exponential backoff retry."""
        start = time.time()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            latency = time.time() - start
            self.request_count += 1
            self.total_latency += latency

            if response.status_code == 429:
                # Rate limited -- respect Retry-After if present
                retry_after = float(response.headers.get('Retry-After', self.retry_base_delay))
                if attempt < self.max_retries:
                    wait = min(retry_after + random.uniform(0, 1), self.retry_max_delay)
                    print(f"{Fore.YELLOW}[~] Rate limited, retrying in {wait:.1f}s "
                          f"(attempt {attempt+1}/{self.max_retries})...{Style.RESET_ALL}")
                    time.sleep(wait)
                    return self._request_with_retry(url, headers, payload, parse_func, attempt + 1)

            if response.status_code >= 500 and attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt) + random.uniform(0, 1),
                           self.retry_max_delay)
                print(f"{Fore.YELLOW}[~] Server error {response.status_code}, retrying in "
                      f"{wait:.1f}s (attempt {attempt+1}/{self.max_retries})...{Style.RESET_ALL}")
                time.sleep(wait)
                return self._request_with_retry(url, headers, payload, parse_func, attempt + 1)

            response.raise_for_status()
            return parse_func(response)

        except requests.exceptions.Timeout:
            self.error_count += 1
            if attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                print(f"{Fore.YELLOW}[~] Timeout, retrying in {wait:.1f}s...{Style.RESET_ALL}")
                time.sleep(wait)
                return self._request_with_retry(url, headers, payload, parse_func, attempt + 1)
            raise Exception("API request timed out after all retries")

        except requests.exceptions.ConnectionError:
            self.error_count += 1
            if attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt), self.retry_max_delay)
                print(f"{Fore.YELLOW}[~] Connection error, retrying in {wait:.1f}s...{Style.RESET_ALL}")
                time.sleep(wait)
                return self._request_with_retry(url, headers, payload, parse_func, attempt + 1)
            raise Exception("API connection failed after all retries")

        except requests.exceptions.RequestException as e:
            self.error_count += 1
            raise Exception(f"API request failed: {e}")
        except Exception as e:
            self.error_count += 1
            raise Exception(f"Failed to parse response: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Return request telemetry."""
        return {
            'total_requests': self.request_count,
            'total_errors': self.error_count,
            'avg_latency_ms': (self.total_latency / max(self.request_count, 1)) * 1000,
            'total_latency_s': round(self.total_latency, 2),
        }
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """
        Generate response from a single prompt
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
        
        Returns:
            Response text from LLM
        """
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        
        return self.chat(messages, **kwargs)
    
    def test_connection(self) -> bool:
        """Test connection to LLM API"""
        try:
            test_prompt = "Say 'OK' if you can read this."
            response = self.generate(test_prompt)
            return len(response) > 0
        except Exception as e:
            print(f"{Fore.RED}[!] Connection test failed: {e}{Style.RESET_ALL}")
            return False

