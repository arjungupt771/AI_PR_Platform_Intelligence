export interface User {
  id: number; github_id: string; username: string
  email: string | null; avatar_url: string | null; created_at: string
}
export interface Repository {
  id: number; full_name: string; name: string; description: string | null
  language: string | null; is_private: boolean; is_indexed: boolean
  indexed_at: string | null; created_at: string; pr_count: number
  architecture_docs?: string | null; coding_standards?: string | null; team_conventions?: string | null
}
export type PRStatus = "pending" | "reviewing" | "completed" | "failed"
export type RiskLevel = "low" | "medium" | "high" | "critical"
export interface PullRequest {
  id: number; repository_id: number; github_pr_id: number; number: number
  title: string; description: string | null; author: string; author_avatar: string | null
  base_branch: string; head_branch: string; files_changed: number
  additions: number; deletions: number; status: PRStatus
  github_url: string | null; risk_level: RiskLevel | null; risk_score: number | null
  risk_factors: string[]; created_at: string; reviewed_at: string | null
  latest_review: ReviewSummary | null
}
export type Severity = "critical" | "warning" | "suggestion" | "info"
export interface ReviewIssue {
  severity: Severity; file: string; line: number | null; title: string
  description: string; suggestion: string | null
  confirmed_by?: number; source_model?: string
}
export interface ModelBreakdown {
  provider: string; model: string; score: number | null
  issue_count: number; critical_count: number; security_flags: number; latency_ms: number
}
export interface Review {
  id: number; pull_request_id: number; summary: string | null
  overall_score: number | null; consensus_score: number | null
  model_breakdown: ModelBreakdown[]; issues: ReviewIssue[]
  suggestions: string[]; security_flags: string[]
  metrics: { complexity?: string; test_coverage_hint?: string; documentation?: string; breaking_changes?: boolean }
  models_used: string[]; tokens_used: number; created_at: string
}
export interface ReviewSummary {
  id: number; overall_score: number | null; consensus_score: number | null
  issue_count: number; critical_count: number; models_used: string[]; created_at: string
}
export interface ChatMessage { id: number; role: "user" | "assistant"; content: string; created_at: string }
export interface QualityTrend { date: string; avg_score: number; pr_count: number; critical_issues: number }
export interface DeveloperInsight {
  username: string; avatar_url: string | null; total_prs: number
  avg_score: number; total_issues: number; critical_issues: number
}
export interface Analytics {
  quality_trend: QualityTrend[]; developer_insights: DeveloperInsight[]
  total_prs_reviewed: number; avg_score_all_time: number; issues_caught: number; security_flags: number
}
export interface BadgeInfo { id: string; label: string; desc: string }
export interface LeaderboardEntry {
  rank: number; username: string; avatar_url: string | null; total_prs: number
  avg_score: number; total_issues: number; critical_issues: number
  security_issues: number; score_trend: number; clean_streak: number; badges: BadgeInfo[]
}
export interface LeaderboardResponse { entries: LeaderboardEntry[]; repo_id: number | null; computed_at: string }
export interface PaginatedResponse<T> { items: T[]; total: number; page: number; page_size: number; total_pages: number }
