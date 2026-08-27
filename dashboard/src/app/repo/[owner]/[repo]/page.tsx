"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { investigate } from "@/lib/api";
import type { InvestigationResult } from "@/lib/types";

function gradeColor(grade: string): string {
  switch (grade) {
    case "A": return "text-green-600 bg-green-50";
    case "B": return "text-blue-600 bg-blue-50";
    case "C": return "text-yellow-600 bg-yellow-50";
    case "D": return "text-orange-600 bg-orange-50";
    default:  return "text-red-600 bg-red-50";
  }
}

function riskColor(level: string): string {
  switch (level) {
    case "low":    return "text-green-600 bg-green-50";
    case "medium": return "text-yellow-600 bg-yellow-50";
    case "high":   return "text-red-600 bg-red-50";
    default:       return "text-gray-600 bg-gray-50";
  }
}

function severityBadge(sev: string): string {
  switch (sev) {
    case "high":   return "bg-red-100 text-red-700";
    case "medium": return "bg-yellow-100 text-yellow-700";
    default:       return "bg-green-100 text-green-700";
  }
}

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
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <p className="text-gray-500 text-lg">Investigating {owner}/{repo}...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white p-8 rounded-lg shadow max-w-md">
          <h1 className="text-xl font-bold text-red-600 mb-2">Error</h1>
          <p className="text-gray-600">{error}</p>
          <a href="/" className="text-blue-600 underline mt-4 block">Back to search</a>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-5xl mx-auto space-y-8">
        <a href="/" className="text-blue-600 hover:underline text-sm">&larr; Back to search</a>

        <h1 className="text-3xl font-bold text-gray-900">{owner}/{repo}</h1>

        {/* Health Overview */}
        {data.health && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Health Assessment</h2>
            <div className="flex items-center gap-4 mb-6">
              <span className="text-5xl font-bold text-gray-900">{data.health.overall_score}</span>
              <span className="text-gray-400">/100</span>
              <span className={`text-3xl font-bold px-3 py-1 rounded ${gradeColor(data.health.grade)}`}>
                {data.health.grade}
              </span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {data.health.components.map((c) => (
                <div key={c.name} className="border rounded-lg p-4">
                  <div className="text-sm text-gray-500">{c.label}</div>
                  <div className="text-2xl font-bold text-gray-900">{c.score}</div>
                  <div className="text-xs text-gray-400">weight: {(c.weight * 100).toFixed(0)}%</div>
                  <div className="mt-2 h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full"
                      style={{ width: `${c.score}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Risks */}
        {data.risks && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Maintenance Risks</h2>
            <div className="flex items-center gap-3 mb-4">
              <span className={`text-sm font-medium px-3 py-1 rounded ${riskColor(data.risks.risk_level)}`}>
                {data.risks.risk_level.toUpperCase()}
              </span>
              <span className="text-gray-500">score: {data.risks.risk_score.toFixed(1)}</span>
            </div>
            {data.risks.risks.length === 0 ? (
              <p className="text-green-600">No maintenance risks detected.</p>
            ) : (
              <div className="space-y-4">
                {data.risks.risks.map((r, i) => (
                  <div key={i} className="border rounded-lg p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`text-xs font-medium px-2 py-0.5 rounded ${severityBadge(r.severity)}`}>
                        {r.severity}
                      </span>
                      <span className="text-sm text-gray-500">{r.category}</span>
                    </div>
                    <h3 className="font-medium text-gray-900">{r.title}</h3>
                    <p className="text-sm text-gray-600 mt-1">{r.description}</p>
                    <p className="text-sm text-blue-600 mt-1">{r.recommendation}</p>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Recent Commits */}
        {data.recent_commits.length > 0 && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Commits</h2>
            <ul className="space-y-3">
              {data.recent_commits.slice(0, 10).map((c) => (
                <li key={c.sha} className="flex items-start gap-3 text-sm">
                  <code className="text-xs text-gray-500 font-mono">{c.sha.slice(0, 7)}</code>
                  <span className="text-gray-900">{c.message.split("\n")[0]}</span>
                  <span className="text-gray-400 ml-auto whitespace-nowrap">
                    {c.author ?? "unknown"} &middot; {c.author_date?.slice(0, 10)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Open Issues */}
        {data.open_issues.length > 0 && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Open Issues ({data.open_issues.length})</h2>
            <ul className="space-y-2">
              {data.open_issues.map((i) => (
                <li key={i.number} className="text-sm">
                  <span className="text-gray-400">#{i.number}</span>{" "}
                  <span className="text-gray-900">{i.title}</span>
                  <span className="text-gray-400 ml-2">by {i.author ?? "unknown"}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Open PRs */}
        {data.open_pulls.length > 0 && (
          <section className="bg-white rounded-lg shadow p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Open Pull Requests ({data.open_pulls.length})</h2>
            <ul className="space-y-2">
              {data.open_pulls.map((p) => (
                <li key={p.number} className="text-sm">
                  <span className="text-gray-400">#{p.number}</span>{" "}
                  <span className="text-gray-900">{p.title}</span>
                  {p.draft && <span className="text-xs text-gray-400 ml-1">(draft)</span>}
                  <span className="text-gray-400 ml-2">by {p.author ?? "unknown"}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Errors */}
        {data.errors.length > 0 && (
          <section className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-700 mb-2">Errors</h2>
            <ul className="list-disc list-inside text-sm text-red-600">
              {data.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </section>
        )}
      </div>
    </div>
  );
}
