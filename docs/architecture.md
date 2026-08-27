# Architecture

This document records *why* the system is shaped the way it is. Decisions are
listed with the alternatives considered, so future maintainers can revisit
them without archaeology.

## Layer map

```
src/github_intelligence_mcp/
├── server.py        MCP assembly: config + client lifecycle + registration
├── config.py        typed settings (env / .env), SecretStr token
├── logging.py       stderr-only structured logging setup
├── tools/           MCP boundary: schemas, guards, error translation
│   ├── _guard.py    shared timing/logging/error-translation helper
│   ├── parameters.py  shared Annotated input types (owner/repo/limit…)
│   └── <domain>.py  one module per domain (repositories, issues, …)
├── github/          GitHub REST client + payload→model mapping
│   ├── client.py    httpx wrapper: auth, retries, rate limits, pagination
│   ├── payloads.py  defensive payload access helpers
│   └── <domain>.py  one service module per domain
├── analysis/        deterministic scoring and risk detection
│   ├── scoring.py   shared primitives (capped_ratio, balance_ratio, …)
│   ├── analyzer.py  snapshot gathering + orchestrator
│   ├── health.py    overall score aggregation + grade mapping
│   ├── activity.py, issue_health.py, pr_health.py, …  per-component scorers
│   ├── risks.py     maintenance risk detection rules
│   └── comparison.py  side-by-side repository comparison
├── models/          stable Pydantic response models (output contract)
├── errors/          domain exception hierarchy
└── utils/validation.py  input allow-list validators
```

Dependency rule: `server → tools → github → (models, errors)`. Arrows point
one way. The `github` package imports nothing from `tools` or `server`; the
`models` package imports nothing at all from the other layers.

## Decisions

### Official `mcp` SDK (`MCPServer`) instead of standalone FastMCP

The spec allows "FastMCP / official MCP Python ecosystem". We pinned the
official SDK (v2.x), whose high-level `MCPServer` provides the same
decorator-based authoring model plus in-process `list_tools`/`call_tool` for
integration tests. Fewer third-party dependencies, no fork risk.

### stdio transport

Local MCP clients speak stdio JSON-RPC by default; HTTP transports add auth
and hosting concerns irrelevant to V1. Consequence: **all logs must go to
stderr** — stdout carries the protocol stream (`logging.py` enforces this).

### Reusable async client, one per server

`httpx.AsyncClient` pools connections; creating one per call would waste
sockets and TLS handshakes. The client is constructed eagerly (no I/O) and
closed via the server lifespan hook, so shutdown is deterministic.

### Explicit payload mapping instead of alias magic

Raw GitHub payloads are mapped field-by-field onto public models
(`github/repositories.py::build_repository_response`). Aliases would couple
our output contract to upstream key names forever; explicit mapping keeps
tool schemas stable when GitHub renames or adds fields, and makes required
vs optional explicit and testable.

### Bounded pagination with a filter-aware scan ceiling

`get_paginated(max_items=…)` caps every list fetch. The issues endpoint also
returns pull requests, so it uses the `keep` predicate: matching entries
count toward `max_items`, raw scanning is capped by `max_scan` (default 250)
so a PR-heavy repository can never trigger unbounded paging.

### Bounded retries, never unbounded

Transient failures (5xx, transport errors) retry up to 3 times with
exponential backoff capped at 4s. 4xx responses are never retried — they are
deterministic failures (auth, permission, validation) that retrying would
only amplify, burning the very rate limit we track.

### Rate-limit awareness via response headers

Every response updates `RateLimitInfo(limit, remaining, reset_at)` read from
`x-ratelimit-*` headers. A 403/429 carrying `remaining=0` maps to
`GitHubRateLimitError` including the reset time, so agents can schedule a
retry themselves instead of hammering.

### Errors as values at the boundary

Domain exceptions (`errors/exceptions.py`) carry user-safe messages and
metadata only. The tool guard translates them into SDK `ToolError`s whose
text is exactly what clients receive. Anything unanticipated is masked to a
generic message by the SDK — defense in depth against information leakage.

### Validation twice, deliberately

Input schemas (Pydantic `Annotated` constraints) validate at the protocol
boundary; service functions re-validate semantics (enum membership,
range checks, owner/repo allow-lists). The schema layer protects the LLM
from malformed calls; the service layer protects against any caller that
bypasses the schema.

### Read-only V1

Write operations multiply security review surface for little portfolio value.
Every tool being read-only means worst-case failure is a wasted API call.

### Caching deferred to Phase 4

Config keys exist now (`CACHE_ENABLED`, `CACHE_TTL_SECONDS`) so deployment
docs don't churn later, but the MVP has no cache layer: correctness first,
rate-limit pressure is manageable at MVP scale, and premature caching adds
staleness bugs that would undermine trust in every metric.

### Deterministic scoring with no LLM involvement

Health scores and risk detection are computed entirely in code using explicit
formulas documented in `docs/health-scoring.md`. The LLM never judges
repository health — it can call `analyze_repository`, `find_maintenance_risks`,
and `compare_repositories` to get structured, evidence-backed reports, then
interpret them for the user. This design ensures reproducibility, testability,
and immunity to prompt injection or model mood.

### Snapshot → score separation

`AnalysisSnapshot` gathers raw data from the GitHub API once; scoring functions
and risk detectors consume it without touching the network. This makes the
scoring engine testable with fabricated snapshots (no API mocking needed for
unit tests), and allows `compare_repositories` to score two repos in parallel
with one snapshot-gathering pass each.
