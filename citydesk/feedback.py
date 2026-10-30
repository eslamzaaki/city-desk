"""Counter names for the feedback helpers that live in ``personalize``."""

from personalize.feedback import (
    build_example,
    feedback_ask,
    feedback_ready,
    parse_feedback,
    states_a_fact,
)

is_shop_rule = states_a_fact

__all__ = [
    "build_example",
    "feedback_ask",
    "feedback_ready",
    "is_shop_rule",
    "parse_feedback",
    "states_a_fact",
]
