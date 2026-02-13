"""
LLM client for CAD Hub — centralized text generation.

Provides generate_text() with OpenAI fallback.
Extracted from bfagent/apps/bfagent/services/llm_client.py.
"""
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def generate_text(
    prompt: str,
    system_prompt: str = "",
    model: str = "",
    max_tokens: int = 2000,
    temperature: float = 0.7,
) -> Optional[str]:
    """Generate text using OpenAI API.

    Args:
        prompt: User prompt.
        system_prompt: System instruction.
        model: Model name (default from env or gpt-4o-mini).
        max_tokens: Maximum response tokens.
        temperature: Sampling temperature.

    Returns:
        Generated text or None on error.
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        logger.warning("OPENAI_API_KEY not set, LLM features disabled")
        return None

    if not model:
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    try:
        import openai

        client = openai.OpenAI(api_key=api_key)
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content
    except Exception:
        logger.exception("LLM generation failed")
        return None
