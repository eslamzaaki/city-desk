import { useCallback, useEffect, useMemo, useState } from "react"

import { DeskView } from "@/components/DeskView"
import { LessonView } from "@/components/LessonView"
import { WirePanel } from "@/components/WirePanel"
import { fetchLessons, fetchSource, runLesson } from "@/lib/api"
import type { DeskState, Lesson, RunResult, TraceEvent } from "@/lib/types"
import { cn } from "@/lib/utils"

export default function App() {
  const [lessons, setLessons] = useState<Lesson[]>([])
  const [selectedId, setSelectedId] = useState("assignment")
  const [prompts, setPrompts] = useState<Record<string, string>>({})
  const [results, setResults] = useState<Record<string, RunResult>>({})
  const [loadingId, setLoadingId] = useState<string | null>(null)
  const [error, setError] = useState<{ id: string; message: string } | null>(null)
  const [bootError, setBootError] = useState<string | null>(null)
  const [sources, setSources] = useState<Record<string, string>>({})
  const [loadingSource, setLoadingSource] = useState(false)
  const [deskState, setDeskState] = useState<DeskState | null>(null)
  const rememberDesk = useCallback((next: DeskState | null) => setDeskState(next), [])

  useEffect(() => {
    fetchLessons()
      .then((loaded) => {
        setLessons(loaded)
        setPrompts(Object.fromEntries(loaded.map((lesson) => [lesson.id, lesson.default_prompt])))
      })
      .catch((err: unknown) => {
        setBootError(err instanceof Error ? err.message : "The desk did not open.")
      })
  }, [])

  const selected = lessons.find((lesson) => lesson.id === selectedId) ?? lessons[0]

  useEffect(() => {
    if (!selected) return
    if (sources[selected.id]) return
    let cancelled = false
    setLoadingSource(true)
    fetchSource(selected.id)
      .then((file) => {
        if (!cancelled) setSources((current) => ({ ...current, [selected.id]: file.code }))
      })
      .catch(() => {
        if (!cancelled) setSources((current) => ({ ...current, [selected.id]: "The source file could not be read." }))
      })
      .finally(() => {
        if (!cancelled) setLoadingSource(false)
      })
    return () => {
      cancelled = true
    }
  }, [selected, sources])

  const trace = useMemo<TraceEvent[]>(() => {
    if (!selected) return []
    if (selected.kind === "desk") return deskState?.trace ?? []
    const result = results[selected.id]
    if (!result) return []
    return result.sections.flatMap((section) =>
      section.trace.map((event) => ({
        hook: result.sections.length > 1 ? `${section.label} · ${event.hook}` : event.hook,
        detail: event.detail,
      })),
    )
  }, [selected, results, deskState])

  async function execute(lesson: Lesson) {
    setLoadingId(lesson.id)
    setError(null)
    try {
      const result = await runLesson(lesson.id, prompts[lesson.id] ?? lesson.default_prompt)
      setResults((current) => ({ ...current, [lesson.id]: result }))
    } catch (err) {
      setError({ id: lesson.id, message: err instanceof Error ? err.message : "The station failed." })
    } finally {
      setLoadingId(null)
    }
  }

  return (
    <div className="flex h-screen flex-col">
      <header className="shrink-0 border-b border-ink px-4 py-4 sm:px-6">
        <div className="flex items-end justify-between gap-4">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-stamp">Marsa · LangChain 1.4</p>
            <h1 className="font-display text-3xl leading-none tracking-tight sm:text-4xl">The City Desk</h1>
          </div>
          <p className="hidden max-w-xs text-right text-xs leading-relaxed text-muted sm:block">
            A newsroom you run in order to learn the agent APIs by using them.
          </p>
        </div>
        <div className="mt-3 flex gap-2 overflow-x-auto md:hidden">
          {lessons.map((lesson) => (
            <button
              key={lesson.id}
              type="button"
              onClick={() => setSelectedId(lesson.id)}
              className={cn(
                "shrink-0 rounded-full border px-3 py-1 font-mono text-[10px] uppercase tracking-[0.12em]",
                lesson.id === selected?.id ? "border-stamp bg-stamp text-paper" : "border-rule",
              )}
            >
              {lesson.number} {lesson.title}
            </button>
          ))}
        </div>
      </header>

      <div className="grid min-h-0 flex-1 md:grid-cols-[15.5rem_1fr] lg:grid-cols-[15.5rem_1fr_22rem]">
        <nav className="hidden overflow-y-auto border-r border-rule md:block">
          {lessons.map((lesson) => (
            <button
              key={lesson.id}
              type="button"
              onClick={() => setSelectedId(lesson.id)}
              className={cn(
                "block w-full border-l-2 px-4 py-3 text-left",
                lesson.id === selected?.id ? "border-stamp bg-paper-deep" : "border-transparent hover:bg-paper-deep/50",
              )}
            >
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-stamp">{lesson.number}</span>
              <span className="mt-0.5 block text-sm">{lesson.title}</span>
            </button>
          ))}
        </nav>

        <main className="overflow-y-auto px-4 py-6 sm:px-8">
          {bootError ? (
            <p className="rounded-sm border border-stamp/40 bg-stamp/10 px-3 py-2 text-sm text-stamp" role="alert">
              {bootError}. Start the API, then reload.
            </p>
          ) : null}
          {!selected && !bootError ? <p className="text-sm text-muted">Opening the book…</p> : null}
          {selected && selected.kind === "desk" ? (
            <DeskView lesson={selected} onTrace={rememberDesk} />
          ) : null}
          {selected && selected.kind !== "desk" ? (
            <LessonView
              lesson={selected}
              result={results[selected.id] ?? null}
              loading={loadingId === selected.id}
              error={error?.id === selected.id ? error.message : null}
              prompt={prompts[selected.id] ?? ""}
              onPrompt={(value) => setPrompts((current) => ({ ...current, [selected.id]: value }))}
              onRun={() => execute(selected)}
              onOpen={setSelectedId}
            />
          ) : null}
          {selected ? (
            <div className="mt-10 rounded-sm bg-wire p-4 text-paper lg:hidden">
              <WirePanel
                compact
                trace={trace}
                sourcePath={selected.source}
                source={sources[selected.id] ?? ""}
                loadingSource={loadingSource && !sources[selected.id]}
              />
            </div>
          ) : null}
        </main>

        <aside className="hidden min-h-0 bg-wire p-4 text-paper lg:block">
          {selected ? (
            <WirePanel
              trace={trace}
              sourcePath={selected.source}
              source={sources[selected.id] ?? ""}
              loadingSource={loadingSource && !sources[selected.id]}
            />
          ) : null}
        </aside>
      </div>
    </div>
  )
}
