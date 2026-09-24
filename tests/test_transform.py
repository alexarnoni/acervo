"""Tests for the transform pipeline: cleaning, splitting, and aggregation."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from transform import (  # noqa: E402
    drop_borrowed_listening,
    build_dim_artist,
    build_fact_streams,
    clean_music_streams,
    split_content_types,
)


def make_raw_row(**overrides) -> dict:
    """Build one raw streaming event record with sensible defaults, overridable per test."""
    row = {
        "ts": "2020-06-15T10:00:00Z",
        "platform": "windows",
        "ms_played": 200000,
        "conn_country": "BR",
        "master_metadata_track_name": "Test Track",
        "master_metadata_album_artist_name": "Test Artist",
        "master_metadata_album_album_name": "Test Album",
        "spotify_track_uri": "spotify:track:abc123",
        "episode_name": None,
        "episode_show_name": None,
        "audiobook_title": None,
        "reason_start": "trackdone",
        "reason_end": "trackdone",
        "shuffle": False,
        "skipped": False,
    }
    row.update(overrides)
    return row


@pytest.fixture
def sample_raw() -> pd.DataFrame:
    rows = [
        make_raw_row(),
        make_raw_row(ts="2020-06-16T10:00:00Z", master_metadata_track_name="Another Track"),
        make_raw_row(episode_name="Ep 1", episode_show_name="Show", master_metadata_track_name=None),
        make_raw_row(ms_played=500, ts="2020-06-17T10:00:00Z"),  # noise, below threshold
    ]
    return pd.DataFrame(rows)


def test_split_content_types_separates_music_and_podcasts(sample_raw):
    music, podcasts, audiobooks = split_content_types(sample_raw)
    assert len(music) == 3
    assert len(podcasts) == 1
    assert len(audiobooks) == 0


def test_clean_music_streams_drops_noise_below_threshold(sample_raw):
    music, _, _ = split_content_types(sample_raw)
    cleaned = clean_music_streams(music)
    assert (cleaned["ms_played"] >= 1000).all()
    assert len(cleaned) == 2


def test_clean_music_streams_deduplicates_exact_rows():
    rows = [make_raw_row(), make_raw_row()]
    music, _, _ = split_content_types(pd.DataFrame(rows))
    cleaned = clean_music_streams(music)
    assert len(cleaned) == 1


def test_clean_music_streams_drops_out_of_range_dates():
    rows = [make_raw_row(), make_raw_row(ts="2030-01-01T00:00:00Z")]
    music, _, _ = split_content_types(pd.DataFrame(rows))
    cleaned = clean_music_streams(music)
    assert len(cleaned) == 1


def test_build_dim_artist_aggregates_hours_correctly():
    rows = [
        make_raw_row(ms_played=3_600_000, ts="2020-06-15T10:00:00Z"),
        make_raw_row(ms_played=1_800_000, ts="2020-06-16T10:00:00Z"),
    ]
    music, _, _ = split_content_types(pd.DataFrame(rows))
    cleaned = clean_music_streams(music)
    dim_artist = build_dim_artist(cleaned)

    assert len(dim_artist) == 1
    row = dim_artist.iloc[0]
    assert row["total_plays"] == 2
    assert row["total_hours"] == pytest.approx(1.5, abs=0.01)


def test_build_fact_streams_has_no_orphan_keys(sample_raw):
    music, _, _ = split_content_types(sample_raw)
    cleaned = clean_music_streams(music)
    dim_artist = build_dim_artist(cleaned)
    fact = build_fact_streams(cleaned)

    assert fact["artist_id"].isin(dim_artist["artist_id"]).all()
    assert (fact["ms_played"] >= 1000).all()


def test_drop_borrowed_listening_only_inside_window_and_artist():
    rows = [
        ("2018-12-05T10:00:00Z", "Ariana Grande"),  # emprestimo: sai
        ("2018-12-05T10:00:00Z", "Arctic Monkeys"),  # mesmo dia, outro artista: fica
        ("2020-01-01T10:00:00Z", "Ariana Grande"),  # fora da janela: fica
        ("2019-02-10T10:00:00Z", "Henrique & Juliano"),  # sai
    ]
    df = pd.DataFrame(rows, columns=["ts", "master_metadata_album_artist_name"])
    out = drop_borrowed_listening(df)
    assert list(out["master_metadata_album_artist_name"]) == ["Arctic Monkeys", "Ariana Grande"]
