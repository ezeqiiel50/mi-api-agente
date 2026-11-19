# API Multi-Agente (Pre-entrega 7)

API REST (FastAPI) que expone un sistema multi-agente (supervisor, investigador, analista) construido con LangGraph. Ejecuta tareas en segundo plano, persiste el estado en Redis, traza todo en LangSmith y exige aprobación humana antes de la acción con efecto externo.

## Arquitectura

- `app/main.py`: endpoints `POST /tasks`, `GET /tasks/{id}`, `POST /tasks/{id}/approve`
- `app/graph.py`: grafo LangGraph con checkpointer de Redis
- `app/worker.py`: ejecución en segundo plano y estados del job (PENDING, RUNNING, WAITING_APPROVAL, DONE, FAILED)
- `app/hitl.py`: nodo de aprobación humana (`interrupt`)
- `app/observability.py`: configuración de LangSmith

## Requisitos

Python 3.12+, Docker, y claves de Google AI Studio, Tavily y LangSmith.

## Puesta en marcha

```bash
git clone [URL_DEL_REPO] && cd mi-api-agente
cp .env.example .env        # completar las claves
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d redis  # Redis Stack
uvicorn app.main:app --port 8000
```

Con Docker completo: `docker compose up --build`.

## Uso

```bash
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" \
  -d '{"task":"Investigá el precio del dólar blue y calculá 1500 USD en pesos"}'
curl localhost:8000/tasks/<job_id>
curl -X POST localhost:8000/tasks/<job_id>/approve \
  -H "Content-Type: application/json" -d '{"approved": true}'
```

## Flujo Human-in-the-loop

Cuando el supervisor decide terminar, el grafo pasa por el nodo `approval`, que se pausa con `interrupt()`. El job queda en `WAITING_APPROVAL` hasta que se llama a `/approve`. Con `approved: false` el reporte no se envía.

## Manejo de errores

Cualquier excepción en segundo plano deja el job en `FAILED` con el motivo en el campo `error`, así el cliente no queda haciendo polling indefinido. [Pegar acá la salida del paso `4) FAILED` de test_worker.]

## Prueba de carga (5 peticiones concurrentes)

```bash
python -m scripts.load_test
```