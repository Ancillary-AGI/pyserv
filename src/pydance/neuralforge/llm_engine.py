"""
LLM Engine Module for NeuralForge

Provides a unified interface for multiple LLM providers including OpenAI, Anthropic, Local, and Custom.
"""

import asyncio
import time
from enum import Enum
from typing import Dict, Optional, Any
from dataclasses import dataclass
import aiohttp


class LLMProvider(Enum):
    """Supported LLM providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    CUSTOM = "custom"


@dataclass
class LLMConfig:
    """Configuration for LLM requests"""
    provider: LLMProvider
    model: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048


@dataclass
class LLMResponse:
    """Response from LLM generation"""
    content: str
    tokens_used: int
    latency: float
    model: str


class LLMEngine:
    """
    Unified LLM engine supporting multiple providers
    """

    def __init__(self):
        self.providers: Dict[LLMProvider, callable] = {
            LLMProvider.OPENAI: self._call_openai,
            LLMProvider.ANTHROPIC: self._call_anthropic,
            LLMProvider.LOCAL: self._call_local,
            LLMProvider.CUSTOM: self._call_custom
        }
        self.session = aiohttp.ClientSession()

    async def generate(self, config: LLMConfig, prompt: str, **kwargs) -> LLMResponse:
        """
        Main method to generate text using configured LLM

        Args:
            config: LLM configuration
            prompt: Input prompt
            **kwargs: Additional parameters

        Returns:
            LLMResponse with generated content
        """
        if config.provider not in self.providers:
            raise ValueError(f"Unsupported provider: {config.provider}")

        start_time = time.time()
        try:
            response = await self.providers[config.provider](config, prompt, **kwargs)
            latency = time.time() - start_time
            return LLMResponse(
                content=response["content"],
                tokens_used=response.get("tokens_used", 0),
                latency=latency,
                model=config.model
            )
        except Exception as e:
            raise Exception(f"LLM generation failed: {str(e)}")

    async def _call_openai(self, config: LLMConfig, prompt: str, **kwargs) -> Dict:
        """Call OpenAI API"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            **kwargs
        }

        async with self.session.post(
            f"{config.base_url or 'https://api.openai.com/v1'}/chat/completions",
            headers=headers,
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"OpenAI API error: {response.status} - {error_text}")

            data = await response.json()
            return {
                "content": data["choices"][0]["message"]["content"],
                "tokens_used": data["usage"]["total_tokens"]
            }

    async def _call_anthropic(self, config: LLMConfig, prompt: str, **kwargs) -> Dict:
        """Call Anthropic API"""
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        payload = {
            "model": config.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            **kwargs
        }

        async with self.session.post(
            f"{config.base_url or 'https://api.anthropic.com/v1'}/messages",
            headers=headers,
            json=payload
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"Anthropic API error: {response.status} - {error_text}")

            data = await response.json()
            return {
                "content": data["content"][0]["text"],
                "tokens_used": data["usage"]["input_tokens"] + data["usage"]["output_tokens"]
            }

    async def _call_local(self, config: LLMConfig, prompt: str, **kwargs) -> Dict:
        """Call local LLM (Ollama, LMStudio, etc.)"""
        # Implementation for local LLMs
        # This would need to be implemented based on the specific local LLM setup
        raise NotImplementedError("Local LLM implementation not yet available")

    async def _call_custom(self, config: LLMConfig, prompt: str, **kwargs) -> Dict:
        """Call custom LLM endpoint"""
        # Implementation for custom LLM endpoints
        # This would need to be implemented based on the custom endpoint requirements
        raise NotImplementedError("Custom LLM implementation not yet available")

    async def close(self):
        """Close the HTTP session"""
        await self.session.close()
