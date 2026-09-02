from typing import Protocol

import httpx

from app.config import settings


class LLMClientProtocol(Protocol):
    model: str

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        ...


class AnthropicClient:
    """
    Minimal Anthropic Messages API client.

    This client only requests an LLM response.
    It does not execute any financial action.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
    ):
        self.api_key = api_key
        self.model = model

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        async with httpx.AsyncClient(
            timeout=15.0
        ) as client:

            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 500,
                    "system": system_prompt,
                    "messages": [
                        {
                            "role": "user",
                            "content": user_prompt,
                        }
                    ],
                },
            )

            response.raise_for_status()

            data = response.json()

            return "".join(
                block.get("text", "")
                for block in data.get("content", [])
            )


def get_llm_client() -> LLMClientProtocol:
    if settings.llm_provider == "anthropic":
        return AnthropicClient(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

    raise ValueError(
        f"Unsupported LLM_PROVIDER: {settings.llm_provider}"
    )