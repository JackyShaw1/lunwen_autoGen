"""OpenAI 兼容 Chat Completions 客户端（支持流式输出）"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from collections.abc import Awaitable, Callable
from typing import Any

import httpx

from app.services.runtime_model_service import get_active_model_config

logger = logging.getLogger(__name__)

DeltaCallback = Callable[[str, str], Awaitable[None]]  # (accumulated, delta)


def llm_available() -> bool:
    config = get_active_model_config()
    ok = config.available
    logger.info(
        "llm_available=%s mock=%s key_set=%s model=%s base=%s",
        ok,
        not config.enabled,
        bool(config.api_key),
        config.model,
        config.api_base,
    )
    return ok


async def chat_completion(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: str | None = None,
    on_delta: DeltaCallback | None = None,
) -> str:
    """非流式或带回调的流式补全。有 on_delta 时走 SSE stream；失败则回退非流式。"""
    if on_delta is not None:
        try:
            return await chat_completion_stream(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                model=model,
                on_delta=on_delta,
            )
        except Exception as exc:
            logger.warning("LLM stream failed, fallback non-stream: %s", exc)
            # 告知前端进入非流式等待
            await on_delta("（流式不可用，改为整段生成，请稍候…）\n", "")

    config = get_active_model_config()
    if not config.available:
        raise RuntimeError("大模型尚未启用或配置不完整")

    base = config.api_base.rstrip("/")
    url = f"{base}/chat/completions"
    use_model = model or config.model
    payload = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    logger.info("LLM request model=%s url=%s", use_model, url)
    async with httpx.AsyncClient(timeout=180.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code >= 400:
            logger.error("LLM HTTP %s: %s", resp.status_code, resp.text[:500])
            resp.raise_for_status()
        data = resp.json()
    msg = data["choices"][0]["message"]
    content = msg.get("content") or ""
    if not content and msg.get("reasoning_content"):
        content = msg["reasoning_content"]
    logger.info("LLM response chars=%s", len(content))
    if on_delta is not None and content:
        # 非流式回退：分块回调，仍能看到过程输出
        step = max(24, len(content) // 40)
        acc = ""
        for i in range(0, len(content), step):
            acc = content[: i + step]
            await on_delta(acc, content[i : i + step])
            await asyncio.sleep(0.03)
    return content


async def chat_completion_stream(
    messages: list[dict[str, str]],
    *,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    model: str | None = None,
    on_delta: DeltaCallback | None = None,
) -> str:
    """SSE 流式调用；边生成边回调累积文本。"""
    config = get_active_model_config()
    if not config.available:
        raise RuntimeError("大模型尚未启用或配置不完整")

    base = config.api_base.rstrip("/")
    url = f"{base}/chat/completions"
    use_model = model or config.model
    payload = {
        "model": use_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
    logger.info("LLM stream request model=%s url=%s", use_model, url)

    full = ""
    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            if resp.status_code >= 400:
                body = await resp.aread()
                logger.error("LLM stream HTTP %s: %s", resp.status_code, body[:500])
                resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                piece = delta.get("content") or ""
                # DeepSeek 推理模型可能先推 reasoning_content
                if not piece:
                    piece = delta.get("reasoning_content") or ""
                if not piece:
                    continue
                full += piece
                if on_delta:
                    await on_delta(full, piece)

    logger.info("LLM stream done chars=%s", len(full))
    return full


def extract_json(text: str) -> Any:
    """从模型输出中提取 JSON（支持 ```json 代码块）"""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return json.loads(text[start : end + 1])
        raise
