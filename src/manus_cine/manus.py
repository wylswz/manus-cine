"""Manus API client for movie recommendations."""

import logging
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

MANUS_BASE = "https://api.manus.ai"
POLL_INTERVAL = 5
INITIAL_DELAY = 10
MAX_POLLS = 60  # ~5 min


def _build_prompt(excluded_movies: list[str]) -> str:
    if excluded_movies:
        excluded_block = "\n".join(f"- {m}" for m in excluded_movies)
        excluded_note = f"以下电影已推荐过，请勿重复：\n{excluded_block}"
    else:
        excluded_note = "目前尚无推荐记录。"

    return f"""你是一位资深影评人，请推荐一部值得深度品鉴的电影，并写一篇短评报告。

选片范围：
- 知名作者导演的代表作（库布里克、希区柯克、塔可夫斯基、伯格曼、黑泽明、大卫·林奇、王家卫等）
- 欧洲艺术电影（东欧、北欧、南欧均可）、亚洲独立电影、拉美电影等被忽视的小众佳作
- 时间不限，新老兼顾
- 只要在某方面出彩即可：影像构图、色彩、叙事结构、音效配乐、节奏感、留白……

{excluded_note}

报告格式（严格按此格式输出，不要其他内容）：

# 电影名 / Original Title
导演：XXX　年份：YYYY　国家：Country

## 故事

（文学化的剧情与人物描述，100字左右）

## 影像

（构图、色调、镜头语言、光影运用，80字左右）

## 叙事

（时间结构、视角、节奏、主题意涵，80字左右）

## 为何值得一看

（这部电影留下了什么，对观影者意味着什么，60字左右）
"""


def create_task(client: httpx.Client, api_key: str, prompt: str) -> str:
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


def get_task(client: httpx.Client, api_key: str, task_id: str) -> dict[str, Any] | None:
    """Returns None if task not yet available (404)."""
    r = client.get(
        f"{MANUS_BASE}/v1/tasks/{task_id}",
        headers={"API_KEY": api_key},
    )
    if r.status_code == 404:
        logger.debug("Task %s not yet available, retrying...", task_id)
        return None
    r.raise_for_status()
    return r.json()


def poll_until_done(client: httpx.Client, api_key: str, task_id: str) -> dict[str, Any]:
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


def _extract_text_from_output(output: list[dict]) -> str:
    """Extract the markdown report text from Manus task output."""
    for msg in reversed(output):
        if msg.get("role") != "assistant":
            continue
        for c in msg.get("content", []):
            if c.get("type") == "output_text" and c.get("text", "").strip():
                return c["text"].strip()
    raise ValueError("No text output found in Manus response")


def parse_metadata(markdown: str) -> dict[str, str]:
    """Extract director and movie name from markdown header lines."""
    director = ""
    movie = ""
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("# "):
            # "# 电影名 / Original Title"  or  "# 电影名"
            title_part = line[2:].split(" / ")[0].split("/")[0].strip()
            movie = title_part
        if line.startswith("导演：") or line.startswith("**导演**："):
            part = line.replace("**导演**：", "").replace("导演：", "")
            director = part.split("　")[0].split(" ")[0].strip()
        if movie and director:
            break
    return {"director": director, "movie": movie}


def recommend_movie(api_key: str, excluded_movies: list[str]) -> dict[str, str]:
    """
    Call Manus API to get a movie recommendation.
    Returns {"markdown": "...", "director": "...", "movie": "..."}.
    """
    prompt = _build_prompt(excluded_movies)
    with httpx.Client(timeout=120.0) as client:
        task_id = create_task(client, api_key, prompt)
        logger.info("Created Manus task %s", task_id)
        task = poll_until_done(client, api_key, task_id)
    markdown = _extract_text_from_output(task.get("output", []))
    meta = parse_metadata(markdown)
    return {"markdown": markdown, **meta}
