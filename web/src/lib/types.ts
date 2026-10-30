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

export type Profile = {
  preferences: { language: string; answer_style: string }
  facts: string[]
  corrections: { topic: string; value: string; source_thread?: string }[]
}

export type Refund = { id: string; order_id: string; reason: string; customer_id: string }

export type FeedbackExample = {
  question: string
  judged_reply: string
  feedback_message: string
  problem: string
  preferred_reply: string
}

export type FeedbackRecord = {
  id: string
  thread_id: string
  customer_id: string
  response_id: string
  scope: "personal" | "shared"
  rating: number
  reason: string
  corrected_answer: string
  consent_for_training: boolean
  example?: FeedbackExample
}

export type Candidate = {
  id: string
  customer_id: string
  text: string
  status: string
  consent_for_training: boolean
  source_thread: string
  response_id: string
}

export type DeskState = {
  thread_id: string
  response_id: string
  model: string
  messages: Message[]
  interrupt: Interrupt | null
  trace: TraceEvent[]
  profile: Profile
  refunds: Refund[]
  feedback: FeedbackRecord[]
  candidates: Candidate[]
  handbook: { id: string; title: string }[]
  customer_id: string
  threads: { id: string; title: string; customer_id: string }[]
}

export function messageText(message: Message): string {
  if (typeof message.content === "string") return message.content
  return message.content.map((block) => block.text || "").join("")
}
