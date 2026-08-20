class ModelProviderError(RuntimeError):
    pass


class ChatCompletionsClient:
    def __init__(
        self,
        base_url: str | None,
        api_key: str,
        model_name: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.api_key = api_key
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    async def complete(self, messages: list[dict[str, str]]) -> str:
        """Use LiteLLM's provider adapters for every configured model."""
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
