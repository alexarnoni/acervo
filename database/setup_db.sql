CREATE TABLE IF NOT EXISTS dim_artist (
    artist_id TEXT PRIMARY KEY,
    artist_name TEXT NOT NULL,
    total_hours DOUBLE PRECISION,
    total_plays INTEGER,
    first_play_date DATE,
    last_play_date DATE
);

CREATE TABLE IF NOT EXISTS dim_track (
    track_id TEXT PRIMARY KEY,
    track_name TEXT NOT NULL,
    artist_id TEXT NOT NULL,
    album_name TEXT,
    CONSTRAINT fk_dim_track_artist
        FOREIGN KEY (artist_id)
        REFERENCES dim_artist(artist_id)
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key DATE PRIMARY KEY,
    year INTEGER NOT NULL,
    month INTEGER NOT NULL,
    day INTEGER NOT NULL,
    weekday_name TEXT NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    week_of_year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_streams (
    stream_id TEXT PRIMARY KEY,
    date_key DATE NOT NULL,
    time TIME NOT NULL,
    artist_id TEXT NOT NULL,
    track_id TEXT NOT NULL,
    ms_played BIGINT NOT NULL,
    platform TEXT,
    skipped BOOLEAN NOT NULL DEFAULT FALSE,
    shuffle BOOLEAN NOT NULL DEFAULT FALSE,
    reason_start TEXT,
    reason_end TEXT,
    CONSTRAINT fk_fact_artist
        FOREIGN KEY (artist_id)
        REFERENCES dim_artist(artist_id),
    CONSTRAINT fk_fact_track
        FOREIGN KEY (track_id)
        REFERENCES dim_track(track_id),
    CONSTRAINT fk_fact_date
        FOREIGN KEY (date_key)
        REFERENCES dim_date(date_key)
);

CREATE INDEX IF NOT EXISTS idx_fact_date_key ON fact_streams(date_key);
CREATE INDEX IF NOT EXISTS idx_fact_artist_id ON fact_streams(artist_id);
CREATE INDEX IF NOT EXISTS idx_fact_track_id ON fact_streams(track_id);
CREATE INDEX IF NOT EXISTS idx_dim_artist_name ON dim_artist(artist_name);
CREATE INDEX IF NOT EXISTS idx_dim_track_artist ON dim_track(artist_id);
