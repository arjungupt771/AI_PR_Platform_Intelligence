"use client"
import { useEffect, useState } from "react"
import { GitPullRequest, Shield, TrendingUp, AlertTriangle, CheckCircle, Clock } from "lucide-react"
import { analyticsApi, prsApi } from "@/lib/api"
import type { Analytics, PullRequest } from "@/types"
import { formatDistanceToNow } from "date-fns"
import Link from "next/link"

function ScoreRing({ score }: { score: number }) {
  const r = 20
  const circ = 2 * Math.PI * r
  const offset = circ - (score / 10) * circ
  const color = score >= 7 ? "#22c55e" : score >= 5 ? "#f59e0b" : "#ef4444"

  return (
    <svg width="56" height="56" viewBox="0 0 56 56">
      <circle cx="28" cy="28" r={r} fill="none" stroke="currentColor" strokeWidth="3" className="text-muted" />
      <circle
        cx="28" cy="28" r={r}
        fill="none" stroke={color} strokeWidth="3"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 28 28)"
        style={{ transition: "stroke-dashoffset 1s ease" }}
      />
      <text x="28" y="33" textAnchor="middle" fontSize="11" fontWeight="600" fill={color}>
        {score.toFixed(1)}
      </text>
    </svg>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
    reviewing: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
    completed: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
    failed: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  }
  const icons: Record<string, React.ReactNode> = {
    pending: <Clock className="w-3 h-3" />,
    reviewing: <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />,
    completed: <CheckCircle className="w-3 h-3" />,
    failed: <AlertTriangle className="w-3 h-3" />,
  }
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${styles[status] || ""}`}>
      {icons[status]}
      {status}
    </span>
  )
}

export default function DashboardPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [recentPRs, setRecentPRs] = useState<PullRequest[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      analyticsApi.get({ days: 30 }),
      prsApi.list({ page_size: 8 }),
    ]).then(([a, prs]) => {
      setAnalytics(a)
      setRecentPRs(prs.items)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    )
  }

  const stats = analytics ? [
    {
      label: "PRs reviewed",
      value: analytics.total_prs_reviewed,
      icon: <GitPullRequest className="w-4 h-4" />,
      color: "text-blue-600",
    },
    {
      label: "Avg quality score",
      value: analytics.avg_score_all_time.toFixed(1) + "/10",
      icon: <TrendingUp className="w-4 h-4" />,
      color: "text-green-600",
    },
    {
      label: "Issues caught",
      value: analytics.issues_caught,
      icon: <AlertTriangle className="w-4 h-4" />,
      color: "text-yellow-600",
    },
    {
      label: "Security flags",
      value: analytics.security_flags,
      icon: <Shield className="w-4 h-4" />,
      color: "text-red-600",
    },
  ] : []

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="text-muted-foreground text-sm mt-1">Last 30 days</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <div key={s.label} className="border rounded-xl p-4 bg-card space-y-2">
            <div className={`flex items-center gap-2 ${s.color}`}>
              {s.icon}
              <span className="text-xs text-muted-foreground">{s.label}</span>
            </div>
            <p className="text-2xl font-bold">{s.value}</p>
          </div>
        ))}
      </div>

      {/* Recent PRs */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">Recent Pull Requests</h2>
          <Link href="/dashboard/pulls" className="text-sm text-primary hover:underline">
            View all →
          </Link>
        </div>
        <div className="border rounded-xl overflow-hidden bg-card">
          {recentPRs.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <GitPullRequest className="w-8 h-8 mx-auto mb-3 opacity-50" />
              <p>No PRs yet. Connect a repo and open a pull request.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="border-b bg-secondary/30">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">PR</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Author</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Score</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Age</th>
                </tr>
              </thead>
              <tbody>
                {recentPRs.map((pr, i) => (
                  <tr key={pr.id} className={`border-b last:border-0 hover:bg-secondary/20 transition-colors ${i % 2 === 0 ? "" : "bg-secondary/5"}`}>
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/pulls/${pr.id}`} className="hover:underline font-medium">
                        #{pr.number} {pr.title}
                      </Link>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {pr.files_changed} files · +{pr.additions} -{pr.deletions}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{pr.author}</td>
                    <td className="px-4 py-3"><StatusBadge status={pr.status} /></td>
                    <td className="px-4 py-3 text-right">
                      {pr.latest_review?.overall_score != null ? (
                        <ScoreRing score={pr.latest_review.overall_score} />
                      ) : (
                        <span className="text-muted-foreground text-xs">—</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right text-muted-foreground text-xs">
                      {formatDistanceToNow(new Date(pr.created_at), { addSuffix: true })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Developer Insights */}
      {analytics && analytics.developer_insights.length > 0 && (
        <div>
          <h2 className="font-semibold mb-4">Developer Insights</h2>
          <div className="grid gap-3">
            {analytics.developer_insights.slice(0, 5).map((dev) => (
              <div key={dev.username} className="border rounded-xl p-4 bg-card flex items-center gap-4">
                {dev.avatar_url && (
                  <img src={dev.avatar_url} alt={dev.username} className="w-9 h-9 rounded-full" />
                )}
                <div className="flex-1">
                  <p className="font-medium text-sm">{dev.username}</p>
                  <p className="text-xs text-muted-foreground">
                    {dev.total_prs} PRs · {dev.total_issues} issues · {dev.critical_issues} critical
                  </p>
                </div>
                <div className="text-right">
                  <ScoreRing score={dev.avg_score} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
