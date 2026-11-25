from langgraph.types import interrupt

from app.state import State


def approval_node(state: State) -> dict:
    """Pausa el grafo hasta recibir aprobación humana externa."""
    decision = interrupt({
        "action": "enviar_reporte",
        "reason": "Acción con efecto externo: envío del análisis final.",
        "report": state.get("analysis_output"),
    })

    # `decision` es lo que llega con Command(resume=...)
    approved = bool(decision.get("approved")) if isinstance(decision, dict) else bool(decision)

    if not approved:
        return {
            "approval_status": "REJECTED",
            "messages": [("assistant", "[approval] Envío rechazado por el humano.")],
        }

    # Efecto secundario real (acá simulado)
    print(f"[ENVIO] Reporte enviado:\n{state.get('analysis_output')}")
    return {
        "approval_status": "APPROVED",
        "messages": [("assistant", "[approval] Reporte aprobado y enviado.")],
    }