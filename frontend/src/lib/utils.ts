import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatScore(score: number | null | undefined): string {
  if (score == null) return "—"
  return score.toFixed(1)
}

export function scoreColor(score: number): string {
  if (score >= 7) return "text-green-600"
  if (score >= 5) return "text-yellow-600"
  return "text-red-600"
}

export function scoreBg(score: number): string {
  if (score >= 7) return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
  if (score >= 5) return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400"
  return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400"
}

export function truncate(str: string, maxLen: number): string {
  return str.length > maxLen ? str.slice(0, maxLen) + "…" : str
}

export function downloadPDF(prId: number) {
  const token = localStorage.getItem("access_token")
  const url = `${process.env.NEXT_PUBLIC_API_URL}/api/prs/${prId}/export/pdf`
  const a = document.createElement("a")
  a.href = url
  a.setAttribute("download", `review-pr-${prId}.pdf`)
  // Pass auth via query param for download links
  fetch(url, { headers: { Authorization: `Bearer ${token}` } })
    .then(res => res.blob())
    .then(blob => {
      const objUrl = URL.createObjectURL(blob)
      a.href = objUrl
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(objUrl)
    })
}
