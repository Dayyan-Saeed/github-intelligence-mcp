# GitHub Intelligence MCP

An intelligent, structured MCP (Model Context Protocol) server for investigating
and analyzing GitHub repositories.

> **Status:** under active development. Phase 1 (MVP) in progress — see
> `GitHub Intelligence MCP.md` for the full specification and roadmap.

## Overview

This MCP server exposes GitHub repository data as structured, validated tools
that MCP-compatible AI clients can use to investigate repositories:

- `get_repository` — structured repository metadata

More tools (`search_repositories`, `get_issues`, `get_pull_requests`,
`get_recent_commits`, `get_contributors`, `get_releases`) are being added in
Phase 1, followed by deterministic repository health analysis.

## Documentation

- `docs/architecture.md` — architecture overview *(coming with Phase 1)*
- `docs/development.md` — development setup and workflow *(coming with Phase 1)*

## License

MIT — see [LICENSE](LICENSE).
