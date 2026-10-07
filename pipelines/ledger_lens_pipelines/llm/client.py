"""
Thin client for the two places an LLM appears in Ledger Lens: spec
induction (once per new layout) and targeted repair (once per row that
fails reconciliation). Talks to any OpenAI-compatible endpoint — an
open-weight model via Groq/Together/HF Inference Providers, or a
self-hosted vLLM/Ollama endpoint. No vendor-specific SDK required.
"""

import json

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings

settings = get_settings()


class LlmError(RuntimeError):
    pass


async def complete_json(system_prompt: str, user_prompt: str, *, temperature: float = 0.0) -> dict:
    """Fails fast when no provider is configured; retries only real calls."""

    if not settings.llm_provider_api_key:
        raise LlmError(
            "LLM_PROVIDER_API_KEY is not set: spec induction falls back to header "
            "heuristics and targeted repair is skipped (rows go to human review)."
        )
    return await _complete_json(system_prompt, user_prompt, temperature=temperature)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def _complete_json(system_prompt: str, user_prompt: str, *, temperature: float = 0.0) -> dict:
    """
    Calls the configured LLM and parses its response as JSON. Retries on
    transient failures (rate limits, timeouts) — spec induction happens
    rarely enough (once per new layout) that a slow retry here has no
    meaningful cost impact on the pipeline.
    """

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{settings.llm_provider_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_provider_api_key}"},
            json={
                "model": settings.llm_model,
                "temperature": temperature,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        response.raise_for_status()
        body = response.json()

    try:
        content = body["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise LlmError(f"Malformed LLM response: {e}") from e
