import asyncio
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.observability import init_observability
from app.graph import build_graph
from app.worker import run_job, resume_job, get_job, save_job

init_observability()


@asynccontextmanager
async def lifespan(app: FastAPI):
    url = os.environ["REDIS_URL"]
    app.state.redis = aioredis.from_url(url, decode_responses=True)
    async with AsyncRedisSaver.from_conn_string(url) as saver:
        await saver.asetup()
        app.state.graph = build_graph(saver)
        app.state.tasks = set()  # referencias a tareas en segundo plano
        yield
    await app.state.redis.aclose()


app = FastAPI(title="API Multi-Agente", lifespan=lifespan)


class TaskIn(BaseModel):
    task: str


class ApprovalIn(BaseModel):
    approved: bool


def _spawn(app: FastAPI, coro) -> None:
    """Lanza una corrutina en segundo plano guardando la referencia
    (si no, el GC puede cancelarla a mitad de camino)."""
    t = asyncio.create_task(coro)
    app.state.tasks.add(t)
    t.add_done_callback(app.state.tasks.discard)


@app.post("/tasks", status_code=202)
async def create_task(body: TaskIn):
    job_id = str(uuid.uuid4())
    await save_job(app.state.redis, job_id, status="PENDING", task=body.task)
    _spawn(app, run_job(app.state.graph, app.state.redis, job_id, body.task))
    return {"job_id": job_id, "status": "PENDING"}


@app.get("/tasks/{job_id}")
async def read_task(job_id: str):
    job = await get_job(app.state.redis, job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    return job


@app.post("/tasks/{job_id}/approve", status_code=202)
async def approve_task(job_id: str, body: ApprovalIn):
    job = await get_job(app.state.redis, job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    if job["status"] != "WAITING_APPROVAL":
        raise HTTPException(409, f"El job está en estado {job['status']}, no espera aprobación")
    # Marcamos RUNNING ya, para que un doble clic no reanude dos veces
    await save_job(app.state.redis, job_id, status="RUNNING", pending_approval=None)
    _spawn(app, resume_job(app.state.graph, app.state.redis, job_id, body.approved))
    return {"job_id": job_id, "status": "RUNNING"}