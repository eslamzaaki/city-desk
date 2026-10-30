# How to run City Desk

You need Python 3.11 or newer and Node.js. The API and the web app run in two terminals. The web app is at [http://127.0.0.1:43123](http://127.0.0.1:43123) and proxies `/api` to the API on port 43124.

No API key is required when `CITYDESK_PROVIDER=local`. That uses the local `DeskChatModel`.

Starter shop data is the `data/` folder: handbook notes in `data/handbook/` (what the vector store indexes) and customers, orders, and personal memory in `data/shop.json`. See `data/README.md`.

## Windows (PowerShell)

From the repo root:

```powershell
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
.venv\Scripts\uvicorn citydesk.api:app --host 0.0.0.0 --port 43124
```

In a second terminal:

```powershell
cd web
npm install
npm run dev
```

Open [http://127.0.0.1:43123](http://127.0.0.1:43123).

## macOS and Linux

From the repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/uvicorn citydesk.api:app --host 0.0.0.0 --port 43124
```

In a second terminal:

```bash
cd web
npm install
npm run dev
```

## Tests

Windows:

```powershell
.venv\Scripts\pytest
```

macOS and Linux:

```bash
.venv/bin/pytest
```

## A provider model for the shift

Copy `.env.example` to `.env` in the repo root. Set `CITYDESK_PROVIDER` to `local`, `openai`, or `anthropic`, and set the key for that provider. `CITYDESK_MODEL` is optional; leave it empty to use the default model for the provider. The API loads `.env` when the `citydesk` package starts. Restart uvicorn after you change the file.

A variable already set in the shell is kept. Use that when you want one run to ignore the file:

```powershell
$env:CITYDESK_PROVIDER = "openai"
$env:OPENAI_API_KEY = "your-key"
```

```bash
export CITYDESK_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your-key
```

Install the matching provider package before starting the API (`langchain-openai` or `langchain-anthropic`). If the package or key is missing, the counter falls back to `DeskChatModel`.

Restarting the API clears in-memory chats, personal notes, pending handbook candidates, and feedback.

## Monthly suggestion review

This reads consented feedback that has not been reviewed yet, compares it with the current prompt, tools, and handbook, and prints suggestions. It does not change those files.

```powershell
.venv\Scripts\python -m citydesk.suggest
```

```bash
.venv/bin/python -m citydesk.suggest
```

Run that once a month. The same action is **Suggest changes** on the counter page. A second run skips rows the first run already reviewed.

## Personalization on another agent

The library lives in its own repo: [github.com/eslamzaaki/personalize](https://github.com/eslamzaaki/personalize). Installing this counter installs it (`pip install -e ".[dev]"` above). On its own:

```bash
pip install git+https://github.com/eslamzaaki/personalize.git
```

It carries the three pieces: personal memory, feedback gathering, and the monthly review. Attach it to any `create_agent` call:

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from personalize import Personalize, UserContext

personal = Personalize()
agent = create_agent(
    model="openai:gpt-6.1-sol",
    tools=[*personal.tools],
    middleware=[personal.middleware],
    context_schema=UserContext,
    checkpointer=InMemorySaver(),
    store=InMemoryStore(),
)
agent.invoke(
    {"messages": [{"role": "user", "content": "I prefer short answers."}]},
    {"configurable": {"thread_id": "t1"}},
    context=UserContext(user_id="sara"),
)
```

`personal.tools` is `save_preference`, `recall_preferences`, and `save_feedback`. The model never receives the user id. A preference customizes this user. Feedback, with consent, waits for review:

```python
report = personal.review(
    prompts=["The standing instructions for this agent.", "A second prompt, if the agent has one."],
    tools=personal.tools,
    knowledge=vector_store,  # any LangChain vector store, or a list of texts
)
```

`report["suggestions"]` says handbook, prompt, tool, or leave it on that user. A second call skips rows the first call reviewed. Pass `fold`, `lines`, `render`, and `tool_gaps` when the profile or the missing tools are not the defaults. The counter does that in `citydesk/personal.py`.

## One process, after a production build

Build the UI, then the API serves `web/dist` on port 43124 (no Vite proxy):

```powershell
cd web
npm install
npm run build
cd ..
.venv\Scripts\uvicorn citydesk.api:app --host 0.0.0.0 --port 43124
```

Open [http://127.0.0.1:43124](http://127.0.0.1:43124).
