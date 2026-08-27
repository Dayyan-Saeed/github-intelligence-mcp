const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchRepo(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repository/${owner}/${repo}`);
  if (!res.ok) throw new Error(`Failed to fetch repo: ${res.status}`);
  return res.json();
}

export async function fetchHealth(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repository/${owner}/${repo}/health`);
  if (!res.ok) throw new Error(`Failed to fetch health: ${res.status}`);
  return res.json();
}

export async function fetchRisks(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repository/${owner}/${repo}/risks`);
  if (!res.ok) throw new Error(`Failed to fetch risks: ${res.status}`);
  return res.json();
}

export async function investigate(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repository/${owner}/${repo}/investigate`);
  if (!res.ok) throw new Error(`Failed to investigate: ${res.status}`);
  return res.json();
}

export async function compare(
  ownerA: string, repoA: string, ownerB: string, repoB: string
) {
  const res = await fetch(
    `${API_BASE}/api/compare/${ownerA}/${repoA}/${ownerB}/${repoB}`
  );
  if (!res.ok) throw new Error(`Failed to compare: ${res.status}`);
  return res.json();
}
