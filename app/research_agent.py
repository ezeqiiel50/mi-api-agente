from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent
from app.llm import get_llm, text_of
from app.state import State

_agent = create_react_agent(
    get_llm(),
    tools=[TavilySearch(max_results=4)],
    prompt=(
        "Sos un investigador. Tu único trabajo es buscar información "
        "actual y relevante usando la herramienta de búsqueda. "
        "Devolvé datos concretos (cifras, fechas, fuentes). "
        "NO analices ni concluyas: eso lo hace otro agente."
    ),
)

async def research_node(state: State) -> dict:
    result = await _agent.ainvoke({"messages": [("user", state["instruction"])]})
    output = text_of(result["messages"][-1].content)
    return {
        "research_output": output,
        "contributions": [{"agent": "researcher", "step": state["step_count"], "content": output}],
        "messages": [("assistant", f"[researcher] {output}")],
    }