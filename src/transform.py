"""Clean raw streaming events and build the star schema tables for Power BI."""

import hashlib
import logging

import pandas as pd

logger = logging.getLogger(__name__)

MIN_MS_PLAYED = 1000
VALID_YEAR_MIN = 2014
VALID_YEAR_MAX = 2026

# Escutas de outra pessoa (conta emprestada a uma amiga): nao representam o gosto do dono do historico.
# Cada regra remove os plays desses artistas somente dentro da janela de datas (inclusive).
BORROWED_ACCOUNT_WINDOWS = [
    (
        "2018-12-01",
        "2018-12-31",
        {"Ariana Grande"},
    ),
    (
        "2019-02-01",
        "2019-02-18",
        {"Ariana Grande", "Henrique & Juliano", "Marília Mendonça", "Maiara & Maraisa"},
    ),
]


def split_content_types(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split raw events into music, podcast, and audiobook records.

    Music rows have a non-null master_metadata_track_name. Podcast rows have a
    non-null episode_name. Audiobook rows have a non-null audiobook_title.
    """
    is_music = raw["master_metadata_track_name"].notna()
    is_podcast = raw["episode_name"].notna()
    is_audiobook = raw["audiobook_title"].notna()

    music = raw[is_music].copy()
    podcasts = raw[is_podcast & ~is_music].copy()
    audiobooks = raw[is_audiobook & ~is_music & ~is_podcast].copy()

    logger.info(
        "Split raw records: %d music, %d podcast, %d audiobook",
        len(music),
        len(podcasts),
        len(audiobooks),
    )
    return music, podcasts, audiobooks


def clean_music_streams(music: pd.DataFrame) -> pd.DataFrame:
    """Apply cleaning and validation rules to music streaming events.

    Drops noise plays (ms_played < 1000), rows with negative ms_played, rows
    with a timestamp outside the expected history range, and exact duplicates.
    """
    before = len(music)
    df = music.copy()

    df["ts"] = pd.to_datetime(df["ts"], utc=True)
    df = df.drop_duplicates()
    after_dedupe = len(df)

    df = df[df["ms_played"] >= MIN_MS_PLAYED]
    after_noise = len(df)

    df = df[df["ms_played"] >= 0]

    in_range = (df["ts"].dt.year >= VALID_YEAR_MIN) & (df["ts"].dt.year <= VALID_YEAR_MAX)
    df = df[in_range]
    after_range = len(df)

    logger.info(
        "Cleaned music streams: %d raw -> %d after dedupe -> %d after ms_played filter "
        "-> %d after date range filter",
        before,
        after_dedupe,
        after_noise,
        after_range,
    )
    return df.reset_index(drop=True)


def drop_borrowed_listening(music: pd.DataFrame) -> pd.DataFrame:
    """Remove plays feitos por terceiros na conta (ver BORROWED_ACCOUNT_WINDOWS)."""
    day = pd.to_datetime(music["ts"], utc=True).dt.strftime("%Y-%m-%d")
    drop = pd.Series(False, index=music.index)
    for start, end, artists in BORROWED_ACCOUNT_WINDOWS:
        drop |= day.between(start, end) & music["master_metadata_album_artist_name"].isin(artists)
    logger.info("Dropped %d plays from borrowed-account windows", int(drop.sum()))
    return music[~drop].reset_index(drop=True)


def _stable_id(*parts: str) -> str:
    """Build a short stable surrogate key from one or more string parts."""
    joined = "|".join(p or "" for p in parts)
    return hashlib.sha1(joined.encode("utf-8")).hexdigest()[:16]


def build_dim_artist(music: pd.DataFrame) -> pd.DataFrame:
    """Build the artist dimension with aggregated listening stats."""
    df = music.copy()
    df["artist_id"] = df["master_metadata_album_artist_name"].apply(lambda a: _stable_id("artist", a))

    grouped = df.groupby(["artist_id", "master_metadata_album_artist_name"], as_index=False).agg(
        total_plays=("ts", "count"),
        total_hours=("ms_played", lambda s: round(s.sum() / 3_600_000, 2)),
        first_play_date=("ts", "min"),
        last_play_date=("ts", "max"),
    )
    grouped = grouped.rename(columns={"master_metadata_album_artist_name": "artist_name"})
    grouped["first_play_date"] = grouped["first_play_date"].dt.date
    grouped["last_play_date"] = grouped["last_play_date"].dt.date

    logger.info("Built dim_artist with %d artists", len(grouped))
    return grouped[["artist_id", "artist_name", "total_hours", "total_plays", "first_play_date", "last_play_date"]]


def build_dim_track(music: pd.DataFrame) -> pd.DataFrame:
    """Build the track dimension, one row per unique (track, artist, album)."""
    df = music.copy()
    df["artist_id"] = df["master_metadata_album_artist_name"].apply(lambda a: _stable_id("artist", a))
    df["track_id"] = df.apply(
        lambda r: _stable_id(
            "track",
            r["master_metadata_track_name"],
            r["master_metadata_album_artist_name"],
            r["master_metadata_album_album_name"],
        ),
        axis=1,
    )

    tracks = df.drop_duplicates(subset=["track_id"])[
        ["track_id", "master_metadata_track_name", "artist_id", "master_metadata_album_album_name"]
    ].rename(
        columns={
            "master_metadata_track_name": "track_name",
            "master_metadata_album_album_name": "album_name",
        }
    )

    logger.info("Built dim_track with %d unique tracks", len(tracks))
    return tracks.reset_index(drop=True)


def build_dim_date(music: pd.DataFrame) -> pd.DataFrame:
    """Build a calendar dimension spanning every day from first to last play."""
    start = music["ts"].dt.date.min()
    end = music["ts"].dt.date.max()
    dates = pd.date_range(start=start, end=end, freq="D")

    dim = pd.DataFrame({"date_key": dates.date})
    dim["year"] = dates.year
    dim["month"] = dates.month
    dim["day"] = dates.day
    dim["weekday_name"] = dates.day_name()
    dim["is_weekend"] = dates.dayofweek.isin([5, 6])
    dim["week_of_year"] = dates.isocalendar().week.values

    logger.info("Built dim_date with %d days (%s to %s)", len(dim), start, end)
    return dim


def build_fact_streams(music: pd.DataFrame) -> pd.DataFrame:
    """Build the fact table of individual music streaming events."""
    df = music.copy()
    df["artist_id"] = df["master_metadata_album_artist_name"].apply(lambda a: _stable_id("artist", a))
    df["track_id"] = df.apply(
        lambda r: _stable_id(
            "track",
            r["master_metadata_track_name"],
            r["master_metadata_album_artist_name"],
            r["master_metadata_album_album_name"],
        ),
        axis=1,
    )
    df["stream_id"] = df.apply(
        lambda r: _stable_id("stream", str(r["ts"]), r["track_id"], str(r["ms_played"])),
        axis=1,
    )
    df["date_key"] = df["ts"].dt.date
    df["time"] = df["ts"].dt.strftime("%H:%M:%S")

    fact = df[
        [
            "stream_id",
            "date_key",
            "time",
            "artist_id",
            "track_id",
            "ms_played",
            "platform",
            "skipped",
            "shuffle",
            "reason_start",
            "reason_end",
        ]
    ].copy()

    logger.info("Built fact_streams with %d rows", len(fact))
    return fact.reset_index(drop=True)


def build_star_schema(raw: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Run the full transform pipeline and return all star schema tables."""
    music, podcasts, audiobooks = split_content_types(raw)
    music_raw_count = len(music)
    music = clean_music_streams(music)
    music = drop_borrowed_listening(music)

    return {
        "fact_streams": build_fact_streams(music),
        "dim_artist": build_dim_artist(music),
        "dim_track": build_dim_track(music),
        "dim_date": build_dim_date(music),
        "podcasts": podcasts,
        "audiobooks": audiobooks,
        "music_raw_count": music_raw_count,
    }
