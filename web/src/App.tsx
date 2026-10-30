import { DeskView } from "@/components/DeskView"

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <header className="shrink-0 border-b border-ink px-4 py-4 sm:px-6">
        <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-stamp">Lumen</p>
        <h1 className="font-display text-3xl leading-none tracking-tight sm:text-4xl">The Counter</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-muted">
          Send a prompt as a customer. Feedback is another turn in the same chat: the agent asks for the rating and files it. The page shows the steps and what that turn did to memory.
        </p>
      </header>
      <main className="flex-1 px-4 py-6 sm:px-6">
        <DeskView />
      </main>
      <footer className="shrink-0 border-t border-ink px-4 py-6 sm:px-6">
        <div className="mx-auto grid max-w-6xl gap-6 sm:grid-cols-2">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-stamp">
              Monthly review
            </p>
            <h2 className="mt-1 font-display text-xl">Suggestions for one agent</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              Suggest changes, or{" "}
              <code className="font-mono text-xs text-ink">python -m citydesk.suggest</code>
              , reads one agent: its standing prompt, its tools, and consented feedback not yet reviewed. Exact duplicate sentences are grouped first. Each group becomes one suggestion: add a handbook note, adjust the prompt, add a tool, or leave it on that customer. A person applies the change. The next run only sees new consent.
            </p>
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.22em] text-stamp">
              Any agent in the project
            </p>
            <h2 className="mt-1 font-display text-xl">Same pass, different agent</h2>
            <p className="mt-2 text-sm leading-relaxed text-muted">
              The review is{" "}
              <code className="font-mono text-xs text-ink">citydesk.suggest</code>
              . This page runs it for the Lumen counter. Another agent uses the same function when the run is given that agent&apos;s prompt, that agent&apos;s tools, and that agent&apos;s own unused consented feedback.
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}
