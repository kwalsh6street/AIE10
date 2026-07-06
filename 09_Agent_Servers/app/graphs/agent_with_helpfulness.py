from __future__ import annotations

import os
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from langgraph.graph import END, START, StateGraph

from app.graphs.simple_agent import graph as simple_agent_graph
from app.models import get_chat_model
from app.state import HelpfulnessState

MAX_RETRIES = 2

DEFAULT_JUDGE_MODEL = "gpt-5.4-mini"

JUDGE_PROMPT = """You are a helpfulness judge. Evaluate whether the assistant's response is helpful, accurate, and complete given the user's question.

User question:
{question}

Assistant response:
{response}

Consider:
- Does the response directly address the user's question?
- Is the information accurate and relevant?
- Is the response complete (not missing key information)?
- Does the response cite sources when appropriate?

Respond with structured output indicating whether the response is helpful and provide brief feedback."""


class HelpfulnessVerdict(BaseModel):
    is_helpful: bool = Field(description="Whether the response is helpful, accurate, and complete")
    feedback: str = Field(description="Brief feedback on what could be improved, if anything")


def _get_judge_model():
    judge_model_name = os.getenv("JUDGE_MODEL", DEFAULT_JUDGE_MODEL)
    return get_chat_model(judge_model_name, temperature=0)


def agent_node(state: HelpfulnessState) -> dict:
    attempts = state.get("helpfulness_attempts", 0)

    messages = list(state.get("messages", []))

    if attempts > 0:
        feedback = state.get("helpfulness_feedback", "")
        messages = messages + [
            SystemMessage(
                content=(
                    f"Your previous response was judged not helpful. "
                    f"Feedback: {feedback} "
                    f"Please try again and provide a better response."
                )
            )
        ]

    result = simple_agent_graph.invoke({"messages": messages})

    return {
        "messages": result["messages"],
        "helpfulness_attempts": attempts + 1,
    }


def helpfulness_check_node(state: HelpfulnessState) -> dict:
    messages = state.get("messages", [])

    human_messages = [m for m in messages if isinstance(m, HumanMessage)]
    ai_messages = [m for m in messages if isinstance(m, AIMessage) and m.content]

    if not human_messages or not ai_messages:
        return {"is_helpful": True, "helpfulness_feedback": ""}

    question = human_messages[0].content
    response = ai_messages[-1].content

    judge = _get_judge_model().with_structured_output(HelpfulnessVerdict)
    verdict = judge.invoke(
        JUDGE_PROMPT.format(question=question, response=response)
    )

    return {
        "is_helpful": verdict.is_helpful,
        "helpfulness_feedback": verdict.feedback,
    }


def should_retry(state: HelpfulnessState) -> Literal["agent", "__end__"]:
    if state.get("is_helpful", True):
        return END

    attempts = state.get("helpfulness_attempts", 0)
    if attempts >= MAX_RETRIES + 1:
        return END

    return "agent"


builder = StateGraph(HelpfulnessState)
builder.add_node("agent", agent_node)
builder.add_node("helpfulness_check", helpfulness_check_node)
builder.add_edge(START, "agent")
builder.add_edge("agent", "helpfulness_check")
builder.add_conditional_edges("helpfulness_check", should_retry, {"agent": "agent", END: END})

graph = builder.compile()
