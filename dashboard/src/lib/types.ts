export interface HealthResponse {
  owner: string;
  repo: string;
  overall_score: number;
  grade: string;
  components: ComponentScore[];
  computed_at: string;
}

export interface ComponentScore {
  name: string;
  label: string;
  score: number;
  weight: number;
  details: Record<string, unknown>;
}

export interface RiskResponse {
  owner: string;
  repo: string;
  risk_level: string;
  risk_score: number;
  risks: RiskItem[];
  computed_at: string;
}

export interface RiskItem {
  category: string;
  severity: string;
  title: string;
  description: string;
  recommendation: string;
  evidence: string[];
}

export interface RepoMetadata {
  name: string;
  full_name: string;
  description: string | null;
  language: string | null;
  stars: number;
  forks: number;
  open_issues: number;
  license: string | null;
  default_branch: string;
  html_url: string;
}

export interface Commit {
  sha: string;
  message: string;
  author: string | null;
  author_date: string;
}

export interface Issue {
  number: number;
  title: string;
  state: string;
  author: string | null;
  created_at: string;
}

export interface PullRequest {
  number: number;
  title: string;
  state: string;
  author: string | null;
  created_at: string;
  draft: boolean;
}

export interface InvestigationResult {
  owner: string;
  repo: string;
  health: HealthResponse | null;
  risks: RiskResponse | null;
  recent_commits: Commit[];
  open_issues: Issue[];
  open_pulls: PullRequest[];
  report: string;
  errors: string[];
  completed_steps: string[];
}
