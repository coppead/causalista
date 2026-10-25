"""The arithmetic of the runner: an effect and its confidence interval.

The model decides which columns to adjust for; this module does the computation, the
same way every time. With no adjustment it is the difference between the two groups.
With adjustment it is a doubly robust estimator with cross-fitting (the interactive
regression model of DoubleML), which does not assume a particular shape for how the
columns act on the treatment or on the outcome.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterable
from dataclasses import dataclass

import numpy as np
import pandas as pd
from doubleml import DoubleMLData, DoubleMLIRM
from doubleml.utils.propensity_score_processing import PSProcessorConfig
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FOLDS = 5
CLIP = 0.01
Z_95 = 1.959963984540054
LEARNERS = ("boosting", "linear")


@dataclass(frozen=True)
class EffectEstimate:
    effect: float
    standard_error: float
    low: float
    high: float
    """Bounds of the 95% confidence interval."""
    rows: int
    adjustment_set: tuple[str, ...]
    method: str
    clipped_share: float
    """Share of rows that were almost certain to be treated, or almost certain not to be.

    A large share means the two groups barely overlap and the estimate leans on few rows.
    """

    def covers(self, value: float) -> bool:
        return self.low <= value <= self.high


def _check(table: pd.DataFrame, treatment: str, outcome: str, columns: Iterable[str]) -> tuple[str, ...]:
    if isinstance(columns, str):
        raise TypeError("pass a collection of column names, not a single string")
    chosen = tuple(sorted(set(columns)))
    missing = [name for name in (treatment, outcome, *chosen) if name not in table.columns]
    if missing:
        raise KeyError(f"columns not in the table: {missing}")
    if treatment in chosen or outcome in chosen:
        raise ValueError("the treatment and the outcome cannot be adjusted for")
    if set(table[treatment].unique()) != {0, 1}:
        raise ValueError("the treatment must be a column of 0 and 1 with both values present")
    if table[[treatment, outcome, *chosen]].isna().any().any():
        raise ValueError("the columns used must have no missing values")
    return chosen


def naive_difference(table: pd.DataFrame, treatment: str, outcome: str) -> EffectEstimate:
    """The simple comparison: mean outcome of the treated minus mean outcome of the rest."""
    _check(table, treatment, outcome, ())
    treated = table.loc[table[treatment] == 1, outcome].to_numpy(dtype=float)
    untreated = table.loc[table[treatment] == 0, outcome].to_numpy(dtype=float)
    effect = float(treated.mean() - untreated.mean())
    error = float(np.sqrt(treated.var(ddof=1) / len(treated) + untreated.var(ddof=1) / len(untreated)))
    return EffectEstimate(
        effect=effect,
        standard_error=error,
        low=effect - Z_95 * error,
        high=effect + Z_95 * error,
        rows=len(table),
        adjustment_set=(),
        method="difference in means",
        clipped_share=0.0,
    )


def _learners(kind: str, binary_outcome: bool, seed: int):
    if kind == "boosting":
        settings = {"max_iter": 100, "learning_rate": 0.1, "max_leaf_nodes": 15, "random_state": seed}
        outcome_model = (
            HistGradientBoostingClassifier(**settings)
            if binary_outcome
            else HistGradientBoostingRegressor(**settings)
        )
        return outcome_model, HistGradientBoostingClassifier(**settings)
    if kind == "linear":
        outcome_model = (
            make_pipeline(StandardScaler(), LogisticRegression(C=1e4, max_iter=2_000))
            if binary_outcome
            else make_pipeline(StandardScaler(), LinearRegression())
        )
        return outcome_model, make_pipeline(StandardScaler(), LogisticRegression(C=1e4, max_iter=2_000))
    raise ValueError(f"unknown learner {kind!r}; choose one of {LEARNERS}")


def adjusted_effect(
    table: pd.DataFrame,
    treatment: str,
    outcome: str,
    adjustment_set: Iterable[str],
    *,
    seed: int = 0,
    learner: str = "boosting",
) -> EffectEstimate:
    """The average effect of the treatment, adjusting for the given columns."""
    chosen = _check(table, treatment, outcome, adjustment_set)
    if not chosen:
        raise ValueError("no column to adjust for; use naive_difference")

    frame = table[[outcome, treatment, *chosen]].astype(float).reset_index(drop=True)
    binary_outcome = set(frame[outcome].unique()) <= {0.0, 1.0}
    outcome_model, treatment_model = _learners(learner, binary_outcome, seed)

    folds = StratifiedKFold(n_splits=FOLDS, shuffle=True, random_state=seed)
    splits = list(folds.split(frame, frame[treatment]))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        model = DoubleMLIRM(
            DoubleMLData(frame, y_col=outcome, d_cols=treatment, x_cols=list(chosen)),
            ml_g=outcome_model,
            ml_m=treatment_model,
            score="ATE",
            ps_processor_config=PSProcessorConfig(clipping_threshold=CLIP),
            draw_sample_splitting=False,
        )
        model.set_sample_splitting(splits)
        model.fit()

    effect, error = float(model.coef[0]), float(model.se[0])
    chance = np.asarray(model.predictions["ml_m"]).ravel()
    return EffectEstimate(
        effect=effect,
        standard_error=error,
        low=effect - Z_95 * error,
        high=effect + Z_95 * error,
        rows=len(frame),
        adjustment_set=chosen,
        method=f"doubly robust with cross-fitting ({FOLDS} folds, {learner} learners)",
        clipped_share=float(np.mean((chance <= CLIP) | (chance >= 1 - CLIP))),
    )


def estimate_effect(
    table: pd.DataFrame,
    treatment: str,
    outcome: str,
    adjustment_set: Iterable[str] = (),
    *,
    seed: int = 0,
    learner: str = "boosting",
) -> EffectEstimate:
    """The effect for a choice of columns; with none, the simple comparison."""
    chosen = _check(table, treatment, outcome, adjustment_set)
    if not chosen:
        return naive_difference(table, treatment, outcome)
    return adjusted_effect(table, treatment, outcome, chosen, seed=seed, learner=learner)
