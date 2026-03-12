"""Manus API client for movie recommendations."""

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MANUS_BASE = "https://api.manus.ai"
POLL_INTERVAL = 5
MAX_POLLS = 60  # ~5 min


def _build_prompt(excluded_ids: set[str]) -> str:
    excluded = ", ".join(sorted(excluded_ids)[:50]) if excluded_ids else "（无）"
    return f"""请推荐一位著名导演及其一部经典电影。

要求：
1. 导演需为影史公认大师（如希区柯克、库布里克、黑泽明、费里尼等）
2. 电影需为该导演的代表作
3. 严格按以下 JSON 格式返回，不要包含其他文字或 markdown 标记：
{{
  "director": "导演中文名",
  "movie": "电影中文名",
  "year": 年份数字,
  "reason": "推荐理由，一两句话",
  "brief": "电影简介，2-3句话"
}}

已推荐过的电影（请勿重复）：{excluded}
"""


def create_task(client: httpx.Client, api_key: str, prompt: str) -> str:
    """Create Manus task and return task_id."""
    r = client.post(
        f"{MANUS_BASE}/v1/tasks",
        headers={"API_KEY": api_key, "Content-Type": "application/json"},
        json={"prompt": prompt, "agentProfile": "manus-1.6"},
    )
    r.raise_for_status()
    data = r.json()
    task_id = data.get("task_id")
    if not task_id:
        raise ValueError("Manus API did not return task_id")
    return task_id


def get_task(client: httpx.Client, api_key: str, task_id: str) -> dict[str, Any]:
    """Get task by ID."""
    r = client.get(
        f"{MANUS_BASE}/v1/tasks/{task_id}",
        headers={"API_KEY": api_key},
    )
    r.raise_for_status()
    return r.json()


def poll_until_done(
    client: httpx.Client, api_key: str, task_id: str
) -> dict[str, Any]:
    """Poll task until completed or failed."""
    for _ in range(MAX_POLLS):
        task = get_task(client, api_key, task_id)
        status = task.get("status", "")
        if status == "completed":
            return task
        if status == "failed":
            raise RuntimeError(f"Manus task failed: {task.get('error', 'unknown')}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError("Manus task did not complete in time")


def _extract_json_from_output(output: list[dict]) -> dict[str, Any]:
    """Extract JSON from assistant output_text content."""
    for msg in output:
        if msg.get("role") != "assistant":
            continue
        for c in msg.get("content", []):
            if c.get("type") == "output_text" and c.get("text"):
                text = c["text"].strip()
                # Try to find JSON block
                start = text.find("{")
                end = text.rfind("}") + 1
                if start >= 0 and end > start:
                    try:
                        return json.loads(text[start:end])
                    except json.JSONDecodeError:
                        pass
    raise ValueError("Could not parse JSON from Manus output")


def recommend_movie(api_key: str, excluded_ids: set[str]) -> dict[str, Any]:
    """
    Call Manus API to get a movie recommendation.
    Returns dict with director, movie, year, reason, brief.
    """
    prompt = _build_prompt(excluded_ids)
    with httpx.Client(timeout=120.0) as client:
        task_id = create_task(client, api_key, prompt)
        logger.info("Created Manus task %s", task_id)
        task = poll_until_done(client, api_key, task_id)
    return _extract_json_from_output(task.get("output", []))
