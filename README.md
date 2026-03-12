# manus-cine

通过 Manus API 推荐著名导演的经典电影，生成预告 Markdown，并通过飞书发送。已推荐电影持久化到 `recommended/` 避免重复。

## 快速开始

### 环境变量

| 变量 | 说明 |
|------|------|
| `MANUS_API_KEY` | Manus API 密钥 |
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `FEISHU_CHAT_ID` | 飞书群组 chat_id（以 `oc_` 开头）或用户 ID |
| `FEISHU_RECEIVE_ID_TYPE` | 可选，默认 `chat_id`，群组用 `chat_id`，用户可试 `open_id` |

### 本地运行

```bash
uv run python -m manus_cine
```

调试时可设置 `MOCK_MODE=1` 使用预设 mock 数据，跳过 Manus API 调用：

```bash
MOCK_MODE=1 uv run python -m manus_cine
# 或在 .env.local 中添加 MOCK_MODE=1
```

获取可用的 `FEISHU_CHAT_ID`（需先将机器人加入群聊）：

```bash
uv run python -m manus_cine --list-chats
```

### GitHub Actions

- **定时**：每日 09:00 UTC（北京时间 17:00）
- **手动**：在 Actions 页面选择 "Recommend Movie" → "Run workflow"

在仓库 Settings → Secrets and variables → Actions 中配置上述四个环境变量。

运行结束后，新生成的 `trailers/` 和 `recommended/` 文件会自动 commit 并 push。

## 项目结构

```
manus-cine/
├── src/manus_cine/    # 主逻辑
├── recommended/       # 已推荐电影记录（JSON）
├── trailers/          # 生成的预告 Markdown
├── docs/              # 需求文档
└── .github/workflows/ # CI
```

## 故障排查

**230001 invalid receive_id**：`receive_id` 无效，需与 `receive_id_type` 对应：

| receive_id_type | 获取方式 |
|-----------------|----------|
| `chat_id` | [群 ID 说明](https://open.feishu.cn/document/server-docs/im-v1/chat-id-description) |
| `open_id` | [如何获取 Open ID](https://open.feishu.cn/document/home/user-identity-introduction/open-id) |
| `user_id` | [如何获取 User ID](https://open.feishu.cn/document/home/user-identity-introduction/user-id) |
| `union_id` | [如何获取 Union ID](https://open.feishu.cn/document/home/user-identity-introduction/union-id) |
| `email` | 用户真实飞书邮箱 |
| `thread_id` | [话题概述 - 获取 thread_id](https://open.feishu.cn/document/server-docs/im-v1/thread/overview) |

**其他飞书错误**：
- 230002：机器人未加入该群
- 230006：未开启机器人能力
- 权限不足：在飞书开放平台为应用添加「获取群组信息」「发送消息」等权限

## 文档

- [需求文档](docs/REQUIREMENTS.md)
