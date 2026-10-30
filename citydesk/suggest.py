"""Monthly review for the counter. The sorting lives in ``personalize``."""

from __future__ import annotations

import json
from typing import Any

from citydesk.corpus import all_notes, vector_store
from citydesk.desk import COUNTER_RULES
from citydesk.personal import shop_personal
from citydesk.tools import (
    lookup_order,
    recall_preferences,
    request_refund,
    save_feedback,
    save_preference,
    search_handbook,
    who_is_shopping,
)

TOOLS = (
    search_handbook,
    lookup_order,
    save_preference,
    recall_preferences,
    who_is_shopping,
    request_refund,
    save_feedback,
)

_LAST: dict[str, Any] = {"reviewed": 0, "suggestions": []}


def last_report() -> dict[str, Any]:
    return {"reviewed": _LAST["reviewed"], "suggestions": list(_LAST["suggestions"])}


def build_suggestions(*, mark_used: bool = True) -> dict[str, Any]:
    """Group consented feedback that has not been reviewed yet."""

    handbook = all_notes()
    report = shop_personal.review(
        prompts=[COUNTER_RULES],
        tools=TOOLS,
        knowledge=vector_store(),
        knowledge_titles=[note["title"] for note in handbook],
        mark_used=mark_used,
    )
    _LAST.clear()
    _LAST.update(report)
    return report


def main() -> None:
    print(json.dumps(build_suggestions(), indent=2))


if __name__ == "__main__":
    main()
