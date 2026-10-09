"""The Quizzr API server: the FastAPI app that uvicorn runs.

It wires everything together: CORS, a log line per request, the solo questions endpoint, a
health check, the multiplayer and daily-challenge routes, and (in the single-service deploy)
the built React app.

Run locally:  cd backend  then  uvicorn main:app --reload --port 8000 --no-access-log
(the app writes its own structured request log below; uvicorn's access log would only
duplicate it, and it records full URLs)
"""

import os
import time
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

import logs
from daily import router as daily_router
from multiplayer import router as multiplayer_router
from ratelimit import RateLimiter, limited
from trivia import TriviaError, fetch_questions, parse_categories

logs.configure()
app = FastAPI(title="Quizzr API")

# Which websites may call this API from a browser. In development and in the single-service
# deploy the page comes from this same server, so anything goes; when the frontend is hosted
# separately, set ALLOWED_ORIGINS to its address (comma-separated for several).
# A bare host name (Render hands one over as "quizzr.onrender.com") means its https:// address.
allowed_origins = [
    o if o == "*" or "://" in o else f"https://{o}"
    for o in (part.strip().rstrip("/") for part in os.environ.get("ALLOWED_ORIGINS", "*").split(","))
    if o
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Quizzr-Token"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """One structured line per API request: what, how it went, and how long it took."""
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logs.log_event("request_failed", level=40, method=request.method, path=request.url.path)
        raise
    if request.url.path.startswith("/api/") and request.url.path != "/api/health":
        logs.log_event(
            "request",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            ms=round((time.perf_counter() - started) * 1000),
        )
    return response


# Each quiz costs a call to Open Trivia DB, which only allows one per IP every 5 seconds,
# so one visitor hammering Generate would slow everyone down
questions_limit = RateLimiter(limit=20, window=60)


# Returns questions to the frontend, e.g. /api/questions?amount=10&category=9&difficulty=easy&type=multiple
# (category can list several, comma-separated: category=22,23)
@app.get("/api/questions", dependencies=[Depends(limited(questions_limit))])
def get_questions(amount: int = 10, category: str = "all", difficulty: str = "all", type: str = "all", refill: bool = False):
    # Which categories people choose, to learn which are popular (nothing about who chose them).
    # The browser topping up its offline pack (refill=true) isn't a round anyone chose.
    if not refill:
        logs.log_event("round_requested", mode="solo", categories=parse_categories(category) or ["any"], amount=amount)
    try:
        return fetch_questions(amount, category, difficulty, type)
    except TriviaError as e:
        logs.log_event("trivia_error", level=30, message=str(e))
        return JSONResponse({"error": str(e)}, status_code=502)


# Used by the hosting service to check the server is up
@app.get("/api/health")
def health():
    return {"ok": True}


app.include_router(multiplayer_router)
app.include_router(daily_router)


# In the single-service deploy the built React app (npm run build) is served by this same
# server. Must be mounted last so /api routes win. When the frontend is hosted as its own
# static site there's no dist folder here, and this API runs on its own.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
