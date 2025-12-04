"""CLI-based LLM adapter for the LLM Council.

This module replaces the OpenRouter HTTP client with local CLI tools:
- Codex CLI (for OpenAI / potentially xAI models)
- Claude CLI
- Gemini CLI
- Grok One-Shot CLI

Each model is addressed by a "provider:model_id" string, e.g.:
- "codex:gpt-5.1-codex"
- "claude:claude-sonnet-4-20250514"
- "gemini:gemini-2.5-pro"
- "grok:grok-4"

The public interface matches the previous OpenRouter client:
- query_model(model: str, messages: List[Dict[str,str]], timeout: float | None)
- query_models_parallel(models: List[str], messages: List[Dict[str,str]])
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from .config import (
    CODEX_CLI,
    CLAUDE_CLI,
    GEMINI_CLI,
    GROK_CLI,
    DEFAULT_TIMEOUT,
)

logger = logging.getLogger("llm_council.cli")


async def _run_cli(cmd: List[str], timeout: float) -> tuple[int, str, str]:
    """Run a CLI command asynchronously and return (exit_code, stdout, stderr)."""
    logger.debug("Running CLI: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return -1, "", "timeout"

    stdout = stdout_b.decode("utf-8", errors="ignore") if stdout_b else ""
    stderr = stderr_b.decode("utf-8", errors="ignore") if stderr_b else ""

    logger.debug("CLI finished (code=%s)", proc.returncode)
    if proc.returncode != 0:
        logger.warning("CLI stderr (truncated): %s", (stderr or "")[:500])

    return proc.returncode, stdout, stderr


def _extract_last_message_from_codex_jsonl(output: str) -> str:
    """Best-effort extraction of the final assistant message from Codex JSONL.

    Codex `--json` typically emits one JSON object per line. We look for the last
    object that appears to contain an assistant message and return its text
    content. If anything goes wrong, fall back to the raw output.
    """
    lines = [l for l in output.splitlines() if l.strip()]
    last_content: Optional[str] = None

    for line in lines:
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Heuristic: look for a "message" field with role/content
        msg = obj.get("message") or obj.get("data") or obj.get("event")
        if isinstance(msg, dict):
            role = msg.get("role")
            content = msg.get("content")
            if isinstance(content, str) and (role in (None, "assistant")):
                last_content = content
        # Some formats might nest messages differently; extend as needed.

    return last_content or output.strip()


def _extract_claude_text(payload: Any) -> str:
    """Extract plain text from Claude CLI JSON output.

    Different versions of the Claude CLI may structure JSON slightly differently.
    This function is intentionally defensive and will fall back to a stringified
    payload if it doesn't recognize the structure.
    """
    # Common patterns we might see:
    # {"completion": {"text": "..."}}
    # {"output": "..."}
    # {"message": {"content": "..."}}
    if isinstance(payload, dict):
        completion = payload.get("completion") or payload.get("result") or {}
        if isinstance(completion, dict):
            text = completion.get("text") or completion.get("content")
            if isinstance(text, str):
                return text

        output = payload.get("output") or payload.get("text")
        if isinstance(output, str):
            return output

        message = payload.get("message")
        if isinstance(message, dict):
            content = message.get("content")
            if isinstance(content, str):
                return content

    return json.dumps(payload, ensure_ascii=False)


async def _query_codex(model_name: str, prompt: str, timeout: float) -> Optional[Dict[str, Any]]:
    cmd = [
        CODEX_CLI,
        "exec",
        prompt,
        "-m",
        model_name,
        "--json",
    ]
    code, out, err = await _run_cli(cmd, timeout)
    if code != 0:
        print(f"Codex error ({model_name}): {err}")
        return None

    content = _extract_last_message_from_codex_jsonl(out)
    return {"content": content}


async def _query_claude(model_name: str, prompt: str, timeout: float) -> Optional[Dict[str, Any]]:
    cmd = [
        CLAUDE_CLI,
        "--print",
        "--output-format",
        "json",
        "--model",
        model_name,
        prompt,
    ]
    code, out, err = await _run_cli(cmd, timeout)
    if code != 0:
        print(f"Claude error ({model_name}): {err}")
        return None

    try:
        payload = json.loads(out)
    except json.JSONDecodeError:
        # Fallback: treat entire stdout as content
        return {"content": out.strip()}

    content = _extract_claude_text(payload)
    return {"content": content}


async def _query_gemini(model_name: str, prompt: str, timeout: float) -> Optional[Dict[str, Any]]:
    cmd = [
        GEMINI_CLI,
        "-p",
        prompt,
        "-m",
        model_name,
    ]
    code, out, err = await _run_cli(cmd, timeout)
    if code != 0:
        print(f"Gemini error ({model_name}): {err}")
        return None

    return {"content": out.strip()}


async def _query_grok(model_name: str, prompt: str, timeout: float) -> Optional[Dict[str, Any]]:
    """Query Grok One-Shot CLI.

    We rely on the user to configure the X API key via environment or CLI config,
    so we do not handle credentials here.
    """
    cmd = [
        GROK_CLI,
        "-p",
        prompt,
        "-m",
        model_name,
        "-q",  # quiet
    ]
    code, out, err = await _run_cli(cmd, timeout)
    if code != 0:
        print(f"Grok error ({model_name}): {err}")
        return None

    return {"content": out.strip()}


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """Query a single model via the appropriate CLI tool.

    Args:
        model: Provider-prefixed model identifier, e.g. "codex:gpt-5.1-codex".
        messages: List of chat messages; we use the last message's content.
        timeout: Optional timeout in seconds.
    """
    timeout = timeout or DEFAULT_TIMEOUT

    if not messages:
        raise ValueError("messages must contain at least one item")

    prompt = messages[-1].get("content", "")
    if not prompt:
        raise ValueError("last message must contain non-empty 'content'")

    if ":" not in model:
        raise ValueError(f"Model identifier must be 'provider:model', got: {model}")

    provider, model_name = model.split(":", 1)

    logger.info("query_model start provider=%s model=%s", provider, model_name)

    if provider == "codex":
        result = await _query_codex(model_name, prompt, timeout)
    elif provider == "claude":
        result = await _query_claude(model_name, prompt, timeout)
    elif provider == "gemini":
        result = await _query_gemini(model_name, prompt, timeout)
    elif provider == "grok":
        result = await _query_grok(model_name, prompt, timeout)
    else:
        raise ValueError(f"Unknown provider in model identifier: {provider}")

    logger.info("query_model done provider=%s model=%s success=%s", provider, model_name, result is not None)
    return result


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Query multiple models in parallel via their respective CLIs."""
    tasks = [query_model(m, messages) for m in models]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    return {m: r for m, r in zip(models, results)}
