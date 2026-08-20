from types import SimpleNamespace

import pytest

from app.model_client import ChatCompletionsClient, ModelProviderError


@pytest.mark.asyncio
async def test_complete_uses_litellm_with_configured_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_acompletion(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="safe reply"))])

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    client = ChatCompletionsClient("http://localhost:11434/", "secret", "ollama/llama3.2", 45)

    result = await client.complete([{"role": "user", "content": "protected"}])

    assert result == "safe reply"
    assert captured == {
        "model": "ollama/llama3.2",
        "messages": [{"role": "user", "content": "protected"}],
        "api_key": "secret",
        "timeout": 45,
        "api_base": "http://localhost:11434",
    }


@pytest.mark.asyncio
async def test_complete_omits_empty_base_url_and_rejects_non_text(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    async def fake_acompletion(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=None))])

    import litellm

    monkeypatch.setattr(litellm, "acompletion", fake_acompletion)
    client = ChatCompletionsClient(None, "", "gemini/gemini-2.5-flash", 30)

    with pytest.raises(ModelProviderError, match="non-text content"):
        await client.complete([{"role": "user", "content": "protected"}])

    assert "api_base" not in captured
    assert captured["api_key"] is None
