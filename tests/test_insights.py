import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from insights import _optimal_segmentation, _segment_costs, kaplan_meier, rediscoveries  # noqa: E402


def test_kaplan_meier_matches_hand_calculation():
    # 4 artistas: abandonam em t=1 e t=2; um e censurado em t=3, outro em t=4
    durations = np.array([1.0, 2.0, 3.0, 4.0])
    observed = np.array([1, 1, 0, 0])
    curve = kaplan_meier(durations, observed, np.array([0.0, 1.0, 2.0, 3.5]))
    assert curve == [1.0, 0.75, 0.5, 0.5]


def test_segmentation_recovers_single_change_point():
    a = np.tile([1.0, 0.0], (10, 1))
    b = np.tile([0.0, 1.0], (12, 1))
    X = np.vstack([a, b])
    totals, bounds = _optimal_segmentation(_segment_costs(X), k_max=4)
    assert bounds[2] == [0, 10, 22]
    assert totals[1] < 1e-9


def test_rediscoveries_counts_only_gaps_over_one_year():
    dates = pd.to_datetime(["2015-01-01", "2015-06-01", "2017-01-01", "2017-01-02"])
    df = pd.DataFrame(
        {"track_id": "t1", "track_name": "Song", "artist_name": "Band", "date_key": dates}
    )
    out = rediscoveries(df)
    by_year = {r["year"]: r["returns"] for r in out["by_year"]}
    assert by_year == {2015: 0, 2017: 1}
