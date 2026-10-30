# Starting data

This folder is the shop the process starts with. Nothing here is a saved database. Restarting the API reads these files again and drops chats, personal notes added during a run, and handbook notes that were approved in that run.

## Handbook, and the vector store

`handbook/` is the only text indexed at startup. One markdown file is one shared note. The filename sets the id (`03-trail-shoe.md` is `trail-shoe`). The first line is the title. The rest is the body.

`citydesk/corpus.py` reads those files, splits each body, and builds a LangChain `InMemoryVectorStore` in process memory. The embedder is local (`ArchiveEmbeddings`): a bag of words over the handbook, not a hosted model, and not a file on disk. There is no vector-store dump to open. The store is rebuilt from `handbook/` the first time a search runs after startup, and again after a shared note is approved.

A personal correction does not get a file here. Approving a shared candidate appends it in memory for that process only.

## Customers

`shop.json` is the other starter data, and it is not in the vector store.

- `customers` — the only ids the counter accepts (`sara`, `omar`)
- `orders` — what `lookup_order` returns
- `profiles` — the personal memory written the first time that customer is used
- `return_days` — the window those orders are checked against
