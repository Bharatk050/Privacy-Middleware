import base64
import hashlib
import hmac
import threading
import time
import uuid
from dataclasses import dataclass, field

from cryptography.fernet import Fernet


@dataclass
class Session:
    key: bytes
    created_at: float
    last_accessed_at: float
    encrypted_values: dict[str, bytes] = field(default_factory=dict)
    fingerprints: dict[str, str] = field(default_factory=dict)
    history: list[dict[str, str]] = field(default_factory=list)


class SessionNotFoundError(KeyError):
    pass


class SessionStore:
    """In-process session storage. Nothing here is persisted to disk."""

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = threading.RLock()

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        now = time.monotonic()
        with self._lock:
            self._remove_expired_locked(now)
            self._sessions[session_id] = Session(
                key=Fernet.generate_key(), created_at=now, last_accessed_at=now
            )
        return session_id

    def delete(self, session_id: str) -> bool:
        with self._lock:
            return self._sessions.pop(session_id, None) is not None

    def protect_value(self, session_id: str, entity_type: str, plaintext: str) -> str:
        """Encrypt a value once per session and return its stable safe token."""
        with self._lock:
            session = self._get_locked(session_id)
            fingerprint = self._fingerprint(session.key, entity_type, plaintext)
            token = session.fingerprints.get(fingerprint)
            if token is None:
                prefix = self._safe_entity_type(entity_type)
                token = f"<PII_{prefix}_{len(session.encrypted_values) + 1}>"
                session.encrypted_values[token] = Fernet(session.key).encrypt(plaintext.encode("utf-8"))
                session.fingerprints[fingerprint] = token
            return token

    def restore(self, session_id: str, text: str) -> str:
        with self._lock:
            session = self._get_locked(session_id)
            # Tokens are generated internally, so direct replacement cannot decrypt unknown text.
            for token, ciphertext in session.encrypted_values.items():
                if token in text:
                    plaintext = Fernet(session.key).decrypt(ciphertext).decode("utf-8")
                    text = text.replace(token, plaintext)
            return text

    def history(self, session_id: str) -> list[dict[str, str]]:
        with self._lock:
            return list(self._get_locked(session_id).history)

    def append_history(self, session_id: str, role: str, content: str) -> None:
        with self._lock:
            self._get_locked(session_id).history.append({"role": role, "content": content})

    def _get_locked(self, session_id: str) -> Session:
        now = time.monotonic()
        self._remove_expired_locked(now)
        session = self._sessions.get(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        session.last_accessed_at = now
        return session

    def _remove_expired_locked(self, now: float) -> None:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now - session.last_accessed_at >= self.ttl_seconds
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)

    @staticmethod
    def _fingerprint(key: bytes, entity_type: str, plaintext: str) -> str:
        # A keyed digest permits stable replacement without retaining plaintext in session state.
        digest = hmac.new(key, f"{entity_type}\0{plaintext}".encode("utf-8"), hashlib.sha256).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii")

    @staticmethod
    def _safe_entity_type(entity_type: str) -> str:
        return "".join(character if character.isalnum() else "_" for character in entity_type.upper())
