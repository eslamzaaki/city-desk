"""The Lumen handbook: notes, a splitter, and an in-memory vector store.

Starter notes are the markdown files in ``data/handbook``. This module reads
them, splits them, and builds an ``InMemoryVectorStore``. Nothing is written
back to disk. The embedder is a bag of words over the handbook, with stopwords
removed and a light stem. It implements the LangChain ``Embeddings`` interface,
so the vector-store call is the same one you would point at a hosted embedding
model.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

HANDBOOK_DIR = Path(__file__).resolve().parent.parent / "data" / "handbook"


def load_notes(directory: Path | None = None) -> list[dict[str, str]]:
    """Read ``data/handbook/*.md``. A leading ``01-`` on the filename is sort order only."""

    folder = directory or HANDBOOK_DIR
    notes: list[dict[str, str]] = []
    for path in sorted(folder.glob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        heading, _, body = text.partition("\n")
        title = heading.removeprefix("# ").strip()
        prefix, _, rest = path.stem.partition("-")
        note_id = rest if prefix.isdigit() and rest else path.stem
        notes.append({"id": note_id, "title": title, "body": body.strip()})
    return notes


NOTES: list[dict[str, str]] = load_notes()

# Notes a person approved into the handbook. Personal memory never lands here on its own.
EXTRA_NOTES: list[dict[str, str]] = []

_STOPWORDS = {
    "the", "a", "an", "of", "and", "to", "in", "on", "for", "at", "is", "it", "its",
    "by", "from", "with", "that", "this", "as", "be", "or", "was", "are", "not", "but",
    "after", "before", "while", "into", "over", "they", "their", "has", "have", "will",
    "been", "were", "can", "does", "did", "about", "what", "when", "where", "which",
    "who", "how", "does", "the",
}


def _stem(token: str) -> str:
    for suffix in ("ing", "ed", "es", "ly"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    if token.endswith("s") and len(token) >= 5:
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    tokens = []
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        if token in _STOPWORDS or len(token) < 3:
            continue
        tokens.append(_stem(token))
    return tokens


class ArchiveEmbeddings(Embeddings):
    """Bag-of-words over the handbook vocabulary.

    One dimension per stemmed word in the notes, stopwords removed. Cosine
    similarity then prefers notes that share the question's words. This is the
    ``Embeddings`` interface: ``InMemoryVectorStore`` does not care that the
    vectors came from a word list instead of an API.
    """

    def __init__(self, texts: list[str]) -> None:
        vocabulary = sorted({token for text in texts for token in tokenize(text)})
        self.index = {token: position for position, token in enumerate(vocabulary)}

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * (len(self.index) or 1)
        for token in tokenize(text):
            slot = self.index.get(token)
            if slot is not None:
                vector[slot] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


def all_notes() -> list[dict[str, str]]:
    return [*NOTES, *EXTRA_NOTES]


def add_handbook_note(note_id: str, title: str, body: str) -> None:
    EXTRA_NOTES.append({"id": note_id, "title": title, "body": body})
    vector_store.cache_clear()


def clear_extra_notes() -> None:
    EXTRA_NOTES.clear()
    vector_store.cache_clear()


def split_notes() -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=280, chunk_overlap=40)
    documents = [
        Document(page_content=note["body"], metadata={"id": note["id"], "title": note["title"]})
        for note in all_notes()
    ]
    return splitter.split_documents(documents)


@lru_cache(maxsize=1)
def vector_store() -> InMemoryVectorStore:
    chunks = split_notes()
    embeddings = ArchiveEmbeddings([chunk.page_content for chunk in chunks])
    return InMemoryVectorStore.from_documents(chunks, embeddings)


def search_notes(query: str, k: int = 2) -> list[dict[str, str | float]]:
    try:
        hits = vector_store().similarity_search_with_score(query, k=k)
    except ValueError:
        return []
    return [
        {
            "title": str(document.metadata.get("title", "note")),
            "text": document.page_content,
            "score": round(float(score), 3),
        }
        for document, score in hits
    ]
