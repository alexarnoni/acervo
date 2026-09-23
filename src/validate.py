"""Data quality checks over the cleaned star schema, written to a markdown report."""

import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


def check_no_negative_ms_played(fact: pd.DataFrame) -> int:
    """Return the count of rows with negative ms_played (should always be 0)."""
    count = int((fact["ms_played"] < 0).sum())
    if count:
        logger.warning("Found %d rows with negative ms_played", count)
    return count


def check_orphan_keys(fact: pd.DataFrame, dim_artist: pd.DataFrame, dim_track: pd.DataFrame) -> dict[str, int]:
    """Return counts of fact rows whose artist_id or track_id has no matching dimension row."""
    orphan_artists = int((~fact["artist_id"].isin(dim_artist["artist_id"])).sum())
    orphan_tracks = int((~fact["track_id"].isin(dim_track["track_id"])).sum())
    if orphan_artists or orphan_tracks:
        logger.warning("Orphan keys: %d artist_id, %d track_id", orphan_artists, orphan_tracks)
    return {"orphan_artist_id": orphan_artists, "orphan_track_id": orphan_tracks}


def check_date_range(fact: pd.DataFrame, min_year: int = 2014, max_year: int = 2026) -> int:
    """Return the count of fact rows with a date_key outside the expected range."""
    years = pd.to_datetime(fact["date_key"]).dt.year
    out_of_range = int((~years.between(min_year, max_year)).sum())
    if out_of_range:
        logger.warning("Found %d rows with date_key outside %d-%d", out_of_range, min_year, max_year)
    return out_of_range


def build_quality_report(
    raw_count: int,
    music_count: int,
    podcast_count: int,
    audiobook_count: int,
    fact: pd.DataFrame,
    dim_artist: pd.DataFrame,
    dim_track: pd.DataFrame,
) -> str:
    """Assemble the markdown data quality report content."""
    negative_ms = check_no_negative_ms_played(fact)
    orphans = check_orphan_keys(fact, dim_artist, dim_track)
    out_of_range = check_date_range(fact)

    lines = [
        "# Data Quality Report",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Record counts",
        "",
        f"- Raw records ingested: {raw_count}",
        f"- Music records: {music_count}",
        f"- Podcast records (excluded from music tables): {podcast_count}",
        f"- Audiobook records (excluded from music tables): {audiobook_count}",
        f"- Clean fact_streams rows: {len(fact)}",
        f"- Records dropped as noise (ms_played < 1000) or duplicates: {music_count - len(fact)}",
        "",
        "## Validation checks",
        "",
        f"- Rows with negative ms_played: {negative_ms}",
        f"- Orphan artist_id in fact_streams: {orphans['orphan_artist_id']}",
        f"- Orphan track_id in fact_streams: {orphans['orphan_track_id']}",
        f"- Rows with date_key outside 2014-2026: {out_of_range}",
        "",
        "## Dimension sizes",
        "",
        f"- dim_artist: {len(dim_artist)} artists",
        f"- dim_track: {len(dim_track)} tracks",
    ]
    return "\n".join(lines) + "\n"


def write_quality_report(report_text: str, output_path: Path) -> None:
    """Write the quality report to disk."""
    output_path.write_text(report_text, encoding="utf-8")
    logger.info("Wrote data quality report to %s", output_path)
