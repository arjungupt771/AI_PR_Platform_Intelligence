"use client"
import { useEffect, useState } from "react"
import { GitPullRequest, Search, Filter, CheckCircle, Clock, AlertTriangle } from "lucide-react"
import { prsApi, reposApi } from "@/lib/api"
import type { PullRequest, Repository } from "@/types"
import { formatDistanceToNow } from "date-fns"
import Link from "next/link"
import { useAutoRefreshList } from "@/hooks/usePRPoller"

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

function ScorePill({ score }: { score: number | null }) {
  if (score == null) return <span className="text-muted-foreground text-xs">—</span>
  const color = score >= 7 ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
    : score >= 5 ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
    : "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>
      {score.toFixed(1)}
    </span>
  )
}

export default function PullsPage() {
  const [prs, setPrs] = useState<PullRequest[]>([])
  const [repos, setRepos] = useState<Repository[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [repoFilter, setRepoFilter] = useState<number | undefined>()
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    reposApi.list().then(setRepos)
  }, [])

  const loadPRs = () => {
    setLoading(true)
    prsApi.list({ repo_id: repoFilter, status: statusFilter, page, page_size: 20 })
      .then((res) => { setPrs(res.items); setTotal(res.total) })
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadPRs() }, [repoFilter, statusFilter, page])

  // Auto-refresh while any PR is still being reviewed
  useAutoRefreshList(prs, loadPRs)

  const filtered = search
    ? prs.filter(pr => pr.title.toLowerCase().includes(search.toLowerCase()) || pr.author.toLowerCase().includes(search.toLowerCase()))
    : prs

  const totalPages = Math.ceil(total / 20)

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Pull Requests</h1>
          <p className="text-sm text-muted-foreground mt-1">{total} total</p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search PRs..."
            className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary"
          />
        </div>
        <select
          value={repoFilter ?? ""}
          onChange={e => { setRepoFilter(e.target.value ? Number(e.target.value) : undefined); setPage(1) }}
          className="border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All repos</option>
          {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
        <select
          value={statusFilter ?? ""}
          onChange={e => { setStatusFilter(e.target.value || undefined); setPage(1) }}
          className="border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="reviewing">Reviewing</option>
          <option value="completed">Completed</option>
          <option value="failed">Failed</option>
        </select>
      </div>

      {/* Table */}
      <div className="border rounded-xl overflow-hidden bg-card">
        {loading ? (
          <div className="flex items-center justify-center p-12">
            <div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center p-12 text-muted-foreground">
            <GitPullRequest className="w-8 h-8 mx-auto mb-3 opacity-50" />
            <p>No pull requests found</p>
          </div>
        ) : (
          <>
            <table className="w-full text-sm">
              <thead className="border-b bg-secondary/30">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Pull Request</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden md:table-cell">Repo</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden sm:table-cell">Author</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Status</th>
                  <th className="text-center px-4 py-3 font-medium text-muted-foreground">Score</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground hidden lg:table-cell">Issues</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground hidden lg:table-cell">Age</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((pr, i) => (
                  <tr key={pr.id} className={`border-b last:border-0 hover:bg-secondary/20 transition-colors`}>
                    <td className="px-4 py-3">
                      <Link href={`/dashboard/pulls/${pr.id}`} className="hover:underline font-medium line-clamp-1">
                        #{pr.number} {pr.title}
                      </Link>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {pr.head_branch} → {pr.base_branch}
                      </p>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground hidden md:table-cell">
                      {repos.find(r => r.id === pr.repository_id)?.name ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground hidden sm:table-cell">{pr.author}</td>
                    <td className="px-4 py-3"><StatusBadge status={pr.status} /></td>
                    <td className="px-4 py-3 text-center">
                      <ScorePill score={pr.latest_review?.overall_score ?? null} />
                    </td>
                    <td className="px-4 py-3 text-right hidden lg:table-cell">
                      {pr.latest_review ? (
                        <span className="text-xs">
                          {pr.latest_review.critical_count > 0 && (
                            <span className="text-red-600 mr-1">{pr.latest_review.critical_count} crit</span>
                          )}
                          {pr.latest_review.issue_count} total
                        </span>
                      ) : "—"}
                    </td>
                    <td className="px-4 py-3 text-right text-muted-foreground text-xs hidden lg:table-cell">
                      {formatDistanceToNow(new Date(pr.created_at), { addSuffix: true })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {/* Pagination */}
            {totalPages > 1 && (
              <div className="border-t px-4 py-3 flex items-center justify-between">
                <p className="text-sm text-muted-foreground">
                  Page {page} of {totalPages}
                </p>
                <div className="flex gap-2">
                  <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}
                    className="px-3 py-1.5 text-sm border rounded-lg hover:bg-secondary disabled:opacity-50 transition-colors">
                    Previous
                  </button>
                  <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}
                    className="px-3 py-1.5 text-sm border rounded-lg hover:bg-secondary disabled:opacity-50 transition-colors">
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
