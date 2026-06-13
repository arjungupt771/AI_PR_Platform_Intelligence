"use client"
import { useEffect, useState } from "react"
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { analyticsApi, reposApi } from "@/lib/api"
import type { Analytics, Repository, LeaderboardResponse, LeaderboardEntry } from "@/types"
import { TrendingUp, Shield, AlertTriangle, GitPullRequest, RefreshCw, Trophy, ArrowUp, ArrowDown, Minus } from "lucide-react"

const BADGE_COLORS: Record<string, string> = {
  quality_master: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300",
  security_champion: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
  clean_streak: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  most_improved: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  prolific: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300",
  rapid_reviewer: "bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300",
}

function TrendIcon({ value }: { value: number }) {
  if (value > 0.3) return <ArrowUp className="w-3.5 h-3.5 text-green-500" />
  if (value < -0.3) return <ArrowDown className="w-3.5 h-3.5 text-red-500" />
  return <Minus className="w-3.5 h-3.5 text-muted-foreground" />
}

function LeaderboardTab({ repos }: { repos: Repository[] }) {
  const [repoId, setRepoId] = useState<number | undefined>(repos[0]?.id)
  const [data, setData] = useState<LeaderboardResponse | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!repos.length) return
    setRepoId(repos[0].id)
  }, [repos])

  useEffect(() => {
    if (!repoId) return
    setLoading(true)
    analyticsApi.getLeaderboard({ repo_id: repoId })
      .then(setData)
      .finally(() => setLoading(false))
  }, [repoId])

  const refresh = async () => {
    if (!repoId) return
    setRefreshing(true)
    analyticsApi.getLeaderboard({ repo_id: repoId, refresh: true })
      .then(setData)
      .finally(() => setRefreshing(false))
  }

  const rankEmoji = (rank: number) => rank === 1 ? "🥇" : rank === 2 ? "🥈" : rank === 3 ? "🥉" : `#${rank}`

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="font-semibold text-lg flex items-center gap-2"><Trophy className="w-5 h-5 text-yellow-500" /> Team Leaderboard</h2>
          <p className="text-sm text-muted-foreground mt-0.5">Rankings across all reviewed PRs in this repo</p>
        </div>
        <div className="flex gap-3">
          <select value={repoId ?? ""} onChange={e => setRepoId(Number(e.target.value))}
            className="border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary">
            {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <button onClick={refresh} disabled={refreshing}
            className="flex items-center gap-2 border px-3 py-2 rounded-lg text-sm hover:bg-secondary transition-colors disabled:opacity-50">
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" /></div>
      ) : !data?.entries.length ? (
        <div className="text-center py-16 border rounded-xl bg-card text-muted-foreground">
          <Trophy className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium">No leaderboard data yet</p>
          <p className="text-sm mt-1">Complete some PR reviews first, then click Refresh.</p>
        </div>
      ) : (
        <>
          {/* Top 3 podium */}
          {data.entries.length >= 3 && (
            <div className="grid grid-cols-3 gap-4">
              {[data.entries[1], data.entries[0], data.entries[2]].map((entry, i) => {
                if (!entry) return null
                const heights = ["h-24", "h-32", "h-20"]
                const colors = ["bg-gray-100 dark:bg-gray-800", "bg-yellow-50 dark:bg-yellow-900/20", "bg-orange-50 dark:bg-orange-900/20"]
                return (
                  <div key={entry.username} className={`border rounded-xl ${colors[i]} p-4 flex flex-col items-center justify-end ${heights[i]} transition-all`}>
                    {entry.avatar_url && <img src={entry.avatar_url} alt={entry.username} className="w-10 h-10 rounded-full mb-2 border-2 border-white" />}
                    <p className="font-semibold text-sm">{entry.username}</p>
                    <p className="text-2xl">{rankEmoji(entry.rank)}</p>
                    <p className="text-sm font-bold" style={{ color: entry.avg_score >= 7 ? "#22c55e" : entry.avg_score >= 5 ? "#f59e0b" : "#ef4444" }}>
                      {entry.avg_score.toFixed(1)}
                    </p>
                  </div>
                )
              })}
            </div>
          )}

          {/* Full table */}
          <div className="border rounded-xl bg-card overflow-hidden">
            <table className="w-full text-sm">
              <thead className="border-b bg-secondary/30">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Rank</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground">Developer</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">PRs</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground">Avg Score</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground hidden md:table-cell">Trend</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground hidden lg:table-cell">Critical</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground hidden lg:table-cell">Security</th>
                  <th className="text-right px-4 py-3 font-medium text-muted-foreground hidden xl:table-cell">Streak</th>
                  <th className="text-left px-4 py-3 font-medium text-muted-foreground hidden xl:table-cell">Badges</th>
                </tr>
              </thead>
              <tbody>
                {data.entries.map((entry) => (
                  <tr key={entry.username} className="border-b last:border-0 hover:bg-secondary/20 transition-colors">
                    <td className="px-4 py-3 text-lg">{rankEmoji(entry.rank)}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {entry.avatar_url && <img src={entry.avatar_url} alt={entry.username} className="w-7 h-7 rounded-full" />}
                        <span className="font-medium">{entry.username}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">{entry.total_prs}</td>
                    <td className="px-4 py-3 text-right">
                      <span className={`font-semibold ${entry.avg_score >= 7 ? "text-green-600" : entry.avg_score >= 5 ? "text-yellow-600" : "text-red-600"}`}>
                        {entry.avg_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right hidden md:table-cell">
                      <div className="flex items-center justify-end gap-1">
                        <TrendIcon value={entry.score_trend} />
                        <span className="text-xs text-muted-foreground">{entry.score_trend > 0 ? "+" : ""}{entry.score_trend.toFixed(1)}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right hidden lg:table-cell">
                      {entry.critical_issues > 0 ? <span className="text-red-600 font-medium">{entry.critical_issues}</span> : <span className="text-green-600">0</span>}
                    </td>
                    <td className="px-4 py-3 text-right hidden lg:table-cell">
                      {entry.security_issues > 0 ? <span className="text-orange-600">{entry.security_issues}</span> : <span className="text-green-600">0</span>}
                    </td>
                    <td className="px-4 py-3 text-right hidden xl:table-cell">
                      {entry.clean_streak > 0 && <span className="text-orange-600">🔥 {entry.clean_streak}</span>}
                    </td>
                    <td className="px-4 py-3 hidden xl:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {entry.badges.map(b => (
                          <span key={b.id} title={b.desc} className={`text-xs px-2 py-0.5 rounded-full font-medium cursor-help ${BADGE_COLORS[b.id] || "bg-secondary"}`}>
                            {b.label}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

export default function AnalyticsPage() {
  const [analytics, setAnalytics] = useState<Analytics | null>(null)
  const [repos, setRepos] = useState<Repository[]>([])
  const [repoFilter, setRepoFilter] = useState<number | undefined>()
  const [days, setDays] = useState(30)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<"overview" | "leaderboard">("overview")

  useEffect(() => { reposApi.list().then(setRepos) }, [])

  useEffect(() => {
    setLoading(true)
    analyticsApi.get({ repo_id: repoFilter, days }).then(setAnalytics).finally(() => setLoading(false))
  }, [repoFilter, days])

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-1">Code quality trends and team insights</p>
        </div>
        <div className="flex gap-3">
          <select value={repoFilter ?? ""} onChange={e => setRepoFilter(e.target.value ? Number(e.target.value) : undefined)}
            className="border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary">
            <option value="">All repos</option>
            {repos.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}
          </select>
          <select value={days} onChange={e => setDays(Number(e.target.value))}
            className="border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary">
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
          </select>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b">
        <div className="flex gap-0">
          {(["overview", "leaderboard"] as const).map(tab => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-5 py-3 text-sm font-medium border-b-2 transition-colors capitalize ${activeTab === tab ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
              {tab === "leaderboard" ? "🏆 Leaderboard" : "📊 Overview"}
            </button>
          ))}
        </div>
      </div>

      {activeTab === "leaderboard" && <LeaderboardTab repos={repos} />}

      {activeTab === "overview" && (
        loading ? (
          <div className="flex items-center justify-center h-48"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" /></div>
        ) : !analytics ? null : (
          <div className="space-y-6">
            {/* Stats */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              {[
                { label: "PRs reviewed", value: analytics.total_prs_reviewed, icon: <GitPullRequest className="w-4 h-4" />, color: "text-blue-600" },
                { label: "Avg score", value: analytics.avg_score_all_time.toFixed(1) + "/10", icon: <TrendingUp className="w-4 h-4" />, color: "text-green-600" },
                { label: "Issues caught", value: analytics.issues_caught, icon: <AlertTriangle className="w-4 h-4" />, color: "text-yellow-600" },
                { label: "Security flags", value: analytics.security_flags, icon: <Shield className="w-4 h-4" />, color: "text-red-600" },
              ].map(s => (
                <div key={s.label} className="border rounded-xl p-4 bg-card space-y-2">
                  <div className={`flex items-center gap-2 ${s.color}`}>{s.icon}<span className="text-xs text-muted-foreground">{s.label}</span></div>
                  <p className="text-2xl font-bold">{s.value}</p>
                </div>
              ))}
            </div>

            {/* Quality trend */}
            {analytics.quality_trend.length > 0 && (
              <div className="border rounded-xl p-6 bg-card space-y-4">
                <h2 className="font-semibold">Quality Score Over Time</h2>
                <ResponsiveContainer width="100%" height={240}>
                  <LineChart data={analytics.quality_trend} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--border))" />
                    <YAxis domain={[0, 10]} tick={{ fontSize: 11 }} stroke="hsl(var(--border))" />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                    <Line type="monotone" dataKey="avg_score" name="Avg score" stroke="#3b82f6" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Issues per day */}
            {analytics.quality_trend.length > 0 && (
              <div className="border rounded-xl p-6 bg-card space-y-4">
                <h2 className="font-semibold">Issues Caught Per Day</h2>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={analytics.quality_trend} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} stroke="hsl(var(--border))" />
                    <YAxis tick={{ fontSize: 11 }} stroke="hsl(var(--border))" />
                    <Tooltip contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                    <Bar dataKey="critical_issues" name="Critical" fill="#ef4444" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="pr_count" name="PRs reviewed" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}

            {analytics.quality_trend.length === 0 && (
              <div className="text-center py-16 border rounded-xl bg-card text-muted-foreground">
                <TrendingUp className="w-10 h-10 mx-auto mb-3 opacity-30" />
                <p className="font-medium">No analytics data yet</p>
                <p className="text-sm mt-1">Connect a repo and let AI review some PRs first.</p>
              </div>
            )}
          </div>
        )
      )}
    </div>
  )
}
