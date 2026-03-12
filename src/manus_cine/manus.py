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


def _build_prompt(excluded_movies: list[str]) -> str:
    if excluded_movies:
        excluded_block = "\n".join(f"- {m}" for m in excluded_movies)
        excluded_note = f"以下电影已经推荐过，请勿重复选择：\n{excluded_block}"
    else:
        excluded_note = "目前尚无已推荐记录。"

    return f"""你是一位资深影评人，请从影史中推荐一部值得深度品鉴的电影。

要求：
1. 可以是知名导演的代表作，例如库布里克，希区柯克，大卫·林奇等等
2. 也可以推荐被忽视的小众作品，尤其是欧洲艺术电影（东欧、北欧、南欧均可）、亚洲独立电影、拉美电影等
3. 时间不限，可以是老电影，也可以是新电影。根据历史推荐来选择，两者兼顾。
4. 选片标准：在某一方面有突出成就即可，例如：影像构图、色彩运用、叙事结构、音效与配乐、时间感与节奏、对沉默与留白的处理……不必面面俱到
5. {excluded_note}
6. 严格只返回如下 JSON，不含任何其他文字或 markdown：
{{
  "director": "导演中文名",
  "movie": "电影中文名",
  "original_title": "原片名（英文或原语言）",
  "year": 年份数字,
  "country": "出品国",
  "synopsis": "剧情概述，用文学化的语言描述故事与人物，100字左右",
  "visual_style": "影像风格描述：构图、色调、镜头语言、光影运用，80字左右",
  "narrative": "叙事特点：时间结构、视角、节奏、主题意涵，80字左右",
  "why_watch": "为什么值得一看：这部电影留下了什么，对观影者意味着什么，60字左右"
}}
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


INITIAL_DELAY = 10  # seconds to wait before first poll


def get_task(client: httpx.Client, api_key: str, task_id: str) -> dict[str, Any] | None:
    """Get task by ID. Returns None if task not yet available (404)."""
    r = client.get(
        f"{MANUS_BASE}/v1/tasks/{task_id}",
        headers={"API_KEY": api_key},
    )
    if r.status_code == 404:
        logger.debug("Task %s not yet available (404), will retry", task_id)
        return None
    r.raise_for_status()
    return r.json()


def poll_until_done(
    client: httpx.Client, api_key: str, task_id: str
) -> dict[str, Any]:
    """Poll task until completed or failed."""
    logger.info("Waiting %ds before first poll...", INITIAL_DELAY)
    time.sleep(INITIAL_DELAY)

    for i in range(MAX_POLLS):
        task = get_task(client, api_key, task_id)
        if task is None:
            time.sleep(POLL_INTERVAL)
            continue
        status = task.get("status", "")
        if status == "completed":
            return task
        if status == "failed":
            raise RuntimeError(f"Manus task failed: {task.get('error', 'unknown')}")
        logger.debug("Poll %d: status=%s", i, status)
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


def recommend_movie(api_key: str, excluded_movies: list[str]) -> dict[str, Any]:
    """
    Call Manus API to get a movie recommendation.
    Returns dict with director, movie, year, synopsis, visual_style, narrative, why_watch.
    """
    prompt = _build_prompt(excluded_movies)
    with httpx.Client(timeout=120.0) as client:
        task_id = create_task(client, api_key, prompt)
        logger.info("Created Manus task %s", task_id)
        task = poll_until_done(client, api_key, task_id)
    return _extract_json_from_output(task.get("output", []))
