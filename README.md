# GitHub Intelligence MCP

An intelligent, structured MCP (Model Context Protocol) server for
investigating and analyzing GitHub repositories.

MCP-compatible AI clients (OpenCode, Claude, Cursor, etc.) connect to this
server and gain read-only tools that return **deterministic, validated,
structured JSON** about any GitHub repository — metadata, issues, pull
requests, commits, contributors, releases, and search.

## Why it exists

AI agents answering questions like *"analyze facebook/react"* or *"find stale
issues"* need reliable facts. Computing repository metrics with an LLM is slow,
expensive, and error-prone. This server does the deterministic work in code —
fetching, validating, bounding, and structuring GitHub data — so the LLM can
focus on what it is good at: reasoning and explanation.

## Architecture

```
 ┌───────────────────────────── MCP client (LLM) ─────────────────────────────┐
 │  asks questions, reasons over structured results                          │
 └───────────────────────────────┬───────────────────────────────────────────┘
                                 │ MCP protocol (stdio JSON-RPC)
 ┌───────────────────────────────▼───────────────────────────────────────────┐
 │  server.py            MCPServer assembly + tool registration              │
 ├───────────────────────────────────────────────────────────────────────────┤
 │  tools/*             tool boundary: validation, logging, clean errors     │
 ├───────────────────────────────────────────────────────────────────────────┤
 │  github/*            async GitHub REST client (httpx), payload mapping    │
 ├───────────────────────────────────────────────────────────────────────────┤
 │  models/*            stable Pydantic response models (output contract)    │
 └───────────────────────────────┬───────────────────────────────────────────┘
                                 │ HTTPS + Bearer token
                        ▼  GitHub REST API v3
```

Key layers are strictly separated: the `github` package knows nothing about
MCP; the `tools` package contains no HTTP logic; the `models` package defines
a stable output contract decoupled from raw API payloads. See
[docs/architecture.md](docs/architecture.md) for the reasoning behind every
decision.

## Available tools (Phase 1 MVP)

| Tool | Description |
|---|---|
| `get_repository` | Structured metadata for one repository (stars, forks, license, timestamps, …) |
| `search_repositories` | Search repos; optional sort (`stars`, `forks`, `help-wanted-issues`, `updated`), order, bounded limit |
| `get_issues` | Issues filtered by state/labels/sort — **pull requests automatically excluded** |
| `get_pull_requests` | PRs with created/updated/closed/merged timestamps and draft flag |
| `get_recent_commits` | Commits from the last N days (1–365) with author/committer info |
| `get_contributors` | Top contributors by contribution count |
| `get_releases` | Recent releases with tag, author, draft/prerelease flags |

All list operations accept a `limit` clamped to **1–100**, enforced twice:
once by the generated input schema, once inside the service layer.

### Example interaction

An MCP client calling the server over stdio:

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/call",
 "params": {"name": "get_repository", "arguments": {"owner": "facebook", "repo": "react"}}}
```

returns structured content:

```json
{
  "name": "react",
  "full_name": "facebook/react",
  "stars": 238000,
  "open_issues": 612,
  "license": "MIT",
  "default_branch": "main",
  "created_at": "2013-05-24T16:15:54Z"
}
```

Natural-language prompts the tools support:

- *"Compare stars, issue health, and recent activity of X and Y."*
- *"Who are the most active contributors of this repository?"*
- *"What was merged or released here recently?"*

## Installation

Requirements: Python **3.12+** and [uv](https://docs.astral.sh/uv/).

```bash
git clone <repository-url>
cd github-intelligence-mcp
uv sync
cp .env.example .env   # then set GITHUB_TOKEN in .env
```

Create a GitHub token at <https://github.com/settings/tokens> — a fine-grained
token with read-only access is sufficient.

## Running locally

```bash
uv run github-intelligence-mcp        # stdio transport (default)
```

## Connecting to an MCP client

Example OpenCode configuration (`opencode.json`):

```json
{
  "mcp": {
    "github-intelligence": {
      "type": "local",
      "command": ["uv", "run", "--directory", "/path/to/github-intelligence-mcp", "github-intelligence-mcp"],
      "environment": { "GITHUB_TOKEN": "your-token" }
    }
  }
}
```

Claude Desktop (`claude_desktop_config.json`) uses the equivalent
`mcpServers` block with `command`/`args`.

## Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `GITHUB_TOKEN` | yes | — | GitHub PAT used for all requests |
| `GITHUB_API_URL` | no | `https://api.github.com` | API root (useful for GitHub Enterprise) |
| `LOG_LEVEL` | no | `INFO` | `DEBUG`…`CRITICAL`; logs go to **stderr** |
| `REQUEST_TIMEOUT_SECONDS` | no | `30` | Per-request HTTP timeout |
| `CACHE_ENABLED` | no | `false` | Reserved for Phase 4 response caching |
| `CACHE_TTL_SECONDS` | no | `300` | Reserved for Phase 4 response caching |

Secrets are never hardcoded and never logged: the token lives in a
`SecretStr` and is only materialized inside the Authorization header.

## Error handling

Domain exceptions map to clean, user-safe messages — never stack traces,
never credentials:

| Situation | Client sees |
|---|---|
| Unknown/private repo | `Repository 'owner/repo' was not found or is inaccessible.` |
| Bad token | `GitHub rejected the configured credentials. Check GITHUB_TOKEN.` |
| Rate limit exhausted | `GitHub API rate limit exceeded. Please retry after the provided reset time. Reset at: …` |
| Missing permission | `The configured token does not have permission to access this resource.` |
| Invalid input | Field-specific validation message |

Transient failures (5xx, network errors) retry up to 3 times with capped
exponential backoff. Client errors are never retried.

## Repository health algorithm (Phase 2 roadmap)

Phase 2 adds deterministic scoring — no LLM involved — using explainable,
documented weights:

| Component | Weight | Signals |
|---|---|---|
| Activity | 25% | commits 30/90 days, active contributors, recent PRs/releases |
| Issue health | 20% | stale-issue ratio, closure activity, average age (stale = open & untouched ≥ 90 days) |
| PR health | 20% | open/stale PR counts, merge cadence (stale = open ≥ 30 days) |
| Contributor health | 15% | active contributor count, concentration / bus-factor risk |
| Release activity | 10% | release intervals over 30/90-day windows |
| Documentation | 10% | README/docs/license presence signals |

Each component yields a 0–100 score with published formulas so results are
reproducible.

## Security model

- **Read-only V1**: no write operations exist to misuse; attack surface stays minimal.
- Input allow-lists prevent path traversal via `owner`/`repo`.
- Pagination and retries are bounded by construction.
- Logs contain tool names, repos, durations, statuses — never tokens or headers.
- Unanticipated exceptions are masked by the SDK; clients only see curated messages.

## Testing

```bash
uv run pytest          # 100% offline — respx mocks every HTTP call
```

Unit tests cover config, validation, models, client behavior (auth headers,
error mapping, retries, rate limits, pagination), and service filtering.
Integration tests drive the real `MCPServer` instance end-to-end: schema
generation, dispatch, structured output, and error translation.

## Docker

```bash
docker build -t github-intelligence-mcp .
docker run --rm -i -e GITHUB_TOKEN=ghp_xxx github-intelligence-mcp
```

Multi-stage build on `python:3.12-slim`, runs as non-root, installs from the
committed `uv.lock`, and receives secrets only at runtime.

## Development

See [docs/development.md](docs/development.md). Quality gates:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy .
uv run pytest
```

CI runs all four on every push and pull request.

## Roadmap

- **Phase 2** — deterministic health analysis, maintenance-risk detection, repository comparison
- **Phase 3** — MCP resources (`github://repo/{owner}/{repo}/…`) and guided prompts
- **Phase 4** — SQLite response cache with per-endpoint TTLs, advanced rate-limit handling, GraphQL
- **Phase 5** — LangGraph autonomous investigation agent
- **Phase 6** — Next.js dashboard

## License

[MIT](LICENSE)
