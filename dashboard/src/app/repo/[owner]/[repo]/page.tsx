"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import { fetchRepo } from "@/lib/api";

interface RepoData {
  repository: {
    name: string;
    full_name: string;
    description: string | null;
    stars: number;
    forks: number;
    open_issues: number;
    language: string | null;
    license: string | null;
    default_branch: string;
    created_at: string;
    html_url: string;
  };
  issues: Array<{
    number: number;
    title: string;
    state: string;
    author: string | null;
    created_at: string;
    labels: string[];
  }>;
  pulls: Array<{
    number: number;
    title: string;
    state: string;
    author: string | null;
    created_at: string;
    draft: boolean;
  }>;
  commits: Array<{
    sha: string;
    message: string;
    author: string | null;
    author_date: string;
  }>;
  contributors: Array<{
    login: string;
    contributions: number;
  }>;
  releases: Array<{
    tag_name: string;
    name: string | null;
    published_at: string | null;
    draft: boolean;
    prerelease: boolean;
  }>;
}

function computeHealth(data: RepoData) {
  const now = new Date();
  const daysAgo = (d: number) =>
    new Date(now.getTime() - d * 86400000).toISOString();

  // Activity (25%)
  const commits30 = data.commits.filter(
    (c) => c.author_date >= daysAgo(30)
  ).length;
  const activeAuthors = new Set(
    data.commits
      .filter((c) => c.author_date >= daysAgo(30))
      .map((c) => c.author)
      .filter(Boolean)
  ).size;
  const activityScore = Math.min(
    100,
    (commits30 / 30) * 40 + Math.min(activeAuthors * 10, 60)
  );

  // Issue health (20%)
  const staleIssues = data.issues.filter(
    (i) => i.created_at < daysAgo(90)
  ).length;
  const issueRatio =
    data.issues.length > 0 ? staleIssues / data.issues.length : 0;
  const issueScore = Math.max(0, 100 - issueRatio * 100);

  // PR health (20%)
  const stalePrs = data.pulls.filter(
    (p) => p.created_at < daysAgo(30)
  ).length;
  const prRatio = data.pulls.length > 0 ? stalePrs / data.pulls.length : 0;
  const prScore = Math.max(0, 100 - prRatio * 100);

  // Contributor health (15%)
  const contributorScore = Math.min(100, data.contributors.length * 5);

  // Release activity (10%)
  const releases90 = data.releases.filter(
    (r) => r.published_at && r.published_at >= daysAgo(90)
  ).length;
  const releaseScore = Math.min(100, releases90 * 30);

  // Documentation (10%)
  const docScore = data.repository.license ? 100 : 50;

  const components = [
    { name: "activity", label: "Activity", score: Math.round(activityScore), weight: 0.25 },
    { name: "issue_health", label: "Issue Health", score: Math.round(issueScore), weight: 0.20 },
    { name: "pr_health", label: "PR Health", score: Math.round(prScore), weight: 0.20 },
    { name: "contributor_health", label: "Contributors", score: Math.round(contributorScore), weight: 0.15 },
    { name: "release_activity", label: "Releases", score: Math.round(releaseScore), weight: 0.10 },
    { name: "documentation", label: "Documentation", score: Math.round(docScore), weight: 0.10 },
  ];

  const overall = Math.round(
    components.reduce((sum, c) => sum + c.score * c.weight, 0)
  );

  let grade = "F";
  if (overall >= 85) grade = "A";
  else if (overall >= 70) grade = "B";
  else if (overall >= 55) grade = "C";
  else if (overall >= 40) grade = "D";

  return { overall, grade, components };
}

const gradeColor: Record<string, string> = {
  A: "#00ff88",
  B: "#6c63ff",
  C: "#ffd700",
  D: "#ff8844",
  F: "#ff4466",
};

export default function RepoPage() {
  const params = useParams();
  const owner = params.owner as string;
  const repo = params.repo as string;
  const [data, setData] = useState<RepoData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRepo(owner, repo)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [owner, repo]);

  const health = useMemo(() => (data ? computeHealth(data) : null), [data]);

  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{
          background:
            "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)",
        }}
      >
        <div className="text-center">
          <div
            className="w-12 h-12 border-4 rounded-full animate-spin mx-auto mb-4"
            style={{ borderColor: "#2a2a4a", borderTopColor: "#6c63ff" }}
          />
          <p style={{ color: "#8888aa" }}>
            Investigating {owner}/{repo}...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{
          background:
            "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)",
        }}
      >
        <div
          className="p-8 rounded-xl max-w-md text-center"
          style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}
        >
          <h1 className="text-xl font-bold mb-2" style={{ color: "#ff4466" }}>
            Error
          </h1>
          <p style={{ color: "#8888aa" }}>{error}</p>
          <a
            href="/"
            className="mt-4 inline-block"
            style={{ color: "#6c63ff" }}
          >
            &larr; Back to search
          </a>
        </div>
      </div>
    );
  }

  if (!data || !health) return null;

  return (
    <div
      className="min-h-screen p-8"
      style={{
        background:
          "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)",
      }}
    >
      <div className="max-w-5xl mx-auto space-y-8">
        <a
          href="/"
          className="text-sm hover:underline"
          style={{ color: "#6c63ff" }}
        >
          &larr; Back to search
        </a>

        <div className="flex items-center gap-3">
          <h1 className="text-3xl font-bold">{owner}/{repo}</h1>
          <a
            href={data.repository.html_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-sm px-3 py-1 rounded-lg"
            style={{
              color: "#6c63ff",
              background: "rgba(108, 99, 255, 0.1)",
              border: "1px solid rgba(108, 99, 255, 0.3)",
            }}
          >
            GitHub
          </a>
        </div>

        {data.repository.description && (
          <p style={{ color: "#8888aa" }}>{data.repository.description}</p>
        )}

        <div className="flex gap-6 text-sm" style={{ color: "#555577" }}>
          <span>⭐ {data.repository.stars.toLocaleString()}</span>
          <span>🍴 {data.repository.forks.toLocaleString()}</span>
          <span>📋 {data.repository.open_issues} issues</span>
          {data.repository.language && <span>💻 {data.repository.language}</span>}
          {data.repository.license && <span>📄 {data.repository.license}</span>}
        </div>

        {/* Health */}
        <section
          className="rounded-xl p-6"
          style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}
        >
          <h2
            className="text-xl font-semibold mb-4"
            style={{ color: "#e0e0ff" }}
          >
            Health Assessment
          </h2>
          <div className="flex items-center gap-4 mb-6">
            <span className="text-5xl font-bold">{health.overall}</span>
            <span style={{ color: "#8888aa" }}>/100</span>
            <span
              className="text-3xl font-bold px-3 py-1 rounded-lg"
              style={{
                color: gradeColor[health.grade],
                background: `${gradeColor[health.grade]}15`,
              }}
            >
              {health.grade}
            </span>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            {health.components.map((c) => (
              <div
                key={c.name}
                className="rounded-lg p-4"
                style={{ background: "#12121a", border: "1px solid #2a2a4a" }}
              >
                <div className="text-sm" style={{ color: "#8888aa" }}>
                  {c.label}
                </div>
                <div className="text-2xl font-bold mt-1">{c.score}</div>
                <div className="text-xs mt-1" style={{ color: "#555577" }}>
                  weight: {(c.weight * 100).toFixed(0)}%
                </div>
                <div
                  className="mt-2 h-2 rounded-full overflow-hidden"
                  style={{ background: "#2a2a4a" }}
                >
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${c.score}%`,
                      background: `linear-gradient(90deg, #6c63ff, ${gradeColor[health.grade]})`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Risks */}
        {(() => {
          const risks: Array<{
            category: string;
            severity: string;
            title: string;
            desc: string;
          }> = [];
          if (
            data.issues.filter((i) => i.created_at < daysAgo(90)).length >= 10
          ) {
            risks.push({
              category: "issues",
              severity: "high",
              title: "Many stale issues",
              desc: `${data.issues.filter((i) => i.created_at < daysAgo(90)).length} issues older than 90 days`,
            });
          }
          if (data.pulls.filter((p) => p.created_at < daysAgo(30)).length >= 5) {
            risks.push({
              category: "pull_requests",
              severity: "medium",
              title: "Stale pull requests",
              desc: `${data.pulls.filter((p) => p.created_at < daysAgo(30)).length} PRs open for 30+ days`,
            });
          }
          if (
            data.contributors.length > 0 &&
            data.contributors[0].contributions /
              data.commits.length >
              0.8
          ) {
            risks.push({
              category: "bus_factor",
              severity: "high",
              title: "Bus factor risk",
              desc: "One contributor dominates commit activity",
            });
          }
          if (risks.length === 0) return null;
          const sevColor: Record<string, string> = {
            low: "#00ff88",
            medium: "#ffd700",
            high: "#ff4466",
          };
          return (
            <section
              className="rounded-xl p-6"
              style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}
            >
              <h2
                className="text-xl font-semibold mb-4"
                style={{ color: "#e0e0ff" }}
              >
                Maintenance Risks
              </h2>
              <div className="space-y-3">
                {risks.map((r, i) => (
                  <div
                    key={i}
                    className="rounded-lg p-4"
                    style={{
                      background: "#12121a",
                      border: `1px solid ${sevColor[r.severity]}30`,
                    }}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span
                        className="text-xs font-medium px-2 py-0.5 rounded"
                        style={{
                          color: sevColor[r.severity],
                          background: `${sevColor[r.severity]}15`,
                        }}
                      >
                        {r.severity}
                      </span>
                      <span className="text-sm" style={{ color: "#555577" }}>
                        {r.category}
                      </span>
                    </div>
                    <h3 className="font-medium">{r.title}</h3>
                    <p className="text-sm mt-1" style={{ color: "#8888aa" }}>
                      {r.desc}
                    </p>
                  </div>
                ))}
              </div>
            </section>
          );
        })()}

        {/* Commits */}
        {data.commits.length > 0 && (
          <section
            className="rounded-xl p-6"
            style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}
          >
            <h2
              className="text-xl font-semibold mb-4"
              style={{ color: "#e0e0ff" }}
            >
              Recent Commits
            </h2>
            <ul className="space-y-3">
              {data.commits.slice(0, 10).map((c) => (
                <li
                  key={c.sha}
                  className="flex items-start gap-3 text-sm"
                >
                  <code
                    className="text-xs font-mono px-2 py-0.5 rounded shrink-0"
                    style={{
                      color: "#6c63ff",
                      background: "rgba(108, 99, 255, 0.1)",
                    }}
                  >
                    {c.sha.slice(0, 7)}
                  </code>
                  <span>{String(c.message).split("\n")[0]}</span>
                  <span
                    className="ml-auto whitespace-nowrap"
                    style={{ color: "#555577" }}
                  >
                    {c.author ?? "unknown"} &middot;{" "}
                    {c.author_date?.slice(0, 10)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Issues */}
        {data.issues.length > 0 && (
          <section
            className="rounded-xl p-6"
            style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}
          >
            <h2
              className="text-xl font-semibold mb-4"
              style={{ color: "#e0e0ff" }}
            >
              Open Issues ({data.issues.length})
            </h2>
            <ul className="space-y-2">
              {data.issues.slice(0, 15).map((i) => (
                <li key={i.number} className="text-sm">
                  <span style={{ color: "#555577" }}>#{i.number}</span>{" "}
                  <span>{i.title}</span>
                  <span className="ml-2" style={{ color: "#555577" }}>
                    by {i.author ?? "unknown"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* PRs */}
        {data.pulls.length > 0 && (
          <section
            className="rounded-xl p-6"
            style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}
          >
            <h2
              className="text-xl font-semibold mb-4"
              style={{ color: "#e0e0ff" }}
            >
              Open Pull Requests ({data.pulls.length})
            </h2>
            <ul className="space-y-2">
              {data.pulls.slice(0, 15).map((p) => (
                <li key={p.number} className="text-sm">
                  <span style={{ color: "#555577" }}>#{p.number}</span>{" "}
                  <span>{p.title}</span>
                  {p.draft && (
                    <span className="text-xs ml-1" style={{ color: "#555577" }}>
                      (draft)
                    </span>
                  )}
                  <span className="ml-2" style={{ color: "#555577" }}>
                    by {p.author ?? "unknown"}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Contributors */}
        {data.contributors.length > 0 && (
          <section
            className="rounded-xl p-6"
            style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}
          >
            <h2
              className="text-xl font-semibold mb-4"
              style={{ color: "#e0e0ff" }}
            >
              Top Contributors
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {data.contributors.slice(0, 9).map((c) => (
                <div
                  key={c.login}
                  className="flex items-center gap-2 p-2 rounded-lg"
                  style={{ background: "#12121a" }}
                >
                  <span className="text-sm font-medium">{c.login}</span>
                  <span
                    className="text-xs ml-auto"
                    style={{ color: "#6c63ff" }}
                  >
                    {c.contributions}
                  </span>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

function daysAgo(d: number): string {
  return new Date(Date.now() - d * 86400000).toISOString();
}
