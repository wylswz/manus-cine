---
name: manus-cine
description: >-
  Guides development of manus-cine: a Python project that uses Manus API to recommend
  famous directors' classic films, generates trailer markdown, and sends via Feishu.
  Use when working on manus-cine, Manus API integration, Feishu messaging, movie
  recommendation logic, or GitHub Actions automation.
---

# Manus Cine Project

## Project Overview

manus-cine is a scheduled Python project that:
1. Calls Manus API to recommend famous directors' classic movies
2. Generates trailer preview markdown files
3. Sends recommendations via Feishu
4. Persists recommended movies to avoid duplicates
5. Runs on GitHub Actions with auto-commit

## Tech Stack

- **Runtime**: Python 3.12+
- **Package manager**: uv (not pip/poetry)
- **APIs**: Manus API (https://api.manus.ai), Feishu Open API

## Best Practices

### Code Style

- Use `uv` for all dependency management: `uv add`, `uv sync`, `uv run`
- Type hints on all public functions
- Async preferred for I/O (Manus, Feishu, file ops)
- Logging via `logging` module, no print for production paths

### Project Structure

```
manus-cine/
├── src/manus_cine/       # Main package
├── recommended/          # Persisted movie records (git-tracked)
├── trailers/             # Generated markdown trailers
├── docs/                 # Requirements, design docs
└── .github/workflows/    # CI/CD
```

### Secrets & Environment

- All tokens via environment variables: `MANUS_API_KEY`, `FEISHU_*`
- Never commit secrets; use GitHub Secrets for Actions
- Validate required env vars at startup

### Idempotency

- Recommended movies stored in `recommended/` (one file per movie, e.g. `{director}_{title}.json`)
- Before recommending, check `recommended/` for existing entries
- Use deterministic identifiers (director + title) for deduplication

### Error Handling

- Retry with backoff for transient API failures
- Fail gracefully: log errors, don't crash entire run
- Return exit codes: 0 success, 1 for recoverable, 2 for fatal

### Testing

- Unit tests in `tests/` with pytest
- Mock external APIs in tests
- Run: `uv run pytest`

## Key Workflows

### Adding a Dependency

```bash
uv add <package>
```

### Running Locally

```bash
export MANUS_API_KEY=xxx FEISHU_APP_ID=xxx FEISHU_APP_SECRET=xxx
uv run python -m manus_cine
```

### Commit After Run

GitHub Action runs the script, then commits new files in `trailers/` and `recommended/` with a conventional commit message.

## Reference

- [REQUIREMENTS.md](../../docs/REQUIREMENTS.md) - Full requirements
- Manus API: https://open.manus.ai/docs
- Feishu API: https://open.feishu.cn/document
