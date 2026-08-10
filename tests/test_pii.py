from dataclasses import dataclass

from app.pii import PiiProtector
from app.session_store import SessionStore


@dataclass
class Result:
    start: int
    end: int
    entity_type: str
    score: float


class FakeAnalyzer:
    def analyze(self, text: str, language: str):
        start = text.index("alex@example.com")
        return [
            Result(start=start, end=start + len("alex@example.com"), entity_type="EMAIL_ADDRESS", score=0.9)
        ]


def test_protection_replaces_and_restores_pii() -> None:
    store = SessionStore(ttl_seconds=60)
    session_id = store.create()
    result = PiiProtector(FakeAnalyzer()).protect(session_id, "Email alex@example.com now", store)

    assert "alex@example.com" not in result.protected_text
    assert result.protected_text == "Email <PII_EMAIL_ADDRESS_1> now"
    assert store.restore(session_id, result.protected_text) == "Email alex@example.com now"
