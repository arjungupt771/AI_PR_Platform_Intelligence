import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { User, Repository } from "@/types"

interface AuthStore {
  user: User | null
  token: string | null
  setAuth: (user: User, token: string) => void
  clearAuth: () => void
  isAuthenticated: boolean
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setAuth: (user, token) => {
        localStorage.setItem("access_token", token)
        set({ user, token, isAuthenticated: true })
      },
      clearAuth: () => {
        localStorage.removeItem("access_token")
        set({ user: null, token: null, isAuthenticated: false })
      },
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ user: state.user, token: state.token }),
    }
  )
)

interface AppStore {
  selectedRepoId: number | null
  setSelectedRepo: (id: number | null) => void
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
}

export const useAppStore = create<AppStore>((set) => ({
  selectedRepoId: null,
  setSelectedRepo: (id) => set({ selectedRepoId: id }),
  sidebarOpen: true,
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
}))
