"""Manus API client for movie recommendations."""

import logging
import re
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

**输出要求：直接从下面格式的第一行开始输出，不要有任何前言、说明或对话性文字。**

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

## 预告片（如有）
这里贴上一个目前 YouTube 上可观看的预告片链接。

## 同行评价（如有）
来自电影行业德高望重的导演、编剧、摄影师、制片人对该电影的评价

重要：请**以附件/文件形式单独输出** 1 张该电影的海报或经典镜头截图（使用平台的「上传/输出文件」能力），不要在图里写链接，正文报告里也不要出现任何配图或图片链接。我们会用你输出的文件在本地组装推送。
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


def _looks_like_report(text: str) -> bool:
    """True if text IS the report: starts directly with the markdown title line."""
    t = text.strip()
    if not t or len(t) < 100:
        return False
    # The report always starts with the movie title as a top-level heading.
    # Conversational preambles ("我已经为你挑选了…") never start with "# ".
    if not t.startswith("# "):
        return False
    has_section = "## 故事" in t or "## 影像" in t or "导演：" in t
    return bool(has_section)


def _extract_text_from_output(output: list[dict]) -> str:
    """Extract the markdown report body from Manus task output. Prefer the block that looks like the actual report (## 故事, 导演：), not the short meta-description."""
    candidates: list[str] = []
    for msg in output:
        if msg.get("role") != "assistant":
            continue
        for c in msg.get("content", []):
            if c.get("type") != "output_text":
                continue
            t = (c.get("text") or "").strip()
            if not t:
                continue
            candidates.append(t)
    if not candidates:
        raise ValueError("No text output found in Manus response")
    # Prefer the one that looks like our report format
    for t in candidates:
        if _looks_like_report(t):
            return t
    # Else return the longest (report is usually longer than meta-description)
    return max(candidates, key=len)


def _extract_output_files(output: list[dict]) -> list[dict[str, str]]:
    """Extract output_file items from Manus task output (e.g. image attachments). Returns list of {file_url, file_name, mime_type}."""
    files: list[dict[str, str]] = []
    for msg in output:
        if msg.get("role") != "assistant":
            continue
        for c in msg.get("content", []):
            if c.get("type") != "output_file":
                continue
            url = c.get("fileUrl") or c.get("file_url")
            if not url:
                continue
            name = c.get("fileName") or c.get("file_name") or "image"
            mime = (c.get("mimeType") or c.get("mime_type") or "").lower()
            is_image = (
                mime.startswith("image/")
                or name.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"))
            )
            if is_image:
                files.append({"file_url": url, "file_name": name, "mime_type": mime or "image/jpeg"})
    return files


def parse_metadata(markdown: str) -> dict[str, str]:
    """Extract director, movie, year and optional English title from markdown header lines."""
    director = ""
    movie = ""
    year = ""
    original_title = ""
    for line in markdown.splitlines():
        line = line.strip()
        if line.startswith("# "):
            # "# 电影名 / Original Title"  or  "# 电影名"
            rest = line[2:].strip()
            parts = rest.split(" / ", 1)
            movie = parts[0].split("/")[0].strip()
            if len(parts) > 1:
                original_title = parts[1].strip()
        if line.startswith("导演：") or line.startswith("**导演**："):
            part = line.replace("**导演**：", "").replace("导演：", "")
            director = part.split("　")[0].split(" ")[0].strip()
        if "年份：" in line or "**年份**：" in line:
            part = line.replace("**年份**：", "").split("年份：")[-1]
            year = part.split("　")[0].split(" ")[0].strip()
        if movie and director:
            break
    return {"director": director, "movie": movie, "year": year, "original_title": original_title}


# Match Markdown image syntax ![alt](url). URL can be any non-) chars.
_IMG_RE = re.compile(r"!\[[^\]]*\]\s*\(\s*(https?://[^)\s]+)\s*\)")
_HTTP_RE = re.compile(r"https?://[^\s)\]]+", re.IGNORECASE)


def extract_image_urls(markdown: str) -> list[str]:
    """Collect image URLs from markdown: ![alt](url) anywhere, and plain http(s) URLs in ## 配图 section."""
    urls: list[str] = []
    in_fig = False
    for line in markdown.splitlines():
        s = line.strip()
        if s.startswith("## ") and "配图" in s:
            in_fig = True
            continue
        if in_fig and s.startswith("## "):
            in_fig = False
        if in_fig and s and ("http://" in s or "https://" in s):
            # Plain URL line in 配图 section
            m = _HTTP_RE.search(s)
            if m:
                urls.append(m.group(0).rstrip(".,;)"))
        for m in _IMG_RE.finditer(line):
            urls.append(m.group(1))
    if not urls:
        for m in _IMG_RE.finditer(markdown):
            urls.append(m.group(1))
    return urls


def strip_fig_section(markdown: str) -> str:
    """Remove ## 配图 ... block so we don't show raw URLs in Feishu post (image is embedded instead)."""
    lines = markdown.splitlines()
    out: list[str] = []
    skip = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## ") and "配图" in stripped:
            skip = True
            continue
        if skip and stripped.startswith("## "):
            skip = False
        if skip:
            continue
        out.append(line)
    return "\n".join(out).strip()


def recommend_movie(
    api_key: str,
    excluded_movies: list[str],
    resume_task_id: str | None = None,
) -> dict[str, str]:
    """
    Call Manus API to get a movie recommendation.
    If resume_task_id is provided, skip task creation and poll/fetch that task directly.
    Returns {"markdown": "...", "director": "...", "movie": "...", "task_id": "..."}.
    """
    with httpx.Client(timeout=120.0) as client:
        if resume_task_id:
            logger.info("Resuming existing Manus task %s", resume_task_id)
            task = get_task(client, api_key, resume_task_id)
            if task is None:
                raise ValueError(f"Task {resume_task_id} not found")
            status = task.get("status", "")
            if status not in ("completed", "failed"):
                logger.info("Task %s status=%s, polling until done...", resume_task_id, status)
                task = poll_until_done(client, api_key, resume_task_id)
            elif status == "failed":
                raise RuntimeError(f"Manus task {resume_task_id} already failed: {task.get('error')}")
            task_id = resume_task_id
        else:
            prompt = _build_prompt(excluded_movies)
            task_id = create_task(client, api_key, prompt)
            logger.info("Created Manus task %s", task_id)
            task = poll_until_done(client, api_key, task_id)
    output = task.get("output", [])
    markdown = _extract_text_from_output(output)
    meta = parse_metadata(markdown)
    image_files = _extract_output_files(output)
    return {"markdown": markdown, "image_files": image_files, "task_id": task_id, **meta}
