from langgraph.graph import StateGraph, START, END

from app.state import State
from app.supervisor import supervisor_node
from app.research_agent import research_node
from app.analyst_agent import analyst_node
from app.hitl import approval_node


def route(state: State) -> str:
    return state["next_agent"]


def build_graph(checkpointer):
    g = StateGraph(State)
    g.add_node("supervisor", supervisor_node)
    g.add_node("researcher", research_node)
    g.add_node("analyst", analyst_node)
    g.add_node("approval", approval_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route,
        {"researcher": "researcher", "analyst": "analyst", "FINISH": "approval"},
    )
    g.add_edge("researcher", "supervisor")
    g.add_edge("analyst", "supervisor")
    g.add_edge("approval", END)

    return g.compile(checkpointer=checkpointer)