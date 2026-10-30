import { useEffect, useState } from "react"

import { fetchState, resumeTurn, sendTurn } from "@/lib/api"
import type { DeskState, Lesson } from "@/lib/types"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Transcript } from "@/components/Transcript"

const starters = [
  "When does harbor dredging start?",
  "Where did the corniche flood?",
  "What is the new tram stop called?",
  "Remember that my beat is the night market.",
  "What is my beat?",
  "Who is on duty?",
  "File a brief on the corniche flood.",
  "Email the desk at nour@marsa.test — press card PC-4412 — about the heat.",
  "hello",
]

function freshId() {
  return `shift-${crypto.randomUUID().slice(0, 8)}`
}

export function DeskView({ lesson, onTrace }: { lesson: Lesson; onTrace: (state: DeskState | null) => void }) {
  const [threadId, setThreadId] = useState(freshId)
  const [reporter, setReporter] = useState("Nour El-Sayed")
  const [desk, setDesk] = useState("harbor")
  const [draft, setDraft] = useState("")
  const [headline, setHeadline] = useState("")
  const [hold, setHold] = useState("Hold it. The kilometre markers are not confirmed.")
  const [state, setState] = useState<DeskState | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    onTrace(state)
  }, [state, onTrace])

  useEffect(() => {
    const pending = state?.interrupt?.value.action_requests[0]?.args.headline
    if (typeof pending === "string") setHeadline(pending)
  }, [state?.interrupt?.id])

  async function run(message: string) {
    const text = message.trim()
    if (!text || busy) return
    setBusy(true)
    setError(null)
    try {
      const next = await sendTurn({ thread_id: threadId, message: text, reporter, desk })
      setState(next)
      setDraft("")
    } catch (err) {
      setError(err instanceof Error ? err.message : "The desk missed the call.")
    } finally {
      setBusy(false)
    }
  }

  async function decide(decisions: Record<string, unknown>[]) {
    if (busy) return
    setBusy(true)
    setError(null)
    try {
      const next = await resumeTurn({ thread_id: threadId, reporter, desk, decisions })
      setState(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : "The resume failed.")
    } finally {
      setBusy(false)
    }
  }

  function openShift() {
    const id = freshId()
    setThreadId(id)
    setState((current) =>
      current
        ? { ...current, thread_id: id, messages: [], interrupt: null, trace: [] }
        : current,
    )
    setDraft("")
    setError(null)
  }

  async function reopen(id: string) {
    setBusy(true)
    setError(null)
    try {
      const next = await fetchState(id, reporter, desk)
      setThreadId(id)
      setState(next)
    } catch (err) {
      setError(err instanceof Error ? err.message : "That shift would not open.")
    } finally {
      setBusy(false)
    }
  }

  const action = state?.interrupt?.value.action_requests[0]
  const memories = state?.reporter === reporter ? state.memories : []

  return (
    <article className="rise mx-auto max-w-3xl">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-stamp">
        Station {lesson.number} · {lesson.kicker}
      </p>
      <h2 className="mt-2 font-display text-4xl leading-tight">{lesson.title}</h2>
      <p className="mt-4 text-[17px] leading-7">{lesson.summary}</p>

      <div className="mt-6 grid gap-3 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">Reporter</span>
          <Input className="mt-1" value={reporter} onChange={(event) => setReporter(event.target.value)} />
        </label>
        <label className="block text-sm">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">Desk</span>
          <Input className="mt-1" value={desk} onChange={(event) => setDesk(event.target.value)} />
        </label>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge variant="default">{threadId}</Badge>
        <Button type="button" variant="outline" size="sm" onClick={openShift}>
          New shift
        </Button>
        {state?.model ? <span className="font-mono text-[11px] text-muted">{state.model}</span> : null}
      </div>
      {state && state.threads.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {state.threads.map((thread) => (
            <button
              key={thread.id}
              type="button"
              onClick={() => reopen(thread.id)}
              className="rounded-sm border border-rule px-2 py-1 text-left text-xs hover:bg-paper-deep"
            >
              <span className="block font-mono text-[10px] uppercase tracking-[0.12em] text-stamp">{thread.id}</span>
              {thread.title}
            </button>
          ))}
        </div>
      ) : null}

      <Tabs defaultValue="shift" className="mt-6">
        <TabsList>
          <TabsTrigger value="shift">Shift</TabsTrigger>
          <TabsTrigger value="file">On file</TabsTrigger>
          <TabsTrigger value="spike">Spike</TabsTrigger>
        </TabsList>
        <TabsContent value="shift">
          {state && state.messages.length > 0 ? (
            <Transcript messages={state.messages.filter((message) => message.type !== "system")} />
          ) : (
            <div className="rounded-sm border border-dashed border-rule px-4 py-8">
              <p className="font-display text-2xl">The spike is clear.</p>
              <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
                Ask about Marsa, tell the desk your beat, then open a new shift and ask what it remembers.
                Filing a brief stops until you approve it.
              </p>
            </div>
          )}

          {action ? (
            <div className="mt-5 rounded-sm border border-stamp bg-stamp/5 p-4">
              <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-stamp">
                Waiting on the editor · {action.name}
              </p>
              <p className="mt-2 text-sm leading-relaxed text-muted">{String(action.args.summary ?? "")}</p>
              <label className="mt-3 block text-sm" htmlFor="headline">
                Headline on the spike
                <Input
                  id="headline"
                  className="mt-1"
                  value={headline}
                  onChange={(event) => setHeadline(event.target.value)}
                />
              </label>
              <label className="mt-3 block text-sm" htmlFor="hold">
                If you reject it
                <Input id="hold" className="mt-1" value={hold} onChange={(event) => setHold(event.target.value)} />
              </label>
              <div className="mt-3 flex flex-wrap gap-2">
                <Button variant="grove" disabled={busy} onClick={() => decide([{ type: "approve" }])}>
                  Approve
                </Button>
                <Button
                  variant="stamp"
                  disabled={busy || !headline.trim()}
                  onClick={() =>
                    decide([
                      {
                        type: "edit",
                        edited_action: {
                          name: "file_brief",
                          args: { ...action.args, headline },
                        },
                      },
                    ])
                  }
                >
                  File this headline
                </Button>
                <Button variant="outline" disabled={busy} onClick={() => decide([{ type: "reject", message: hold }])}>
                  Reject
                </Button>
              </div>
            </div>
          ) : null}

          <div className="mt-5 flex flex-wrap gap-2">
            {starters.map((starter) => (
              <button
                key={starter}
                type="button"
                disabled={busy || Boolean(action)}
                onClick={() => run(starter)}
                className="rounded-full border border-rule px-3 py-1 text-left text-xs leading-5 hover:border-ink disabled:opacity-40"
              >
                {starter}
              </button>
            ))}
          </div>

          <form
            className="mt-4 space-y-3"
            onSubmit={(event) => {
              event.preventDefault()
              void run(draft)
            }}
          >
            <Textarea
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              placeholder="Ask the harbor desk…"
              aria-label="Message the desk"
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault()
                  void run(draft)
                }
              }}
            />
            <div className="flex items-center justify-between gap-3">
              <p className="text-xs text-muted">Search runs immediately. Filing waits for you.</p>
              <Button type="submit" disabled={busy || !draft.trim() || Boolean(action)}>
                {busy ? "Sending…" : "Send"}
              </Button>
            </div>
          </form>
          {error ? (
            <p className="mt-3 rounded-sm border border-stamp/40 bg-stamp/10 px-3 py-2 text-sm text-stamp" role="alert">
              {error}
            </p>
          ) : null}
        </TabsContent>
        <TabsContent value="file">
          {memories.length === 0 ? (
            <p className="text-sm leading-relaxed text-muted">
              Nothing is stored for {reporter}. Preferences live in the long-term store, under the reporter’s name,
              and they survive a new shift.
            </p>
          ) : (
            <ul className="space-y-2">
              {memories.map((note) => (
                <li key={note} className="border-l-2 border-grove pl-3 text-sm leading-relaxed">
                  {note}
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
        <TabsContent value="spike">
          {!state || state.spike.length === 0 ? (
            <p className="text-sm text-muted">No brief has been approved onto the spike.</p>
          ) : (
            <ul className="space-y-3">
              {state.spike.map((entry) => (
                <li key={entry.id} className="border-t border-rule pt-3">
                  <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">{entry.id}</p>
                  <p className="font-display text-xl">{entry.headline}</p>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{entry.summary}</p>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
      </Tabs>
    </article>
  )
}
