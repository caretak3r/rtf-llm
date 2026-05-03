#!/usr/bin/env python3
"""
LLM Client Adapter Module - Universal Provider Support
"""

import requests
import json
import time
import random
from urllib.parse import urlparse
from typing import Dict, List, Optional, Any
from colorama import Fore, Style

OPENAI_COMPATIBLE_PROVIDERS = [
    "openai", "groq", "together", "perplexity", "mistral",
    "fireworks", "lmstudio", "custom", "openrouter",
    "anyscale", "novita", "deepinfra", "sambanova", "any",
]

NATIVE_PROVIDERS = ["anthropic", "google", "cohere", "bedrock"]

PROVIDER_URL_MAP = {
    "openai": ["api.openai.com"],
    "anthropic": ["api.anthropic.com"],
    "google": ["generativelanguage.googleapis.com"],
    "cohere": ["api.cohere.ai"],
    "groq": ["api.groq.com"],
    "together": ["api.together.xyz"],
    "perplexity": ["api.perplexity.ai"],
    "mistral": ["api.mistral.ai"],
    "fireworks": ["api.fireworks.ai"],
    "openrouter": ["openrouter.ai"],
    "anyscale": ["api.endpoints.anyscale.com"],
    "novita": ["api.novita.ai"],
    "deepinfra": ["api.deepinfra.com"],
    "sambanova": ["api.sambanova.ai"],
    "ollama": ["localhost", "127.0.0.1"],
    "lmstudio": ["localhost", "127.0.0.1"],
}

PROVIDER_ENDPOINTS = {
    "openai": {"base": "https://api.openai.com/v1", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "anthropic": {"base": "https://api.anthropic.com/v1", "chat": "/messages", "auth": "api-key", "requires_key": True},
    "google": {"base": "https://generativelanguage.googleapis.com/v1beta", "chat": "/models/{model}:generateContent", "auth": "bearer", "requires_key": True},
    "cohere": {"base": "https://api.cohere.ai/v1", "chat": "/generate", "auth": "bearer", "requires_key": True},
    "groq": {"base": "https://api.groq.com/openai/v1", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "together": {"base": "https://api.together.xyz/v1", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "perplexity": {"base": "https://api.perplexity.ai", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "mistral": {"base": "https://api.mistral.ai/v1", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "fireworks": {"base": "https://api.fireworks.ai/inference/v1", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "anyscale": {"base": "https://api.endpoints.anyscale.com/v1", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "novita": {"base": "https://api.novita.ai/v3/openai", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "deepinfra": {"base": "https://api.deepinfra.com/v1/openai", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "sambanova": {"base": "https://api.sambanova.ai/v1", "chat": "/chat/completions", "auth": "bearer", "requires_key": True},
    "ollama": {"base": "http://localhost:11434", "chat": "/api/chat", "auth": "none", "requires_key": False},
    "lmstudio": {"base": "http://localhost:1234/v1", "chat": "/chat/completions", "auth": "none", "requires_key": False},
}


def auto_detect_provider(base_url):
    if not base_url:
        return "custom"
    parsed = urlparse(base_url)
    host = parsed.hostname or ""
    # Check local providers by port first
    if host in ("localhost", "127.0.0.1", "::1", ""):
        port = parsed.port
        if port == 11434:
            return "ollama"
        if port == 1234:
            return "lmstudio"
    # Then check known provider domains (skip localhost entries)
    for provider, domains in PROVIDER_URL_MAP.items():
        if provider in ("ollama", "lmstudio"):
            continue
        for domain in domains:
            if domain not in ("localhost", "127.0.0.1") and domain in host:
                return provider
    return "custom"


class LLMClient:
    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "openai").lower()
        self.api_key = config.get("api_key")
        self.model = config.get("model", "gpt-4")
        self.base_url = config.get("base_url")
        self.temperature = config.get("temperature", 0.7)
        self.max_tokens = config.get("max_tokens", 2000)
        self.timeout = config.get("timeout", 60)
        auto_detect = config.get("auto_detect", True)
        if auto_detect and self.provider == "any":
            self.provider = auto_detect_provider(self.base_url)
        elif auto_detect and self.base_url and self.provider == "custom":
            detected = auto_detect_provider(self.base_url)
            if detected != "custom":
                self.provider = detected
        self.max_retries = config.get("max_retries", 3)
        self.retry_base_delay = config.get("retry_base_delay", 1.0)
        self.retry_max_delay = config.get("retry_max_delay", 30.0)
        self.request_count = 0
        self.total_latency = 0.0
        self.error_count = 0
        endpoint_info = PROVIDER_ENDPOINTS.get(self.provider, {})
        requires_key = endpoint_info.get("requires_key", True)
        if requires_key and not self.api_key:
            raise ValueError(f"API key required for provider '{self.provider}'. Set via --api-key, LLM_API_KEY env var, or config.json.")
        self._setup_endpoints()

    def _setup_endpoints(self):
        if self.provider in PROVIDER_ENDPOINTS:
            ep = PROVIDER_ENDPOINTS[self.provider]
            base = self.base_url or ep["base"]
            chat_path = ep["chat"]
        else:
            base = self.base_url or "http://localhost:8000/v1"
            chat_path = "/chat/completions"
        self.endpoint_base = base
        self.chat_url = f"{base}{chat_path}"

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.provider == "anthropic":
            headers["x-api-key"] = self.api_key or ""
            headers["anthropic-version"] = "2023-06-01"
        elif self.api_key and self.api_key not in ("", "none", "not-needed", "null", "sk-none"):
            ep = PROVIDER_ENDPOINTS.get(self.provider, {})
            auth_type = ep.get("auth", "bearer")
            if auth_type == "api-key":
                headers["x-api-key"] = self.api_key
            elif auth_type == "bearer":
                headers["Authorization"] = f"Bearer {self.api_key}"
        if self.provider == "openrouter" and self.api_key:
            headers["HTTP-Referer"] = "llm-redteam-framework"
            headers["X-Title"] = "LLM Red Team Framework"
        return headers

    def _format_openai_request(self, messages, **kwargs):
        return {"model": self.model, "messages": messages, "temperature": kwargs.get("temperature", self.temperature), "max_tokens": kwargs.get("max_tokens", self.max_tokens), **kwargs}

    def _format_ollama_request(self, messages, **kwargs):
        return {"model": self.model, "messages": messages, "options": {"temperature": kwargs.get("temperature", self.temperature)}, "stream": False}

    def _format_anthropic_request(self, messages, **kwargs):
        system_prompt = None
        formatted_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                formatted_messages.append({"role": msg["role"], "content": msg["content"]})
        request = {"model": self.model, "messages": formatted_messages, "max_tokens": kwargs.get("max_tokens", self.max_tokens), "temperature": kwargs.get("temperature", self.temperature), **kwargs}
        if system_prompt:
            request["system"] = system_prompt
        return request

    def _format_google_request(self, messages, **kwargs):
        contents = []
        system_instruction = None
        for msg in messages:
            if msg["role"] == "system":
                system_instruction = msg["content"]
            else:
                contents.append({"role": "user" if msg["role"] == "user" else "model", "parts": [{"text": msg["content"]}]})
        request = {"contents": contents, "generationConfig": {"temperature": kwargs.get("temperature", self.temperature), "maxOutputTokens": kwargs.get("max_tokens", self.max_tokens)}}
        if system_instruction:
            request["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        return request

    def _format_cohere_request(self, messages, **kwargs):
        prompt = ""
        for msg in messages:
            if msg["role"] == "user":
                prompt += msg["content"] + "\n"
        return {"model": self.model, "prompt": prompt.strip(), "temperature": kwargs.get("temperature", self.temperature), "max_tokens": kwargs.get("max_tokens", self.max_tokens), **kwargs}

    def _parse_openai_response(self, response):
        data = response.json()
        if "choices" in data and len(data["choices"]) > 0:
            return data["choices"][0].get("message", {}).get("content", "")
        raise ValueError(f"Unexpected response format: {json.dumps(data, indent=2)}")

    def _parse_ollama_response(self, response):
        data = response.json()
        return data.get("message", {}).get("content", "")

    def _parse_anthropic_response(self, response):
        data = response.json()
        if "content" in data and len(data["content"]) > 0:
            return data["content"][0].get("text", "")
        raise ValueError(f"Unexpected response format: {json.dumps(data, indent=2)}")

    def _parse_google_response(self, response):
        data = response.json()
        if "candidates" in data and len(data["candidates"]) > 0:
            content = data["candidates"][0].get("content", {})
            parts = content.get("parts", [])
            if parts:
                return parts[0].get("text", "")
        raise ValueError(f"Unexpected response format: {json.dumps(data, indent=2)}")

    def _parse_cohere_response(self, response):
        data = response.json()
        if "generations" in data and len(data["generations"]) > 0:
            return data["generations"][0].get("text", "")
        raise ValueError(f"Unexpected response format: {json.dumps(data, indent=2)}")

    def chat(self, messages, **kwargs):
        if self.provider == "ollama":
            payload, parse_func = self._format_ollama_request(messages, **kwargs), self._parse_ollama_response
        elif self.provider == "anthropic":
            payload, parse_func = self._format_anthropic_request(messages, **kwargs), self._parse_anthropic_response
        elif self.provider == "google":
            payload, parse_func = self._format_google_request(messages, **kwargs), self._parse_google_response
        elif self.provider == "cohere":
            payload, parse_func = self._format_cohere_request(messages, **kwargs), self._parse_cohere_response
        else:
            payload, parse_func = self._format_openai_request(messages, **kwargs), self._parse_openai_response
        headers = self._get_headers()
        url = self.chat_url.replace("{model}", self.model) if self.provider == "google" else self.chat_url
        return self._request_with_retry(url, headers, payload, parse_func)

    def _request_with_retry(self, url, headers, payload, parse_func, attempt=0):
        start = time.time()
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
            latency = time.time() - start
            self.request_count += 1
            self.total_latency += latency
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", self.retry_base_delay))
                if attempt < self.max_retries:
                    wait = min(retry_after + random.uniform(0, 1), self.retry_max_delay)
                    print(f"{Fore.YELLOW}[~] Rate limited, retrying in {wait:.1f}s (attempt {attempt+1}/{self.max_retries})...{Style.RESET_ALL}")
                    time.sleep(wait)
                    return self._request_with_retry(url, headers, payload, parse_func, attempt + 1)
            if response.status_code >= 500 and attempt < self.max_retries:
                wait = min(self.retry_base_delay * (2 ** attempt) + random.uniform(0, 1), self.retry_max_delay)
                print(f"{Fore.YELLOW}[~] Server error {response.status_code}, retrying in {wait:.1f}s (attempt {attempt+1}/{self.max_retries})...{Style.RESET_ALL}")
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
        return {"total_requests": self.request_count, "total_errors": self.error_count, "avg_latency_ms": (self.total_latency / max(self.request_count, 1)) * 1000, "total_latency_s": round(self.total_latency, 2)}

    def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages, **kwargs)

    def test_connection(self) -> bool:
        try:
            response = self.generate("Say OK if you can read this.")
            return len(response) > 0
        except Exception as e:
            print(f"{Fore.RED}[!] Connection test failed: {e}{Style.RESET_ALL}")
            return False
