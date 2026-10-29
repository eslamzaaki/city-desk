"""The Marsa archive: notes, a splitter, and an in-memory vector store.

The embedder is a bag of words over the archive, with stopwords removed and a
light stem. It implements the LangChain ``Embeddings`` interface, so the
vector-store call is the same one you would point at a hosted embedding model.
"""

from __future__ import annotations

import math
import re
from functools import lru_cache

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter

NOTES: list[dict[str, str]] = [
    {
        "id": "harbor-dredging",
        "title": "Harbor dredging",
        "body": (
            "Harbor dredging starts Monday at pier 4. The port authority closed the inner "
            "basin to ferries from dawn until 14:00. Barges will lift silt that has sat "
            "since the spring storm. Fishermen move to pier 7 for the week. A notice on "
            "the harbor gate says the crane stays up through Thursday. Night work is not "
            "permitted because the lamps on pier 4 failed inspection."
        ),
    },
    {
        "id": "corniche-flood",
        "title": "Corniche flood",
        "body": (
            "The corniche flooded between kilometre 2 and kilometre 4 after the storm drain "
            "at the customs ramp clogged. Water reached the shop thresholds but not the "
            "tram bed. Municipal crews opened two pumps at noon. The road reopens to cars "
            "once the last pool in front of the date market drains. Pedestrians can use "
            "the upper walk, which stayed dry."
        ),
    },
    {
        "id": "tram-extension",
        "title": "Tram extension",
        "body": (
            "The tram extension adds a stop at the Customs House and another at the fish "
            "market. Test cars run empty on Sunday. Fares do not change. The old terminus "
            "at the warehouse gate closes the same morning. Drivers were told to call the "
            "stop Customs, not Port, so the board matches the printed map."
        ),
    },
    {
        "id": "night-market",
        "title": "Night market",
        "body": (
            "Night market lantern permits are due Friday at the licensing window. Stalls "
            "that fry fish must keep a bucket of sand, not a bucket of water. The market "
            "master will walk the row at 18:00. Unpermitted lanterns are cut down. Last "
            "year two canvas roofs scorched because a stall used a candle instead of a lamp."
        ),
    },
    {
        "id": "museum",
        "title": "Museum mosaic wing",
        "body": (
            "The museum reopens the mosaic wing on Saturday at 10:00. The new room holds "
            "the harbor mosaic that was lifted from the old customs floor. Tickets stay "
            "at the side door while the main stair is scaffolded. School groups enter "
            "from the garden. Photography of the mosaic is allowed without flash."
        ),
    },
    {
        "id": "heat",
        "title": "Heat advisory",
        "body": (
            "A heat advisory covers Marsa from 11:00 until 16:00. The noon bells are the "
            "cue for outdoor crews to stop. The port will set water barrels at pier 7 and "
            "at the tram stop. Schools dismiss early. The advisory does not close the "
            "harbor, but crane work pauses while the advisory holds."
        ),
    },
    {
        "id": "ferry-strike",
        "title": "Ferry strike",
        "body": (
            "Ferry crews vote Thursday morning on a one-day stoppage. The sailors want the "
            "hazard pay that was promised after the spring storm. If the vote passes, the "
            "first cancelled sailing is the 06:10 to the outer island. The port authority "
            "has not published a replacement bus. Cargo barges are not part of the vote."
        ),
    },
    {
        "id": "warehouse-fire",
        "title": "Spice warehouse fire",
        "body": (
            "A fire in the spice warehouse on Rope Walk started just after midnight and was "
            "out by 02:20. No one was inside. Smoke stained the pepper sacks on the east "
            "wall. The fire captain blamed a cracked lamp, not the wiring. The building "
            "reopens for inventory on Wednesday. Neighbors reported the smell of clove "
            "through the morning."
        ),
    },
]

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
    """Bag-of-words over the archive vocabulary.

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


def split_notes() -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(chunk_size=280, chunk_overlap=40)
    documents = [
        Document(page_content=note["body"], metadata={"id": note["id"], "title": note["title"]})
        for note in NOTES
    ]
    return splitter.split_documents(documents)


@lru_cache(maxsize=1)
def vector_store() -> InMemoryVectorStore:
    chunks = split_notes()
    embeddings = ArchiveEmbeddings([chunk.page_content for chunk in chunks])
    return InMemoryVectorStore.from_documents(chunks, embeddings)


def search_notes(query: str, k: int = 2) -> list[dict[str, str | float]]:
    hits = vector_store().similarity_search_with_score(query, k=k)
    return [
        {
            "title": str(document.metadata.get("title", "note")),
            "text": document.page_content,
            "score": round(float(score), 3),
        }
        for document, score in hits
    ]
