"""Carrega os CSVs processados (schema estrela) no PostgreSQL.

Somente as colunas da whitelist abaixo sao lidas: qualquer outra coluna do CSV
(ex.: ip_addr, localizacao) e ignorada e nunca chega ao banco.

Uso:
    python database/load_data.py --truncate
    DATABASE_URL=postgresql://... python database/load_data.py --data-dir data/processed
"""
from __future__ import annotations

import argparse
import csv
import io
import os
from pathlib import Path
from urllib.parse import urlsplit

import psycopg2

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_URL = "postgresql://spotify:spotify@localhost:5432/spotify"

# ordem respeita as FKs
TABLES = {
    "dim_artist": ["artist_id", "artist_name", "total_hours", "total_plays", "first_play_date", "last_play_date"],
    "dim_track": ["track_id", "track_name", "artist_id", "album_name"],
    "dim_date": ["date_key", "year", "month", "day", "weekday_name", "is_weekend", "week_of_year"],
    "fact_streams": [
        "stream_id", "date_key", "time", "artist_id", "track_id", "ms_played",
        "platform", "skipped", "shuffle", "reason_start", "reason_end",
    ],
}


def masked(url: str) -> str:
    parts = urlsplit(url)
    return f"{parts.scheme}://{parts.username}:***@{parts.hostname}:{parts.port}{parts.path}"


def prepare(csv_path: Path, columns: list[str]) -> io.StringIO:
    """Reescreve o CSV mantendo apenas as colunas da whitelist, na ordem da tabela."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in columns if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"{csv_path.name}: colunas ausentes {missing}")
        seen = set()
        for row in reader:
            if row[columns[0]] in seen:  # export do Spotify repete alguns eventos: mantem o primeiro
                continue
            seen.add(row[columns[0]])
            writer.writerow([row[c] if row[c] != "" else "\\N" for c in columns])
    buf.seek(0)
    return buf


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=ROOT / "data" / "processed")
    ap.add_argument("--database-url", default=os.getenv("DATABASE_URL", DEFAULT_URL))
    ap.add_argument("--truncate", action="store_true", help="limpa as tabelas antes de carregar")
    args = ap.parse_args()

    print(f"Banco: {masked(args.database_url)}")
    with psycopg2.connect(args.database_url) as conn, conn.cursor() as cur:
        if args.truncate:
            cur.execute("TRUNCATE fact_streams, dim_track, dim_date, dim_artist")
        for table, columns in TABLES.items():
            buf = prepare(args.data_dir / f"{table}.csv", columns)
            cur.copy_expert(
                f"COPY {table} ({', '.join(columns)}) FROM STDIN WITH (FORMAT csv, NULL '\\N')", buf
            )
            print(f"{table}: {cur.rowcount} linhas")


if __name__ == "__main__":
    main()
