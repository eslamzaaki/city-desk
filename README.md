# The City Desk

A shop counter for Lumen, built so you can learn LangChain 1.x and LangGraph by doing the job.

You stand with one customer. The assistant checks the shared handbook, remembers that customer's size and language, and files a refund only after you approve it. Sara and Omar can ask the same question and get different answers. A correction stays on that customer until someone approves it into the handbook. The page is one counter: a customer id, a prompt, and the effect of that prompt on the chat, personal memory, the handbook, and feedback.

The chat model is local unless `.env` says otherwise. `CITYDESK_PROVIDER` is `local`, `openai`, or `anthropic`. `DeskChatModel` implements the same interface as `init_chat_model`, so `local` runs with no API key and every tool call stays visible.

This tracks LangChain 1.4 and LangGraph 1.2: `create_agent` (not `create_react_agent`), middleware instead of `pre_model_hook`, content blocks, `ToolRuntime`, a checkpointer for the chat, and a store for personal memory.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn citydesk.api:app --host 0.0.0.0 --port 43124

cd web
npm install
npm run dev
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123). The dev server proxies `/api` to port 43124.

```bash
.venv/bin/pytest
```

## A live model

The counter uses `resolve_model()`. On startup the API loads a `.env` file from the repo root. A variable already set in the shell is left as-is. `CITYDESK_PROVIDER=local` keeps `DeskChatModel`. `openai` and `anthropic` use `CITYDESK_MODEL` when it names that provider, and a default model when it does not.

```bash
# CITYDESK_PROVIDER=openai
.venv/bin/pip install langchain-openai
```

If the provider package is missing, the counter falls back to the local model.

## Where the code lives

| Path | What it is |
| --- | --- |
| [personalize](https://github.com/eslamzaaki/personalize) | The library this counter installs. Personal memory, feedback, and the monthly review. Wired in `citydesk/personal.py`. |
| `data/` | The shop the process starts with. `handbook/` is indexed into the vector store. `shop.json` is customers, orders, and starter personal memory. |
| `citydesk/corpus.py` | Reads `data/handbook`, splits it, and builds the in-memory vector store. |
| `citydesk/shop.py` | Reads `data/shop.json`. Personal memory helpers. |
| `citydesk/model.py` | A `BaseChatModel` you can swap for `init_chat_model`. |
| `citydesk/tools.py` | `@tool` and `ToolRuntime`. |
| `citydesk/middleware.py` | A trace hook and a tool-error wrapper. |
| `citydesk/desk.py` | The composed agent: PII, dynamic prompt, review, memory. |

Memory is in-process (`InMemorySaver` for the chat, `InMemoryStore` for the customer). Restarting the API clears chats, personal notes, and pending handbook candidates. That is the seam where a database checkpointer and a hosted trace (LangSmith) would land next. Feedback can be marked for a future training set. It does not fine-tune a model.
