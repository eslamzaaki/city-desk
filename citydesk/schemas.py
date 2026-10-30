"""Shared types the counter passes through context."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ShopContext:
    """Per-invoke context. Tools read the customer off ``ToolRuntime``, not from the model."""

    customer_id: str
