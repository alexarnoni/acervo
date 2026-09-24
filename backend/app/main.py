from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import queries

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "https://alexarnoni.com,https://spotify.alexarnoni.com,http://localhost:8081"
    ).split(",")
    if o.strip()
]
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
CACHE_TTL = 3600  # dados historicos, quase estaticos

app = FastAPI(title="Spotify Analytics API", version="1.0.0", docs_url=None, redoc_url=None)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["GET"], allow_headers=[])

_hits: dict[str, deque] = defaultdict(deque)
_hits_lock = Lock()
_cache: dict = {}


@app.middleware("http")
async def rate_limit(request: Request, call_next):
    """Limite simples por IP (janela de 60s). O nginx tambem aplica limit_req."""
    if request.url.path.startswith("/api"):
        ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "?")
        now = time.monotonic()
        with _hits_lock:
            q = _hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= RATE_LIMIT:
                return JSONResponse(
                    {"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "60"}
                )
            q.append(now)
    return await call_next(request)


def cached(fn, *args):
    key = (fn.__name__, args)
    hit = _cache.get(key)
    if hit and time.monotonic() - hit[0] < CACHE_TTL:
        return hit[1]
    value = fn(*args)
    _cache[key] = (time.monotonic(), value)
    return value


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/summary")
def api_summary():
    return cached(queries.summary)


@app.get("/api/top-artists")
def api_top_artists(limit: int = Query(15, ge=1, le=50)):
    return cached(queries.top_artists, limit)


@app.get("/api/top-tracks")
def api_top_tracks(limit: int = Query(12, ge=1, le=50)):
    return cached(queries.top_tracks, limit)


@app.get("/api/by-year")
def api_by_year():
    return cached(queries.by_year)


@app.get("/api/by-hour")
def api_by_hour():
    return cached(queries.by_hour)


@app.get("/api/by-weekday")
def api_by_weekday():
    return cached(queries.by_weekday)


@app.get("/api/heatmap")
def api_heatmap():
    return cached(queries.heatmap)


@app.get("/api/dominant-artist-per-year")
def api_dominant():
    return cached(queries.dominant_artist_per_year)


@app.get("/api/diversity-per-year")
def api_diversity():
    return cached(queries.diversity_per_year)


@app.get("/api/discovery")
def api_discovery(artists: int = Query(15, ge=1, le=50)):
    return cached(queries.discovery, artists)


@app.get("/api/obsession-days")
def api_obsession(limit: int = Query(12, ge=1, le=50)):
    return cached(queries.obsession_days, limit)


@app.get("/api/skip-rate")
def api_skip_rate(limit: int = Query(20, ge=1, le=50)):
    return cached(queries.skip_rate, limit)
