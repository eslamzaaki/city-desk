import { useState } from "react";

import {
  approveCandidate,
  fetchState,
  resumeTurn,
  reviewFeedback,
  sendTurn,
  type Suggestion,
} from "@/lib/api";
import { messageText, type DeskState, type FeedbackRecord, type Message } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Transcript } from "@/components/Transcript";

type Effect = {
  steps: string;
  tools: string[];
  passes: number;
  personalization: string;
  conversation: string[];
  personal: string[];
  shared: string[];
  feedback: string[];
};

function freshId() {
  return `chat-${crypto.randomUUID().slice(0, 8)}`;
}

function linesOf(items: string[], empty: string) {
  return items.length > 0 ? items : [empty];
}

function agentReply(messages: Message[]) {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (message.type !== "ai") continue;
    const text = messageText(message).trim();
    if (text) return text;
  }
  return "";
}

function profileLines(state: DeskState) {
  const prefs = state.profile.preferences;
  return [
    `Language: ${prefs.language || "none"}`,
    `Answer style: ${prefs.answer_style || "none"}`,
    ...state.profile.facts.map((fact) => `Fact: ${fact}`),
    ...state.profile.corrections.map((item) => `Correction: ${item.value}`),
  ];
}

function describe(before: DeskState | null, after: DeskState): Effect {
  const trace = after.trace ?? [];
  const tools = trace
    .filter((event) => event.hook.startsWith("tool:"))
    .map((event) => event.hook.slice(5));
  const passes = trace.filter((event) => event.hook === "before_model").length;
  const promptLine = [...trace]
    .reverse()
    .find((event) => event.hook === "dynamic_prompt");
  const personalization =
    promptLine?.detail || "No personal memory was injected on this turn.";

  const conversation: string[] = [];
  if (!before || before.thread_id !== after.thread_id) {
    conversation.push("This prompt started or continued a separate chat.");
  }
  const addedMessages = Math.max(
    0,
    after.messages.length -
      (before?.thread_id === after.thread_id ? before.messages.length : 0),
  );
  conversation.push(
    addedMessages === 0
      ? "The transcript did not grow."
      : `The transcript gained ${addedMessages} message${addedMessages === 1 ? "" : "s"}.`,
  );
  if (after.interrupt)
    conversation.push("The loop paused for a refund decision.");

  const beforePersonal = new Set(
    before && before.customer_id === after.customer_id
      ? profileLines(before)
      : [],
  );
  const personal = profileLines(after).filter(
    (line) => !beforePersonal.has(line),
  );
  const personalEffect =
    personal.length > 0
      ? personal.map((line) => `Added ${line}`)
      : ["Personal memory did not change."];

  const afterHandbook = after.handbook ?? [];
  const beforeTitles = new Set((before?.handbook ?? []).map((note) => note.id));
  const shared = before
    ? afterHandbook
        .filter((note) => !beforeTitles.has(note.id))
        .map((note) => `Handbook gained “${note.title}”.`)
    : [];
  const beforeCandidates = new Set(
    (before?.candidates ?? []).map((item) => item.id),
  );
  for (const item of after.candidates) {
    if (!beforeCandidates.has(item.id))
      shared.push(`Candidate waiting: ${item.text}`);
    const previous = before?.candidates.find((row) => row.id === item.id);
    if (previous && previous.status !== item.status)
      shared.push(`Candidate ${item.id} is now ${item.status}.`);
  }
  if (shared.length === 0) shared.push("The shared handbook did not change.");

  const beforeFeedback = new Set(
    (before?.feedback ?? []).map((item) => item.id),
  );
  const feedback = after.feedback
    .filter((item) => !beforeFeedback.has(item.id))
    .map(
      (item) =>
        `${item.scope} feedback, rating ${item.rating}${item.consent_for_training ? ", consent saved" : ""}.`,
    );
  if (feedback.length === 0)
    feedback.push("This prompt did not record feedback.");

  const stepBits = [`${passes} model pass${passes === 1 ? "" : "es"}`];
  if (tools.length > 0)
    stepBits.push(`${tools.length} tool call${tools.length === 1 ? "" : "s"}`);
  if (after.interrupt) stepBits.push("paused for review");

  return {
    steps: stepBits.join(" · "),
    tools,
    passes,
    personalization,
    conversation,
    personal: personalEffect,
    shared,
    feedback,
  };
}

export function DeskView() {
  const [threadId, setThreadId] = useState(freshId);
  const [customerId, setCustomerId] = useState("sara");
  const [prompt, setPrompt] = useState("Can I return my shoes?");
  const [state, setState] = useState<DeskState | null>(null);
  const [effect, setEffect] = useState<Effect | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<Suggestion[] | null>(null);
  const [reason, setReason] = useState("");
  const [hold, setHold] = useState("Hold it. Confirm the receipt first.");

  function apply(before: DeskState | null, next: DeskState) {
    setEffect(describe(before, next));
    setState(next);
  }

  async function send() {
    const text = prompt.trim();
    const customer = customerId.trim();
    if (!text || !customer || busy) return;
    setBusy(true);
    setError(null);
    try {
      const same =
        state && state.customer_id === customer && state.thread_id === threadId;
      const before = same ? state : await fetchState(threadId, customer);
      const next = await sendTurn({
        thread_id: threadId,
        message: text,
        customer_id: customer,
      });
      apply(before, next);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "The counter missed the call.",
      );
    } finally {
      setBusy(false);
    }
  }

  async function decide(decisions: Record<string, unknown>[]) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const next = await resumeTurn({
        thread_id: threadId,
        customer_id: customerId.trim(),
        decisions,
      });
      apply(state, next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The resume failed.");
    } finally {
      setBusy(false);
    }
  }

  async function review() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const report = await reviewFeedback();
      setSuggestions(report.suggestions);
    } catch (err) {
      setError(err instanceof Error ? err.message : "The review did not run.");
    } finally {
      setBusy(false);
    }
  }

  async function acceptCandidate(id: string) {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      await approveCandidate(id);
      const next = await fetchState(threadId, customerId.trim());
      apply(state, next);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "The note was not approved.",
      );
    } finally {
      setBusy(false);
    }
  }

  const action = state?.interrupt?.value.action_requests[0];

  return (
    <div className="mx-auto grid max-w-6xl gap-8 lg:grid-cols-[22rem_1fr]">
      <section>
        <label className="block text-sm" htmlFor="customer">
          Customer id
          <Input
            id="customer"
            className="mt-1"
            value={customerId}
            onChange={(event) => setCustomerId(event.target.value)}
            placeholder="sara"
          />
        </label>
        <p className="mt-1 text-xs leading-relaxed text-muted">
          Known customers: sara, omar. A chat stays with the first id that uses
          it.
        </p>
        <label className="mt-4 block text-sm" htmlFor="prompt">
          Prompt
          <Textarea
            id="prompt"
            className="mt-1"
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            rows={4}
          />
        </label>
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            type="button"
            disabled={
              busy || !prompt.trim() || !customerId.trim() || Boolean(action)
            }
            onClick={() => void send()}
          >
            {busy ? "Sending…" : "Send"}
          </Button>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              setThreadId(freshId());
              setState(null);
              setEffect(null);
              setError(null);
            }}
          >
            New chat
          </Button>
        </div>
        <p className="mt-3 font-mono text-[11px] text-muted">{threadId}</p>
        {error ? (
          <p
            className="mt-3 rounded-sm border border-stamp/40 bg-stamp/10 px-3 py-2 text-sm text-stamp"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        {action ? (
          <div className="mt-5 rounded-sm border border-stamp bg-stamp/5 p-4">
            <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-stamp">
              Paused · {action.name}
            </p>
            <label className="mt-3 block text-sm" htmlFor="reason">
              Refund reason
              <Input
                id="reason"
                className="mt-1"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
              />
            </label>
            <label className="mt-3 block text-sm" htmlFor="hold">
              If you reject it
              <Input
                id="hold"
                className="mt-1"
                value={hold}
                onChange={(event) => setHold(event.target.value)}
              />
            </label>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button
                variant="grove"
                disabled={busy}
                onClick={() => decide([{ type: "approve" }])}
              >
                Approve
              </Button>
              <Button
                variant="stamp"
                disabled={busy || !reason.trim()}
                onClick={() =>
                  decide([
                    {
                      type: "edit",
                      edited_action: {
                        name: "request_refund",
                        args: { reason },
                      },
                    },
                  ])
                }
              >
                File this reason
              </Button>
              <Button
                variant="outline"
                disabled={busy}
                onClick={() => decide([{ type: "reject", message: hold }])}
              >
                Reject
              </Button>
            </div>
          </div>
        ) : null}

        <p className="mt-4 text-xs leading-relaxed text-muted">
          To rate a reply, say so in this chat. The agent asks for a rating, personal or shared, and the right answer, then files it.
        </p>
      </section>

      <section className="space-y-8">
        <div>
          <h2 className="font-display text-2xl">Agent reply</h2>
          {state && agentReply(state.messages) ? (
            <p className="mt-3 whitespace-pre-wrap rounded-sm border border-ink bg-paper-deep px-4 py-3 text-sm leading-relaxed text-ink">
              {agentReply(state.messages)}
            </p>
          ) : (
            <p className="mt-2 text-sm text-muted">
              {state?.interrupt
                ? "The agent paused before answering. Approve or reject the refund on the left."
                : "Send a prompt. The agent's answer appears here."}
            </p>
          )}
        </div>

        <div>
          <h2 className="font-display text-2xl">This prompt</h2>
          {!effect ? (
            <p className="mt-2 text-sm text-muted">
              Send a prompt to see the steps and the effect on each store.
            </p>
          ) : (
            <div className="mt-4 space-y-4">
              <p className="font-mono text-xs text-stamp">{effect.steps}</p>
              <div className="flex flex-wrap gap-2">
                {effect.tools.length === 0 ? <Badge>no tools</Badge> : null}
                {effect.tools.map((name, index) => (
                  <Badge key={`${name}-${index}`} variant="grove">
                    {index + 1}. {name}
                  </Badge>
                ))}
              </div>
              <p className="text-sm leading-relaxed">
                <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                  Personalization used
                </span>
                <span className="mt-1 block">{effect.personalization}</span>
              </p>
              <div className="grid gap-3 sm:grid-cols-2">
                <EffectCard title="Conversation" lines={effect.conversation} />
                <EffectCard title="Personal memory" lines={effect.personal} />
                <EffectCard title="Shared handbook" lines={effect.shared} />
                <EffectCard title="Feedback" lines={effect.feedback} />
              </div>
            </div>
          )}
        </div>

        <div>
          <h2 className="font-display text-2xl">Steps</h2>
          {!state || state.trace.length === 0 ? (
            <p className="mt-2 text-sm text-muted">
              Tool calls and model passes appear here in order.
            </p>
          ) : (
            <ol className="mt-3 space-y-3">
              {state.trace.map((event, index) => (
                <li
                  key={`${event.hook}-${index}`}
                  className="border-l-2 border-grove pl-3"
                >
                  <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">
                    {index + 1}. {event.hook}
                  </p>
                  <p className="mt-1 whitespace-pre-wrap font-mono text-xs leading-relaxed">
                    {event.detail}
                  </p>
                </li>
              ))}
            </ol>
          )}
        </div>

        <div>
          <h2 className="font-display text-2xl">Chat (short-term memory) </h2>
          {state && state.messages.length > 0 ? (
            <Transcript
              messages={state.messages.filter(
                (message) => message.type !== "system",
              )}
            />
          ) : (
            <p className="mt-2 text-sm text-muted">This chat is empty.</p>
          )}
        </div>

        <Store
          title="Personal memory now (long-term memory)"
          lines={state ? profileLines(state) : ["Nothing loaded."]}
        />
        <Store
          title="Shared handbook now (Knowledge base)"
          lines={
            state && state.handbook.length > 0
              ? state.handbook.map((note) => note.title)
              : ["The handbook has not been loaded."]
          }
        />
        <div>
          <h2 className="font-display text-2xl">Feedback now (Training data)</h2>
          {!state || state.feedback.length === 0 ? (
            <p className="mt-2 text-sm text-muted">No feedback yet.</p>
          ) : (
            <ul className="mt-3 space-y-3">
              {state.feedback.map((item) => (
                <li key={item.id} className="border-t border-rule pt-3 text-sm leading-relaxed">
                  <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">
                    {item.scope} · {item.rating}/5
                    {item.consent_for_training ? " · consent" : ""}
                  </p>
                  <FeedbackExampleView item={item} />
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h2 className="font-display text-2xl">Monthly review</h2>
          <p className="mt-2 text-sm text-muted">
            Compares consented feedback that has not been reviewed yet with the prompt, the tools, and the handbook.
          </p>
          <Button type="button" variant="outline" className="mt-3" disabled={busy} onClick={() => void review()}>
            Suggest changes
          </Button>
          {suggestions ? (
            suggestions.length === 0 ? (
              <p className="mt-3 text-sm text-muted">No new consented feedback to review.</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {suggestions.map((item) => (
                  <li key={item.feedback_ids.join("-")} className="border-t border-rule pt-3 text-sm">
                    <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">
                      {item.where} · {item.count}
                    </p>
                    <p className="mt-1">{item.what}</p>
                    <p className="mt-1 text-muted">{item.why}</p>
                  </li>
                ))}
              </ul>
            )
          ) : null}
        </div>
        <div>
          <h2 className="font-display text-2xl">Candidates</h2>
          {!state || state.candidates.length === 0 ? (
            <p className="mt-2 text-sm text-muted">
              No shared note is waiting.
            </p>
          ) : (
            <ul className="mt-3 space-y-3">
              {state.candidates.map((item) => (
                <li key={item.id} className="border-t border-rule pt-3 text-sm">
                  <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">
                    {item.status}
                  </p>
                  <p className="mt-1">{item.text}</p>
                  {item.status === "pending" ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="mt-2"
                      disabled={busy}
                      onClick={() => void acceptCandidate(item.id)}
                    >
                      Approve into the handbook
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>
    </div>
  );
}

function EffectCard({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div className="rounded-sm border border-rule px-3 py-3">
      <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-stamp">
        {title}
      </p>
      <ul className="mt-2 space-y-1 text-sm leading-relaxed">
        {linesOf(lines, "")
          .filter(Boolean)
          .map((line) => (
            <li key={line}>{line}</li>
          ))}
      </ul>
    </div>
  );
}

function FeedbackExampleView({ item }: { item: FeedbackRecord }) {
  const example = item.example;
  const customer = example?.feedback_message || "";
  const problem = example?.problem || item.reason;
  const preferred = example?.preferred_reply || item.corrected_answer;
  const rows = [
    customer ? ["Customer", customer] : null,
    example?.question ? ["Asked", example.question] : null,
    example?.judged_reply ? ["Reply judged", example.judged_reply] : null,
    problem && problem !== customer ? ["Problem", problem] : null,
    preferred ? ["Preferred reply", preferred] : null,
  ].filter((row): row is [string, string] => row !== null);
  if (rows.length === 0) return <p className="mt-1 text-muted">No text saved.</p>;
  return (
    <dl className="mt-2 space-y-1">
      {rows.map(([label, value]) => (
        <div key={label}>
          <dt className="font-mono text-[10px] uppercase tracking-[0.14em] text-muted">{label}</dt>
          <dd className="whitespace-pre-wrap">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function Store({ title, lines }: { title: string; lines: string[] }) {
  return (
    <div>
      <h2 className="font-display text-2xl">{title}</h2>
      <ul className="mt-2 space-y-1 text-sm leading-relaxed">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </div>
  );
}
