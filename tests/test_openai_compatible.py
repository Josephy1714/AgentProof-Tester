"""Tests for the OpenAI-compatible adapter without making network requests."""
import json
from unittest.mock import patch

import pytest

from agentproof.adapters.openai_compatible import OpenAICompatibleAdapter


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def adapter() -> OpenAICompatibleAdapter:
    return OpenAICompatibleAdapter("test-model", api_key="test-secret")


def test_structured_json_content_is_returned_as_object() -> None:
    response = {"choices": [{"message": {"content": '{"answer":"yes"}'}}]}
    with patch("agentproof.adapters.openai_compatible.urlopen", return_value=FakeResponse(response)) as call:
        result = adapter().invoke("Answer with JSON")
    assert result == {"answer": "yes"}
    request = call.call_args.args[0]
    assert request.full_url.endswith("/chat/completions")
    assert request.get_header("Authorization") == "Bearer test-secret"
    assert json.loads(request.data)["messages"] == [{"role": "user", "content": "Answer with JSON"}]


def test_plain_text_content_has_metadata_wrapper() -> None:
    response = {"model": "served-model", "usage": {"total_tokens": 7}, "choices": [{"message": {"content": "hello"}}]}
    with patch("agentproof.adapters.openai_compatible.urlopen", return_value=FakeResponse(response)):
        result = adapter().invoke({"prompt": "Say hello"})
    assert result == {"content": "hello", "model": "served-model", "usage": {"total_tokens": 7}}


def test_supplied_messages_are_forwarded() -> None:
    response = {"choices": [{"message": {"content": '{"ok":true}'}}]}
    messages = [{"role": "system", "content": "Be concise"}, {"role": "user", "content": "Test"}]
    with patch("agentproof.adapters.openai_compatible.urlopen", return_value=FakeResponse(response)) as call:
        assert adapter().invoke({"messages": messages}) == {"ok": True}
    assert json.loads(call.call_args.args[0].data)["messages"] == messages


def test_missing_api_key_fails_before_network() -> None:
    with patch.dict("os.environ", {}, clear=True), pytest.raises(ValueError, match="Missing API key"):
        OpenAICompatibleAdapter("test-model", api_key_env="AGENTPROOF_TEST_KEY")


def test_invalid_base_url_is_rejected() -> None:
    with pytest.raises(ValueError, match="base_url"):
        OpenAICompatibleAdapter("test-model", api_key="secret", base_url="file:///tmp")
