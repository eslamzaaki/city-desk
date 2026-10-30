"""The counter: retrieval, personal memory, review, and middleware in one agent."""

from __future__ import annotations

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, ModelRequest, PIIMiddleware, dynamic_prompt
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore

from citydesk.middleware import TraceMiddleware
from citydesk.model import resolve_model
from citydesk.personal import shop_personal
from citydesk.schemas import ShopContext
from citydesk.shop import customer_name
from citydesk.tools import (
    lookup_order,
    recall_preferences,
    request_refund,
    save_feedback,
    save_preference,
    search_handbook,
    who_is_shopping,
)

COUNTER_RULES = (
    "Check the handbook before you state a shop rule. "
    "Look up this customer's order before you decide a return. "
    "Request a refund only when they ask for one. "
    "Never use another customer's memory. "
    "Choose the tool from what the sentence is about, not from a form. "
    "A preference customizes answers for this customer only: language, how short to be, their size, their name, or what they want next. "
    "Call save_preference. It updates their profile and never changes the agent for anyone else. "
    "Feedback improves the agent for every customer: a wrong shop answer, a missing shop fact, or a step the agent cannot do. "
    "Call save_feedback with scope shared. "
    "The corrected answer is the fact or the missing capability every customer needs, not an apology. "
    "Do not file feedback to customize one customer. Do not save a preference to change answers for everyone. "
    "Use scope personal only when they say the correction is for them alone, such as their own gifts. "
    "Ask for a rating from 1 to 5 only when they are judging a reply and did not give one. "
    "Keep a training example only when they agree, and that agreement does not train a model."
)


@dynamic_prompt
def counter_prompt(request: ModelRequest) -> str:
    context = request.runtime.context
    customer_id = getattr(context, "customer_id", "")
    name = customer_name(customer_id) if customer_id else "the customer"
    return f"You are the assistant at the Lumen counter, with {name}. {COUNTER_RULES}"


def build_desk():
    """Compile the counter agent. The saver and the store live as long as this object does."""

    model, label = resolve_model()
    agent = create_agent(
        model=model,
        tools=[
            search_handbook,
            lookup_order,
            save_preference,
            recall_preferences,
            who_is_shopping,
            request_refund,
            save_feedback,
        ],
        system_prompt="You work the Lumen counter.",
        middleware=[
            PIIMiddleware("email", strategy="redact", apply_to_input=True),
            PIIMiddleware("loyalty_card", detector=r"LC-\d{4}", strategy="mask", apply_to_input=True),
            counter_prompt,
            shop_personal.middleware,
            TraceMiddleware(),
            HumanInTheLoopMiddleware(interrupt_on={"request_refund": True}),
        ],
        context_schema=ShopContext,
        checkpointer=InMemorySaver(),
        store=InMemoryStore(),
    )
    return agent, label
