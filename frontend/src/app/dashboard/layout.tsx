"use client"
import { useEffect } from "react"
import { useRouter, usePathname } from "next/navigation"
import Link from "next/link"
import {
  LayoutDashboard, GitPullRequest, BarChart2,
  Settings, Zap, LogOut, Database, Menu
} from "lucide-react"
import { useAuthStore, useAppStore } from "@/store"
import Image from "next/image"

const nav = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/dashboard/pulls", icon: GitPullRequest, label: "Pull Requests" },
  { href: "/dashboard/analytics", icon: BarChart2, label: "Analytics" },
  { href: "/dashboard/repos", icon: Database, label: "Repositories" },
  { href: "/dashboard/settings", icon: Settings, label: "Settings" },
]

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const { isAuthenticated, user, clearAuth } = useAuthStore()
  const { sidebarOpen, setSidebarOpen } = useAppStore()

  useEffect(() => {
    if (!isAuthenticated) router.push("/")
  }, [isAuthenticated, router])

  if (!isAuthenticated) return null

  return (
    <div className="min-h-screen flex bg-background">
      {/* Sidebar */}
      <aside className={`
        ${sidebarOpen ? "w-56" : "w-14"} 
        transition-all duration-200 border-r flex flex-col bg-card
        shrink-0
      `}>
        {/* Logo */}
        <div className="h-14 border-b flex items-center px-3 gap-3">
          <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center shrink-0">
            <Zap className="w-4 h-4 text-primary-foreground" />
          </div>
          {sidebarOpen && <span className="font-semibold text-sm">PRIntel</span>}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 space-y-1 px-2">
          {nav.map(({ href, icon: Icon, label }) => {
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={`
                  flex items-center gap-3 px-2 py-2 rounded-lg text-sm transition-colors
                  ${active
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  }
                `}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {sidebarOpen && <span>{label}</span>}
              </Link>
            )
          })}
        </nav>

        {/* User */}
        <div className="border-t p-2 space-y-1">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-muted-foreground hover:bg-secondary hover:text-foreground transition-colors"
          >
            <Menu className="w-4 h-4 shrink-0" />
            {sidebarOpen && <span>Collapse</span>}
          </button>
          {user && (
            <div className="flex items-center gap-2 px-2 py-2">
              {user.avatar_url && (
                <Image
                  src={user.avatar_url}
                  alt={user.username}
                  width={28}
                  height={28}
                  className="rounded-full shrink-0"
                />
              )}
              {sidebarOpen && (
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate">{user.username}</p>
                </div>
              )}
            </div>
          )}
          <button
            onClick={() => { clearAuth(); router.push("/") }}
            className="w-full flex items-center gap-3 px-2 py-2 rounded-lg text-sm text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-colors"
          >
            <LogOut className="w-4 h-4 shrink-0" />
            {sidebarOpen && <span>Sign out</span>}
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">
        {children}
      </main>
    </div>
  )
}
