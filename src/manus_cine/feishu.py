"""Feishu (Lark) API client."""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MESSAGE_URL = "https://open.feishu.cn/open-apis/im/v1/messages"


def get_tenant_access_token(app_id: str, app_secret: str) -> str:
    with httpx.Client(timeout=30.0) as client:
        r = client.post(TOKEN_URL, json={"app_id": app_id, "app_secret": app_secret})
        r.raise_for_status()
        data = r.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu token error: {data}")
    return data["tenant_access_token"]


def send_message(
    token: str,
    receive_id: str,
    receive_id_type: str,
    text: str,
) -> dict[str, Any]:
    payload = json.dumps({
        "receive_id": receive_id,
        "msg_type": "text",
        "content": json.dumps({"text": text}, ensure_ascii=False),
    }, ensure_ascii=False)
    with httpx.Client(timeout=30.0) as client:
        r = client.post(
            MESSAGE_URL,
            params={"receive_id_type": receive_id_type},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            content=payload.encode("utf-8"),
        )
    logger.debug("Feishu response: %s %s", r.status_code, r.text)
    resp = r.json()
    if resp.get("code") != 0:
        raise RuntimeError(f"Feishu send error: {resp}")
    return resp


def send_trailer_to_feishu(
    app_id: str,
    app_secret: str,
    chat_id: str,
    text: str,
    receive_id_type: str = "chat_id",
) -> None:
    token = get_tenant_access_token(app_id, app_secret)
    send_message(token, chat_id, receive_id_type, text)
    logger.info("Sent to Feishu %s %s", receive_id_type, chat_id)
