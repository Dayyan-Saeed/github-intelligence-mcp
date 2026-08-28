const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export async function fetchRepo(owner: string, repo: string) {
  const res = await fetch(`${API_BASE}/api/repository/${owner}/${repo}`);
  if (!res.ok) throw new Error(`Failed to fetch repo: ${res.status}`);
  return res.json();
}
