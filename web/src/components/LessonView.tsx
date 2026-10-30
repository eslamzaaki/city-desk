import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Transcript } from "@/components/Transcript"
import type { Lesson, RunResult, Section } from "@/lib/types"

export function LessonView({
  lesson,
  result,
  loading,
  error,
  prompt,
  onPrompt,
  onRun,
  onOpen,
}: {
  lesson: Lesson
  result: RunResult | null
  loading: boolean
  error: string | null
  prompt: string
  onPrompt: (value: string) => void
  onRun: () => void
  onOpen: (id: string) => void
}) {
  if (lesson.kind === "reading") {
    return (
      <article className="rise mx-auto max-w-3xl">
        <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-stamp">{lesson.kicker}</p>
        <h2 className="mt-2 font-display text-4xl leading-tight text-ink sm:text-5xl">Learn LangChain by working a shift.</h2>
        <div className="mt-6 space-y-4 text-[17px] leading-7 text-ink/90">
          {lesson.paragraphs.map((paragraph) => (
            <p key={paragraph.slice(0, 32)}>{paragraph}</p>
          ))}
        </div>
        <h3 className="mt-10 font-display text-2xl">What the shift forces you to use</h3>
        <ul className="mt-4 divide-y divide-rule border-y border-rule">
          {lesson.features.map((feature) => (
            <li key={feature.station}>
              <button
                type="button"
                onClick={() => onOpen(feature.station)}
                className="flex w-full items-baseline justify-between gap-4 py-3 text-left hover:bg-paper-deep/60"
              >
                <span>{feature.name}</span>
                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">Open</span>
              </button>
            </li>
          ))}
        </ul>
      </article>
    )
  }

  return (
    <article className="rise mx-auto max-w-3xl">
      <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-stamp">
        Station {lesson.number} · {lesson.kicker}
      </p>
      <h2 className="mt-2 font-display text-4xl leading-tight">{lesson.title}</h2>
      <p className="mt-4 text-[17px] leading-7 text-ink/90">{lesson.summary}</p>
      {lesson.look_for.length > 0 ? (
        <ul className="mt-6 space-y-2">
          {lesson.look_for.map((item) => (
            <li key={item} className="flex gap-3 text-sm leading-relaxed text-muted">
              <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-stamp" />
              <span>{item}</span>
            </li>
          ))}
        </ul>
      ) : null}

      {lesson.accepts_prompt ? (
        <div className="mt-8 space-y-3">
          <label className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted" htmlFor="prompt">
            The reporter’s line
          </label>
          <Textarea
            id="prompt"
            value={prompt}
            onChange={(event) => onPrompt(event.target.value)}
            rows={3}
          />
          <Button onClick={onRun} disabled={loading || !prompt.trim()} variant="stamp">
            {loading ? "Running the station…" : result ? "Run it again" : "Run the station"}
          </Button>
        </div>
      ) : (
        <div className="mt-8">
          <Button onClick={onRun} disabled={loading} variant="stamp">
            {loading ? "Running the station…" : result ? "Run it again" : "Run the station"}
          </Button>
        </div>
      )}

      {error ? (
        <p className="mt-4 rounded-sm border border-stamp/40 bg-stamp/10 px-3 py-2 text-sm text-stamp" role="alert">
          {error}
        </p>
      ) : null}

      {loading && !result ? <LoadingRules /> : null}

      {result ? (
        <div className="mt-10">
          <p className="font-display text-2xl leading-snug text-ink">{result.headline}</p>
          <div className="mt-6 space-y-8">
            {result.sections.map((section) => (
              <SectionBlock key={section.label} section={section} />
            ))}
          </div>
        </div>
      ) : null}
    </article>
  )
}

function SectionBlock({ section }: { section: Section }) {
  return (
    <section className="border-t border-rule pt-5">
      <h3 className="font-mono text-[11px] uppercase tracking-[0.16em] text-grove">{section.label}</h3>
      <p className="mt-2 text-sm leading-relaxed text-muted">{section.body}</p>
      {section.tokens ? (
        <p className="mt-3 flex flex-wrap gap-1">
          {section.tokens.map((token, index) => (
            <span key={`${token}-${index}`} className="rounded-sm bg-paper-deep px-1.5 py-0.5 font-mono text-xs">
              {token || "␣"}
            </span>
          ))}
        </p>
      ) : null}
      {section.card ? <BriefCard card={section.card} /> : null}
      {section.todos ? (
        <ul className="mt-3 space-y-1">
          {section.todos.map((todo) => (
            <li key={todo.content} className="flex items-center gap-2 text-sm">
              <Badge variant={todo.status === "completed" ? "grove" : "amber"}>{todo.status}</Badge>
              {todo.content}
            </li>
          ))}
        </ul>
      ) : null}
      {section.table ? (
        <div className="mt-3 overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                {section.table.columns.map((column) => (
                  <th key={column} className="py-2 pr-3 font-medium">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {section.table.rows.map((row) => (
                <tr key={row.join("|")} className="border-b border-rule/80">
                  {row.map((cell, index) => (
                    <td key={`${cell}-${index}`} className="py-2 pr-3">
                      {cell === "pass" || cell === "fail" ? (
                        <Badge variant={cell === "pass" ? "grove" : "stamp"}>{cell}</Badge>
                      ) : (
                        cell
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {section.stream ? (
        <ol className="mt-3 space-y-2">
          {section.stream.map((step, index) => (
            <li key={`${step.node}-${index}`} className="grid grid-cols-[5.5rem_1fr] gap-3 text-sm">
              <Badge variant="grove">{step.node}</Badge>
              <span className="whitespace-pre-wrap leading-relaxed">{step.summary}</span>
            </li>
          ))}
        </ol>
      ) : null}
      {section.routes ? (
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          {section.routes.map((route) => (
            <div key={route.input} className="rounded-sm border border-rule bg-paper-deep/50 p-3">
              <Badge variant={route.route === "research" ? "grove" : "default"}>{route.route}</Badge>
              <p className="mt-2 text-sm font-medium">{route.input}</p>
              <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-muted">{route.reply}</p>
            </div>
          ))}
        </div>
      ) : null}
      {section.hits ? (
        <ul className="mt-3 space-y-2">
          {section.hits.map((hit) => (
            <li key={hit.title + hit.text.slice(0, 24)} className="border-l-2 border-grove pl-3 text-sm">
              <span className="font-medium">{hit.title}</span>
              <span className="ml-2 font-mono text-[11px] text-muted">{hit.score.toFixed(2)}</span>
              <p className="mt-1 leading-relaxed text-muted">{hit.text}</p>
            </li>
          ))}
        </ul>
      ) : null}
      {section.interrupt ? (
        <div className="mt-3 rounded-sm border border-stamp/40 bg-stamp/5 p-3 text-sm">
          <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">Paused</p>
          {section.interrupt.value.action_requests.map((action) => (
            <p key={action.name} className="mt-2">
              <span className="font-medium">{action.name}</span>
              <span className="mt-1 block font-mono text-xs text-muted">{JSON.stringify(action.args)}</span>
            </p>
          ))}
        </div>
      ) : null}
      {section.diagram ? (
        <details className="mt-3">
          <summary className="cursor-pointer font-mono text-[11px] uppercase tracking-[0.14em] text-muted">
            Mermaid
          </summary>
          <pre className="mt-2 overflow-x-auto font-mono text-[11px] leading-5 text-muted">{section.diagram}</pre>
        </details>
      ) : null}
      {section.schema ? (
        <pre className="mt-3 overflow-x-auto rounded-sm bg-ink px-3 py-2 font-mono text-[11px] leading-5 text-paper">
          {JSON.stringify(section.schema, null, 2)}
        </pre>
      ) : null}
      <Transcript messages={section.messages} />
    </section>
  )
}

function BriefCard({ card }: { card: Record<string, unknown> }) {
  const confidence = typeof card.confidence === "number" ? card.confidence : 0
  const sources = Array.isArray(card.sources) ? card.sources.map(String) : []
  return (
    <div className="mt-3 rounded-sm border border-ink bg-paper-deep/40 p-4">
      <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-stamp">Brief card</p>
      <h4 className="mt-1 font-display text-2xl leading-snug">{String(card.headline ?? "")}</h4>
      <p className="mt-2 text-sm leading-relaxed">{String(card.summary ?? "")}</p>
      <div className="mt-3 h-1.5 w-full bg-rule">
        <div className="h-full bg-grove" style={{ width: `${Math.round(confidence * 100)}%` }} />
      </div>
      <p className="mt-1 font-mono text-[11px] text-muted">confidence {confidence.toFixed(2)}</p>
      <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.12em] text-muted">{sources.join(" · ")}</p>
    </div>
  )
}

function LoadingRules() {
  return (
    <div className="mt-8 space-y-2" aria-hidden>
      <div className="h-3 w-2/3 animate-pulse bg-rule" />
      <div className="h-3 w-1/2 animate-pulse bg-rule" />
      <div className="h-3 w-3/5 animate-pulse bg-rule" />
    </div>
  )
}
