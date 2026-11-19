import asyncio
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from app.observability import init_observability, trace_config
init_observability()

from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from app.graph import build_graph


async def main():
    async with AsyncRedisSaver.from_conn_string(os.environ["REDIS_URL"]) as saver:
        await saver.asetup()
        graph = build_graph(saver)

        thread_id = str(uuid.uuid4())
        cfg = trace_config(job_id=thread_id, thread_id=thread_id)

        out = await graph.ainvoke(
            {"task": "Investigá el precio actual del dólar blue en Argentina y calculá cuánto sería 1500 USD en pesos.",
             "step_count": 0},
            cfg,
        )
        print("ANÁLISIS:", out["analysis_output"])
        print("PASOS:", out["step_count"])

        snapshot = await graph.aget_state(cfg)
        print("Estado recuperado desde Redis, siguiente nodo:", snapshot.next)
        print("thread_id:", thread_id)


asyncio.run(main())