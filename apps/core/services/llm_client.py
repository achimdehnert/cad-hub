"""
LLM client for CAD Hub — centralized text generation via aifw.

Provides:
- generate_text(): simple sync text generation
- AifwChatCompletion: async CompletionBackend adapter for ChatAgent

DO NOT use openai/anthropic directly — all LLM calls go through aifw.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from aifw import LLMResult, sync_completion

logger = logging.getLogger(__name__)

ACTION_CAD_NLP = "cad_nlp"
ACTION_CAD_CHAT = "cad_chat"


@dataclass(frozen=True)
class _ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class _CompletionResponse:
    content: str | None
    tool_calls: list[_ToolCall] = field(default_factory=list)
    model: str = ""

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class AifwChatCompletion:
    """CompletionBackend adapter wrapping aifw.sync_completion.

    Implements the ChatAgent CompletionBackend protocol.
    Tool-use is passed through to aifw via extra_kwargs.
    """

    def __init__(self, action_code: str = ACTION_CAD_CHAT) -> None:
        self._action_code = action_code

    async def complete(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str = "auto",
        **kwargs: Any,
    ) -> _CompletionResponse:
        extra: dict[str, Any] = {}
        if tools:
            extra["tools"] = tools
            extra["tool_choice"] = tool_choice

        result: LLMResult = sync_completion(
            action_code=self._action_code,
            messages=messages,
            **extra,
        )

        tool_calls: list[_ToolCall] = []
        if result.tool_calls:
            for tc in result.tool_calls:
                tool_calls.append(
                    _ToolCall(
                        id=tc.id,
                        name=tc.name,
                        arguments=tc.arguments,
                    )
                )

        return _CompletionResponse(
            content=result.content if result.success else None,
            tool_calls=tool_calls,
            model=result.model or "",
        )


def generate_text(
    prompt: str,
    system_prompt: str = "",
    model: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.7,
    action_code: str = ACTION_CAD_NLP,
) -> str | None:
    """Generate text using aifw (DB-driven model routing).

    Args:
        prompt: User prompt.
        system_prompt: System instruction.
        model: Ignored — model is configured via AIActionType in admin.
        max_tokens: Maximum response tokens.
        temperature: Sampling temperature.
        action_code: aifw action code (default: cad_nlp).

    Returns:
        Generated text or None on error.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    try:
        result: LLMResult = sync_completion(
            action_code=action_code,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if result.success:
            return result.content
        logger.warning("LLM call returned no success: %s", result.error)
        return None
    except Exception:
        logger.exception("LLM generation failed")
        return None
