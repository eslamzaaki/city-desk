import { Badge } from "@/components/ui/badge"
import { messageText, type Message } from "@/lib/types"

const labels: Record<string, string> = {
  system: "System",
  human: "Reporter",
  ai: "Desk",
  tool: "Archive",
}

export function Transcript({ messages }: { messages: Message[] }) {
  if (messages.length === 0) return null
  return (
    <ol className="mt-4 space-y-4">
      {messages.map((message, index) => {
        const calls = message.tool_calls ?? []
        const text = messageText(message)
        const redacted = text.includes("REDACTED") || text.includes("_hash:")
        return (
          <li key={`${message.type}-${index}`} className="rise">
            <div className="mb-1 flex flex-wrap items-center gap-2">
              <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-stamp">
                {message.type === "tool" ? message.name || labels.tool : labels[message.type] || message.type}
              </span>
              {message.status === "error" ? <Badge variant="stamp">error</Badge> : null}
              {redacted ? <Badge variant="amber">rewritten</Badge> : null}
              {calls.map((call) => (
                <Badge key={call.id || call.name} variant="grove">
                  {call.name}
                </Badge>
              ))}
            </div>
            {calls.length > 0 ? (
              <pre className="overflow-x-auto rounded-sm bg-grove-soft px-3 py-2 font-mono text-xs leading-relaxed text-grove">
                {calls.map((call) => `${call.name}(${JSON.stringify(call.args)})`).join("\n")}
              </pre>
            ) : null}
            {text ? (
              <p className="mt-1 whitespace-pre-wrap text-sm leading-relaxed text-ink">{text}</p>
            ) : null}
            {message.content_blocks && message.content_blocks.length > 0 ? (
              <p className="mt-1 font-mono text-[11px] text-muted">
                blocks: {message.content_blocks.map((block) => block.type || "block").join(", ")}
              </p>
            ) : null}
          </li>
        )
      })}
    </ol>
  )
}
