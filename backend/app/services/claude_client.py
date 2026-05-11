"""AI model wrapper used by APES modules.

The class name stays ClaudeClient for compatibility with existing services,
but it can route calls to Anthropic or a local Ollama model.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Small LLM client with explicit graceful failure behavior."""

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: float | None = None) -> None:
        """Store provider settings so services can share a single AI client."""

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        explicit_provider = os.getenv("LLM_PROVIDER") or os.getenv("LOCAL_LLM_PROVIDER")
        default_provider = "anthropic" if self.api_key else "ollama"
        self.provider = (explicit_provider or default_provider).strip().lower()
        self.model = model or self._default_model()
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
        self.timeout = timeout if timeout is not None else self._default_timeout()

    @property
    def is_configured(self) -> bool:
        """Report whether a live model call is possible without leaking credentials."""

        if self.provider == "ollama":
            return bool(self.model)
        return bool(self.api_key)

    @property
    def is_ollama(self) -> bool:
        """Return true when calls are routed to a local Ollama server."""

        return self.provider == "ollama"

    async def complete_text(self, system_prompt: str, user_prompt: str, max_tokens: int = 1200) -> str:
        """Call the configured model and return natural language text."""

        if self.provider == "ollama":
            return await self._complete_ollama(system_prompt, user_prompt, max_tokens=max_tokens, json_mode=False)
        return await self._complete_anthropic(system_prompt, user_prompt, max_tokens=max_tokens)

    async def complete_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 1200) -> str:
        """Call the configured model and return text intended to be JSON."""

        json_instruction = (
            f"{user_prompt}\n\nReturn valid JSON only. Do not include markdown, comments, or a preamble."
        )
        if self.provider == "ollama":
            return await self._complete_ollama(system_prompt, json_instruction, max_tokens=max_tokens, json_mode=True)
        return await self._complete_anthropic(system_prompt, json_instruction, max_tokens=max_tokens)

    def _default_model(self) -> str:
        """Select provider-specific model defaults from environment variables."""

        if self.provider == "ollama":
            return os.getenv("OLLAMA_MODEL", "llama3.1:8b")
        return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

    def _default_timeout(self) -> float:
        """Use a longer timeout for local models because first load can be slow."""

        if self.provider == "ollama":
            return env_float("OLLAMA_TIMEOUT", env_float("OLLAMA_TIMEOUT_SECONDS", 180.0))
        return 30.0

    async def _complete_anthropic(self, system_prompt: str, user_prompt: str, max_tokens: int) -> str:
        """Call Anthropic Messages API and return text content."""

        if not self.api_key:
            raise RuntimeError("Claude API key is not configured")
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
        except Exception as exc:
            logger.warning("Claude call failed gracefully: %s: %r", type(exc).__name__, exc)
            raise RuntimeError("Claude call failed") from exc
        content = body.get("content", [])
        text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
        if not text_parts:
            raise RuntimeError("Claude returned no text content")
        return "\n".join(text_parts)

    async def _complete_ollama(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        json_mode: bool,
    ) -> str:
        """Call local Ollama generate API and return its response text."""

        requested_tokens = min(max_tokens, env_int("OLLAMA_MAX_TOKENS", max_tokens))
        payload: dict[str, Any] = {
            "model": self.model,
            "system": system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {
                "num_predict": requested_tokens,
                "temperature": env_float("OLLAMA_TEMPERATURE", 0.2 if json_mode else 0.4),
                "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "8192")),
            },
        }
        if json_mode:
            payload["format"] = "json"
        max_retries = max(1, env_int("OLLAMA_MAX_RETRIES", 1))
        retry_delay = env_float("OLLAMA_RETRY_DELAY", 2.0)
        last_error: Exception | None = None
        try:
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(f"{self.ollama_base_url}/api/generate", json=payload)
                        response.raise_for_status()
                        body = response.json()
                    break
                except Exception as exc:
                    last_error = exc
                    if attempt >= max_retries - 1:
                        raise
                    await asyncio.sleep(retry_delay)
        except Exception as exc:
            logger.warning(
                "Ollama call failed gracefully against %s with model %s: %s: %r",
                self.ollama_base_url,
                self.model,
                type(exc).__name__,
                last_error or exc,
            )
            raise RuntimeError("Ollama call failed") from exc
        text = str(body.get("response") or "").strip()
        if not text:
            raise RuntimeError("Ollama returned no text content")
        return text


def env_float(name: str, default: float) -> float:
    """Read a float environment variable with a safe default."""

    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def env_int(name: str, default: int) -> int:
    """Read an integer environment variable with a safe default."""

    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default
