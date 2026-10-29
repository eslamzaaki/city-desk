# The City Desk

A newsroom for the port city of Marsa, built so you can learn LangChain 1.x and LangGraph by doing the job.

You are the editor. The assistant on the harbor desk searches a local archive, remembers a reporter’s beat across shifts, and files a brief only after you approve it. Each station on the left is one current LangChain surface — messages, models, tools, structured output, `create_agent`, streaming, middleware, memory, human review, retrieval, graphs, and evals — running real library code. The last station is a shift that composes them.

The chat model is local. `DeskChatModel` implements the same interface as `init_chat_model`, so the lab runs with no API key and every tool call stays visible. Set `CITYDESK_MODEL` when you want a provider model in the live shift.

This tracks LangChain 1.4 and LangGraph 1.2: `create_agent` (not `create_react_agent`), middleware instead of `pre_model_hook`, `ToolStrategy` for structured output, content blocks, `ToolRuntime`, checkpointers for a thread, stores for everything that outlives a thread, and a `StateGraph` that can hold an agent as a node.

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

The stations always use `DeskChatModel`, so the lesson output stays inspectable. The shift uses `resolve_model()`:

```bash
export CITYDESK_MODEL=openai:gpt-4.1-mini
.venv/bin/pip install langchain-openai
```

If the provider package is missing, the shift falls back to the local model and says so in the masthead line of the desk.

## Where the code lives

| Path | What it teaches |
| --- | --- |
| `citydesk/lessons/` | One file per station. This is the code the Source tab shows. |
| `citydesk/model.py` | A `BaseChatModel` you can swap for `init_chat_model`. |
| `citydesk/tools.py` | `@tool` and `ToolRuntime`. |
| `citydesk/middleware.py` | A trace hook and a tool-error wrapper. |
| `citydesk/corpus.py` | Splitter, `Embeddings`, `InMemoryVectorStore`. |
| `citydesk/desk.py` | The composed agent: PII, dynamic prompt, review, memory. |

Memory in the shift is in-process (`InMemorySaver` and `InMemoryStore`). Restarting the API clears shifts and beats. That is the seam where a database checkpointer and a hosted trace (LangSmith) would land next.
