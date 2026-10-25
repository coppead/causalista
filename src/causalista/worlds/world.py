"""A world: a structure, its numbers, what the analyst sees and what stays hidden."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path

import numpy as np
import pandas as pd

from causalista.verifier import CausalProblem, identify, valid_adjustment_sets
from causalista.worlds.mechanism import Parameters, Simulator, has_overlap, sample_parameters
from causalista.worlds.narrative import QUESTION, ColumnInfo, build_dictionary, build_narrative
from causalista.worlds.structure import Piece, Structure, sample_structure, sample_twin
from causalista.worlds.theory import Role, Theory

MAX_ATTEMPTS = 50


@dataclass(frozen=True)
class Truth:
    """The answer key of a world. Never shown to a model."""

    identifiable: bool
    adjustment_set: tuple[str, ...] | None
    """The smallest valid set; None when the effect is not identifiable."""
    valid_sets: tuple[tuple[str, ...], ...]
    missing: tuple[str, ...] | None
    """Hidden variables that would make the effect identifiable if they were in the table."""
    true_effect: float
    expected_naive: float
    """What the simple comparison shows with infinitely many rows."""
    roles: dict[str, str]


@dataclass(frozen=True)
class World:
    id: str
    theory_id: str
    structure: Structure
    parameters: Parameters
    problem: CausalProblem
    # what the analyst sees
    question: str
    narrative: str
    dictionary: tuple[ColumnInfo, ...]
    table: pd.DataFrame
    # what stays hidden
    truth: Truth
    twin_id: str | None = None
    language: str = "pt"
    level: int = 1
    """How the story is told: 1 for one fact per sentence, 2 for running prose."""

    @property
    def name(self) -> str:
        """What tells this telling of the world from the others: the id, the language and the level."""
        return self.id if (self.language, self.level) == ("pt", 1) else f"{self.id}.{self.language}{self.level}"


def _truth(theory: Theory, structure: Structure, simulator: Simulator) -> tuple[Truth, dict[str, float]]:
    problem = structure.problem(theory)
    answer = identify(problem)
    numbers = simulator.truth()
    truth = Truth(
        identifiable=answer.identifiable,
        adjustment_set=None if answer.adjustment_set is None else tuple(sorted(answer.adjustment_set)),
        valid_sets=tuple(tuple(sorted(chosen)) for chosen in valid_adjustment_sets(problem)),
        missing=None if answer.missing is None else tuple(sorted(answer.missing)),
        true_effect=numbers["true_effect"],
        expected_naive=numbers["expected_naive"],
        roles={piece.variable: piece.role.value for piece in structure.pieces},
    )
    return truth, numbers


def make_world(
    theory: Theory,
    structure: Structure,
    parameters: Parameters,
    world_id: str,
    *,
    twin_id: str | None = None,
) -> World | None:
    """Put a world together. Returns None when the treated and untreated barely overlap."""
    simulator = Simulator(theory, structure, parameters)
    truth, numbers = _truth(theory, structure, simulator)
    if not has_overlap(numbers):
        return None
    table = simulator.table()
    rng = np.random.default_rng([parameters.seed, 4])
    question = QUESTION[theory.language].format(
        treatment=theory.treatment.column, outcome=theory.outcome.column
    )
    return World(
        id=world_id,
        theory_id=theory.id,
        structure=structure,
        parameters=parameters,
        problem=structure.problem(theory),
        question=question,
        narrative=build_narrative(theory, structure, rng),
        dictionary=tuple(build_dictionary(theory, structure, list(table.columns))),
        table=table,
        truth=truth,
        twin_id=twin_id,
        language=theory.language,
    )


def retell(world: World, theory: Theory) -> World:
    """The same world told in the language of another reading of its theory card.

    Nothing of the world changes (structure, numbers, table, answer key): only the words
    of the question, of the story and of the dictionary.
    """
    if theory.id != world.theory_id:
        raise ValueError(f"{world.id} was made from the card {world.theory_id!r}, not {theory.id!r}")
    rng = np.random.default_rng([world.parameters.seed, 4])
    return replace(
        world,
        question=QUESTION[theory.language].format(
            treatment=theory.treatment.column, outcome=theory.outcome.column
        ),
        narrative=build_narrative(theory, world.structure, rng),
        dictionary=tuple(build_dictionary(theory, world.structure, list(world.table.columns))),
        language=theory.language,
        level=1,
    )


def generate_pair(theory: Theory, seed: int) -> tuple[World, World | None]:
    """Draw a world and, when one exists, its twin: same world, one fact changed.

    The same seed always gives the same pair.
    """
    rng = np.random.default_rng([seed, 0])
    for attempt in range(MAX_ATTEMPTS):
        structure = sample_structure(theory, rng)
        parameters = sample_parameters(theory, structure, rng, seed=seed)
        base_id = f"{theory.id}-{seed:06d}"
        twin_structure = sample_twin(theory, structure, rng)
        world = make_world(
            theory, structure, parameters, f"{base_id}-a",
            twin_id=f"{base_id}-b" if twin_structure else None,
        )  # fmt: skip
        if world is None:
            continue
        if twin_structure is None:
            return world, None
        twin_parameters = sample_parameters(theory, twin_structure, rng, seed=seed, like=parameters)
        twin = make_world(theory, twin_structure, twin_parameters, f"{base_id}-b", twin_id=world.id)
        if twin is not None:
            return world, twin
    raise RuntimeError(f"no world with enough overlap after {MAX_ATTEMPTS} attempts (seed {seed})")


# -- storage -----------------------------------------------------------------


def save_world(world: World, folder: Path) -> Path:
    """Write a world to ``folder/<name>``, keeping the answer key apart from what is visible."""
    home = folder / world.name
    visible, hidden = home / "visible", home / "hidden"
    visible.mkdir(parents=True, exist_ok=True)
    hidden.mkdir(parents=True, exist_ok=True)

    about = {
        "treatment": world.problem.treatment,
        "outcome": world.problem.outcome,
        "language": world.language,
        "level": world.level,
    }
    (visible / "about.json").write_text(json.dumps(about, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (visible / "question.txt").write_text(world.question + "\n", encoding="utf-8")
    (visible / "narrative.txt").write_text(world.narrative + "\n", encoding="utf-8")
    (visible / "dictionary.json").write_text(
        json.dumps([asdict(entry) for entry in world.dictionary], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    world.table.to_csv(visible / "table.csv", index=False)

    answer_key = {
        "id": world.id,
        "name": world.name,
        "theory": world.theory_id,
        "twin": world.twin_id,
        "treatment": world.problem.treatment,
        "outcome": world.problem.outcome,
        "edges": sorted(world.problem.graph.edges),
        "unobserved": sorted(world.problem.unobserved),
        "truth": asdict(world.truth),
        "structure": {
            "direct_effect": world.structure.direct_effect,
            "pieces": [
                {"variable": piece.variable, "role": piece.role.value, "hidden": piece.hidden}
                for piece in world.structure.pieces
            ],
        },
        "parameters": {
            "weights": [[cause, effect, weight] for (cause, effect), weight in world.parameters.weights.items()],
            "rates": dict(world.parameters.rates),
            "rows": world.parameters.rows,
            "seed": world.parameters.seed,
        },
    }
    (hidden / "answer_key.json").write_text(
        json.dumps(answer_key, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return home


def read_world(home: Path, theory: Theory) -> World:
    """Read back a world written by ``save_world``. ``theory`` is its card, in the language of the telling."""
    visible, hidden = home / "visible", home / "hidden"
    key = json.loads((hidden / "answer_key.json").read_text(encoding="utf-8"))
    about = json.loads((visible / "about.json").read_text(encoding="utf-8"))
    if theory.id != key["theory"] or theory.language != about["language"]:
        raise ValueError(f"{home.name} needs the card {key['theory']!r} in {about['language']!r}")
    structure = structure_from_key(key)
    truth = key["truth"]
    return World(
        id=key["id"],
        theory_id=key["theory"],
        structure=structure,
        parameters=Parameters(
            weights={(cause, effect): weight for cause, effect, weight in key["parameters"]["weights"]},
            rates=key["parameters"]["rates"],
            rows=key["parameters"]["rows"],
            seed=key["parameters"]["seed"],
        ),
        problem=structure.problem(theory),
        question=(visible / "question.txt").read_text(encoding="utf-8").strip(),
        narrative=(visible / "narrative.txt").read_text(encoding="utf-8").strip(),
        dictionary=tuple(
            ColumnInfo(**entry) for entry in json.loads((visible / "dictionary.json").read_text(encoding="utf-8"))
        ),
        table=pd.read_csv(visible / "table.csv"),
        truth=Truth(
            identifiable=truth["identifiable"],
            adjustment_set=None if truth["adjustment_set"] is None else tuple(truth["adjustment_set"]),
            valid_sets=tuple(tuple(chosen) for chosen in truth["valid_sets"]),
            missing=None if truth["missing"] is None else tuple(truth["missing"]),
            true_effect=truth["true_effect"],
            expected_naive=truth["expected_naive"],
            roles=truth["roles"],
        ),
        twin_id=key["twin"],
        language=about["language"],
        level=about["level"],
    )


def structure_from_key(answer_key: dict) -> Structure:
    """Rebuild a structure from a saved answer key."""
    return Structure(
        pieces=tuple(
            Piece(piece["variable"], Role(piece["role"]), piece["hidden"])
            for piece in answer_key["structure"]["pieces"]
        ),
        direct_effect=answer_key["structure"]["direct_effect"],
    )
