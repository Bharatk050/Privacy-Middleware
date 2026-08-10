import pytest

from app.model_client import ChatCompletionsClient
from app.pii import PiiProtector
from app.session_store import SessionStore


class FakeAnalyzer:
    def analyze(self, text: str, language: str):
        start = text.index("alex@example.com")
        return [type("Result", (), {"start": start, "end": start + 16, "entity_type": "EMAIL_ADDRESS", "score": 1.0})()]


class FakeClient(ChatCompletionsClient):
    def __init__(self) -> None:
        self.messages = []

    async def complete(self, messages: list[dict[str, str]]) -> str:
        self.messages = messages
        return "I will email <PII_EMAIL_ADDRESS_1>."


@pytest.mark.asyncio
async def test_model_only_receives_protected_content() -> None:
    store = SessionStore(ttl_seconds=60)
    session_id = store.create()
    protector = PiiProtector(FakeAnalyzer())
    model = FakeClient()
    protected = protector.protect(session_id, "Email alex@example.com", store)

    response = await model.complete([{"role": "user", "content": protected.protected_text}])

    assert "alex@example.com" not in model.messages[0]["content"]
    assert store.restore(session_id, response) == "I will email alex@example.com."
