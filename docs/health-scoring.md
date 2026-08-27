# Health scoring algorithm

Every score is computed deterministically in code — no LLM, no hidden
heuristics. This document is the single source of truth for the formulas;
`src/github_intelligence_mcp/analysis/` is its implementation, and the unit
tests pin the numbers.

All component scores are integers in **0–100**. The overall score is the
weighted sum below (spec §20), and grades map onto it linearly.

## Overall

```
overall = activity * 0.25
        + issue_health * 0.20
        + pr_health * 0.20
        + contributor_health * 0.15
        + release_activity * 0.10
        + documentation * 0.10
```

| Grade | Overall |
|-------|---------|
| A | ≥ 85 |
| B | ≥ 70 |
| C | ≥ 55 |
| D | ≥ 40 |
| F | < 40 |

### Shared primitives

- **Saturating ratio** `capped_ratio(value, target) = min(100, value / target × 100)`
  — values at or above `target` earn full marks, so very large repositories are
  not over-rewarded.
- **Balance ratio** `balance_ratio(part, total)` = saturating ratio of part vs
  total; when `total == 0` it returns a neutral **50** instead of guessing.
- **Recency decay** — 100 at `fresh_days`, linear to 0 at `stale_days`.
- Component scores are the rounded mean of their sub-signals.

## Activity (25%)

Mean of five saturating ratios:

| Signal | Target (full marks) |
|---|---|
| commits in last 30 days | 30 |
| commits in last 90 days | 60 |
| distinct active contributors in last 30 days | 5 |
| pull requests opened in last 30 days | 10 |
| releases in last 90 days | 2 |

Evidence returned: every raw count.

## Issue health (20%)

Stale issue = open issue not updated within `stale_issue_days` (default 90,
configurable via env). Mean of:

- `freshness = (1 − stale_count / open_count) × 100`
- `flow_balance = closed_last_90 / (closed_last_90 + created_last_90)` (neutral 50 if no flow)
- `age_score`: recency decay of average open-issue age (fresh ≤ 30d → 0 at ≥ 365d)

## Pull request health (20%)

Stale PR = open PR created more than `stale_pr_days` ago (default 30,
configurable) and not merged. Mean of:

- `freshness = (1 − stale_prs / open_prs) × 100`
- `throughput = merged_last_90 / (merged_last_90 + opened_last_90)` (neutral 50)
- `age_score`: recency decay of average open-PR age (fresh ≤ 14d → 0 at ≥ 180d)

## Contributor health (15%)

From the ranked contributions list plus recent activity count. Mean of:

- `diversity = (1 − top1_share) × 100` where `top1_share` is the largest
  contributor's share of all sampled contributions
- `breadth`: saturating ratio of active contributors last 30 days (target 5)

Also reported as evidence: **bus-factor proxy** — the fewest people whose
combined contributions reach 50% of the total. High concentration is labeled
a *potential* risk; it is a signal, never a verdict.

## Release activity (10%)

Mean of:

- `recency`: decay of days since last published release (≤30d fresh → 0 at ≥365d)
- `frequency`: saturating ratio of releases in last 90 days (target 2)
- `cadence`: median interval between the most recent releases; ~45-day or
  shorter intervals earn full marks, double that scores 50. Unknown cadence
  (< 2 dated releases) is neutral 50.

Release cadence is deliberately gentle-weighted: frequent releases alone do
not prove a healthier repository (spec §25).

## Documentation (10%)

Presence-based points: README 50, license 25, description 15, homepage 10.

## Sampling honesty

Scores derive from bounded API samples (most recent ≤ 100 items per endpoint,
per Phase 1 limits). For very high-volume repositories the sampled window may
undercount raw totals; evidence fields make the sample sizes visible so
consumers can judge confidence. This is an accepted MVP trade-off documented
in the README roadmap (Phase 4 caching widens windows cheaply).

## Maintenance risk detection

The `find_maintenance_risks` tool operates alongside (not inside) the scoring
engine. It identifies concrete, evidence-backed maintenance risks — each with
machine-readable evidence so consumers can judge the finding themselves.

Severity is classified **low**, **medium**, or **high**. A risk is a signal;
concentration findings are phrased as *potential* risks, never as verdicts.

### Risk rules

| Risk type | Severity | Trigger |
|---|---|---|
| `stale_issues` | low / medium / high | Open issues not updated within `stale_issue_days`. Low when < 5 stale; medium when ≥ 5; high when ≥ 10 with ≥ 50% share. |
| `stale_pull_requests` | low / medium / high | Open PRs created > `stale_pr_days` ago and not merged. Low when < 5; medium when ≥ 5; high when ≥ 15. |
| `inactive_repository` | medium / high | No pushes in ≥ 180 days (medium) or ≥ 365 days (high). |
| `low_commit_activity` | low / medium | 0 commits in last 30 days (medium) or 1–2 commits (low). |
| `aging_open_issues` | medium | Average open-issue age ≥ 365 days. |
| `bus_factor` | medium / high | Only 1 active contributor in 30 days (high) or 2 (medium). |
| `contributor_concentration` | medium | Most active contributor ≥ 80% of sampled contributions. |
| `long_release_gap` | medium / high | Last stable release > 365 days ago (medium) or > 730 days (high). |
| `no_releases` | low | No published releases found in sampled history. |

### Risk aggregation

- **`risk_level`** = highest severity present; `low` when nothing detected.
- **`risk_score`** = bounded magnitude (high=25, medium=10, low=5 per risk, capped at 100).
