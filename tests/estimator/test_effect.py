"""The estimator on small tables where the right answer is known by construction."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from causalista.estimator import adjusted_effect, estimate_effect, naive_difference


def _sigmoid(x):
    return 1 / (1 + np.exp(-x))


def confounded_table(rows: int, seed: int, *, effect: float = -0.8) -> tuple[pd.DataFrame, float]:
    """Older customers get the offer more and cancel less. Returns the table and the true effect."""
    rng = np.random.default_rng(seed)
    tenure = rng.standard_normal(rows)
    offer = (rng.uniform(size=rows) < _sigmoid(-0.5 + 1.0 * tenure)).astype(int)
    noise = rng.uniform(size=rows)
    base = -1.0 - 0.9 * tenure
    cancelled = (noise < _sigmoid(base + effect * offer)).astype(int)
    truth = float(np.mean(_sigmoid(base + effect) - _sigmoid(base)))
    return pd.DataFrame({"tenure": tenure, "offer": offer, "cancelled": cancelled}), truth


def test_simple_comparison_is_right_when_treatment_is_random() -> None:
    rng = np.random.default_rng(1)
    rows = 40_000
    offer = rng.integers(0, 2, size=rows)
    cancelled = (rng.uniform(size=rows) < np.where(offer == 1, 0.20, 0.30)).astype(int)
    estimate = naive_difference(pd.DataFrame({"offer": offer, "cancelled": cancelled}), "offer", "cancelled")
    assert estimate.covers(-0.10)
    assert estimate.effect == pytest.approx(-0.10, abs=0.015)
    assert estimate.adjustment_set == ()
    assert estimate.high - estimate.low == pytest.approx(2 * 1.96 * estimate.standard_error, rel=1e-3)


@pytest.mark.parametrize("learner", ["boosting", "linear"])
def test_adjusting_for_the_confounder_recovers_the_effect(learner: str) -> None:
    table, truth = confounded_table(20_000, seed=2)
    naive = naive_difference(table, "offer", "cancelled")
    adjusted = adjusted_effect(table, "offer", "cancelled", ["tenure"], seed=0, learner=learner)
    assert not naive.covers(truth), "the simple comparison should be off"
    assert adjusted.covers(truth)
    assert abs(adjusted.effect - truth) < abs(naive.effect - truth) / 3
    assert adjusted.adjustment_set == ("tenure",)
    assert adjusted.clipped_share < 0.01


def test_the_same_seed_gives_the_same_estimate() -> None:
    table, _ = confounded_table(4_000, seed=3)
    first = adjusted_effect(table, "offer", "cancelled", ["tenure"], seed=7)
    again = adjusted_effect(table, "offer", "cancelled", ["tenure"], seed=7)
    assert first == again


def test_no_columns_means_the_simple_comparison() -> None:
    table, _ = confounded_table(4_000, seed=4)
    assert estimate_effect(table, "offer", "cancelled") == naive_difference(table, "offer", "cancelled")
    assert estimate_effect(table, "offer", "cancelled", ["tenure"]).adjustment_set == ("tenure",)


def test_a_continuous_outcome_is_handled() -> None:
    rng = np.random.default_rng(5)
    rows = 20_000
    tenure = rng.standard_normal(rows)
    offer = (rng.uniform(size=rows) < _sigmoid(0.9 * tenure)).astype(int)
    spend = 100 + 12 * offer + 15 * tenure + rng.normal(scale=20, size=rows)
    table = pd.DataFrame({"tenure": tenure, "offer": offer, "spend": spend})
    assert not naive_difference(table, "offer", "spend").covers(12)
    assert adjusted_effect(table, "offer", "spend", ["tenure"]).covers(12)


def test_poor_overlap_is_reported() -> None:
    rng = np.random.default_rng(6)
    rows = 6_000
    tenure = rng.standard_normal(rows)
    offer = (rng.uniform(size=rows) < _sigmoid(6.0 * tenure)).astype(int)  # almost determined
    cancelled = (rng.uniform(size=rows) < 0.3).astype(int)
    table = pd.DataFrame({"tenure": tenure, "offer": offer, "cancelled": cancelled})
    assert adjusted_effect(table, "offer", "cancelled", ["tenure"]).clipped_share > 0.2


def test_bad_requests_are_refused() -> None:
    table, _ = confounded_table(500, seed=7)
    with pytest.raises(KeyError, match="not in the table"):
        estimate_effect(table, "offer", "cancelled", ["typo"])
    with pytest.raises(ValueError, match="cannot be adjusted for"):
        estimate_effect(table, "offer", "cancelled", ["cancelled"])
    with pytest.raises(TypeError):
        estimate_effect(table, "offer", "cancelled", "tenure")
    with pytest.raises(ValueError, match="0 and 1"):
        estimate_effect(table.assign(offer=1), "offer", "cancelled")
    with pytest.raises(ValueError, match="missing values"):
        estimate_effect(table.assign(tenure=np.nan), "offer", "cancelled", ["tenure"])
    with pytest.raises(ValueError, match="unknown learner"):
        adjusted_effect(table, "offer", "cancelled", ["tenure"], learner="magic")
