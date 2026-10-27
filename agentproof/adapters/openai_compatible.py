"""OpenAI-compatible Chat Completions adapter using only the Python standard library."""
from __future__ import annotations

import json
import os
from typing import Any
from agentproof.adapters.base import AgentAdapter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OpenAICompatibleAdapter(AgentAdapter):
    """Call an OpenAI-compatible `/chat/completions` endpoint.

    The API key is read from an environment variable and is never included in
    adapter configuration or evaluation reports.
    """

    name = "openai-compatible"
    is_simulated = False

    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        api_key_env: str = "OPENAI_API_KEY",
        request_timeout: float = 30.0,
        temperature: float = 0.0,
        max_tokens: int = 256,
    ) -> None:
        if not model.strip():
            raise ValueError("Model name must not be empty")
        if not base_url.startswith(("https://", "http://")):
            raise ValueError("base_url must start with http:// or https://")
        if request_timeout <= 0:
            raise ValueError("request_timeout must be greater than zero")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.request_timeout = request_timeout
        self.temperature = temperature
        if not 1 <= max_tokens <= 2048:
            raise ValueError("max_tokens must be between 1 and 2048")
        self.max_tokens = max_tokens
        self._api_key = api_key or os.environ.get(api_key_env)
        if not self._api_key:
            raise ValueError(
                f"Missing API key. Set the {api_key_env} environment variable "
                "or provide api_key directly."
            )

    def invoke(self, payload: Any) -> Any:
        messages = self._messages(payload)
        body = json.dumps(
            {
                "model": self.model,
                "messages": messages,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        request = Request(
            f"{self.base_url}/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.request_timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            # Do not echo request headers or credentials in the error.
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"Provider returned HTTP {exc.code}: {detail}") from None
        except URLError as exc:
            raise RuntimeError(f"Could not reach provider: {exc.reason}") from None
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Provider returned invalid JSON: {exc}") from None

        try:
            content = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Provider response is missing choices[0].message.content") from exc

        if not isinstance(content, str):
            raise RuntimeError("Provider response content must be a string")

        # Preserve structured model output when the assistant returns valid JSON.
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {
                "content": content,
                "model": result.get("model", self.model),
                "usage": result.get("usage", {}),
            }

    @staticmethod
    def _messages(payload: Any) -> list[dict[str, str]]:
        if isinstance(payload, dict) and isinstance(payload.get("messages"), list):
            messages = payload["messages"]
            if not messages or any(
                not isinstance(message, dict)
                or not isinstance(message.get("role"), str)
                or not isinstance(message.get("content"), str)
                for message in messages
            ):
                raise ValueError("messages must be a non-empty list of role/content strings")
            return [{"role": item["role"], "content": item["content"]} for item in messages]
        if isinstance(payload, dict) and isinstance(payload.get("prompt"), str):
            prompt = payload["prompt"]
        elif isinstance(payload, str):
            prompt = payload
        else:
            prompt = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return [{"role": "user", "content": prompt}]
