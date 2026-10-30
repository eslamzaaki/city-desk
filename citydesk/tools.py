"""Tools the counter model is allowed to call.

``ToolRuntime`` carries the customer, the store, and the call id. Those values
never appear in the arguments the model fills in, so one customer cannot ask
the tool to open another customer's order or memory.
"""

from __future__ import annotations

from langchain.tools import ToolRuntime, tool

from citydesk.corpus import search_notes
from citydesk.feedback import feedback_ask, feedback_ready
from citydesk.personal import shop_personal
from citydesk.schemas import ShopContext
from citydesk.shop import customer_name, order_summary
from citydesk.tracing import emit

save_preference = shop_personal.save_preference
recall_preferences = shop_personal.recall_preferences

REFUNDS: list[dict[str, str]] = []


@tool
def search_handbook(query: str) -> str:
    """Search the shared Lumen handbook and return the closest notes."""

    hits = search_notes(query, k=2)
    emit("tool:search_handbook", query[:120])
    if not hits:
        return "The handbook has no note for that."
    blocks = [f"[{hit['title']} · similarity {hit['score']}] {hit['text']}" for hit in hits]
    return "\n\n".join(blocks)


@tool
def lookup_order(runtime: ToolRuntime[ShopContext]) -> str:
    """Read this customer's own order. The model does not choose whose order."""

    customer_id = runtime.context.customer_id
    emit("tool:lookup_order", customer_id)
    return order_summary(customer_id)


@tool
def who_is_shopping(runtime: ToolRuntime[ShopContext]) -> str:
    """Say which customer this chat belongs to."""

    customer_id = runtime.context.customer_id
    emit("tool:who_is_shopping", customer_id)
    return f"{customer_name(customer_id)} is at the Lumen counter."


@tool
def request_refund(reason: str, runtime: ToolRuntime[ShopContext]) -> str:
    """File a refund for this customer's order. A person must approve this before it runs."""

    customer_id = runtime.context.customer_id
    summary = order_summary(customer_id)
    if "has closed" in summary:
        emit("tool:request_refund", f"{customer_id}: refused")
        return f"Refund not filed. {summary}"
    order_id = summary.split(" for ", 1)[0].replace("Order ", "")
    entry = {
        "id": f"refund-{len(REFUNDS) + 1}",
        "order_id": order_id,
        "reason": reason,
        "customer_id": customer_id,
    }
    REFUNDS.append(entry)
    emit("tool:request_refund", entry["id"])
    return f"Refund {entry['id']} filed for {order_id}: {reason}"


def clear_refunds() -> None:
    REFUNDS.clear()


@tool
def save_feedback(
    rating: int,
    scope: str,
    reason: str,
    corrected_answer: str,
    consent_for_training: bool,
    runtime: ToolRuntime[ShopContext],
) -> str:
    """File a judgment that should make the agent better for every customer.

    scope shared: a wrong shop answer, a missing fact, or a missing capability,
    such as who approves a refund. This is the normal scope.
    scope personal: only when they say the correction is for them alone.
    corrected_answer is the fact or capability every customer should get.
    Never put an apology there.
    consent_for_training is true only when they agree to keep the example.
    """

    customer_id = runtime.context.customer_id
    parsed = {
        "rating": int(rating) if str(rating).isdigit() else rating,
        "scope": scope,
        "reason": reason,
        "corrected_answer": corrected_answer,
        "consent_for_training": consent_for_training,
    }
    if not feedback_ready(parsed):
        return feedback_ask(parsed)
    thread_id = ""
    if runtime.config:
        thread_id = str((runtime.config.get("configurable") or {}).get("thread_id") or "")
    from citydesk.service import last_response_id, record_feedback

    response_id = last_response_id(thread_id)
    if not response_id:
        return "There is no earlier reply in this chat to rate. Ask a shop question first."
    state = getattr(runtime, "state", None) or {}
    messages = state.get("messages", []) if isinstance(state, dict) else []
    record_feedback(
        thread_id,
        customer_id,
        response_id,
        scope,
        int(rating),
        reason or None,
        corrected_answer or None,
        bool(consent_for_training),
        messages,
    )
    emit("tool:save_feedback", f"{customer_id}: {scope} {rating}")
    kept = "Consent is stored for a future training set." if consent_for_training else "No training example was kept."
    if scope == "personal":
        return f"Saved personal feedback, rating {rating}, on your profile only. {kept}"
    return f"Saved shared feedback, rating {rating}. It waits as a handbook candidate until someone approves it. {kept}"
