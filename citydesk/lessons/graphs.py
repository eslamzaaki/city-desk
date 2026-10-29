"""Station 11 — a StateGraph for the topology the agent loop does not express."""

from __future__ import annotations

from langchain.agents import AgentState, create_agent
from langchain.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from citydesk.model import DeskChatModel
from citydesk.serialize import dump_message, message_text
from citydesk.tools import search_archive
from citydesk.tracing import emit, trace_scope

META = {
    "id": "graphs",
    "number": "11",
    "title": "Graphs",
    "kicker": "Conditional edges, and an agent used as a node",
    "summary": (
        "create_agent is the right loop until the topology is more than “continue until "
        "the model stops.” A StateGraph has ordinary nodes, conditional edges, and — "
        "this is the composition that matters — a compiled agent as one of those nodes. "
        "Middleware on that agent still runs. Intake routes a greeting to the copy desk "
        "and a city question to the research agent."
    ),
    "look_for": [
        "hello never calls the archive. The route is direct.",
        "A flood question takes the research edge. The agent node searches, then answers.",
        "The mermaid diagram is the graph you compiled, not a drawing of the agent loop.",
    ],
    "default_prompt": "What about the flood?",
    "accepts_prompt": True,
    "source": "citydesk/lessons/graphs.py",
}


class ShiftState(AgentState):
    route: str


def intake(state: ShiftState) -> dict:
    text = message_text(state["messages"][-1]).lower()
    words = ("flood", "harbor", "tram", "market", "heat", "ferry", "museum", "fire", "dredg", "corniche", "pier")
    route = "research" if any(word in text for word in words) else "direct"
    emit("graph:intake", route)
    return {"route": route}


def direct(state: ShiftState) -> dict:
    del state
    return {"messages": [AIMessage(content="Copy desk received it. No archive pull for a greeting.")]}


def pick(state: ShiftState) -> str:
    return state["route"]


def _compile():
    research = create_agent(
        model=DeskChatModel(),
        tools=[search_archive],
        system_prompt="You research Marsa. Search the archive before you answer.",
        name="research",
    )
    graph = (
        StateGraph(ShiftState)
        .add_node("intake", intake)
        .add_node("research", research)
        .add_node("direct", direct)
        .add_edge(START, "intake")
        .add_conditional_edges("intake", pick, ["research", "direct"])
        .add_edge("research", END)
        .add_edge("direct", END)
        .compile()
    )
    return graph


def run(prompt: str | None = None) -> dict:
    question = (prompt or META["default_prompt"]).strip()
    graph = _compile()
    try:
        diagram = graph.get_graph().draw_mermaid()
    except Exception as exc:  # drawing is optional; the routes are the lesson
        diagram = f"flowchart LR\n  intake --> research\n  intake --> direct\n  %% {exc}"
    routes = [
        _run(graph, question),
        _run(graph, "hello"),
    ]
    return {
        "headline": f"“{question}” took the {routes[0]['route']} desk.",
        "sections": [
            {
                "label": "Two inputs, one graph",
                "body": "Intake is ordinary Python. Research is a create_agent graph dropped in as a node.",
                "messages": [],
                "trace": [],
                "routes": routes,
                "diagram": diagram,
            }
        ],
    }


def _run(graph, text: str) -> dict:
    with trace_scope() as events:
        result = graph.invoke(
            {"messages": [{"role": "user", "content": text}], "route": ""},
            {"recursion_limit": 20},
        )
    reply = result["messages"][-1]
    return {
        "input": text,
        "route": result["route"],
        "reply": message_text(reply)[:400],
        "messages": [dump_message(message) for message in result["messages"]],
        "trace": list(events),
    }
