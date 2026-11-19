import argparse
import asyncio
import time

import httpx

BASE = "http://localhost:8000"
TASK = ("Investigá el precio actual del dólar blue en Argentina y "
        "calculá cuánto sería 1500 USD en pesos.")


async def run_one(client: httpx.AsyncClient, i: int, stagger: float) -> dict:
    await asyncio.sleep(i * stagger)
    t0 = time.perf_counter()
    r = await client.post("/tasks", json={"task": TASK})
    job_id = r.json()["job_id"]
    t_post = time.perf_counter() - t0

    # Polling hasta pausa o fallo
    while True:
        job = (await client.get(f"/tasks/{job_id}")).json()
        if job["status"] in ("WAITING_APPROVAL", "FAILED", "DONE"):
            break
        await asyncio.sleep(2)
    t_pause = time.perf_counter() - t0

    if job["status"] == "WAITING_APPROVAL":
        await client.post(f"/tasks/{job_id}/approve", json={"approved": True})
        while True:
            job = (await client.get(f"/tasks/{job_id}")).json()
            if job["status"] in ("FAILED", "DONE"):
                break
            await asyncio.sleep(2)
    total = time.perf_counter() - t0

    return {"i": i, "job_id": job_id, "status": job["status"],
            "post_s": round(t_post, 3), "hasta_pausa_s": round(t_pause, 1),
            "total_s": round(total, 1), "error": job.get("error")}


async def main(n: int, stagger: float):
    async with httpx.AsyncClient(base_url=BASE, timeout=30) as client:
        res = await asyncio.gather(*(run_one(client, i, stagger) for i in range(n)))
    for r in res:
        print(r)
    ok = sum(r["status"] == "DONE" for r in res)
    print(f"\nTerminaron OK: {ok}/{n}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=5)
    ap.add_argument("--stagger", type=float, default=0.0,
                    help="segundos entre lanzamientos (0 = concurrencia real)")
    a = ap.parse_args()
    asyncio.run(main(a.n, a.stagger))