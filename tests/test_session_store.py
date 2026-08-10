import pytest

from app.session_store import SessionNotFoundError, SessionStore


def test_session_values_are_isolated_and_restored() -> None:
    store = SessionStore(ttl_seconds=60)
    first = store.create()
    second = store.create()
    token = store.protect_value(first, "EMAIL_ADDRESS", "alex@example.com")

    assert token == store.protect_value(first, "EMAIL_ADDRESS", "alex@example.com")
    assert store.restore(first, f"Contact {token}") == "Contact alex@example.com"
    assert store.restore(second, token) == token


def test_deleted_session_cannot_be_reused() -> None:
    store = SessionStore(ttl_seconds=60)
    session_id = store.create()
    store.delete(session_id)

    with pytest.raises(SessionNotFoundError):
        store.history(session_id)
