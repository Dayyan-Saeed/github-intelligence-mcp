"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { investigate } from "@/lib/api";
import type { InvestigationResult } from "@/lib/types";

const gradeColor: Record<string, string> = {
  A: "#00ff88",
  B: "#6c63ff",
  C: "#ffd700",
  D: "#ff8844",
  F: "#ff4466",
};

const riskColor: Record<string, string> = {
  low: "#00ff88",
  medium: "#ffd700",
  high: "#ff4466",
};

const severityBg: Record<string, string> = {
  low: "rgba(0, 255, 136, 0.1)",
  medium: "rgba(255, 215, 0, 0.1)",
  high: "rgba(255, 68, 102, 0.1)",
};

const severityBorder: Record<string, string> = {
  low: "#00ff88",
  medium: "#ffd700",
  high: "#ff4466",
};

export default function RepoPage() {
  const params = useParams();
  const owner = params.owner as string;
  const repo = params.repo as string;
  const [data, setData] = useState<InvestigationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    investigate(owner, repo)
      .then(setData)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [owner, repo]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center"
        style={{ background: "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)" }}>
        <div className="text-center">
          <div className="w-12 h-12 border-4 rounded-full animate-spin mx-auto mb-4"
            style={{ borderColor: "#2a2a4a", borderTopColor: "#6c63ff" }} />
          <p style={{ color: "#8888aa" }}>Investigating {owner}/{repo}...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center"
        style={{ background: "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)" }}>
        <div className="p-8 rounded-xl max-w-md text-center"
          style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}>
          <h1 className="text-xl font-bold mb-2" style={{ color: "#ff4466" }}>Error</h1>
          <p style={{ color: "#8888aa" }}>{error}</p>
          <a href="/" className="mt-4 inline-block" style={{ color: "#6c63ff" }}>&larr; Back to search</a>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen p-8"
      style={{ background: "linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%)" }}>
      <div className="max-w-5xl mx-auto space-y-8">
        <a href="/" className="text-sm hover:underline" style={{ color: "#6c63ff" }}>&larr; Back to search</a>

        <h1 className="text-3xl font-bold">{owner}/{repo}</h1>

        {/* Health */}
        {data.health && (
          <section className="rounded-xl p-6" style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}>
            <h2 className="text-xl font-semibold mb-4" style={{ color: "#e0e0ff" }}>Health Assessment</h2>
            <div className="flex items-center gap-4 mb-6">
              <span className="text-5xl font-bold">{data.health.overall_score}</span>
              <span style={{ color: "#8888aa" }}>/100</span>
              <span className="text-3xl font-bold px-3 py-1 rounded-lg"
                style={{ color: gradeColor[data.health.grade] ?? "#8888aa", background: `${gradeColor[data.health.grade] ?? "#8888aa"}15` }}>
                {data.health.grade}
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {data.health.components.map((c) => (
                <div key={c.name} className="rounded-lg p-4" style={{ background: "#12121a", border: "1px solid #2a2a4a" }}>
                  <div className="text-sm" style={{ color: "#8888aa" }}>{c.label}</div>
                  <div className="text-2xl font-bold mt-1">{c.score}</div>
                  <div className="text-xs mt-1" style={{ color: "#555577" }}>weight: {(c.weight * 100).toFixed(0)}%</div>
                  <div className="mt-2 h-2 rounded-full overflow-hidden" style={{ background: "#2a2a4a" }}>
                    <div className="h-full rounded-full" style={{ width: `${c.score}%`, background: `linear-gradient(90deg, #6c63ff, ${gradeColor[data.health.grade] ?? "#6c63ff"})` }} />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Risks */}
        {data.risks && (
          <section className="rounded-xl p-6" style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}>
            <h2 className="text-xl font-semibold mb-4" style={{ color: "#e0e0ff" }}>Maintenance Risks</h2>
            <div className="flex items-center gap-3 mb-4">
              <span className="text-sm font-medium px-3 py-1 rounded-lg"
                style={{ color: riskColor[data.risks.risk_level] ?? "#8888aa", background: `${riskColor[data.risks.risk_level] ?? "#8888aa"}15` }}>
                {data.risks.risk_level.toUpperCase()}
              </span>
              <span style={{ color: "#8888aa" }}>score: {data.risks.risk_score.toFixed(1)}</span>
            </div>
            {data.risks.risks.length === 0 ? (
              <p style={{ color: "#00ff88" }}>No maintenance risks detected.</p>
            ) : (
              <div className="space-y-3">
                {data.risks.risks.map((r, i) => (
                  <div key={i} className="rounded-lg p-4" style={{ background: "#12121a", border: `1px solid ${severityBorder[r.severity] ?? "#2a2a4a"}30` }}>
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs font-medium px-2 py-0.5 rounded"
                        style={{ color: severityBorder[r.severity] ?? "#8888aa", background: severityBg[r.severity] ?? "#1a1a2e" }}>
                        {r.severity}
                      </span>
                      <span className="text-sm" style={{ color: "#555577" }}>{r.category}</span>
                    </div>
                    <h3 className="font-medium">{r.title}</h3>
                    <p className="text-sm mt-1" style={{ color: "#8888aa" }}>{r.description}</p>
                    <p className="text-sm mt-1" style={{ color: "#6c63ff" }}>{r.recommendation}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Commits */}
        {data.recent_commits.length > 0 && (
          <section className="rounded-xl p-6" style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}>
            <h2 className="text-xl font-semibold mb-4" style={{ color: "#e0e0ff" }}>Recent Commits</h2>
            <ul className="space-y-3">
              {data.recent_commits.slice(0, 10).map((c) => (
                <li key={c.sha} className="flex items-start gap-3 text-sm">
                  <code className="text-xs font-mono px-2 py-0.5 rounded" style={{ color: "#6c63ff", background: "rgba(108, 99, 255, 0.1)" }}>
                    {c.sha.slice(0, 7)}
                  </code>
                  <span>{c.message.split("\n")[0]}</span>
                  <span className="ml-auto whitespace-nowrap" style={{ color: "#555577" }}>
                    {c.author ?? "unknown"} &middot; {c.author_date?.slice(0, 10)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Issues */}
        {data.open_issues.length > 0 && (
          <section className="rounded-xl p-6" style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}>
            <h2 className="text-xl font-semibold mb-4" style={{ color: "#e0e0ff" }}>Open Issues ({data.open_issues.length})</h2>
            <ul className="space-y-2">
              {data.open_issues.map((i) => (
                <li key={i.number} className="text-sm">
                  <span style={{ color: "#555577" }}>#{i.number}</span>{" "}
                  <span>{i.title}</span>
                  <span className="ml-2" style={{ color: "#555577" }}>by {i.author ?? "unknown"}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* PRs */}
        {data.open_pulls.length > 0 && (
          <section className="rounded-xl p-6" style={{ background: "#1a1a2e", border: "1px solid #2a2a4a" }}>
            <h2 className="text-xl font-semibold mb-4" style={{ color: "#e0e0ff" }}>Open Pull Requests ({data.open_pulls.length})</h2>
            <ul className="space-y-2">
              {data.open_pulls.map((p) => (
                <li key={p.number} className="text-sm">
                  <span style={{ color: "#555577" }}>#{p.number}</span>{" "}
                  <span>{p.title}</span>
                  {p.draft && <span className="text-xs ml-1" style={{ color: "#555577" }}>(draft)</span>}
                  <span className="ml-2" style={{ color: "#555577" }}>by {p.author ?? "unknown"}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Errors */}
        {data.errors.length > 0 && (
          <section className="rounded-xl p-6" style={{ background: "rgba(255, 68, 102, 0.05)", border: "1px solid rgba(255, 68, 102, 0.2)" }}>
            <h2 className="text-xl font-semibold mb-2" style={{ color: "#ff4466" }}>Errors</h2>
            <ul className="list-disc list-inside text-sm" style={{ color: "#ff8899" }}>
              {data.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
