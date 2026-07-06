from __future__ import annotations

from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class HelpfulnessState(TypedDict):
    messages: Annotated[list, add_messages]
    helpfulness_attempts: int
    helpfulness_feedback: str
    is_helpful: bool
