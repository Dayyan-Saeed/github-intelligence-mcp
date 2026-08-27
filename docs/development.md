# Development guide

## Prerequisites

- Python 3.12+ (uv installs its own interpreter if missing)
- [uv](https://docs.astral.sh/uv/) package manager
- Docker (optional, for container builds)

## Setup

```bash
uv sync                 # create .venv from uv.lock, install dev tools
cp .env.example .env    # add your GITHUB_TOKEN
```

## Daily commands

```bash
uv run pytest                     # full offline test suite
uv run pytest -q                  # quiet
uv run pytest tests/unit          # slice of the suite
uv run ruff check . --fix         # lint + autofix
uv run ruff format .              # format
uv run mypy .                     # strict type check
uv run github-intelligence-mcp    # start the server over stdio
```

All four quality gates must pass before committing. CI runs them on push/PR.

## Project layout

See [architecture.md](architecture.md) for the layer map and decision log.

## Testing philosophy

- **Offline always** — `respx` mocks all HTTP; no test needs network or a real token.
- **Fixtures over literals** — realistic payloads live in `tests/fixtures/*.json`.
- **Two levels**:
  - unit: services/models/client behavior, including error mapping and pagination bounds;
  - integration: the real `MCPServer` instance driven through `list_tools` /
    `call_tool`, asserting structured outputs and translated errors.
- Error-path assertions check the exact user-facing message, because those
  strings are part of the product contract.

## Adding a new tool (checklist)

1. **Model** — add the response model under `models/<domain>.py`; export it in
   `models/__init__.py`. Frozen config, only fields worth returning.
2. **Mapping helpers** — extend `github/payloads.py` if the payload needs new
   defensive accessors. Never index raw payloads directly in services.
3. **Service** — `github/<domain>.py`: validate inputs first, then fetch, then
   map. Raise domain exceptions, never return raw dicts.
4. **Tool** — `tools/<domain>.py`: thin implementation routed through
   `guarded_tool_call`, registered in a `register_*_tools(server, client)`
   function wired into `tools/__init__.py`.
5. **Tests** — fixture JSON + unit tests for validation/mapping/filtering +
   integration test asserting registration, happy path, and one error path.
6. **Gates** — pytest, ruff, format, mypy all green before commit.

## Commit conventions

Conventional Commits, one logical change per commit:

```text
feat: add get_issues, get_pull_requests, and get_recent_commits tools
feat: add analyze_repository tool with deterministic health report
feat: add find_maintenance_risks tool with evidence-backed risk detection
feat: add compare_repositories tool with side-by-side health comparison
fix: reject ".." repository names in validation
docs: record pagination design decisions
```

## Releasing

1. Update `__version__` in `src/github_intelligence_mcp/__init__.py`.
2. Verify `docker build -t github-intelligence-mcp .` succeeds.
3. Tag `vX.Y.Z` and push; CI must be green on main.
