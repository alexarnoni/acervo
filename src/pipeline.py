"""End-to-end pipeline: ingest raw JSONs, transform into star schema, validate, write CSVs."""

import json
import logging
from pathlib import Path

from ingest import load_raw_streams
from transform import build_star_schema
from validate import build_quality_report, write_quality_report

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
QUALITY_REPORT_PATH = PROCESSED_DIR / "data_quality_report.md"


def run() -> None:
    """Run the full pipeline from raw JSON files to processed CSVs and a quality report."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw = load_raw_streams(RAW_DIR)
    tables = build_star_schema(raw)

    fact = tables["fact_streams"]
    dim_artist = tables["dim_artist"]
    dim_track = tables["dim_track"]
    dim_date = tables["dim_date"]
    podcasts = tables["podcasts"]
    audiobooks = tables["audiobooks"]

    fact.to_csv(PROCESSED_DIR / "fact_streams.csv", index=False)
    dim_artist.to_csv(PROCESSED_DIR / "dim_artist.csv", index=False)
    dim_track.to_csv(PROCESSED_DIR / "dim_track.csv", index=False)
    dim_date.to_csv(PROCESSED_DIR / "dim_date.csv", index=False)
    logger.info("Wrote star schema CSVs to %s", PROCESSED_DIR)
    tables["anomalies"]["candidates"].to_csv(PROCESSED_DIR / "anomaly_candidates.csv", index=False)
    site_data = PROJECT_ROOT / "frontend" / "data"
    site_data.mkdir(parents=True, exist_ok=True)
    (site_data / "anomalies.json").write_text(json.dumps(tables["anomalies"]["summary"]), encoding="utf-8")

    report = build_quality_report(
        raw_count=len(raw),
        music_count=tables["music_raw_count"],
        podcast_count=len(podcasts),
        audiobook_count=len(audiobooks),
        fact=fact,
        dim_artist=dim_artist,
        dim_track=dim_track,
    )
    write_quality_report(report, QUALITY_REPORT_PATH)

    logger.info("Pipeline complete.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
