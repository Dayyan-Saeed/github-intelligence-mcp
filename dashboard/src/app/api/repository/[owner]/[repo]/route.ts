import { NextRequest, NextResponse } from "next/server";

const GITHUB_API = "https://api.github.com";
const TOKEN = process.env.GITHUB_TOKEN;

async function ghFetch(path: string) {
  const res = await fetch(`${GITHUB_API}${path}`, {
    headers: {
      Authorization: `Bearer ${TOKEN}`,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
    },
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`GitHub ${res.status}: ${path}`);
  return res.json();
}

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ owner: string; repo: string }> }
) {
  try {
    const { owner, repo } = await params;
    const [repoData, issues, pulls, commits, contributors, releases] =
      await Promise.all([
        ghFetch(`/repos/${owner}/${repo}`),
        ghFetch(`/repos/${owner}/${repo}/issues?state=open&per_page=100`).catch(
          () => []
        ),
        ghFetch(
          `/repos/${owner}/${repo}/pulls?state=open&per_page=100`
        ).catch(() => []),
        ghFetch(
          `/repos/${owner}/${repo}/commits?per_page=100`
        ).catch(() => []),
        ghFetch(`/repos/${owner}/${repo}/contributors?per_page=100`).catch(
          () => []
        ),
        ghFetch(`/repos/${owner}/${repo}/releases?per_page=20`).catch(
          () => []
        ),
      ]);

    return NextResponse.json({
      repository: {
        name: repoData.name,
        full_name: repoData.full_name,
        description: repoData.description,
        stars: repoData.stargazers_count,
        forks: repoData.forks_count,
        open_issues: repoData.open_issues_count,
        language: repoData.language,
        license: repoData.license?.spdx_id,
        default_branch: repoData.default_branch,
        created_at: repoData.created_at,
        updated_at: repoData.updated_at,
        html_url: repoData.html_url,
        homepage: repoData.homepage,
      },
      issues: Array.isArray(issues)
        ? issues
            .filter((i: Record<string, unknown>) => !i.pull_request)
            .slice(0, 100)
            .map((i: Record<string, unknown>) => ({
              number: i.number,
              title: i.title,
              state: i.state,
              author: (i.user as Record<string, unknown>)?.login,
              created_at: i.created_at,
              updated_at: i.updated_at,
              labels: (i.labels as Array<Record<string, unknown>>).map(
                (l) => l.name
              ),
              html_url: i.html_url,
            }))
        : [],
      pulls: Array.isArray(pulls)
        ? pulls.slice(0, 100).map((p: Record<string, unknown>) => ({
            number: p.number,
            title: p.title,
            state: p.state,
            author: (p.user as Record<string, unknown>)?.login,
            created_at: p.created_at,
            updated_at: p.updated_at,
            draft: p.draft,
            html_url: p.html_url,
          }))
        : [],
      commits: Array.isArray(commits)
        ? commits.slice(0, 30).map((c: Record<string, unknown>) => ({
            sha: c.sha,
            message: (c.commit as Record<string, unknown>)?.message,
            author: (c.commit as Record<string, unknown>)?.author?.name,
            author_date: (c.commit as Record<string, unknown>)?.author?.date,
            html_url: c.html_url,
          }))
        : [],
      contributors: Array.isArray(contributors)
        ? contributors.slice(0, 30).map((c: Record<string, unknown>) => ({
            login: c.login,
            contributions: c.contributions,
            html_url: c.html_url,
          }))
        : [],
      releases: Array.isArray(releases)
        ? releases.slice(0, 20).map((r: Record<string, unknown>) => ({
            tag_name: r.tag_name,
            name: r.name,
            published_at: r.published_at,
            draft: r.draft,
            prerelease: r.prerelease,
            html_url: r.html_url,
          }))
        : [],
    });
  } catch (err) {
    return NextResponse.json(
      { error: (err as Error).message },
      { status: 500 }
    );
  }
}
