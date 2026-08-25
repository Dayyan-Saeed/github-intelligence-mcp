# GitHub Intelligence MCP — Project Initialization & Implementation Specification

## 1. Role

You are the lead software engineer responsible for designing and implementing a production-quality MCP server called **GitHub Intelligence MCP**.

The goal is to build a portfolio-quality project that demonstrates:

- MCP protocol knowledge
- Python backend engineering
- GitHub API integration
- Tool/resource/prompt design
- Pydantic-based validation
- Async programming
- Error handling
- Caching
- Rate-limit awareness
- Security
- Automated testing
- Docker
- CI/CD
- AI-agent integration

Do NOT build a simple wrapper around the GitHub API.

The final project should provide an intelligent, structured interface that allows MCP-compatible AI clients to investigate and analyze GitHub repositories.

---

# 2. Product Vision

The system should allow an MCP-compatible AI client such as OpenCode or another MCP client to ask questions like:

- "Analyze facebook/react."
- "What has changed in this repository recently?"
- "Find stale issues."
- "Analyze the repository's pull request health."
- "Who are the most active contributors?"
- "Compare two repositories."
- "What are the maintenance risks?"
- "Give me an overall repository health score."
- "Investigate this repository and identify potential maintenance problems."

The MCP server should retrieve structured information from GitHub, calculate deterministic metrics where appropriate, and expose those capabilities through MCP.

The LLM should primarily be responsible for reasoning and explanation.

Do NOT rely on an LLM to calculate basic repository metrics that can be deterministically calculated in code.

---

# 3. Initial Scope

Implement the project incrementally.

Do NOT attempt to build every planned feature in the first implementation.

Start with a clean, working MVP containing:

1. MCP server
2. GitHub API client
3. Configuration system
4. Repository tools
5. Issue tools
6. Pull-request tools
7. Commit tools
8. Pydantic models
9. Structured error handling
10. Unit tests
11. Basic logging
12. README
13. `.env.example`

After the MVP is working and tested, prepare the project for later phases.

---

# 4. Recommended Technology Stack

Use:

- Python 3.12+
- FastMCP / official MCP Python ecosystem
- httpx for HTTP requests
- Pydantic v2
- pytest
- pytest-asyncio
- respx for mocking HTTP requests
- ruff
- mypy
- python-dotenv or equivalent configuration mechanism
- SQLite for future caching
- Docker for future deployment

Avoid unnecessary dependencies.

Do not introduce LangChain or LangGraph in the initial MCP implementation.

They will be added later as a separate agent integration layer.

---

# 5. Project Structure

Use a clean modular architecture similar to:

github-intelligence-mcp/
│
├── src/
│   └── github_intelligence_mcp/
│       │
│       ├── __init__.py
│       ├── server.py
│       ├── config.py
│       ├── logging.py
│       │
│       ├── github/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   ├── repositories.py
│       │   ├── issues.py
│       │   ├── pull_requests.py
│       │   ├── commits.py
│       │   └── contributors.py
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── repositories.py
│       │   ├── issues.py
│       │   ├── pull_requests.py
│       │   ├── commits.py
│       │   └── analysis.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── repository.py
│       │   ├── issue.py
│       │   ├── pull_request.py
│       │   ├── commit.py
│       │   └── contributor.py
│       │
│       ├── analysis/
│       │   ├── __init__.py
│       │   ├── health.py
│       │   ├── activity.py
│       │   ├── issue_health.py
│       │   ├── pr_health.py
│       │   └── contributor_health.py
│       │
│       ├── errors/
│       │   ├── __init__.py
│       │   └── exceptions.py
│       │
│       └── utils/
│           ├── __init__.py
│           └── validation.py
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── examples/
│
├── docs/
│
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── .env.example
├── .gitignore
├── Dockerfile
├── pyproject.toml
├── README.md
└── LICENSE

Keep dependencies between modules clean.

The MCP layer should not contain GitHub HTTP implementation details.

The GitHub client should not know about MCP.

The analysis layer should not depend directly on MCP.

---

# 6. Configuration

Create a typed configuration system.

Required environment variable:

GITHUB_TOKEN

Optional:

GITHUB_API_URL
LOG_LEVEL
CACHE_ENABLED
CACHE_TTL_SECONDS

Never hardcode secrets.

Never commit `.env`.

Add `.env` to `.gitignore`.

Provide `.env.example`.

---

# 7. GitHub API Client

Create a reusable asynchronous GitHub client.

Responsibilities:

- authentication
- HTTP requests
- headers
- timeout configuration
- response parsing
- GitHub error handling
- rate-limit information
- pagination support

Use `httpx.AsyncClient`.

Do not create a new HTTP client for every tool call.

Prefer a reusable client lifecycle.

Use the GitHub REST API initially.

Keep the client abstract enough that GraphQL can be added later.

---

# 8. GitHub API Requirements

The client should support:

Repositories:

GET /repos/{owner}/{repo}

Issues:

GET /repos/{owner}/{repo}/issues

Pull requests:

GET /repos/{owner}/{repo}/pulls

Commits:

GET /repos/{owner}/{repo}/commits

Contributors:

GET /repos/{owner}/{repo}/contributors

Releases:

GET /repos/{owner}/{repo}/releases

Repository search:

GET /search/repositories

Implement pagination where relevant.

Do not fetch unlimited data.

Every list operation must have a reasonable maximum limit.

For example:

minimum = 1
maximum = 100

Validate limits with Pydantic.

---

# 9. MCP Tools — MVP

Implement these tools first.

## Tool 1: get_repository

Input:

- owner
- repo

Output:

Structured repository information.

Include fields such as:

- name
- full_name
- description
- private
- fork
- stars
- forks
- watchers
- open_issues
- language
- license
- default_branch
- created_at
- updated_at
- pushed_at
- html_url

Do not return the entire raw GitHub API response.

Transform it into a stable Pydantic response model.

---

# 10. Tool 2: search_repositories

Input:

- query
- sort
- order
- limit

Supported sorting:

- stars
- forks
- help-wanted-issues
- updated

Return structured repository summaries.

Validate all inputs.

---

# 11. Tool 3: get_issues

Input:

- owner
- repo
- state
- labels
- sort
- direction
- limit

State:

- open
- closed
- all

Return structured issue objects.

Important:

GitHub's issues endpoint may also return pull requests.

Detect and handle this appropriately.

---

# 12. Tool 4: get_pull_requests

Input:

- owner
- repo
- state
- sort
- direction
- limit

Return:

- number
- title
- state
- author
- created_at
- updated_at
- closed_at
- merged_at
- draft
- labels
- html_url

---

# 13. Tool 5: get_recent_commits

Input:

- owner
- repo
- days
- limit

Validate:

days >= 1
days <= 365

Return:

- SHA
- message
- author
- author_date
- committer
- commit_date
- html_url

---

# 14. Tool 6: get_contributors

Input:

- owner
- repo
- limit

Return:

- username
- contributions
- avatar_url
- html_url

---

# 15. Tool 7: get_releases

Input:

- owner
- repo
- limit

Return:

- tag_name
- name
- author
- created_at
- published_at
- prerelease
- draft
- html_url

---

# 16. Structured Outputs

Every MCP tool must return predictable structured data.

Do not simply return huge strings.

Use Pydantic models.

For example:

RepositoryResponse

RepositorySummary

IssueResponse

PullRequestResponse

CommitResponse

ContributorResponse

ReleaseResponse

SearchRepositoriesResponse

Keep internal GitHub API models separate from public MCP response models where appropriate.

---

# 17. Error Handling

Create custom exceptions:

GitHubAuthenticationError
GitHubNotFoundError
GitHubRateLimitError
GitHubPermissionError
GitHubAPIError
ValidationError

Convert these into clean MCP-compatible errors.

Do not expose stack traces to users.

Do not expose GitHub tokens.

Example user-facing error:

"Repository 'owner/repo' was not found or is inaccessible."

For rate limits:

"GitHub API rate limit exceeded. Please retry after the provided reset time."

Include useful metadata when safe.

---

# 18. Logging

Implement structured application logging.

Log:

- tool name
- repository
- request duration
- success/failure
- GitHub API status
- cache hit/miss when caching is enabled

Never log:

- GitHub tokens
- Authorization headers
- environment secrets

Use configurable log levels.

---

# 19. Repository Analysis — Phase 2

After MVP tools work, implement:

analyze_repository()

This should combine GitHub data and calculate deterministic metrics.

Do not call an LLM.

Calculate:

Activity Score
Issue Health Score
PR Health Score
Contributor Health Score
Release Activity Score
Overall Health Score

---

# 20. Repository Health Algorithm

Use an explainable scoring system.

Initial weighting:

Activity: 25%
Issue Health: 20%
PR Health: 20%
Contributor Health: 15%
Release Activity: 10%
Documentation: 10%

Overall score:

activity * 0.25
+
issue_health * 0.20
+
pr_health * 0.20
+
contributor_health * 0.15
+
release_activity * 0.10
+
documentation * 0.10

Every component must produce a 0–100 score.

Document the exact scoring rules.

Do not use arbitrary hidden heuristics.

---

# 21. Activity Score

Use measurable signals such as:

- commits in last 30 days
- commits in last 90 days
- active contributors
- recent pull requests
- recent releases

Normalize values.

Avoid making the score unfair to extremely large repositories.

---

# 22. Issue Health Score

Consider:

- stale issue ratio
- issue closure activity
- average issue age
- open issue growth

Define "stale" clearly.

Initial definition:

An issue is stale if it has not been updated for 90+ days and remains open.

Make the threshold configurable.

---

# 23. Pull Request Health

Calculate:

- open PR count
- stale PR count
- average PR age
- recently merged PR count
- merge activity

Initial stale PR threshold:

30 days.

Make it configurable.

---

# 24. Contributor Health

Analyze:

- number of active contributors
- contribution distribution
- contributor concentration

Calculate a contributor concentration metric.

Detect potential "bus factor" risk.

Do not claim that a high concentration mathematically proves a project is unhealthy.

Use language such as:

"Potential contributor concentration risk."

---

# 25. Release Activity

Calculate:

- releases in last 30 days
- releases in last 90 days
- average release interval

Do not automatically assume frequent releases always mean a healthier repository.

Use release activity as one signal.

---

# 26. Maintenance Risk Detection

Create:

find_maintenance_risks()

Potential risk categories:

- stale issues
- stale pull requests
- inactive repository
- low recent commit activity
- high contributor concentration
- long release gaps
- unusually old open issues
- low contributor diversity

Return:

risk_level
risk_score
risks[]
evidence[]

Example:

{
  "risk_level": "medium",
  "risks": [
    {
      "type": "stale_issues",
      "severity": "medium",
      "description": "...",
      "evidence": {
        "stale_issue_count": 31
      }
    }
  ]
}

Every detected risk should have evidence.

---

# 27. Repository Comparison

Implement:

compare_repositories()

Input:

repository_a
repository_b

Compare:

- stars
- forks
- contributors
- commits
- open issues
- stale issues
- open PRs
- releases
- activity score
- issue health
- PR health
- overall health

Do not simply compare stars and declare a winner.

Return structured comparison data.

---

# 28. MCP Resources — Phase 3

Add resources such as:

github://repo/{owner}/{repo}

github://repo/{owner}/{repo}/issues

github://repo/{owner}/{repo}/pulls

github://repo/{owner}/{repo}/commits

github://repo/{owner}/{repo}/contributors

github://repo/{owner}/{repo}/releases

Resources should provide useful structured information.

Do not duplicate large amounts of data unnecessarily.

---

# 29. MCP Prompts — Phase 3

Create prompts such as:

analyze_repository

investigate_repository

review_maintenance_health

compare_repositories

summarize_recent_activity

Prompts should guide an LLM to use the appropriate MCP tools.

Do not put GitHub API implementation inside prompts.

---

# 30. Caching — Phase 4

Implement a cache abstraction.

Start with SQLite or an in-memory implementation.

Do not tightly couple GitHub tools to a specific cache implementation.

Example interface:

Cache.get(key)

Cache.set(key, value, ttl)

Cache.delete(key)

Cache.clear()

Suggested initial TTL:

Repository metadata: 10 minutes

Issues: 5 minutes

Pull requests: 5 minutes

Commits: 2 minutes

Contributors: 10 minutes

Releases: 10 minutes

Make TTL configurable.

---

# 31. Rate-Limit Awareness

Read GitHub rate-limit headers.

Track:

remaining
limit
reset

Avoid unnecessary requests.

When rate limits are low, return useful information.

Never implement uncontrolled retry loops.

For transient errors, use limited exponential backoff.

Do not retry authentication failures.

Do not retry validation failures.

---

# 32. Security Requirements

The server must be read-only in V1.

Do NOT implement:

create_issue
delete_issue
merge_pull_request
close_issue
comment_on_issue
create_repository
delete_repository

These can be future features.

Reasons:

- minimize attack surface
- avoid accidental destructive actions
- demonstrate security-conscious MCP design

Validate all tool inputs.

Never expose credentials.

Never log credentials.

Limit data returned by tools.

---

# 33. Testing Strategy

Write tests before declaring each feature complete.

Unit tests:

- GitHub client
- validation
- models
- health calculations
- stale detection
- contributor concentration
- repository comparison
- error mapping

Integration-style tests:

- MCP tool invocation
- mocked GitHub API
- pagination
- GitHub API failures
- rate-limit responses

Do not require a real GitHub token for tests.

Tests must run offline.

Target high coverage for analysis logic.

---

# 34. Quality Checks

The project should support:

ruff check .

ruff format --check .

mypy .

pytest

Use pyproject.toml as the central configuration.

Do not add unnecessary configuration files.

---

# 35. Docker

Create a minimal Dockerfile.

Requirements:

- small base image
- non-root user
- no secrets baked into image
- environment variables supplied at runtime
- deterministic dependency installation

The container should run the MCP server.

---

# 36. CI/CD

Create GitHub Actions workflow:

.github/workflows/ci.yml

Run on:

- push
- pull_request

Steps:

1. checkout
2. setup Python
3. install dependencies
4. run Ruff
5. run mypy
6. run pytest

The project must pass CI before considering the MVP complete.

---

# 37. README Requirements

The README should explain:

1. What the project is
2. Why it exists
3. Architecture
4. MCP concepts used
5. Available tools
6. Available resources
7. Available prompts
8. Installation
9. Configuration
10. Running locally
11. Connecting to an MCP client
12. Example interactions
13. Repository health algorithm
14. Security model
15. Testing
16. Docker
17. Roadmap

Include an ASCII architecture diagram if a graphical diagram is not available.

Include real example tool calls.

---

# 38. Documentation Quality

Document important architectural decisions.

Create:

docs/
├── architecture.md
├── tools.md
├── health-scoring.md
├── security.md
└── development.md

Explain WHY decisions were made.

For example:

Why REST API instead of GraphQL initially?

Why read-only?

Why deterministic scoring?

Why caching?

Why Pydantic?

Why separate GitHub client from MCP tools?

---

# 39. Future Roadmap

Do not implement these yet, but document them.

Phase 2:

- code search
- repository structure analysis
- maintenance risk detection
- repository comparison

Phase 3:

- MCP resources
- MCP prompts

Phase 4:

- SQLite cache
- advanced rate-limit handling
- GitHub GraphQL API

Phase 5:

- LangGraph agent
- autonomous repository investigation

Phase 6:

- Next.js dashboard

Phase 7:

- optional GitHub write operations with explicit authorization

---

# 40. Important Engineering Rules

Follow these rules throughout the project.

1. Prefer simple architecture over unnecessary abstraction.

2. Do not create giant files.

3. Keep functions small and focused.

4. Use type hints everywhere.

5. Use Pydantic for external input/output validation.

6. Avoid global mutable state.

7. Keep GitHub API logic separate from MCP logic.

8. Keep analysis logic deterministic and independently testable.

9. Do not use an LLM where ordinary code is more reliable.

10. Do not over-engineer caching in the MVP.

11. Do not implement write operations in V1.

12. Do not add dependencies unless they solve a real problem.

13. Do not silently swallow exceptions.

14. Never expose secrets.

15. Never hardcode credentials.

16. Do not make tests dependent on the live GitHub API.

17. Prefer async I/O.

18. Return structured data rather than large unstructured strings.

19. Preserve backwards-compatible tool schemas once released.

20. Keep MCP-specific code isolated from domain logic.

---

# 41. Development Workflow

Before implementing code:

1. Inspect the repository.
2. Check whether an existing project structure exists.
3. Check Python version.
4. Check existing configuration.
5. Check existing OpenCode instructions.
6. Do not overwrite existing project files without understanding them.
7. Propose the implementation plan.
8. Implement incrementally.

After each major phase:

1. Run tests.
2. Run Ruff.
3. Run mypy.
4. Fix failures.
5. Review architecture.
6. Update documentation.
7. Show changed files.
8. Explain important decisions.

Do not move to the next phase if the current phase is broken.

---

# 42. First Task

For the first implementation pass, DO NOT implement the entire roadmap.

Implement only:

### Foundation

- project structure
- pyproject.toml
- configuration
- logging
- GitHub async client
- Pydantic models
- custom exceptions

### MCP

Implement:

- get_repository
- search_repositories
- get_issues
- get_pull_requests
- get_recent_commits
- get_contributors
- get_releases

### Testing

Implement tests for all of the above.

### Documentation

Create:

- README.md
- docs/development.md
- docs/architecture.md

### CI

Create:

- `.github/workflows/ci.yml`

### Docker

Create the initial Dockerfile.

Do NOT implement:

- LangGraph
- LangChain
- frontend
- vector database
- code search
- write operations
- autonomous agent
- complex caching

Those are later phases.

---

# 43. Completion Criteria for Phase 1

Phase 1 is complete only when:

- MCP server starts successfully.
- GitHub authentication works through environment variables.
- All MVP tools are registered.
- Tool inputs are validated.
- Tool outputs are structured.
- GitHub errors are handled cleanly.
- Pagination works where needed.
- API limits are bounded.
- Secrets are never logged.
- Tests run without internet access.
- Ruff passes.
- Mypy passes.
- Pytest passes.
- Docker image builds.
- CI workflow is valid.
- README contains setup instructions.
- Architecture documentation exists.

Before finishing, provide:

1. Project tree
2. Files created
3. Files modified
4. Dependencies added
5. MCP tools implemented
6. Test results
7. Ruff result
8. Mypy result
9. Docker build result
10. Known limitations
11. Recommended next phase

Do not claim functionality is complete unless it has actually been tested.

---

# 44. Coding Philosophy

Build this as if another developer will maintain it six months from now.

The goal is not merely:

"Make it work."

The goal is:

"Make it understandable, testable, secure, extensible, and demonstrable."

The final repository should look like a serious open-source project rather than a tutorial project.

Start with analysis and repository inspection, then implement Phase 1 only.