"""Lumen, a shoe and clothing shop.

Customers, orders, and starter personal memory are loaded from ``data/shop.json``.
The handbook is separate, in ``data/handbook`` via ``corpus``. A private
correction never enters that handbook from this module.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_SHOP = json.loads((Path(__file__).resolve().parent.parent / "data" / "shop.json").read_text(encoding="utf-8"))

RETURN_DAYS = int(_SHOP["return_days"])
CUSTOMERS: dict[str, dict[str, str]] = _SHOP["customers"]
ORDERS: dict[str, dict[str, Any]] = _SHOP["orders"]
_SEEDS: dict[str, dict[str, Any]] = _SHOP["profiles"]


def customer_name(customer_id: str) -> str:
    found = CUSTOMERS.get(customer_id)
    return found["name"] if found else customer_id


def require_customer(customer_id: str) -> dict[str, str]:
    found = CUSTOMERS.get(customer_id)
    if found is None:
        raise ValueError("Unknown customer.")
    return found


def blank_profile() -> dict[str, Any]:
    return {"preferences": {"language": "", "answer_style": ""}, "facts": [], "corrections": []}


def seed_profile(customer_id: str) -> dict[str, Any]:
    seed = _SEEDS.get(customer_id)
    if seed is None:
        return blank_profile()
    return {
        "preferences": dict(seed["preferences"]),
        "facts": list(seed["facts"]),
        "corrections": [dict(item) for item in seed["corrections"]],
    }


def read_profile(store: Any, customer_id: str) -> dict[str, Any]:
    if store is None:
        return blank_profile()
    current = store.get((customer_id,), "profile")
    if current is None:
        return blank_profile()
    value = dict(current.value)
    value.setdefault("preferences", {"language": "", "answer_style": ""})
    value.setdefault("facts", [])
    value.setdefault("corrections", [])
    return value


def write_profile(store: Any, customer_id: str, profile: dict[str, Any]) -> None:
    store.put((customer_id,), "profile", profile)


def ensure_seed(store: Any, customer_id: str) -> dict[str, Any]:
    """Write the starter profile once. Later notes stay on top of it."""

    if store is None:
        return blank_profile()
    if store.get((customer_id,), "profile") is None:
        write_profile(store, customer_id, seed_profile(customer_id))
    return read_profile(store, customer_id)


def apply_note(profile: dict[str, Any], note: str, thread_id: str) -> dict[str, Any]:
    """Fold one customer sentence into preferences, a fact, or a correction."""

    text = note.strip()
    lowered = text.lower()
    if not text:
        return profile
    prefs = profile["preferences"]
    if "arabic" in lowered:
        prefs["language"] = "Arabic"
    if "english" in lowered:
        prefs["language"] = "English"
    if any(word in lowered for word in ("short", "concise", "brief", "shorter")):
        prefs["answer_style"] = "concise"
    if lowered.startswith("correction") or "the right answer is" in lowered:
        value = text.split(":", 1)[-1].strip()
        profile["corrections"].append(
            {"topic": "reply", "value": value[:500], "source_thread": thread_id}
        )
        return profile
    size = re.search(r"size\s*(\d{2})", lowered)
    if size:
        fact = f"Wears size {size.group(1)}"
        if fact not in profile["facts"]:
            profile["facts"].append(fact)
    if text not in profile["facts"]:
        profile["facts"].append(text[:240])
    return profile


def profile_lines(profile: dict[str, Any]) -> list[str]:
    prefs = profile.get("preferences") or {}
    lines: list[str] = []
    if prefs.get("language"):
        lines.append(f"Language: {prefs['language']}")
    if prefs.get("answer_style"):
        lines.append(f"Answer style: {prefs['answer_style']}")
    lines.extend(str(fact) for fact in profile.get("facts") or [])
    for item in profile.get("corrections") or []:
        lines.append(f"Correction ({item.get('topic', 'reply')}): {item.get('value', '')}")
    return lines


def render_profile(profile: dict[str, Any], customer_id: str) -> str:
    lines = profile_lines(profile)
    name = customer_name(customer_id)
    if not lines:
        return f"Nothing saved yet for {name}."
    return f"On file for {name}: " + " | ".join(lines)


def relevant_lines(profile: dict[str, Any], question: str) -> list[str]:
    """Preferences always. Facts and corrections only when the question shares their words."""

    prefs = profile.get("preferences") or {}
    lines: list[str] = []
    if prefs.get("language"):
        lines.append(f"Language: {prefs['language']}")
    if prefs.get("answer_style"):
        lines.append(f"Answer style: {prefs['answer_style']}")
    lowered = question.lower()
    ask_all = any(phrase in lowered for phrase in ("remember", "preference", "about me", "my size", "what size"))
    tokens = set(re.findall(r"[a-z0-9]+", lowered))
    for fact in profile.get("facts") or []:
        fact_tokens = set(re.findall(r"[a-z0-9]+", str(fact).lower()))
        if ask_all or tokens & fact_tokens:
            lines.append(str(fact))
    for item in profile.get("corrections") or []:
        blob = f"{item.get('topic', '')} {item.get('value', '')}"
        if ask_all or tokens & set(re.findall(r"[a-z0-9]+", blob.lower())):
            lines.append(f"Correction ({item.get('topic', 'reply')}): {item.get('value', '')}")
    return lines


def order_summary(customer_id: str) -> str:
    order = ORDERS[customer_id]
    name = customer_name(customer_id)
    open_return = int(order["delivered_days_ago"]) <= RETURN_DAYS
    window = (
        f"A {RETURN_DAYS}-day return is still open."
        if open_return
        else f"The {RETURN_DAYS}-day return window has closed."
    )
    return (
        f"Order {order['id']} for {name}: {order['item']}, size {order['size']}, "
        f"delivered {order['delivered_days_ago']} days ago. {window}"
    )
