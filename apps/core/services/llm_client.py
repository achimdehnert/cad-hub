"""
LLM client for CAD Hub — centralized text generation via aifw.

Provides generate_text() backed by aifw (DB-driven model routing).
DO NOT use openai/anthropic directly — all LLM calls go through aifw.
"""
import logging

from aifw import LLMResult, sync_completion

logger = logging.getLogger(__name__)

ACTION_CAD_NLP = "cad_nlp"


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
