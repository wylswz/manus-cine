# manus-cine 需求文档

## 1. 项目概述

manus-cine 是一个定时运行的 Python 项目，通过调用 Manus API 推荐著名导演的经典电影，生成预告风格的 Markdown 文件，并通过飞书发送给用户。已推荐电影会持久化存储，避免重复推荐。

## 2. 功能需求

### 2.1 核心流程

1. **获取推荐**：调用 Manus API，请求推荐一位著名导演及其经典电影
2. **生成预告**：根据推荐结果生成 Markdown 格式的「电影预告」文档
3. **发送飞书**：将预告内容通过飞书 API 发送到指定群组/用户
4. **持久化记录**：将本次推荐的电影信息写入 `recommended/` 目录
5. **自动提交**：运行结束后，将新生成的文件自动 commit 到 Git 仓库

### 2.2 去重机制

- **存储位置**：`recommended/` 目录
- **存储格式**：每部电影一个 JSON 文件，命名规则：`{director_slug}_{movie_slug}.json`
- **去重逻辑**：每次推荐前，从 Manus 返回的候选中排除 `recommended/` 中已存在的电影
- **持久化内容**：导演名、电影名、推荐时间、简要信息等

### 2.3 输出物

- **预告 Markdown**：存放在 `trailers/` 目录，命名如 `{date}_{director}_{movie}.md`
- **Markdown 结构**：包含电影名、导演、简介、推荐理由、海报/链接等（可扩展）

## 3. 技术需求

### 3.1 技术栈

| 组件 | 选型 |
|------|------|
| 语言 | Python 3.12+ |
| 包管理 | uv |
| Manus API | REST API，Base URL: `https://api.manus.ai` |
| 飞书 API | REST API，消息发送端点: `https://open.feishu.cn/open-apis/im/v1/messages` |

### 3.2 环境变量（Secrets）

| 变量名 | 说明 | 来源 |
|-------|------|------|
| `MANUS_API_KEY` | Manus API 密钥 | GitHub Secrets |
| `FEISHU_APP_ID` | 飞书应用 App ID | GitHub Secrets |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | GitHub Secrets |
| `FEISHU_CHAT_ID` | 飞书群组/用户 ID（接收消息） | GitHub Secrets |

### 3.3 Manus API 调用

- **认证**：请求头 `API_KEY: {MANUS_API_KEY}`
- **创建任务**：`POST /v1/tasks`
- **Prompt 示例**：  
  「请推荐一位著名导演及其一部经典电影。要求：1) 导演需为影史公认大师；2) 电影需为该导演代表作；3) 返回 JSON：`{director, movie, year, reason, brief}`。不要推荐我已经推荐过的电影，已知列表：[从 recommended/ 读取]」

### 3.4 飞书 API 调用

- **认证**：需先获取 `tenant_access_token`（通过 App ID + App Secret）
- **发送消息**：`POST https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id`
- **消息类型**：支持 `text` 或富文本，可将 Markdown 转为飞书支持的格式

## 4. 自动化需求

### 4.1 GitHub Actions

- **触发方式**：定时触发（如每日一次，可配置 cron）
- **执行步骤**：
  1. Checkout 代码
  2. 配置 uv 环境并安装依赖
  3. 设置 Secrets 为环境变量
  4. 运行主程序 `uv run python -m manus_cine`
  5. 若有新文件（`trailers/`、`recommended/`），执行 git add、commit、push

### 4.2 自动 Commit

- **提交范围**：仅 `trailers/` 和 `recommended/` 下的新增/修改文件
- **Commit 信息**：`feat: add trailer for {director} - {movie}` 或类似约定
- **权限**：Workflow 需具备 `contents: write` 以 push 到仓库

## 5. 非功能需求

- **幂等性**：同一电影不应被重复推荐
- **容错**：API 调用失败时记录日志，可重试或跳过，不导致整个流程崩溃
- **可观测**：关键步骤有日志输出，便于排查问题

## 6. 目录结构

```
manus-cine/
├── pyproject.toml
├── src/
│   └── manus_cine/
│       ├── __init__.py
│       ├── main.py          # 入口
│       ├── manus.py         # Manus API 封装
│       ├── feishu.py        # 飞书 API 封装
│       ├── storage.py       # recommended/ 读写
│       └── trailer.py       # Markdown 生成
├── recommended/             # 已推荐电影记录
├── trailers/                # 生成的预告 MD
├── docs/
│   └── REQUIREMENTS.md
└── .github/
    └── workflows/
        └── recommend.yml
```

## 7. 验收标准

- [ ] 使用 uv 创建并管理项目依赖
- [ ] 能成功调用 Manus API 获取电影推荐
- [ ] 能生成符合约定的 Markdown 预告文件
- [ ] 能通过飞书 API 发送消息
- [ ] 已推荐电影写入 `recommended/` 且不会重复推荐
- [ ] GitHub Action 能定时触发并完成自动 commit
