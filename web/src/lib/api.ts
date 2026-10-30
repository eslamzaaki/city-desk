import type { DeskState } from "@/lib/types"

async function read<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = response.statusText
    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* the body was not JSON */
    }
    throw new Error(detail)
  }
  return response.json() as Promise<T>
}

export type TurnBody = {
  thread_id: string
  message: string
  customer_id: string
}

export async function sendTurn(body: TurnBody): Promise<DeskState> {
  return read(
    await fetch("/api/desk/turn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  )
}

export async function resumeTurn(body: {
  thread_id: string
  customer_id: string
  decisions: Record<string, unknown>[]
}): Promise<DeskState> {
  return read(
    await fetch("/api/desk/resume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  )
}

export async function fetchState(threadId: string, customerId: string): Promise<DeskState> {
  const params = new URLSearchParams({ thread_id: threadId, customer_id: customerId })
  return read(await fetch(`/api/desk/state?${params.toString()}`))
}

export async function sendFeedback(body: {
  thread_id: string
  customer_id: string
  response_id: string
  scope: "personal" | "shared"
  rating: number
  reason: string
  corrected_answer: string
  consent_for_training: boolean
}): Promise<DeskState> {
  return read(
    await fetch("/api/desk/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }),
  )
}

export type Suggestion = {
  where: "handbook" | "prompt" | "tool" | "ignore"
  what: string
  why: string
  count: number
  feedback_ids: string[]
}

export async function reviewFeedback(): Promise<{ reviewed: number; suggestions: Suggestion[] }> {
  return read(await fetch("/api/desk/suggestions", { method: "POST" }))
}

export async function approveCandidate(id: string): Promise<{ candidates: DeskState["candidates"] }> {
  return read(await fetch(`/api/desk/candidates/${id}/approve`, { method: "POST" }))
}
