"""Queries de leitura sobre o schema estrela (fact_streams, dim_artist, dim_track, dim_date)."""
from __future__ import annotations

from .db import fetch_all, fetch_one

HOURS = "SUM(f.ms_played) / 3600000.0"


def summary() -> dict:
    row = fetch_one(
        f"""
        SELECT ROUND(({HOURS})::numeric, 1)::float AS total_hours,
               COUNT(*) AS total_plays,
               COUNT(DISTINCT f.artist_id) AS unique_artists,
               COUNT(DISTINCT f.track_id) AS unique_tracks,
               ROUND(AVG(f.skipped::int)::numeric, 4)::float AS skip_rate,
               MIN(f.date_key) AS first_date,
               MAX(f.date_key) AS last_date,
               COUNT(DISTINCT f.date_key) AS active_days
        FROM fact_streams f
        """
    )
    row["total_days"] = (row["last_date"] - row["first_date"]).days + 1
    row["first_date"] = row["first_date"].isoformat()
    row["last_date"] = row["last_date"].isoformat()
    return row


def top_artists(limit: int) -> list[dict]:
    return fetch_all(
        f"""
        SELECT a.artist_name, ROUND(({HOURS})::numeric, 1)::float AS hours, COUNT(*) AS plays
        FROM fact_streams f JOIN dim_artist a USING (artist_id)
        GROUP BY a.artist_id, a.artist_name
        ORDER BY SUM(f.ms_played) DESC LIMIT %s
        """,
        (limit,),
    )


def top_tracks(limit: int) -> list[dict]:
    return fetch_all(
        f"""
        SELECT t.track_name, a.artist_name, COUNT(*) AS plays,
               ROUND(({HOURS})::numeric, 1)::float AS hours
        FROM fact_streams f
        JOIN dim_track t USING (track_id)
        JOIN dim_artist a ON a.artist_id = t.artist_id
        GROUP BY t.track_id, t.track_name, a.artist_name
        ORDER BY plays DESC, SUM(f.ms_played) DESC LIMIT %s
        """,
        (limit,),
    )


def by_year() -> list[dict]:
    return fetch_all(
        f"""
        SELECT d.year, ROUND(({HOURS})::numeric, 1)::float AS hours, COUNT(*) AS plays
        FROM fact_streams f JOIN dim_date d USING (date_key)
        GROUP BY d.year ORDER BY d.year
        """
    )


def by_hour() -> list[dict]:
    return fetch_all(
        f"""
        SELECT EXTRACT(HOUR FROM f.time)::int AS hour,
               ROUND(({HOURS})::numeric, 1)::float AS hours, COUNT(*) AS plays
        FROM fact_streams f GROUP BY 1 ORDER BY 1
        """
    )


def by_weekday() -> list[dict]:
    # ISODOW: 1 = segunda ... 7 = domingo
    return fetch_all(
        f"""
        SELECT EXTRACT(ISODOW FROM f.date_key)::int AS weekday,
               ROUND(({HOURS})::numeric, 1)::float AS hours, COUNT(*) AS plays
        FROM fact_streams f GROUP BY 1 ORDER BY 1
        """
    )


def heatmap() -> list[dict]:
    return fetch_all(
        f"""
        SELECT EXTRACT(ISODOW FROM f.date_key)::int AS weekday,
               EXTRACT(HOUR FROM f.time)::int AS hour,
               ROUND(({HOURS})::numeric, 2)::float AS hours, COUNT(*) AS plays
        FROM fact_streams f GROUP BY 1, 2 ORDER BY 1, 2
        """
    )


def dominant_artist_per_year() -> list[dict]:
    return fetch_all(
        f"""
        SELECT DISTINCT ON (d.year) d.year, a.artist_name,
               ROUND(({HOURS})::numeric, 1)::float AS hours, COUNT(*) AS plays
        FROM fact_streams f
        JOIN dim_date d USING (date_key)
        JOIN dim_artist a USING (artist_id)
        GROUP BY d.year, a.artist_id, a.artist_name
        ORDER BY d.year, SUM(f.ms_played) DESC
        """
    )


def diversity_per_year() -> list[dict]:
    return fetch_all(
        """
        SELECT d.year, COUNT(DISTINCT f.artist_id) AS unique_artists,
               COUNT(DISTINCT f.track_id) AS unique_tracks
        FROM fact_streams f JOIN dim_date d USING (date_key)
        GROUP BY d.year ORDER BY d.year
        """
    )


def discovery(artists: int) -> list[dict]:
    return fetch_all(
        """
        WITH top AS (
            SELECT artist_id, SUM(ms_played) AS ms, COUNT(*) AS plays, MIN(date_key) AS first_play
            FROM fact_streams GROUP BY artist_id ORDER BY ms DESC LIMIT %s
        )
        SELECT a.artist_name, TO_CHAR(t.first_play, 'YYYY-MM-DD') AS first_play,
               EXTRACT(YEAR FROM t.first_play)::int AS first_year,
               ROUND((t.ms / 3600000.0)::numeric, 1)::float AS hours, t.plays
        FROM top t JOIN dim_artist a USING (artist_id)
        ORDER BY t.first_play, t.ms DESC
        """,
        (artists,),
    )


def obsession_days(limit: int) -> list[dict]:
    return fetch_all(
        """
        SELECT TO_CHAR(f.date_key, 'YYYY-MM-DD') AS date, t.track_name, a.artist_name,
               COUNT(*) AS plays
        FROM fact_streams f
        JOIN dim_track t USING (track_id)
        JOIN dim_artist a ON a.artist_id = t.artist_id
        GROUP BY f.date_key, t.track_id, t.track_name, a.artist_name
        ORDER BY plays DESC, f.date_key LIMIT %s
        """,
        (limit,),
    )


def skip_rate(limit: int) -> list[dict]:
    return fetch_all(
        """
        SELECT a.artist_name, COUNT(*) AS plays, SUM(f.skipped::int) AS skips,
               ROUND(AVG(f.skipped::int)::numeric, 4)::float AS skip_rate
        FROM fact_streams f JOIN dim_artist a USING (artist_id)
        GROUP BY a.artist_id, a.artist_name
        ORDER BY plays DESC LIMIT %s
        """,
        (limit,),
    )
