from __future__ import annotations

import os
from threading import BoundedSemaphore
from contextlib import contextmanager

from psycopg2.extras import RealDictCursor
from psycopg2.pool import ThreadedConnectionPool

_POOL_SIZE = 5
_slots = BoundedSemaphore(_POOL_SIZE)  # getconn() falha se o pool esgotar; aqui as requisicoes esperam
_pool: ThreadedConnectionPool | None = None


def _get_pool() -> ThreadedConnectionPool:
    global _pool
    if _pool is None:
        url = os.environ["DATABASE_URL"]
        _pool = ThreadedConnectionPool(1, _POOL_SIZE, url, options="-c default_transaction_read_only=on")
    return _pool


@contextmanager
def cursor():
    """Cursor de somente leitura vindo do pool."""
    with _slots:
        pool = _get_pool()
        conn = pool.getconn()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                yield cur
            conn.rollback()
        finally:
            pool.putconn(conn)


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def fetch_one(sql: str, params: tuple = ()) -> dict:
    with cursor() as cur:
        cur.execute(sql, params)
        return dict(cur.fetchone())
