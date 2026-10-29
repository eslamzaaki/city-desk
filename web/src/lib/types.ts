export type Feature = { name: string; station: string }

export type Lesson = {
  id: string
  number: string
  title: string
  kicker: string
  summary: string
  look_for: string[]
  default_prompt: string
  accepts_prompt: boolean
  kind: "reading" | "lesson" | "desk"
  source: string
  paragraphs: string[]
  features: Feature[]
}

export type TraceEvent = { hook: string; detail: string }

export type ToolCall = {
  name: string
  args: Record<string, unknown>
  id?: string
}

export type ContentBlock = { type?: string; text?: string }

export type Message = {
  type: string
  content: string | ContentBlock[]
  tool_calls?: ToolCall[]
  content_blocks?: ContentBlock[]
  tool_call_id?: string
  status?: string
  name?: string
}

export type ActionRequest = {
  name: string
  args: Record<string, unknown>
  description?: string
}

export type Interrupt = {
  id: string
  value: {
    action_requests: ActionRequest[]
    review_configs?: { action_name: string; allowed_decisions: string[] }[]
  }
}

export type Section = {
  label: string
  body: string
  messages: Message[]
  trace: TraceEvent[]
  card?: Record<string, unknown>
  todos?: { content: string; status: string }[]
  interrupt?: Interrupt
  tokens?: string[]
  stream?: { node: string; summary: string }[]
  routes?: { input: string; route: string; reply: string }[]
  diagram?: string
  hits?: { title: string; text: string; score: number }[]
  table?: { columns: string[]; rows: string[][] }
  schema?: unknown
}

export type RunResult = {
  headline: string
  sections: Section[]
}

export type DeskState = {
  thread_id: string
  model: string
  messages: Message[]
  interrupt: Interrupt | null
  trace: TraceEvent[]
  memories: string[]
  spike: { id: string; headline: string; summary: string }[]
  reporter: string
  desk: string
  threads: { id: string; title: string; reporter: string; desk: string }[]
}

export function messageText(message: Message): string {
  if (typeof message.content === "string") return message.content
  return message.content.map((block) => block.text || "").join("")
}
