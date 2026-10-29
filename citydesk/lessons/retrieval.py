"""Station 10 — split, embed, search, and hand the retriever to the agent as a tool."""

from __future__ import annotations

from langchain.agents import create_agent

from citydesk.corpus import NOTES, search_notes, split_notes
from citydesk.lessons.support import RUN, pack
from citydesk.model import DeskChatModel
from citydesk.tools import search_archive
from citydesk.tracing import trace_scope

META = {
    "id": "retrieval",
    "number": "10",
    "title": "Retrieval",
    "kicker": "Split, embed, retrieve, then let the agent call it",
    "summary": (
        "The archive is eight notes. RecursiveCharacterTextSplitter cuts them into "
        "chunks. ArchiveEmbeddings implements the Embeddings interface: stopwords "
        "dropped, a light stem, one dimension per word in the archive. "
        "InMemoryVectorStore ranks chunks by cosine similarity. search_archive is that "
        "retriever wrapped in @tool. The agent does not know there is a vector store. "
        "It knows there is a tool."
    ),
    "look_for": [
        "There are more chunks than notes. Overlap is why a fact can land in two chunks.",
        "The tool result includes the title and the similarity score.",
        "Swap ArchiveEmbeddings for a provider embedding class and this station's agent code stays put.",
    ],
    "default_prompt": "What does the heat advisory tell outdoor crews?",
    "accepts_prompt": True,
    "source": "citydesk/lessons/retrieval.py",
}


def run(prompt: str | None = None) -> dict:
    text = (prompt or META["default_prompt"]).strip()
    chunks = split_notes()
    hits = search_notes(text, k=3)
    agent = create_agent(
        model=DeskChatModel(),
        tools=[search_archive],
        system_prompt="Answer from the archive tool. Do not add facts that are not in the note.",
    )
    with trace_scope() as events:
        result = agent.invoke({"messages": [{"role": "user", "content": text}]}, RUN)
    reply = result["messages"][-1].content
    headline = reply.split("\n")[0][:180] if isinstance(reply, str) else "Retrieved."
    section = pack(
        result,
        events,
        label=f"{len(NOTES)} notes → {len(chunks)} chunks",
        body="Top of the index for this question, before the agent speaks.",
        hits=hits,
    )
    return {"headline": headline, "sections": [section]}
