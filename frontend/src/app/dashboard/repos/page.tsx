"use client"
import { useEffect, useState } from "react"
import { Database, Plus, RefreshCw, Trash2, Lock, Globe, CheckCircle, Clock, Search, ChevronDown, ChevronUp, Save } from "lucide-react"
import { reposApi } from "@/lib/api"
import type { Repository } from "@/types"
import { formatDistanceToNow } from "date-fns"

function IndexStatus({ repo }: { repo: Repository }) {
  if (repo.is_indexed) return <span className="inline-flex items-center gap-1 text-xs text-green-600"><CheckCircle className="w-3 h-3" /> Indexed</span>
  return <span className="inline-flex items-center gap-1 text-xs text-yellow-600"><Clock className="w-3 h-3" /> Pending</span>
}

function MemoryEditor({ repo, onClose }: { repo: Repository; onClose: () => void }) {
  const [arch, setArch] = useState(repo.architecture_docs ?? "")
  const [standards, setStandards] = useState(repo.coding_standards ?? "")
  const [conventions, setConventions] = useState(repo.team_conventions ?? "")
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    reposApi.getMemory(repo.id).then(m => {
      setArch(m.architecture_docs ?? "")
      setStandards(m.coding_standards ?? "")
      setConventions(m.team_conventions ?? "")
    }).catch(() => {})
  }, [repo.id])

  const save = async () => {
    setSaving(true)
    await reposApi.updateMemory(repo.id, {
      architecture_docs: arch,
      coding_standards: standards,
      team_conventions: conventions,
    })
    setSaving(false)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="border-t bg-secondary/10 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="font-medium text-sm">Semantic Memory</h3>
          <p className="text-xs text-muted-foreground mt-0.5">This context is injected into every AI review for {repo.name}</p>
        </div>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground text-xl leading-none">×</button>
      </div>
      <div className="grid gap-3">
        {[
          { label: "🏗️ Architecture Docs", placeholder: "e.g. FastAPI backend + Next.js frontend. Auth uses JWT. DB is PostgreSQL with Alembic migrations.", value: arch, set: setArch },
          { label: "📏 Coding Standards", placeholder: "e.g. All functions must have type hints. Use snake_case. Max function length 50 lines. No bare exceptions.", value: standards, set: setStandards },
          { label: "🤝 Team Conventions", placeholder: "e.g. PRs must reference a Jira ticket. Migrations should be reversible. Never store secrets in code.", value: conventions, set: setConventions },
        ].map(f => (
          <div key={f.label}>
            <label className="block text-xs font-medium text-muted-foreground mb-1">{f.label}</label>
            <textarea
              value={f.value}
              onChange={e => f.set(e.target.value)}
              placeholder={f.placeholder}
              rows={3}
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary resize-none"
            />
          </div>
        ))}
      </div>
      <div className="flex justify-end">
        <button onClick={save} disabled={saving}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 disabled:opacity-50 transition-colors">
          <Save className="w-3.5 h-3.5" />
          {saving ? "Saving..." : saved ? "✓ Saved" : "Save to memory"}
        </button>
      </div>
    </div>
  )
}

export default function ReposPage() {
  const [repos, setRepos] = useState<Repository[]>([])
  const [available, setAvailable] = useState<any[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [search, setSearch] = useState("")
  const [connecting, setConnecting] = useState<string | null>(null)
  const [reindexing, setReindexing] = useState<number | null>(null)
  const [expandedMemory, setExpandedMemory] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)

  const connectedIds = new Set(repos.map(r => r.full_name))

  useEffect(() => { reposApi.list().then(setRepos).finally(() => setLoading(false)) }, [])

  const loadAvailable = async () => {
    const data = await reposApi.listAvailable()
    setAvailable(data)
    setShowAdd(true)
  }

  const connect = async (repo: any) => {
    setConnecting(repo.full_name)
    try {
      const connected = await reposApi.connect({
        github_repo_id: repo.github_repo_id, full_name: repo.full_name,
        name: repo.name, description: repo.description,
        language: repo.language, is_private: repo.is_private,
      })
      setRepos(prev => [...prev, connected])
      setShowAdd(false)
    } finally { setConnecting(null) }
  }

  const disconnect = async (repoId: number) => {
    if (!confirm("Disconnect this repo? All review history will be removed.")) return
    await reposApi.disconnect(repoId)
    setRepos(prev => prev.filter(r => r.id !== repoId))
  }

  const reindex = async (repoId: number) => {
    setReindexing(repoId)
    await reposApi.reindex(repoId).finally(() => setReindexing(null))
  }

  const filteredAvailable = available.filter(r =>
    r.full_name.toLowerCase().includes(search.toLowerCase()) && !connectedIds.has(r.full_name)
  )

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Repositories</h1>
          <p className="text-sm text-muted-foreground mt-1">{repos.length} connected</p>
        </div>
        <button onClick={loadAvailable}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors">
          <Plus className="w-4 h-4" /> Add repository
        </button>
      </div>

      {/* Add repo panel */}
      {showAdd && (
        <div className="border rounded-xl bg-card p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">Select a repository to connect</h2>
            <button onClick={() => setShowAdd(false)} className="text-muted-foreground hover:text-foreground text-xl leading-none">×</button>
          </div>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search repositories..."
              className="w-full pl-9 pr-4 py-2 border rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <div className="max-h-72 overflow-y-auto space-y-1">
            {filteredAvailable.length === 0 ? (
              <p className="text-center py-6 text-muted-foreground text-sm">No repositories found</p>
            ) : filteredAvailable.map(repo => (
              <div key={repo.github_repo_id} className="flex items-center justify-between p-3 hover:bg-secondary/50 rounded-lg transition-colors">
                <div className="flex items-center gap-2">
                  {repo.is_private ? <Lock className="w-4 h-4 text-muted-foreground" /> : <Globe className="w-4 h-4 text-muted-foreground" />}
                  <div>
                    <p className="text-sm font-medium">{repo.full_name}</p>
                    {repo.language && <p className="text-xs text-muted-foreground">{repo.language}</p>}
                  </div>
                </div>
                <button onClick={() => connect(repo)} disabled={connecting === repo.full_name}
                  className="text-sm bg-primary text-primary-foreground px-3 py-1.5 rounded-lg hover:bg-primary/90 disabled:opacity-50 transition-colors">
                  {connecting === repo.full_name ? "Connecting..." : "Connect"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Connected repos */}
      {loading ? (
        <div className="flex items-center justify-center h-32"><div className="animate-spin w-5 h-5 border-2 border-primary border-t-transparent rounded-full" /></div>
      ) : repos.length === 0 ? (
        <div className="text-center py-16 border rounded-xl bg-card text-muted-foreground">
          <Database className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="font-medium">No repositories connected</p>
          <p className="text-sm mt-1">Connect a GitHub repo to start getting AI reviews.</p>
        </div>
      ) : (
        <div className="space-y-2">
          {repos.map(repo => (
            <div key={repo.id} className="border rounded-xl bg-card overflow-hidden">
              <div className="p-5 flex items-center justify-between gap-4">
                <div className="flex items-start gap-3 flex-1 min-w-0">
                  <div className="w-10 h-10 bg-secondary rounded-lg flex items-center justify-center shrink-0">
                    <Database className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="font-medium text-sm truncate">{repo.full_name}</p>
                      {repo.is_private && <Lock className="w-3 h-3 text-muted-foreground shrink-0" />}
                      {repo.language && <span className="text-xs text-muted-foreground bg-secondary px-1.5 py-0.5 rounded shrink-0">{repo.language}</span>}
                    </div>
                    {repo.description && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">{repo.description}</p>}
                    <div className="flex items-center gap-4 mt-1.5 flex-wrap">
                      <IndexStatus repo={repo} />
                      {repo.is_indexed && repo.indexed_at && (
                        <span className="text-xs text-muted-foreground">Indexed {formatDistanceToNow(new Date(repo.indexed_at), { addSuffix: true })}</span>
                      )}
                      <span className="text-xs text-muted-foreground">{repo.pr_count} PRs</span>
                      {(repo.architecture_docs || repo.coding_standards || repo.team_conventions) && (
                        <span className="text-xs text-purple-600">🧠 Memory set</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button onClick={() => setExpandedMemory(expandedMemory === repo.id ? null : repo.id)}
                    title="Edit semantic memory" className="flex items-center gap-1 p-2 border rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground transition-colors text-xs">
                    🧠 {expandedMemory === repo.id ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                  </button>
                  <button onClick={() => reindex(repo.id)} disabled={reindexing === repo.id} title="Re-index codebase"
                    className="p-2 border rounded-lg hover:bg-secondary text-muted-foreground hover:text-foreground disabled:opacity-50 transition-colors">
                    <RefreshCw className={`w-4 h-4 ${reindexing === repo.id ? "animate-spin" : ""}`} />
                  </button>
                  <button onClick={() => disconnect(repo.id)} title="Disconnect repository"
                    className="p-2 border rounded-lg hover:bg-destructive/10 text-muted-foreground hover:text-destructive transition-colors">
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              {expandedMemory === repo.id && <MemoryEditor repo={repo} onClose={() => setExpandedMemory(null)} />}
            </div>
          ))}
        </div>
      )}

      {/* Webhook setup */}
      {repos.length > 0 && (
        <div className="border rounded-xl p-5 bg-card space-y-3">
          <h2 className="font-medium text-sm">Webhook Setup</h2>
          <p className="text-sm text-muted-foreground">To receive automatic PR reviews, add a webhook to each connected repo:</p>
          <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
            <li>Go to your repo → Settings → Webhooks → Add webhook</li>
            <li>Payload URL: <code className="bg-secondary px-1 rounded">https://your-domain/api/webhooks/github</code></li>
            <li>Content type: <code className="bg-secondary px-1 rounded">application/json</code></li>
            <li>Events: Pull requests only</li>
            <li>Secret: your <code className="bg-secondary px-1 rounded">GITHUB_WEBHOOK_SECRET</code></li>
          </ol>
          <p className="text-xs text-muted-foreground">For local dev: run <code className="bg-secondary px-1 rounded">bash scripts/ngrok-setup.sh</code></p>
        </div>
      )}
    </div>
  )
}
