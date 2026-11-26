import numexpr
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from app.llm import get_llm, text_of
from app.state import State

@tool
def calculadora(expresion: str) -> str:
    """Evalua una expresion matematica y devuelve su resultado"""
    try:
        return str(numexpr.evaluate(expresion))
    except Exception as e:
        return f"Error: {e}"

@tool
def sentimiento(texto: str) -> str:
    """Clasifica un texto como positivo, negativo o neutro."""
    pos = ["sube", "crece", "positivo", "mejora", "récord", "ganancia", "éxito"]
    neg = ["baja", "cae", "negativo", "pérdida", "crisis", "riesgo", "caída"]
    t = texto.lower()
    p, n = sum(w in t for w in pos), sum(w in t for w in neg)
    label = "positivo" if p > n else "negativo" if n > p else "neutro"
    return f"{label} (pos={p}, neg={n})"

_agent = create_react_agent(
    get_llm(),
    tools=[calculadora, sentimiento],
    prompt=(
        "Sos un analista. Recibís datos ya obtenidos y los procesás con tus "
        "herramientas (cálculos, sentimiento). No busques información nueva. "
        "Mostrá los resultados numéricos explícitamente. "
        "ATENCIÓN con los números: en formato argentino el punto separa miles "
        "y la coma separa decimales ('1.545' = mil quinientos cuarenta y cinco). "
        "Antes de usar la calculadora, convertí las cifras a formato sin separadores "
        "(1545) y verificá que el orden de magnitud del resultado sea razonable."
    ),
)

async def analyst_node(state: State) -> dict:
    prompt = (
        f"{state['instruction']}\n\n"
        f"DATOS A ANALIZAR:\n{state.get('research_output')}"
    )

    result = await _agent.ainvoke({"messages": [("user", prompt)]})

    output = text_of(result["messages"][-1].content)

    # Registrar las herramientas que realmente se ejecutaron
    tool_trace = []

    for message in result["messages"]:
        for call in getattr(message, "tool_calls", []):
            tool_trace.append(
                f"Solicitud: {call.get('name')} - {call.get('args')}"
            )

        if message.__class__.__name__ == "ToolMessage":
            tool_trace.append(
                f"Resultado: {message.name} - {text_of(message.content)}"
            )

    messages = []

    if tool_trace:
        messages.append((
            "assistant",
            "[HERRAMIENTAS DEL ANALISTA]\n" + "\n".join(tool_trace)
        ))
    else:
        messages.append((
            "assistant",
            "[ADVERTENCIA] No se registraron ejecuciones de herramientas."
        ))

    messages.append(("assistant", f"[analyst] {output}"))

    return {
        "analysis_output": output,
        "contributions": [{
            "agent": "analyst",
            "step": state["step_count"],
            "content": output
        }],
        "messages": messages,
    }
