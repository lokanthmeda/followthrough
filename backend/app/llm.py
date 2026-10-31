"""LLM client supporting OpenAI-compatible endpoints (FreeLLMAPI on 31415) and local Ollama (11434)."""
import json
import logging
import httpx
from .config import settings

log = logging.getLogger(__name__)


async def chat_json(system: str, user: str, model: str | None = None, max_tokens: int = 4096) -> dict:
    """Send chat request and parse returned JSON."""
    chosen_model = model or settings.llm_model

    # 1. Try OpenAI-compatible endpoint (e.g. FreeLLMAPI)
    if "31415" in settings.llm_base_url or "/v1" in settings.llm_base_url:
        endpoint = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        }
        full_content = f"{system}\n\n{user}\n\nOutput raw valid JSON only." if system else user
        body = {
            "model": chosen_model,
            "messages": [
                {"role": "user", "content": full_content},
            ],
            "temperature": 0.1,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.post(endpoint, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
            text = data["choices"][0]["message"]["content"]
            return _parse_or_raise(text)
        except Exception as e:
            log.warning("OpenAI-compatible LLM call failed (%r), attempting fallback...", e)

    # 2. Fallback to Ollama (/api/generate)
    ollama_url = getattr(settings, "ollama_base_url", "http://127.0.0.1:11434")
    prompt = f"{system}\n\n{user}\n\nOutput ONLY valid JSON matching the requested schema. No markdown formatting, no explanation."
    body = {
        "model": "qwen2.5:0.5b" if chosen_model == "auto" else chosen_model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": min(max_tokens, 768), "temperature": 0.1},
    }
    async with httpx.AsyncClient(timeout=8.0) as client:
        r = await client.post(f"{ollama_url.rstrip('/')}/api/generate", json=body)
        r.raise_for_status()
        data = r.json()
    text = data.get("response", "")
    return _parse_or_raise(text)


async def chat_text(system: str, user: str, model: str | None = None, max_tokens: int = 1024) -> str:
    """Send chat request and return text response."""
    chosen_model = model or settings.llm_model

    # 1. Try OpenAI-compatible endpoint
    if "31415" in settings.llm_base_url or "/v1" in settings.llm_base_url:
        endpoint = f"{settings.llm_base_url.rstrip('/')}/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.llm_api_key}",
        }
        full_content = f"{system}\n\n{user}" if system else user
        body = {
            "model": chosen_model,
            "messages": [
                {"role": "user", "content": full_content},
            ],
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                r = await client.post(endpoint, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            log.warning("OpenAI-compatible text call failed (%s), attempting fallback...", e)

    # 2. Fallback to Ollama
    ollama_url = getattr(settings, "ollama_base_url", "http://127.0.0.1:11434")
    prompt = f"{system}\n\n{user}"
    body = {
        "model": "qwen2.5:0.5b" if chosen_model == "auto" else chosen_model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": max_tokens},
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{ollama_url.rstrip('/')}/api/generate", json=body)
        r.raise_for_status()
        data = r.json()
    return data.get("response", "")


import re


def _parse_or_raise(text: str) -> dict:
    text = text.strip()

    # 1. Direct JSON parse
    try:
        val = json.loads(text)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    candidates: list[dict] = []

    # 2. Extract from ALL markdown code fences
    for m in re.finditer(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text):
        try:
            val = json.loads(m.group(1))
            if isinstance(val, dict):
                candidates.append(val)
        except Exception:
            pass

    # 3. Widest outer braces
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        try:
            val = json.loads(text[first_brace:last_brace + 1])
            if isinstance(val, dict):
                candidates.append(val)
        except Exception:
            pass

    # 4. Scan braces from longest span to shortest
    if not candidates:
        starts = [i for i, ch in enumerate(text) if ch == '{']
        ends = [i for i, ch in enumerate(text) if ch == '}']
        for s in starts:
            for e in reversed(ends):
                if e > s and (e - s) > 30:
                    try:
                        val = json.loads(text[s:e + 1])
                        if isinstance(val, dict):
                            candidates.append(val)
                            break
                    except Exception:
                        continue

    if not candidates:
        raise ValueError(f"LLM returned non-JSON:\n{text[:500]}")

    # Prioritize candidate that matches the target schema (meeting/decisions/conflicts)
    domain_keys = {"decisions", "action_items", "meeting", "relation", "confidence", "rationale"}
    scored = []
    for c in candidates:
        score = sum(1 for k in domain_keys if k in c)
        scored.append((score, len(str(c)), c))

    scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return scored[0][2]
