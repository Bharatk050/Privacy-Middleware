# Streamlit private-chat client

This UI sends every chat message to the local privacy middleware. It does not call an LLM provider directly and never needs the provider API key in browser code.

## Configure the LLM

1. Copy `.env.example` to `.env` in this folder.
2. Set the model provider values:
   - `MODEL_PROVIDER=litellm` lets LiteLLM select a provider from `MODEL_NAME`.
   - `MODEL_BASE_URL`: the provider base URL. For Ollama use `http://127.0.0.1:11434`; leave it blank when LiteLLM has a provider default.
   - `MODEL_NAME`: the provider-qualified model identifier, such as `ollama/llama3.2`.
   - `MODEL_API_KEY`: required for hosted providers; leave blank for a local provider such as Ollama when appropriate.
3. Set `PRIVACY_API_BASE_URL` if the middleware is not on `http://127.0.0.1:8000`.

Examples with `MODEL_PROVIDER=litellm`:

| Provider | `MODEL_BASE_URL` | `MODEL_NAME` |
| --- | --- | --- |
| Ollama | `http://127.0.0.1:11434` | `ollama/llama3.2` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4.1-mini` |
| Anthropic | provider default or its API URL | `anthropic/claude-sonnet-4-5` |
| Gemini | provider default or its API URL | `gemini/gemini-2.5-flash` |

For OpenAI-compatible endpoints that already expose `/v1/chat/completions`, set `MODEL_PROVIDER=openai_compatible` and use the provider's unprefixed model ID.

## Run

From the project root, activate the virtual environment and install the UI extra once:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[ui]"
```

Open two terminals in `streamlit_client`.

Terminal 1 starts the privacy middleware using `streamlit_client/.env`:

```powershell
..\.venv\Scripts\python.exe run_middleware.py
```

Terminal 2 starts the web UI:

```powershell
..\.venv\Scripts\streamlit.exe run streamlit_app.py
```

Then open the displayed Streamlit URL, typically `http://localhost:8501`, start a private session, and send a message.

Use **End session and erase mappings** when finished. This calls the middleware's session-deletion endpoint, which removes the session key and encrypted mappings from memory.

## Safe operational logs

The middleware writes rotating logs to `streamlit_client/logs/middleware.log` by default. They record only timestamps, session IDs, entity counts, lifecycle events, and safe error categories. Prompts, responses, PII, tokens, ciphertext, keys, and provider credentials are never written to the file.
