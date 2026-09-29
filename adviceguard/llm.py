"""Minimal OpenRouter client. No framework, one function.

The API key is read from the OPENROUTER_API_KEY environment variable (or a
.env file in the repository root, which is git-ignored). It is never written
to disk by this module. Every call is appended to a spend ledger so the cost
figures in the report come from measured token counts, not estimates.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
API_URL = "https://openrouter.ai/api/v1/chat/completions"


def _load_dotenv() -> None:
    env = REPO_ROOT / ".env"
    if env.exists() and "OPENROUTER_API_KEY" not in os.environ:
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def has_key() -> bool:
    _load_dotenv()
    return bool(os.environ.get("OPENROUTER_API_KEY"))


def chat(
    model: str,
    messages: list[dict],
    *,
    temperature: float = 0.0,
    max_tokens: int = 400,
    response_format: dict | None = None,
    logprobs: bool = False,
    top_logprobs: int | None = None,
    seed: int | None = None,
    ledger: Path | None = None,
    tag: str = "",
    retries: int = 4,
) -> dict:
    """One chat completion. Returns content, usage, logprobs and latency."""
    _load_dotenv()
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set; use offline mode instead.")
    body: dict = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "usage": {"include": True},
    }
    if response_format:
        body["response_format"] = response_format
    if logprobs:
        body["logprobs"] = True
        if top_logprobs:
            body["top_logprobs"] = top_logprobs
    if seed is not None:
        body["seed"] = seed
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}

    last_err = None
    for attempt in range(retries):
        t0 = time.perf_counter()
        try:
            r = requests.post(API_URL, headers=headers, json=body, timeout=120)
            latency_ms = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                data = r.json()
                if "choices" in data:
                    break
                last_err = RuntimeError(str(data)[:500])
            else:
                last_err = RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
        except requests.RequestException as e:  # network blip
            last_err = e
        time.sleep(2 ** attempt)
    else:
        raise RuntimeError(f"OpenRouter call failed after {retries} attempts: {last_err}")

    choice = data["choices"][0]
    usage = data.get("usage", {}) or {}
    out = {
        "content": choice["message"].get("content") or "",
        "logprobs": (choice.get("logprobs") or {}).get("content"),
        "model": data.get("model", model),
        "provider": data.get("provider"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "cost_usd": usage.get("cost"),
        "latency_ms": round(latency_ms, 1),
    }
    if ledger is not None:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a") as f:
            f.write(json.dumps({
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "tag": tag,
                "model": out["model"],
                "provider": out["provider"],
                "prompt_tokens": out["prompt_tokens"],
                "completion_tokens": out["completion_tokens"],
                "cost_usd": out["cost_usd"],
                "latency_ms": out["latency_ms"],
            }) + "\n")
    return out
