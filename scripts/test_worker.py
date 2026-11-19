import asyncio
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

import redis.asyncio as aioredis
from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from app.observability import init_observability
from app.graph import build_graph
from app.worker import run_job, resume_job, get_job, save_job

init_observability()


async def main():
    r = aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    async with AsyncRedisSaver.from_conn_string(os.environ["REDIS_URL"]) as saver:
        await saver.asetup()
        graph = build_graph(saver)

        job_id = str(uuid.uuid4())
        await save_job(r, job_id, status="PENDING")
        print("1)", (await get_job(r, job_id))["status"])

        await run_job(graph, r, job_id,
                      "Investigá el precio actual del dólar blue en Argentina y calculá cuánto sería 1500 USD en pesos.")
        job = await get_job(r, job_id)
        print("2)", job["status"], "| pendiente:", bool(job.get("pending_approval")))

        await resume_job(graph, r, job_id, approved=True)
        job = await get_job(r, job_id)
        print("3)", job["status"], "|", job["result"]["approval_status"])

        # Camino de error: forzamos una excepción
        bad = str(uuid.uuid4())
        await save_job(r, bad, status="PENDING")
        await run_job(None, r, bad, "x")   # graph=None -> AttributeError
        print("4)", (await get_job(r, bad))["status"], "|", (await get_job(r, bad))["error"])

    await r.aclose()


asyncio.run(main())