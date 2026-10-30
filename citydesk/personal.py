"""The counter's personalization, built from the shared library."""

from __future__ import annotations

from personalize import Personalize
from citydesk.shop import apply_note, blank_profile, customer_name, relevant_lines, render_profile
from citydesk.tracing import emit


def _inject(user_id: str, text: str) -> None:
    name = customer_name(user_id) if user_id else "the customer"
    emit("dynamic_prompt", f"{name}.{text}")


def _saved(user_id: str, note: str) -> None:
    emit("tool:save_preference", f"{user_id}: {note}")


def _recalled(user_id: str) -> None:
    emit("tool:recall_preferences", user_id)


TOOL_GAPS = (
    ("address", "update_delivery", "Customers ask to change a delivery address. No tool does that."),
    ("cancel", "cancel_order", "Customers ask to cancel an order. No tool does that."),
    ("track", "track_parcel", "Customers ask to track a parcel. No tool does that."),
    ("approver", "lookup_approver", "Customers ask who approves a refund. No tool can name that person."),
)


shop_personal = Personalize(
    fold=apply_note,
    lines=relevant_lines,
    render=render_profile,
    blank=blank_profile,
    on_inject=_inject,
    on_save=_saved,
    on_recall=_recalled,
    audience="this customer",
    tool_gaps=TOOL_GAPS,
)
