"use client"
import { useState } from "react"
import { useAuthStore } from "@/store"
import { Shield, Bell, User, Bot, MessageSquare } from "lucide-react"

function Toggle({ defaultChecked = false }: { defaultChecked?: boolean }) {
  const [on, setOn] = useState(defaultChecked)
  return (
    <button onClick={() => setOn(v => !v)}
      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors shrink-0 ${on ? "bg-primary" : "bg-muted"}`}>
      <span className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${on ? "translate-x-4" : "translate-x-0.5"}`} />
    </button>
  )
}

function Section({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return (
    <section className="border rounded-xl bg-card overflow-hidden">
      <div className="px-6 py-4 border-b flex items-center gap-2">
        <span className="text-muted-foreground">{icon}</span>
        <h2 className="font-medium">{title}</h2>
      </div>
      <div className="p-6 space-y-5">{children}</div>
    </section>
  )
}

function PrefRow({ label, desc, defaultChecked = false }: { label: string; desc: string; defaultChecked?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
      </div>
      <Toggle defaultChecked={defaultChecked} />
    </div>
  )
}

export default function SettingsPage() {
  const { user } = useAuthStore()
  const [saved, setSaved] = useState(false)
  const [slackToken, setSlackToken] = useState("")
  const [slackChannel, setSlackChannel] = useState("")
  const [discordUrl, setDiscordUrl] = useState("")
  const [openaiKey, setOpenaiKey] = useState("")
  const [googleKey, setGoogleKey] = useState("")

  const handleSave = () => { setSaved(true); setTimeout(() => setSaved(false), 2000) }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your account and preferences</p>
      </div>

      {/* Profile */}
      <Section icon={<User className="w-4 h-4" />} title="Profile">
        <div className="flex items-center gap-4">
          {user?.avatar_url && <img src={user.avatar_url} alt={user.username} className="w-14 h-14 rounded-full border" />}
          <div>
            <p className="font-medium">{user?.username}</p>
            <p className="text-sm text-muted-foreground">{user?.email ?? "No email set"}</p>
            <p className="text-xs text-muted-foreground mt-0.5">Connected via GitHub</p>
          </div>
        </div>
      </Section>

      {/* Multi-LLM config */}
      <Section icon={<Bot className="w-4 h-4" />} title="Multi-LLM Engine">
        <div className="p-3 bg-secondary/50 rounded-lg text-sm space-y-1">
          <p className="font-medium">Primary: Groq (llama-3.3-70b-versatile) ✓</p>
          <p className="text-muted-foreground text-xs">Always active. Set <code className="bg-background px-1 rounded">GROQ_API_KEY</code> in your .env</p>
        </div>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">OpenAI API Key (optional — enables GPT-4o consensus)</label>
            <input value={openaiKey} onChange={e => setOpenaiKey(e.target.value)}
              type="password" placeholder="sk-..."
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
            <p className="text-xs text-muted-foreground mt-1">Set <code className="bg-secondary px-1 rounded">OPENAI_API_KEY</code> in .env or override here</p>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Google API Key (optional — enables Gemini consensus)</label>
            <input value={googleKey} onChange={e => setGoogleKey(e.target.value)}
              type="password" placeholder="AIza..."
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
            <p className="text-xs text-muted-foreground mt-1">Set <code className="bg-secondary px-1 rounded">GOOGLE_API_KEY</code> in .env or override here</p>
          </div>
        </div>
        <div className="bg-blue-50 dark:bg-blue-950/30 rounded-lg p-3 text-xs text-blue-700 dark:text-blue-300">
          With all 3 models active, each PR gets reviewed independently by Groq, GPT-4o, and Gemini — then consensus scored. Issues confirmed by 2+ models are highlighted with higher confidence.
        </div>
      </Section>

      {/* Review prefs */}
      <Section icon={<Shield className="w-4 h-4" />} title="Review Preferences">
        <PrefRow label="Security analysis" desc="OWASP vulnerabilities, auth flaws, injection risks" defaultChecked={true} />
        <PrefRow label="Static scan (Bandit + Semgrep)" desc="Run before LLM review — combined static + AI analysis" defaultChecked={true} />
        <PrefRow label="Performance hints" desc="N+1 queries, inefficient loops, memory issues" defaultChecked={true} />
        <PrefRow label="Test coverage hints" desc="Suggest missing test cases based on changed code" />
        <PrefRow label="Style suggestions" desc="Naming, formatting, and code clarity" />
        <PrefRow label="Post review as GitHub comment" desc="Automatically post the AI review as a PR comment" />
      </Section>

      {/* Notifications */}
      <Section icon={<MessageSquare className="w-4 h-4" />} title="Notifications — Slack &amp; Discord">
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium mb-1">Slack Bot Token</label>
            <input value={slackToken} onChange={e => setSlackToken(e.target.value)}
              type="password" placeholder="xoxb-..."
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Slack Channel ID</label>
            <input value={slackChannel} onChange={e => setSlackChannel(e.target.value)}
              placeholder="C0XXXXXXXXX"
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Discord Webhook URL</label>
            <input value={discordUrl} onChange={e => setDiscordUrl(e.target.value)}
              placeholder="https://discord.com/api/webhooks/..."
              className="w-full border rounded-lg px-3 py-2 text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <p className="text-xs text-muted-foreground">
            These values can also be set in <code className="bg-secondary px-1 rounded">.env</code> as <code className="bg-secondary px-1 rounded">SLACK_BOT_TOKEN</code>, <code className="bg-secondary px-1 rounded">SLACK_CHANNEL_ID</code>, <code className="bg-secondary px-1 rounded">DISCORD_WEBHOOK_URL</code>
          </p>
        </div>
        <div className="border-t pt-4 space-y-3">
          <p className="text-sm font-medium">Notification triggers</p>
          <PrefRow label="Review completed" desc="Notify when an AI review finishes" defaultChecked={true} />
          <PrefRow label="Critical issues found" desc="Alert when critical severity issues are detected" defaultChecked={true} />
          <PrefRow label="Security flags" desc="Immediate alert for any security-related findings" defaultChecked={true} />
          <PrefRow label="High risk PR" desc="Alert when risk prediction scores High or Critical" defaultChecked={true} />
        </div>
      </Section>

      {/* Alert prefs */}
      <Section icon={<Bell className="w-4 h-4" />} title="In-App Alerts">
        <PrefRow label="Auto-refresh PR list" desc="Poll for review status changes every 6 seconds" defaultChecked={true} />
        <PrefRow label="Show model latency" desc="Display response time for each LLM in consensus panel" defaultChecked={true} />
        <PrefRow label="Highlight multi-model issues" desc="Badge issues confirmed by 2+ models" defaultChecked={true} />
      </Section>

      <div className="flex justify-end">
        <button onClick={handleSave}
          className="bg-primary text-primary-foreground px-6 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors">
          {saved ? "✓ Saved" : "Save preferences"}
        </button>
      </div>
    </div>
  )
}
