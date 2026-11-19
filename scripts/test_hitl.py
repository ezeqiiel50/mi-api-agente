import asyncio
import os
import uuid

from dotenv import load_dotenv
load_dotenv()

from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from langgraph.types import Command

from app.observability import init_observability, trace_config
from app.graph import build_graph

init_observability()


async def main():
    async with AsyncRedisSaver.from_conn_string(os.environ["REDIS_URL"]) as saver:
        await saver.asetup()
        graph = build_graph(saver)

        thread_id = str(uuid.uuid4())
        cfg = trace_config(job_id=thread_id, thread_id=thread_id)

        # 1) Primera ejecución: debe frenar en el nodo approval
        out = await graph.ainvoke(
            {"task": "Investigá el precio actual del dólar blue en Argentina y calculá cuánto sería 1500 USD en pesos.",
             "step_count": 0},
            cfg,
        )
        snap = await graph.aget_state(cfg)
        print("Siguiente nodo:", snap.next)            # esperado: ('approval',)
        print("Interrupción:", snap.tasks[0].interrupts[0].value if snap.tasks else None)

        input("\nEl grafo está PAUSADO. Presioná Enter para APROBAR...")

        # 2) Reanudar con la decisión humana
        out = await graph.ainvoke(Command(resume={"approved": True}), cfg)
        print("Estado final:", out.get("approval_status"))

        snap = await graph.aget_state(cfg)
        print("Siguiente nodo:", snap.next)            # esperado: ()


asyncio.run(main())