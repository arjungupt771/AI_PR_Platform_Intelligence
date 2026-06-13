"use client"
import { useEffect, useState, useRef } from "react"
import { useParams } from "next/navigation"
import { AlertTriangle, Shield, Lightbulb, Info, MessageSquare, Send, RefreshCw, ExternalLink, Download, Activity } from "lucide-react"
import { prsApi, downloadPDF } from "@/lib/api"
import type { PullRequest, Review, ChatMessage, ReviewIssue, ModelBreakdown } from "@/types"
import { formatDistanceToNow } from "date-fns"
import ReactMarkdown from "react-markdown"
import { usePRPoller } from "@/hooks/usePRPoller"

const SEVERITY_CFG = {
  critical:   { bar: "border-l-red-500 bg-red-50 dark:bg-red-950/20",    badge: "badge-critical",    icon: <AlertTriangle className="w-4 h-4 text-red-500" /> },
  warning:    { bar: "border-l-yellow-500 bg-yellow-50 dark:bg-yellow-950/20", badge: "badge-warning", icon: <AlertTriangle className="w-4 h-4 text-yellow-500" /> },
  suggestion: { bar: "border-l-blue-500 bg-blue-50 dark:bg-blue-950/20",  badge: "badge-suggestion", icon: <Lightbulb className="w-4 h-4 text-blue-500" /> },
  info:       { bar: "border-l-green-500 bg-green-50 dark:bg-green-950/20", badge: "badge-info",      icon: <Info className="w-4 h-4 text-green-500" /> },
}
const RISK_CFG = {
  low:      { color: "text-green-600 bg-green-100 dark:bg-green-900/30", label: "Low Risk" },
  medium:   { color: "text-yellow-600 bg-yellow-100 dark:bg-yellow-900/30", label: "Medium Risk" },
  high:     { color: "text-red-600 bg-red-100 dark:bg-red-900/30", label: "High Risk" },
  critical: { color: "text-red-700 bg-red-200 dark:bg-red-900/50", label: "Critical Risk" },
}
const PROVIDER_COLOR: Record<string, string> = {
  groq: "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300",
  openai: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300",
  gemini: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300",
}

function ScoreGauge({ score }: { score: number }) {
  const color = score >= 7 ? "#22c55e" : score >= 5 ? "#f59e0b" : "#ef4444"
  return (
    <svg width="88" height="88" viewBox="0 0 88 88">
      <circle cx="44" cy="44" r="34" fill="none" stroke="currentColor" strokeWidth="6" className="text-muted opacity-30" />
      <circle cx="44" cy="44" r="34" fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={2*Math.PI*34} strokeDashoffset={2*Math.PI*34-(score/10)*2*Math.PI*34}
        strokeLinecap="round" transform="rotate(-90 44 44)" />
      <text x="44" y="40" textAnchor="middle" fontSize="18" fontWeight="700" fill={color}>{score.toFixed(1)}</text>
      <text x="44" y="54" textAnchor="middle" fontSize="9" fill="currentColor" className="opacity-60">/10</text>
    </svg>
  )
}

function ConsensusPanel({ review }: { review: Review }) {
  if (!review.model_breakdown?.length) return null
  return (
    <div className="border rounded-xl bg-card p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold flex items-center gap-2">
          <Activity className="w-4 h-4 text-primary" /> Multi-LLM Consensus
        </h3>
        {review.consensus_score !== null && review.consensus_score !== undefined && (
          <span className={`text-sm font-semibold px-2 py-1 rounded-full ${review.consensus_score >= 66 ? "bg-green-100 text-green-800" : "bg-yellow-100 text-yellow-800"}`}>
            {review.consensus_score}% agreement
          </span>
        )}
      </div>
      <div className="grid gap-3">
        {review.model_breakdown.map((m) => (
          <div key={m.provider} className="flex items-center gap-3 p-3 bg-secondary/30 rounded-lg">
            <span className={`text-xs font-semibold px-2 py-0.5 rounded-full uppercase ${PROVIDER_COLOR[m.provider] || "bg-secondary"}`}>
              {m.provider}
            </span>
            <span className="text-xs text-muted-foreground flex-1">{m.model}</span>
            <div className="flex items-center gap-3 text-sm">
              <span className={`font-semibold ${m.score && m.score >= 7 ? "text-green-600" : m.score && m.score >= 5 ? "text-yellow-600" : "text-red-600"}`}>
                {m.score?.toFixed(1) ?? "—"}/10
              </span>
              {m.critical_count > 0 && <span className="text-red-600 text-xs">🔴 {m.critical_count}</span>}
              {m.security_flags > 0 && <span className="text-orange-600 text-xs">🛡 {m.security_flags}</span>}
              <span className="text-xs text-muted-foreground">{m.latency_ms}ms</span>
            </div>
          </div>
        ))}
      </div>
      <p className="text-xs text-muted-foreground">
        Issues confirmed by multiple models are weighted higher. Consensus score = % of models that agree on severity.
      </p>
    </div>
  )
}

function IssueCard({ issue }: { issue: ReviewIssue }) {
  const cfg = SEVERITY_CFG[issue.severity] || SEVERITY_CFG.info
  return (
    <div className={`border-l-4 rounded-r-lg p-4 space-y-1.5 ${cfg.bar}`}>
      <div className="flex items-start gap-2">
        {cfg.icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cfg.badge}`}>{issue.severity}</span>
            <code className="text-xs bg-secondary px-1.5 py-0.5 rounded text-muted-foreground truncate">{issue.file}{issue.line ? `:${issue.line}` : ""}</code>
            {(issue.confirmed_by ?? 1) > 1 && (
              <span className="text-xs bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300 px-2 py-0.5 rounded-full">
                ✓ {issue.confirmed_by} models agree
              </span>
            )}
          </div>
          <p className="font-medium text-sm mt-1">{issue.title}</p>
          <p className="text-sm text-muted-foreground">{issue.description}</p>
          {issue.suggestion && (
            <div className="mt-1.5 text-sm bg-background/60 rounded p-2 border">
              <span className="font-medium">Fix: </span>{issue.suggestion}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default function PRDetailPage() {
  const params = useParams()
  const prId = Number(params.id)
  const [pr, setPr] = useState<PullRequest | null>(null)
  const [review, setReview] = useState<Review | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const [activeTab, setActiveTab] = useState<"review" | "consensus" | "chat">("review")
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    prsApi.get(prId).then(setPr)
    prsApi.getReview(prId).then(setReview).catch(() => {})
    prsApi.getChatHistory(prId).then(setMessages)
  }, [prId])

  usePRPoller(prId, pr?.status ?? "completed", (r) => setReview(r))

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  const handleSend = async () => {
    if (!input.trim() || sending) return
    const text = input.trim(); setInput(""); setSending(true)
    const temp: ChatMessage = { id: Date.now(), role: "user", content: text, created_at: new Date().toISOString() }
    setMessages(p => [...p, temp])
    try {
      const resp = await prsApi.sendMessage(prId, text)
      setMessages(p => [...p.filter(m => m.id !== temp.id), temp, resp])
    } catch { setMessages(p => p.filter(m => m.id !== temp.id)) }
    finally { setSending(false) }
  }

  if (!pr) return <div className="flex items-center justify-center h-64"><div className="animate-spin w-6 h-6 border-2 border-primary border-t-transparent rounded-full" /></div>

  const critCount = review?.issues.filter(i => i.severity === "critical").length ?? 0
  const risk = pr.risk_level ? RISK_CFG[pr.risk_level] : null

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b p-5 bg-card">
        <div className="flex items-start justify-between gap-4">
          <div className="space-y-1 min-w-0">
            <div className="flex items-center gap-2 text-sm text-muted-foreground flex-wrap">
              <span>#{pr.number}</span><span>·</span><span>{pr.author}</span><span>·</span>
              <span>{formatDistanceToNow(new Date(pr.created_at), { addSuffix: true })}</span>
              {risk && <span className={`px-2 py-0.5 rounded-full text-xs font-semibold ${risk.color}`}>{risk.label}</span>}
              {pr.risk_score !== null && pr.risk_score !== undefined && (
                <span className="text-xs text-muted-foreground">risk: {pr.risk_score}/100</span>
              )}
            </div>
            <h1 className="text-xl font-semibold">{pr.title}</h1>
            <div className="flex items-center gap-2 text-sm text-muted-foreground flex-wrap">
              <code className="bg-secondary px-2 py-0.5 rounded">{pr.head_branch}</code>
              <span>→</span><code className="bg-secondary px-2 py-0.5 rounded">{pr.base_branch}</code>
              <span>·</span><span>{pr.files_changed} files</span>
              <span className="text-green-600">+{pr.additions}</span>
              <span className="text-red-600">-{pr.deletions}</span>
            </div>
            {pr.risk_factors?.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-1">
                {pr.risk_factors.slice(0, 3).map((f, i) => (
                  <span key={i} className="text-xs text-muted-foreground bg-secondary px-2 py-0.5 rounded-full">{f}</span>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {pr.github_url && (
              <a href={pr.github_url} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 text-sm border px-3 py-1.5 rounded-lg hover:bg-secondary transition-colors">
                <ExternalLink className="w-3.5 h-3.5" /> GitHub
              </a>
            )}
            {review && (
              <button onClick={() => downloadPDF(prId)}
                className="flex items-center gap-1.5 text-sm border px-3 py-1.5 rounded-lg hover:bg-secondary transition-colors">
                <Download className="w-3.5 h-3.5" /> PDF
              </button>
            )}
            <button onClick={() => prsApi.rereview(prId)}
              className="flex items-center gap-1.5 text-sm bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:bg-primary/90 transition-colors">
              <RefreshCw className="w-3.5 h-3.5" /> Re-review
            </button>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b bg-card px-5">
        <div className="flex gap-0">
          {(["review", "consensus", "chat"] as const).map((tab) => (
            <button key={tab} onClick={() => setActiveTab(tab)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors capitalize ${activeTab === tab ? "border-primary text-foreground" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
              {tab === "consensus" ? "🤖 Consensus" : tab === "chat" ? "💬 Chat" : "📋 Review"}
            </button>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-auto p-5">
        {/* Review Tab */}
        {activeTab === "review" && review && (
          <div className="max-w-4xl space-y-5">
            <div className="border rounded-xl p-5 bg-card flex gap-5 items-start">
              {review.overall_score != null && <ScoreGauge score={review.overall_score} />}
              <div className="flex-1 space-y-2">
                <p className="text-sm leading-relaxed">{review.summary}</p>
                <div className="flex gap-3 text-sm flex-wrap">
                  {critCount > 0 && <span className="flex items-center gap-1 text-red-600"><AlertTriangle className="w-3.5 h-3.5" />{critCount} critical</span>}
                  {review.security_flags.length > 0 && <span className="flex items-center gap-1 text-orange-600"><Shield className="w-3.5 h-3.5" />{review.security_flags.length} security</span>}
                  {review.consensus_score !== null && review.consensus_score !== undefined && (
                    <span className="flex items-center gap-1 text-purple-600"><Activity className="w-3.5 h-3.5" />{review.consensus_score}% consensus</span>
                  )}
                </div>
                <div className="flex gap-4 text-xs text-muted-foreground flex-wrap">
                  {review.metrics.complexity && <span>Complexity: {review.metrics.complexity}</span>}
                  {review.metrics.test_coverage_hint && <span>Tests: {review.metrics.test_coverage_hint}</span>}
                  {review.metrics.breaking_changes && <span className="text-red-600 font-medium">⚠ Breaking changes</span>}
                  <span>Models: {review.models_used.join(", ")}</span>
                </div>
              </div>
            </div>
            {review.security_flags.length > 0 && (
              <div className="border border-red-200 dark:border-red-900 rounded-xl p-4 bg-red-50 dark:bg-red-950/20 space-y-2">
                <h3 className="font-semibold flex items-center gap-2 text-red-700"><Shield className="w-4 h-4" />Security Flags</h3>
                {review.security_flags.map((f, i) => <p key={i} className="text-sm text-red-700">• {f}</p>)}
              </div>
            )}
            {review.issues.length > 0 && (
              <div className="space-y-3">
                <h3 className="font-semibold">Issues ({review.issues.length})</h3>
                {review.issues.map((issue, i) => <IssueCard key={i} issue={issue} />)}
              </div>
            )}
            {review.suggestions.length > 0 && (
              <div className="border rounded-xl p-4 bg-card space-y-2">
                <h3 className="font-semibold">Suggestions</h3>
                {review.suggestions.map((s, i) => <p key={i} className="text-sm text-muted-foreground flex gap-2"><Lightbulb className="w-4 h-4 text-blue-500 shrink-0 mt-0.5" />{s}</p>)}
              </div>
            )}
          </div>
        )}

        {/* Consensus Tab */}
        {activeTab === "consensus" && review && (
          <div className="max-w-3xl space-y-5">
            <ConsensusPanel review={review} />
            {review.issues.filter(i => (i.confirmed_by ?? 1) > 1).length > 0 && (
              <div className="space-y-3">
                <h3 className="font-semibold">Cross-Model Confirmed Issues</h3>
                <p className="text-sm text-muted-foreground">These issues were independently flagged by multiple models — highest confidence.</p>
                {review.issues.filter(i => (i.confirmed_by ?? 1) > 1).map((issue, i) => <IssueCard key={i} issue={issue} />)}
              </div>
            )}
            {review.model_breakdown?.length === 1 && (
              <div className="border rounded-xl p-5 text-center text-muted-foreground bg-card">
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-30" />
                <p className="font-medium">Only Groq reviewed this PR</p>
                <p className="text-sm mt-1">Add OPENAI_API_KEY or GOOGLE_API_KEY to enable multi-model consensus.</p>
              </div>
            )}
          </div>
        )}

        {/* Chat Tab */}
        {activeTab === "chat" && (
          <div className="max-w-3xl mx-auto flex flex-col" style={{ height: "calc(100vh - 280px)" }}>
            <div className="flex-1 overflow-y-auto space-y-4 pb-4">
              {messages.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  <MessageSquare className="w-8 h-8 mx-auto mb-3 opacity-50" />
                  <p>Ask anything about this PR</p>
                  <div className="mt-4 flex flex-wrap gap-2 justify-center">
                    {["What's the risk of merging?", "Explain the main change", "Any performance concerns?", "Which model found the most issues?"].map(q => (
                      <button key={q} onClick={() => setInput(q)} className="text-sm border px-3 py-1.5 rounded-lg hover:bg-secondary transition-colors">{q}</button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map(msg => (
                <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-card border"}`}>
                    {msg.role === "assistant" ? <ReactMarkdown className="prose prose-sm dark:prose-invert max-w-none">{msg.content}</ReactMarkdown> : msg.content}
                  </div>
                </div>
              ))}
              {sending && <div className="flex justify-start"><div className="bg-card border rounded-2xl px-4 py-3"><div className="flex gap-1">{[0,1,2].map(i => <div key={i} className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{animationDelay:`${i*0.15}s`}} />)}</div></div></div>}
              <div ref={messagesEndRef} />
            </div>
            <div className="border-t pt-4 flex gap-2">
              <input value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && !e.shiftKey && handleSend()}
                placeholder="Ask about this PR..."
                className="flex-1 border rounded-xl px-4 py-2.5 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
              <button onClick={handleSend} disabled={sending || !input.trim()}
                className="bg-primary text-primary-foreground p-2.5 rounded-xl hover:bg-primary/90 disabled:opacity-50 transition-colors">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {activeTab === "review" && !review && (
          <div className="text-center py-12 text-muted-foreground">
            <RefreshCw className="w-8 h-8 mx-auto mb-3 opacity-50 animate-spin" />
            <p>Review in progress — auto-updating...</p>
          </div>
        )}
      </div>
    </div>
  )
}
