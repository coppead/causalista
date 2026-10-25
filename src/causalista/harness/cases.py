"""Written cases as a test set: the same question a saved world asks, from a case written by hand.

A written case (``cases/``) has a story, a dictionary of columns, the causal diagram and
the answer, but no table. What a model sees of a table is only the kind and a short
summary of each column, so each column gets a made-up table read off its description:
yes/no columns, scores "de 0 a 10", amounts "em reais", counts. The summaries are
therefore invented, and the records say so (``level`` 3, ``theory`` "caso escrito").
Nothing else about a case is made up: story, columns, diagram and answer are the author's.
"""

from __future__ import annotations

import re
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from causalista.harness.run import SavedWorld
from causalista.task import make_task
from causalista.worlds.narrative import QUESTION
from causalista.written_cases import WrittenCase, load_written_cases

ROWS = 2000
YES_NO = re.compile(r"1 = (sim|yes|sí|oui|ja)", re.IGNORECASE)
RANGE = re.compile(r"(?:de|from|desde|von)\s+(\d+)\s+(?:a|to|até|hasta|bis)\s+(\d+)", re.IGNORECASE)
MONEY = re.compile(r"\b(reais|R\$|dollars?|US\$|\$|euros?|€|pesos|soles)\b", re.IGNORECASE)
COUNT = re.compile(r"^(número|numero|number|cantidad|quantidade|meses|months|meses|dias|days|días|idade|age|edad)\b", re.IGNORECASE)


def made_up_table(case: WrittenCase, rng: np.random.Generator) -> pd.DataFrame:
    """A table whose columns have the kind their descriptions announce. Only its summary is shown."""
    data = {}
    for name, text in case.columns.items():
        scale = RANGE.search(text)
        if YES_NO.search(text):
            data[name] = rng.binomial(1, float(rng.uniform(0.15, 0.6)), ROWS)
        elif scale:
            low, high = int(scale[1]), int(scale[2])
            data[name] = np.round(np.clip(rng.normal((low + high) / 2, (high - low) / 6, ROWS), low, high), 1)
        elif MONEY.search(text):
            data[name] = np.round(1500 * np.exp(0.5 * rng.normal(size=ROWS)), 2)
        elif COUNT.match(text):
            data[name] = np.clip(rng.poisson(8, ROWS), 0, None)
        else:
            data[name] = np.round(rng.normal(50, 15, ROWS), 1)
    return pd.DataFrame(data)


def case_worlds(files: list[Path], *, seed: int = 0) -> list[SavedWorld]:
    """Every case of the given files, in the shape the harness runs and records."""
    worlds = []
    for file in files:
        for case in load_written_cases(file):
            problem = case.problem
            task = make_task(
                world_id=case.id,
                question=QUESTION[case.language].format(treatment=problem.treatment, outcome=problem.outcome),
                treatment=problem.treatment,
                outcome=problem.outcome,
                narrative=case.story,
                descriptions=dict(case.columns),
                table=made_up_table(case, np.random.default_rng([seed, zlib.crc32(case.id.encode())])),
            )
            worlds.append(
                SavedWorld(
                    id=case.id,
                    folder=file.parent,
                    theory="caso escrito",
                    language=case.language,
                    level=3,
                    task=task,
                    problem=problem,
                    truth={"true_effect": None, "roles": {}},
                    twin=case.twin,
                )
            )
    return worlds
