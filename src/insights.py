"""Análises para o site: calendário, eras automáticas, sobrevivência de artistas e redescobertas.

Lê os CSVs processados (esquema estrela) e escreve JSONs agregados em frontend/data/.
Só numpy e pandas: a segmentação das eras usa programação dinâmica e a curva de
sobrevivência é um Kaplan-Meier direto, sem scikit-learn, scipy ou lifelines.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "frontend" / "data"

ABANDON_DAYS = 365  # sem tocar por mais de 1 ano = abandonado
MIN_ARTIST_PLAYS = 3  # artistas que ouvi pelo menos 3 vezes (deram uma chance real)


def load() -> pd.DataFrame:
    fact = pd.read_csv(PROCESSED / "fact_streams.csv", parse_dates=["date_key"])
    artists = pd.read_csv(PROCESSED / "dim_artist.csv")[["artist_id", "artist_name"]]
    tracks = pd.read_csv(PROCESSED / "dim_track.csv")[["track_id", "track_name"]]
    df = fact.merge(artists, on="artist_id").merge(tracks, on="track_id")
    df["hours"] = df["ms_played"] / 3_600_000
    return df


# --- calendário -------------------------------------------------------------------------


def calendar(df: pd.DataFrame) -> dict:
    daily = df.groupby("date_key")["hours"].sum().round(2)
    return {"days": [[d.strftime("%Y-%m-%d"), float(h)] for d, h in daily.items()]}


# --- eras automáticas -------------------------------------------------------------------


def _segment_costs(X: np.ndarray) -> np.ndarray:
    """cost[i, j] = soma dos quadrados dentro do segmento de meses [i, j) (j > i)."""
    n = len(X)
    s1 = np.vstack([np.zeros(X.shape[1]), np.cumsum(X, axis=0)])
    s2 = np.concatenate([[0.0], np.cumsum((X**2).sum(axis=1))])
    cost = np.full((n + 1, n + 1), np.inf)
    for i in range(n):
        j = np.arange(i + 1, n + 1)
        size = j - i
        seg = s1[j] - s1[i]
        cost[i, j] = (s2[j] - s2[i]) - (seg**2).sum(axis=1) / size
    return cost


def _optimal_segmentation(cost: np.ndarray, k_max: int) -> tuple[list[float], dict[int, list[int]]]:
    """Programação dinâmica: menor custo total para dividir n meses em k blocos contíguos."""
    n = cost.shape[0] - 1
    best = np.full((k_max + 1, n + 1), np.inf)
    cut = np.zeros((k_max + 1, n + 1), dtype=int)
    best[0, 0] = 0.0
    for k in range(1, k_max + 1):
        for j in range(k, n + 1):
            cand = best[k - 1, k - 1 : j] + cost[k - 1 : j, j]
            i = int(np.argmin(cand))
            best[k, j] = cand[i]
            cut[k, j] = i + k - 1
    totals = [float(best[k, n]) for k in range(1, k_max + 1)]
    bounds: dict[int, list[int]] = {}
    for k in range(1, k_max + 1):
        edges, j = [n], n
        for kk in range(k, 0, -1):
            j = cut[kk, j]
            edges.append(j)
        bounds[k] = edges[::-1]
    return totals, bounds


def _choose_k(totals: list[float], k_min: int = 4, gain_threshold: float = 0.03) -> int:
    """Menor k a partir do qual dividir mais reduz o custo em menos de `gain_threshold` do total."""
    base = totals[0]
    for k in range(k_min, len(totals)):
        if (totals[k - 1] - totals[k]) / base < gain_threshold:
            return k
    return len(totals)


def eras(df: pd.DataFrame, top_artists: int = 200, k_max: int = 12, min_months: int = 6) -> dict:
    monthly = df.assign(month=df["date_key"].dt.to_period("M")).groupby(["month", "artist_name"])["hours"].sum()
    matrix = monthly.unstack(fill_value=0.0)
    keep = matrix.sum().nlargest(top_artists).index
    shares = matrix[keep].div(matrix.sum(axis=1), axis=0)
    X = np.sqrt(shares.to_numpy())  # distância de Hellinger: pesa menos o artista dominante
    months = list(matrix.index)

    cost = _segment_costs(X)
    cost[np.subtract.outer(np.arange(len(X) + 1), np.arange(len(X) + 1)).T < min_months] = np.inf  # era curta demais
    totals, bounds = _optimal_segmentation(cost, k_max)
    k = _choose_k(totals)
    edges = bounds[k]

    overall = matrix.sum() / matrix.to_numpy().sum()
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        block = matrix.iloc[a:b]
        hours = block.sum()
        share = hours / hours.sum()
        lift = (share / overall).where(share >= 0.01).dropna().sort_values(ascending=False)
        out.append(
            {
                "start": str(months[a]),
                "end": str(months[b - 1]),
                "months": b - a,
                "hours": round(float(hours.sum()), 1),
                "top_artists": [{"artist_name": n, "share": round(float(share[n]), 3)} for n in share.nlargest(3).index],
                "signature_artists": list(lift.head(3).index),
            }
        )
    logger.info("Eras: k=%d (custos %s)", k, [round(t, 1) for t in totals[:8]])
    return {"k": k, "eras": out}


# --- sobrevivência de artistas (Kaplan-Meier) -------------------------------------------


def kaplan_meier(durations: np.ndarray, observed: np.ndarray, grid: np.ndarray) -> list[float]:
    """S(t) nos pontos de `grid` (mesma unidade de `durations`). observed=1 evento, 0 censura."""
    surv, s = [], 1.0
    order = np.argsort(durations)
    d, o = durations[order], observed[order]
    times = np.unique(d[o == 1])
    at_risk = len(d)
    idx = 0
    steps = {}
    for t in times:
        while idx < len(d) and d[idx] < t:
            at_risk -= 1
            idx += 1
        events = int(((d == t) & (o == 1)).sum())
        s *= 1 - events / at_risk
        steps[t] = s
    keys = np.array(sorted(steps))
    for g in grid:
        pos = np.searchsorted(keys, g, side="right") - 1
        surv.append(round(steps[keys[pos]], 4) if pos >= 0 else 1.0)
    return surv


def survival(df: pd.DataFrame) -> dict:
    """Quanto tempo um artista descoberto num ano continua sendo ouvido (em anos)."""
    end = df["date_key"].max()
    g = df.groupby("artist_id")["date_key"].agg(first="min", last="max", plays="size")
    g = g[g["plays"] >= MIN_ARTIST_PLAYS].copy()
    g["duration"] = (g["last"] - g["first"]).dt.days
    g["event"] = ((end - g["last"]).dt.days > ABANDON_DAYS).astype(int)
    g["cohort_year"] = g["first"].dt.year
    grid_years = np.arange(0, 10.5, 0.5)
    grid = grid_years * 365.25

    cohorts = {
        "2014-2016": (2014, 2016),
        "2017-2019": (2017, 2019),
        "2020-2022": (2020, 2022),
        "2023-2026": (2023, 2026),
    }
    curves = []
    for label, (a, b) in cohorts.items():
        c = g[(g["cohort_year"] >= a) & (g["cohort_year"] <= b)]
        if len(c) < 20:
            continue
        curves.append(
            {
                "cohort": label,
                "artists": int(len(c)),
                "abandoned": int(c["event"].sum()),
                "survival": kaplan_meier(c["duration"].to_numpy(float), c["event"].to_numpy(), grid),
            }
        )
    all_curve = kaplan_meier(g["duration"].to_numpy(float), g["event"].to_numpy(), grid)
    half = next((float(y) for y, s in zip(grid_years, all_curve) if s <= 0.5), None)
    return {
        "years": grid_years.tolist(),
        "all": all_curve,
        "median_years": half,
        "cohorts": curves,
        "artists": int(len(g)),
        "rule": f"artistas com pelo menos {MIN_ARTIST_PLAYS} plays; abandonado = sem tocar por mais de {ABANDON_DAYS} dias",
    }


# --- redescobertas / nostalgia ----------------------------------------------------------


def rediscoveries(df: pd.DataFrame, top: int = 12) -> dict:
    """Plays de faixas que voltaram depois de mais de um ano sem tocar."""
    d = df.sort_values("date_key")[["track_id", "track_name", "artist_name", "date_key"]].copy()
    d["gap"] = d.groupby("track_id")["date_key"].diff().dt.days
    d["return"] = d["gap"] > ABANDON_DAYS
    d["year"] = d["date_key"].dt.year

    by_year = d.groupby("year").agg(plays=("track_id", "size"), returns=("return", "sum"))
    by_year["share"] = (100 * by_year["returns"] / by_year["plays"]).round(2)

    ret = d[d["return"]]
    # para cada faixa: maior pausa e quantas vezes voltou
    per_track = ret.groupby(["track_id", "track_name", "artist_name"]).agg(
        max_gap_days=("gap", "max"), comebacks=("gap", "size")
    ).reset_index()
    plays = d.groupby("track_id").size().rename("plays")
    per_track = per_track.merge(plays, on="track_id")
    longest = per_track[per_track["plays"] >= 10].sort_values("max_gap_days", ascending=False).head(top)
    return {
        "rule": f"retorno = faixa que voltou a tocar depois de mais de {ABANDON_DAYS} dias parada",
        "by_year": [
            {"year": int(y), "share": float(r["share"]), "returns": int(r["returns"])} for y, r in by_year.iterrows()
        ],
        "longest": [
            {
                "track_name": r.track_name,
                "artist_name": r.artist_name,
                "gap_years": round(r.max_gap_days / 365.25, 1),
                "plays": int(r.plays),
            }
            for r in longest.itertuples()
        ],
    }


def write(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=lambda o: o.item()), encoding="utf-8")
    logger.info("Wrote %s.json", name)


def run() -> None:
    df = load()
    write("calendar", calendar(df))
    write("eras", eras(df))
    write("survival", survival(df))
    write("rediscoveries", rediscoveries(df))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    run()
