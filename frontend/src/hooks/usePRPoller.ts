import { useEffect, useRef, useState } from "react"
import { prsApi } from "@/lib/api"
import type { PullRequest, Review } from "@/types"

/**
 * Polls a PR's status every `intervalMs` ms until it reaches
 * "completed" or "failed", then stops.
 */
export function usePRPoller(
  prId: number,
  initialStatus: string,
  onComplete: (review: Review) => void,
  intervalMs = 4000
) {
  const [status, setStatus] = useState(initialStatus)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    if (status === "completed" || status === "failed") return

    timerRef.current = setInterval(async () => {
      try {
        const pr = await prsApi.get(prId)
        setStatus(pr.status)
        if (pr.status === "completed") {
          const review = await prsApi.getReview(prId)
          onComplete(review)
          clearInterval(timerRef.current!)
        } else if (pr.status === "failed") {
          clearInterval(timerRef.current!)
        }
      } catch {
        clearInterval(timerRef.current!)
      }
    }, intervalMs)

    return () => { if (timerRef.current) clearInterval(timerRef.current) }
  }, [prId, status, onComplete, intervalMs])

  return status
}

/**
 * Hook to auto-refresh the PR list when any PR is in "reviewing" state.
 */
export function useAutoRefreshList(
  prs: PullRequest[],
  onRefresh: () => void,
  intervalMs = 6000
) {
  const hasActive = prs.some(pr => pr.status === "reviewing" || pr.status === "pending")

  useEffect(() => {
    if (!hasActive) return
    const timer = setInterval(onRefresh, intervalMs)
    return () => clearInterval(timer)
  }, [hasActive, onRefresh, intervalMs])
}
