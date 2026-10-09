"use client"
import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Github, Zap, Shield, TrendingUp, MessageSquare } from "lucide-react"
import { useAuthStore } from "@/store"
import { authApi } from "@/lib/api"

export default function HomePage() {
  const router = useRouter()
  const { isAuthenticated, setAuth } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) {
      router.push("/dashboard")
      return
    }
    // Handle OAuth callback
    const code = new URLSearchParams(window.location.search).get("code")
    if (code) {
      authApi.githubLogin(code).then((data) => {
        setAuth(data.user, data.access_token)
        router.push("/dashboard")
      })
    }
  }, [isAuthenticated, router, setAuth])

  const handleLogin = () => {
    const params = new URLSearchParams({
      client_id: process.env.NEXT_PUBLIC_GITHUB_CLIENT_ID!,
      redirect_uri: `${window.location.origin}/`,
      scope: "repo read:user user:email",
    })
    window.location.href = `https://github.com/login/oauth/authorize?${params}`
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Zap className="w-4 h-4 text-primary-foreground" />
          </div>
          <span className="font-semibold text-lg">PRIntel</span>
        </div>
        <button
          onClick={handleLogin}
          className="flex items-center gap-2 bg-primary text-primary-foreground px-4 py-2 rounded-lg text-sm font-medium hover:bg-primary/90 transition-colors"
        >
          <Github className="w-4 h-4" />
          Sign in with GitHub
        </button>
      </header>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-24 text-center">
        <div className="max-w-3xl space-y-6">
          <div className="inline-flex items-center gap-2 bg-secondary text-secondary-foreground px-3 py-1 rounded-full text-sm">
            <Zap className="w-3 h-3" />
            Powered by Groq AI
          </div>
          <h1 className="text-5xl font-bold tracking-tight">
            Senior-engineer code reviews,{" "}
            <span className="text-primary">on every PR</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Connect your GitHub repo. Get instant, deep AI reviews that catch bugs,
            security issues, and logic errors — with codebase-aware context.
          </p>
          <button
            onClick={handleLogin}
            className="inline-flex items-center gap-2 bg-primary text-primary-foreground px-8 py-4 rounded-xl text-lg font-medium hover:bg-primary/90 transition-colors"
          >
            <Github className="w-5 h-5" />
            Get started with GitHub
          </button>
        </div>

        {/* Features */}
        <div className="mt-24 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-5xl w-full">
          {[
            {
              icon: <Zap className="w-5 h-5" />,
              title: "Instant reviews",
              desc: "PRs reviewed automatically via GitHub webhooks. No manual triggers.",
            },
            {
              icon: <Shield className="w-5 h-5" />,
              title: "Security aware",
              desc: "Catches SQL injection, XSS, auth flaws, and more before they merge.",
            },
            {
              icon: <TrendingUp className="w-5 h-5" />,
              title: "Quality trends",
              desc: "Track your team's code quality over time with per-developer insights.",
            },
            {
              icon: <MessageSquare className="w-5 h-5" />,
              title: "PR chat",
              desc: "Ask follow-up questions about any PR. AI remembers your codebase.",
            },
          ].map((f) => (
            <div key={f.title} className="p-6 border rounded-xl text-left space-y-3 bg-card">
              <div className="w-10 h-10 bg-primary/10 rounded-lg flex items-center justify-center text-primary">
                {f.icon}
              </div>
              <h3 className="font-semibold">{f.title}</h3>
              <p className="text-sm text-muted-foreground">{f.desc}</p>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}
