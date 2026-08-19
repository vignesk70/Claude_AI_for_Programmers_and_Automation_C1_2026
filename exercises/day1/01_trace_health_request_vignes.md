# Exercise 01 — Trace a FastAPI Request

## Goal

Trace one ordinary HTTP request through the backend.

## Time

Approximately 20–25 minutes.

## Starting point

The application is running and exposes:

```text
GET /health
```

## Task

Use Postman and the project source to determine how the request moves through the application.

Record:

```text
HTTP method:
Path:
HTTP status:
Response body:

FastAPI application file:
Application router file:
Route file:
Response model:
Route handler function:
```

Then draw the request flow from Postman to the returned JSON.

## Questions to discuss

1. Which file decides that `/health` is a GET endpoint?
   **`app/api/routes/health.py`, line 7** — the decorator `@router.get("/health", response_model=HealthResponse)` registers the path `/health` as an HTTP GET endpoint. The `get` method on the `APIRouter` instance is what binds both the URL and the HTTP verb.

2. Which file connects the route to the FastAPI application?
   **Two files form a chain:**
   - **`app/api/router.py`, line 6** — `api_router.include_router(health_router)` aggregates the health route into the central API router.
   - **`app/main.py`, line 10** — `app.include_router(api_router)` mounts the aggregated router onto the `FastAPI` application instance.
   The request therefore flows: `main.py → router.py → health.py`.

3. Where is the shape of the response defined?
   **`app/schemas/common.py`, lines 5–6** — the `HealthResponse` Pydantic `BaseModel` defines the response shape: a single field `status: Literal["ok"]` with a default value of `"ok"`. The route references it via `response_model=HealthResponse` in `health.py`, which tells FastAPI to validate and serialize the response against that schema.

4. Does this endpoint need Claude? Why or why not?
   **No.** The endpoint returns a static, hard-coded `{"status": "ok"}` response. It performs no AI inference, no prompt construction, and no LLM call. Its purpose is purely operational — a deterministic health-check used by monitoring tools and load balancers to verify the service is running. Adding Claude here would introduce unnecessary latency, cost, and a potential point of failure for a trivially simple response.

5. What would have to change if this route needed to become `/api/health`?
   **Two options:**
   - **Option A (direct):** Change the decorator in `app/api/routes/health.py` line 7 from `@router.get("/health", ...)` to `@router.get("/api/health", ...)`. This works but hard-codes the prefix inside the route file.
   - **Option B (cleaner, modular):** In `app/api/router.py`, line 6, add a prefix: `api_router.include_router(health_router, prefix="/api")`. The route file stays unaware of the prefix, which is better for modularity and makes it easy to apply the prefix to all routes in one place.

## Deliverable

Be ready to explain the full request flow in approximately one minute.

Do not add Claude to this endpoint.
