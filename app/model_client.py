import httpx


class ModelProviderError(RuntimeError):
    pass


class ChatCompletionsClient:
    def __init__(
        self,
        base_url: str | None,
        api_key: str,
        model_name: str,
        timeout_seconds: float,
        provider: str = "openai_compatible",
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.provider = provider

    async def complete(self, messages: list[dict[str, str]]) -> str:
        if self.provider == "litellm":
            return await self._complete_with_litellm(messages)

        if not self.base_url:
            raise ModelProviderError("MODEL_BASE_URL is required for OpenAI-compatible providers")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        payload = {"model": self.model_name, "messages": messages}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions", json=payload, headers=headers
                )
                response.raise_for_status()
                body = response.json()
            content = body["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ModelProviderError("The model provider returned an invalid response") from exc
        if not isinstance(content, str):
            raise ModelProviderError("The model provider returned non-text content")
        return content

    async def _complete_with_litellm(self, messages: list[dict[str, str]]) -> str:
        """Use LiteLLM for providers with non-OpenAI request formats."""
        try:
            from litellm import acompletion

            options = {
                "model": self.model_name,
                "messages": messages,
                "api_key": self.api_key or None,
                "timeout": self.timeout_seconds,
            }
            if self.base_url:
                options["api_base"] = self.base_url
            response = await acompletion(**options)
            content = response.choices[0].message.content
        except Exception as exc:
            raise ModelProviderError("The model provider returned an invalid response") from exc
        if not isinstance(content, str):
            raise ModelProviderError("The model provider returned non-text content")
        return content
