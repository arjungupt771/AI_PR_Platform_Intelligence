import axios from "axios"
import type { Repository, PullRequest, Review, ChatMessage, Analytics, LeaderboardResponse, PaginatedResponse } from "@/types"

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  headers: { "Content-Type": "application/json" },
})

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token")
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export const authApi = {
  githubLogin: async (code: string) => { const { data } = await api.post("/api/auth/github", { code }); return data },
  getMe: async () => { const { data } = await api.get("/api/auth/me"); return data },
}

export const reposApi = {
  list: async (): Promise<Repository[]> => { const { data } = await api.get("/api/repos/"); return data },
  listAvailable: async (): Promise<any[]> => { const { data } = await api.get("/api/repos/available"); return data },
  connect: async (repoData: any): Promise<Repository> => { const { data } = await api.post("/api/repos/connect", repoData); return data },
  disconnect: async (repoId: number): Promise<void> => { await api.delete(`/api/repos/${repoId}`) },
  reindex: async (repoId: number): Promise<void> => { await api.post(`/api/repos/${repoId}/reindex`) },
  getMemory: async (repoId: number) => { const { data } = await api.get(`/api/repos/${repoId}/memory`); return data },
  updateMemory: async (repoId: number, memory: { architecture_docs?: string; coding_standards?: string; team_conventions?: string }) => {
    const { data } = await api.put(`/api/repos/${repoId}/memory`, memory); return data
  },
}

export const prsApi = {
  list: async (params?: { repo_id?: number; status?: string; page?: number; page_size?: number }): Promise<PaginatedResponse<PullRequest>> => {
    const { data } = await api.get("/api/prs/", { params }); return data
  },
  get: async (prId: number): Promise<PullRequest> => { const { data } = await api.get(`/api/prs/${prId}`); return data },
  getReview: async (prId: number): Promise<Review> => { const { data } = await api.get(`/api/prs/${prId}/review`); return data },
  getLLMReviews: async (prId: number): Promise<any[]> => { const { data } = await api.get(`/api/prs/${prId}/llm-reviews`); return data },
  getScanResults: async (prId: number): Promise<any[]> => { const { data } = await api.get(`/api/prs/${prId}/scans`); return data },
  rereview: async (prId: number): Promise<void> => { await api.post(`/api/prs/${prId}/rereview`) },
  getChatHistory: async (prId: number): Promise<ChatMessage[]> => { const { data } = await api.get(`/api/prs/${prId}/chat`); return data },
  sendMessage: async (prId: number, content: string): Promise<ChatMessage> => { const { data } = await api.post(`/api/prs/${prId}/chat`, { content }); return data },
}

export const analyticsApi = {
  get: async (params?: { repo_id?: number; days?: number }): Promise<Analytics> => {
    const { data } = await api.get("/api/analytics/", { params }); return data
  },
  getLeaderboard: async (params?: { repo_id?: number; refresh?: boolean }): Promise<LeaderboardResponse> => {
    const { data } = await api.get("/api/analytics/leaderboard", { params }); return data
  },
}

export function downloadPDF(prId: number) {
  const token = localStorage.getItem("access_token")
  fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/prs/${prId}/export/pdf`, {
    headers: { Authorization: `Bearer ${token}` },
  }).then(res => res.blob()).then(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url; a.download = `review-pr-${prId}.pdf`
    document.body.appendChild(a); a.click()
    document.body.removeChild(a); URL.revokeObjectURL(url)
  })
}

export default api
