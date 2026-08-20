import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response, status

from app.config import Settings, get_settings
from app.model_client import ChatCompletionsClient, ModelProviderError
from app.pii import PiiProtector, build_protector
from app.schemas import ChatMessage, HealthResponse, ProtectedMessageResponse, SessionCreated
from app.session_store import SessionNotFoundError, SessionStore

logger = logging.getLogger("pii_middleware")


def configure_logging(settings: Settings) -> None:
    """Persist only safe operational metadata; never prompts, PII, or secrets."""
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))
    logger.handlers.clear()
    handler = RotatingFileHandler(
        log_path,
        maxBytes=settings.log_max_bytes,
        backupCount=settings.log_backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.propagate = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings)
    app.state.store = SessionStore(settings.session_ttl_seconds)
    app.state.protector = build_protector()
    app.state.model_client = ChatCompletionsClient(
        str(settings.model_base_url) if settings.model_base_url else None,
        settings.model_api_key,
        settings.model_name,
        settings.model_timeout_seconds,
    )
    logger.info("middleware_started")
    yield
    logger.info("middleware_stopped")


app = FastAPI(title="PII Privacy Middleware", version="0.1.0", lifespan=lifespan)


def get_store() -> SessionStore:
    return app.state.store


def get_protector() -> PiiProtector:
    return app.state.protector


def get_model_client() -> ChatCompletionsClient:
    return app.state.model_client


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@app.post("/sessions", response_model=SessionCreated, status_code=status.HTTP_201_CREATED)
async def create_session(
    store: SessionStore = Depends(get_store), settings: Settings = Depends(get_settings)
) -> SessionCreated:
    session_id = store.create()
    logger.info("session_created session_id=%s", session_id)
    return SessionCreated(session_id=session_id, expires_in_seconds=settings.session_ttl_seconds)


@app.post("/sessions/{session_id}/messages", response_model=ProtectedMessageResponse)
async def send_message(
    session_id: str,
    message: ChatMessage,
    store: SessionStore = Depends(get_store),
    protector: PiiProtector = Depends(get_protector),
    model_client: ChatCompletionsClient = Depends(get_model_client),
) -> ProtectedMessageResponse:
    try:
        protected = protector.protect(session_id, message.content, store)
        history = store.history(session_id)
        safe_messages = [*history, {"role": message.role, "content": protected.protected_text}]
        safe_response = await model_client.complete(safe_messages)
        store.append_history(session_id, message.role, protected.protected_text)
        store.append_history(session_id, "assistant", safe_response)
        restored_response = store.restore(session_id, safe_response)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or expired") from exc
    except ModelProviderError as exc:
        logger.warning("model_provider_failure session_id=%s", session_id)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Model provider request failed") from exc

    logger.info(
        "message_processed session_id=%s entity_counts=%s", session_id, protected.detected_entities
    )
    return ProtectedMessageResponse(
        session_id=session_id,
        content=restored_response,
        detected_entities=protected.detected_entities,
    )


@app.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def close_session(session_id: str, store: SessionStore = Depends(get_store)) -> Response:
    if not store.delete(session_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or expired")
    logger.info("session_deleted session_id=%s", session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
