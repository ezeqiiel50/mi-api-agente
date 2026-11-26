from typing import Literal
from pydantic import BaseModel, Field
from app.llm import get_llm
from app.state import State

MAX_STEPS = 6

class Decision(BaseModel):
    next: Literal["researcher", "analyst", "FINISH"]
    instruction: str = Field(description="Instrucción específica y autocontenida para el agente elegido")
    reason: str

SYSTEM = """Sos el supervisor de un equipo con dos especialistas:
- researcher: busca información externa.
- analyst: calcula y analiza datos ya obtenidos.

Estado actual:
- Investigación: {research}
- Análisis: {analysis}

RÚBRICA DE VALIDACIÓN (todas deben cumplirse para elegir FINISH):
1. La investigación contiene datos concretos (cifras/fechas/fuentes), no generalidades.
2. El análisis usa esos datos y muestra resultados numéricos explícitos.
3. Ambos outputs responden a la consulta original, sin contradicciones entre sí.
4. Los órdenes de magnitud son coherentes con los datos de la investigación.

Reglas:
- Si falta investigación -> researcher.
- Si hay investigación pero no análisis -> analyst.
- Si algún output incumple la rúbrica -> reenviá al agente correspondiente
  con una instrucción que diga QUÉ corregir.
- Si todo cumple -> FINISH (en instruction poné "n/a").
Consulta original: {task}"""

_llm = get_llm().with_structured_output(Decision)

async def supervisor_node(state: State) -> dict:
    step = state.get("step_count", 0) + 1

    if step > MAX_STEPS:
        return {"next_agent": "FINISH", "step_count": step}

    d = await _llm.ainvoke([
        ("system", SYSTEM.format(
            research=state.get("research_output") or "(vacío)",
            analysis=state.get("analysis_output") or "(vacío)",
            task=state["task"],
        )),
        ("user", "Decidí cuál es el próximo paso."),
    ])
    return {
        "next_agent": d.next,
        "instruction": d.instruction,
        "step_count": step,
        "messages": [("assistant", f"[supervisor] -> {d.next}: {d.reason}")],
    }