import type { DeskState, Lesson, RunResult } from "@/lib/types"

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

export async function fetchLessons(): Promise<Lesson[]> {
  const data = await read<{ lessons: Lesson[] }>(await fetch("/api/lessons"))
  return data.lessons
}

export async function runLesson(id: string, prompt: string): Promise<RunResult> {
  const data = await read<{ result: RunResult }>(
    await fetch(`/api/lessons/${id}/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    }),
  )
  return data.result
}

export async function fetchSource(id: string): Promise<{ path: string; code: string }> {
  return read(await fetch(`/api/lessons/${id}/source`))
}

export type TurnBody = {
  thread_id: string
  message: string
  reporter: string
  desk: string
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
  reporter: string
  desk: string
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

export async function fetchState(threadId: string, reporter: string, desk: string): Promise<DeskState> {
  const params = new URLSearchParams({ thread_id: threadId, reporter, desk })
  return read(await fetch(`/api/desk/state?${params.toString()}`))
}
