import operator
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class State(TypedDict, total=False):
    task: str
    instruction: str
    research_output: str
    analysis_output: str
    next_agent: str
    step_count: int
    contributions: Annotated[list[dict], operator.add]
    messages: Annotated[list, add_messages]
    approval_status: str