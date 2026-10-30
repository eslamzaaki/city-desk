import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import type { TraceEvent } from "@/lib/types"

export function WirePanel({
  trace,
  sourcePath,
  source,
  loadingSource,
  compact = false,
}: {
  trace: TraceEvent[]
  sourcePath: string
  source: string
  loadingSource: boolean
  compact?: boolean
}) {
  return (
    <Tabs defaultValue="wire" className="h-full min-h-0">
      <TabsList className="border-paper/20">
        <TabsTrigger value="wire" className="text-paper/60 data-[state=active]:border-amber data-[state=active]:text-amber">
          The wire
        </TabsTrigger>
        <TabsTrigger value="source" className="text-paper/60 data-[state=active]:border-amber data-[state=active]:text-amber">
          Source
        </TabsTrigger>
      </TabsList>
      <TabsContent value="wire" className="min-h-0 flex-1">
        <ScrollArea className={compact ? "h-72 pr-3" : "h-[calc(100vh-9.5rem)] pr-3"}>
          {trace.length === 0 ? (
            <p className="text-sm leading-relaxed text-muted">
              Run a station. Middleware hooks, tool calls, and graph edges land here in the order they fired.
            </p>
          ) : (
            <ol className="space-y-3">
              {trace.map((event, index) => (
                <li key={`${event.hook}-${index}`} className="border-l-2 border-amber/70 pl-3">
                  <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-amber">{event.hook}</p>
                  <p className="mt-1 whitespace-pre-wrap font-mono text-xs leading-relaxed text-paper/90">
                    {event.detail}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </ScrollArea>
      </TabsContent>
      <TabsContent value="source" className="min-h-0 flex-1">
        <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.14em] text-amber">{sourcePath}</p>
        <ScrollArea className={compact ? "h-72" : "h-[calc(100vh-11rem)]"}>
          {loadingSource ? (
            <p className="font-mono text-xs text-paper/70">Pulling the station…</p>
          ) : (
            <pre className="font-mono text-[11px] leading-5 text-paper/90">
              {source.split("\n").map((line, index) => (
                <div key={index} className="flex">
                  <span className="w-8 shrink-0 select-none text-paper/35">{index + 1}</span>
                  <span className="whitespace-pre">{line || " "}</span>
                </div>
              ))}
            </pre>
          )}
        </ScrollArea>
      </TabsContent>
    </Tabs>
  )
}
