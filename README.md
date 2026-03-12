# manus-cine

通过 Manus API 推荐著名导演的经典电影，生成预告 Markdown，并通过飞书发送。已推荐电影持久化到 `recommended/` 避免重复。

## 快速开始

### 环境变量

| 变量 | 说明 |
|------|------|
| `MANUS_API_KEY` | Manus API 密钥 |
| `FEISHU_APP_ID` | 飞书应用 App ID |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret |
| `FEISHU_CHAT_ID` | 飞书群组/用户 ID（接收消息） |

### 本地运行

```bash
uv run python -m manus_cine
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

## 文档

- [需求文档](docs/REQUIREMENTS.md)
