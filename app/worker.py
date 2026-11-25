import json
import time
import traceback

from langgraph.types import Command

from app.observability import trace_config

JOB_TTL = 60 * 60 * 24  # 24 h


def _key(job_id: str) -> str:
    return f"job:{job_id}"


async def save_job(r, job_id: str, **fields) -> dict:
    """Mezcla `fields` con lo que ya hay guardado y persiste en Redis."""
    raw = await r.get(_key(job_id))
    job = json.loads(raw) if raw else {"job_id": job_id, "created_at": time.time()}
    job.update(fields)
    job["updated_at"] = time.time()
    await r.set(_key(job_id), json.dumps(job, ensure_ascii=False), ex=JOB_TTL)
    return job


async def get_job(r, job_id: str) -> dict | None:
    raw = await r.get(_key(job_id))
    return json.loads(raw) if raw else None


async def _finalize(graph, r, job_id: str, cfg: dict) -> None:
    """Mira el estado del grafo: ¿terminó o quedó pausado esperando aprobación?"""
    snap = await graph.aget_state(cfg)
    if snap.next:  # pausado en interrupt()
        pending = snap.tasks[0].interrupts[0].value if snap.tasks and snap.tasks[0].interrupts else None
        await save_job(r, job_id, status="WAITING_APPROVAL", pending_approval=pending)
    else:
        values = snap.values
        await save_job(
            r, job_id,
            status="DONE",
            pending_approval=None,
            result={
                "analysis": values.get("analysis_output"),
                "approval_status": values.get("approval_status"),
                "steps": values.get("step_count"),
            },
        )


async def run_job(graph, r, job_id: str, task: str) -> None:
    cfg = trace_config(job_id=job_id, thread_id=job_id)
    try:
        await save_job(r, job_id, status="RUNNING")
        await graph.ainvoke({"task": task, "step_count": 0}, cfg)
        await _finalize(graph, r, job_id, cfg)
    except Exception as e:
        traceback.print_exc()
        await save_job(r, job_id, status="FAILED", error=f"{type(e).__name__}: {e}")


async def resume_job(graph, r, job_id: str, approved: bool) -> None:
    cfg = trace_config(job_id=job_id, thread_id=job_id)
    try:
        await save_job(r, job_id, status="RUNNING", pending_approval=None)
        await graph.ainvoke(Command(resume={"approved": approved}), cfg)
        await _finalize(graph, r, job_id, cfg)
    except Exception as e:
        traceback.print_exc()
        await save_job(r, job_id, status="FAILED", error=f"{type(e).__name__}: {e}")