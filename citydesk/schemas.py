"""Shared types the desk passes through context and structured output."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass
class DeskContext:
    """Per-invoke context. Tools read it off ``ToolRuntime``, not from the model."""

    reporter: str
    desk: str


class BriefCard(BaseModel):
    """The shape of a filed brief. ``ToolStrategy`` turns this into a tool."""

    headline: str = Field(description="One sentence a copy editor could put on the spike")
    summary: str = Field(description="What the archive actually said, in two or three sentences")
    confidence: float = Field(description="From 0 to 1, how directly the archive supports this", ge=0, le=1)
    sources: list[str] = Field(description="Where the claim came from")
