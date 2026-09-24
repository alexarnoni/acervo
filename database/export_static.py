"""Exporta o resultado de cada endpoint para frontend/data/*.json (site 100% estatico).

Usa as mesmas queries da API, entao o JSON e identico ao que /api/... devolveria.
Uso (com o banco carregado):
    DATABASE_URL=postgresql://spotify:spotify@localhost:5433/spotify python database/export_static.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app import queries  # noqa: E402

OUT = ROOT / "frontend" / "data"

# nome do arquivo -> resultado (parametros iguais aos usados pelo frontend)
EXPORTS = {
    "summary": lambda: queries.summary(),
    "by-year": lambda: queries.by_year(),
    "dominant-artist-per-year": lambda: queries.dominant_artist_per_year(),
    "heatmap": lambda: queries.heatmap(),
    "by-hour": lambda: queries.by_hour(),
    "by-weekday": lambda: queries.by_weekday(),
    "diversity-per-year": lambda: queries.diversity_per_year(),
    "discovery": lambda: queries.discovery(15),
    "top-artists": lambda: queries.top_artists(15),
    "top-tracks": lambda: queries.top_tracks(12),
    "obsession-days": lambda: queries.obsession_days(12),
    "skip-rate": lambda: queries.skip_rate(20),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in EXPORTS.items():
        data = fn()
        (OUT / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
        )
        print(f"{name}.json")


if __name__ == "__main__":
    main()
