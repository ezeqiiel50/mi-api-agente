import os
from dotenv import load_dotenv

load_dotenv()


def init_observability() -> bool:
    """Devuelve True si LangSmith está activo."""
    enabled = (
        os.getenv("LANGSMITH_TRACING", "").lower() == "true"
        and bool(os.getenv("LANGSMITH_API_KEY"))
    )
    if enabled:
        os.environ.setdefault("LANGSMITH_PROJECT", "pre-entrega-7")
        print(f"[observability] LangSmith activo, proyecto: {os.environ['LANGSMITH_PROJECT']}")
    else:
        print("[observability] LangSmith DESACTIVADO (falta LANGSMITH_API_KEY o TRACING=true)")
    return enabled


def trace_config(job_id: str, thread_id: str) -> dict:
    """Config de LangGraph con metadatos para filtrar trazas en LangSmith."""
    return {
        "configurable": {"thread_id": thread_id},
        "run_name": "multi_agent_job",
        "tags": ["pre-entrega-7", "api"],
        "metadata": {"job_id": job_id},
    }