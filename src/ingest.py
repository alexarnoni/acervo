"""Read and consolidate raw Spotify Extended Streaming History JSON files."""

import json
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

AUDIO_FILE_GLOB = "Streaming_History_Audio_*.json"


def find_audio_files(raw_dir: Path) -> list[Path]:
    """Return all audio streaming history JSON files under raw_dir, recursively."""
    files = sorted(raw_dir.rglob(AUDIO_FILE_GLOB))
    logger.info("Found %d audio history files in %s", len(files), raw_dir)
    return files


def load_json_records(path: Path) -> list[dict]:
    """Load a single Extended Streaming History JSON file as a list of records."""
    with path.open(encoding="utf-8") as f:
        records = json.load(f)
    logger.info("Loaded %d records from %s", len(records), path.name)
    return records


def load_raw_streams(raw_dir: Path) -> pd.DataFrame:
    """Read all audio history JSON files under raw_dir and concatenate into one DataFrame.

    Each row is one streaming event as recorded by Spotify, before any cleaning.
    """
    files = find_audio_files(raw_dir)
    if not files:
        raise FileNotFoundError(f"No files matching {AUDIO_FILE_GLOB} found under {raw_dir}")

    frames = [pd.DataFrame(load_json_records(f)) for f in files]
    combined = pd.concat(frames, ignore_index=True)
    logger.info("Consolidated %d total raw records from %d files", len(combined), len(files))
    return combined


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raw_dir = Path(__file__).resolve().parent.parent / "data" / "raw"
    df = load_raw_streams(raw_dir)
    logger.info("Columns: %s", list(df.columns))
    logger.info("Shape: %s", df.shape)
