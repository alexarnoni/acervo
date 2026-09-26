"""Detecção de escutas atípicas: artistas cujos plays se concentram numa janela curta de dias.

Um artista que tem centenas de plays, quase todos em poucas semanas, foge do padrão de quem
escuta música de forma contínua. Pode ser um álbum novo que virou obsessão (legítimo) ou
outra pessoa usando a conta. O detector só sugere candidatos; quem decide é a curadoria
manual em `transform.BORROWED_ACCOUNT_WINDOWS`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

ARTIST_COL = "master_metadata_album_artist_name"


def detect_bursty_artists(
    music: pd.DataFrame,
    min_plays: int = 80,
    window_days: int = 21,
    min_share: float = 0.5,
) -> pd.DataFrame:
    """Retorna artistas com >= `min_share` dos plays dentro de uma janela de `window_days`.

    Colunas: artist, plays, burst_plays, burst_share, hours, window_start, window_end.
    Ordenado pela concentração (burst_share) e depois pelo volume.
    """
    df = music.loc[music[ARTIST_COL].notna(), ["ts", ARTIST_COL, "ms_played"]].copy()
    df["day"] = pd.to_datetime(df["ts"], utc=True).dt.tz_convert(None).dt.normalize()

    rows = []
    for artist, x in df.groupby(ARTIST_COL):
        n = len(x)
        if n < min_plays:
            continue
        days = np.sort(x["day"].values.astype("datetime64[D]").astype("int64"))
        # para cada play i, quantos plays cabem na janela que termina em days[i]
        start = np.searchsorted(days, days - window_days, side="left")
        counts = np.arange(len(days)) - start + 1
        end_idx = int(counts.argmax())
        best = int(counts[end_idx])
        share = best / n
        if share < min_share:
            continue
        rows.append(
            {
                "artist": artist,
                "plays": n,
                "burst_plays": best,
                "burst_share": round(share, 3),
                "hours": round(float(x["ms_played"].sum() / 3.6e6), 1),
                "window_start": str(np.datetime64(int(days[start[end_idx]]), "D")),
                "window_end": str(np.datetime64(int(days[end_idx]), "D")),
            }
        )
    cols = ["artist", "plays", "burst_plays", "burst_share", "hours", "window_start", "window_end"]
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values(["burst_share", "plays"], ascending=False).reset_index(drop=True)
