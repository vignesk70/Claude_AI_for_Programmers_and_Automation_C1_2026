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
   **`app/api/routes/health.py`,  the decorator `@router.get("/health", response_model=HealthResponse)` registers the path `/health` as an HTTP GET endpoint. 

2. Which file connects the route to the FastAPI application?
   **its a chain:**
   - **`app/api/health.py`,**  defines the output of the route.
   - **`app/api/router.py`,** — `api_router.include_router(health_router)` adds the health route into the API router.
   - **`app/main.py`, line 10** — `app.include_router(api_router)` consolidates routers onto the `FastAPI` application instance.
   The request is flows: `main.py → router.py → health.py`.

3. Where is the shape of the response defined?
   **`app/schemas/common.py`, 
   
   the `HealthResponse` Pydantic `BaseModel` defines the response shape: 
   a single field `status: Literal["ok"]` with a default value of `"ok"`. 
   The route references it via `response_model=HealthResponse` in `health.py`, which tells FastAPI to validate and serialize the response against that schema.

4. Does this endpoint need Claude? Why or why not?
   **No.** 
   
   The endpoint returns a static, hard-coded `{"status": "ok"}` response. 
   
5. What would have to change if this route needed to become `/api/health`?
   - In `app/api/router.py`, add a prefix: `api_router.include_router(health_router, prefix="/api")`. 

## Deliverable

Be ready to explain the full request flow in approximately one minute.

Do not add Claude to this endpoint.
