"""Run a responder over saved worlds and record every answer.

One record per world and responder: the world, the point of the training (if any), the
answer as given, the score and the reason given by the verifier, and the effect the
runner computes with the chosen columns. The pages only ever read these records.
"""

from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from causalista.estimator import estimate_effect
from causalista.harness.backends import Reply, Responder
from causalista.task import InvalidAnswer, Task, judge, make_task, parse_answer
from causalista.verifier import CausalProblem

NEUTRAL = ("outcome_cause", "treatment_cause", "unrelated")
MAX_FAILURES = 5


class BackendFailure(RuntimeError):
    """The machinery that serves a model failed (no memory, a server that went away). Not an answer."""


@dataclass(frozen=True)
class SavedWorld:
    """A world read back from disk: what a model may see, and the answer key."""

    id: str
    folder: Path
    theory: str
    language: str
    level: int
    task: Task
    problem: CausalProblem
    truth: dict
    twin: str | None

    def table(self) -> pd.DataFrame:
        return pd.read_csv(self.folder / "visible" / "table.csv")


def load_world(folder: Path) -> SavedWorld:
    visible, hidden = folder / "visible", folder / "hidden"
    key = json.loads((hidden / "answer_key.json").read_text(encoding="utf-8"))
    about = json.loads((visible / "about.json").read_text(encoding="utf-8"))
    table = pd.read_csv(visible / "table.csv")
    dictionary = json.loads((visible / "dictionary.json").read_text(encoding="utf-8"))
    task = make_task(
        world_id=key["name"],
        question=(visible / "question.txt").read_text(encoding="utf-8").strip(),
        treatment=about["treatment"],
        outcome=about["outcome"],
        narrative=(visible / "narrative.txt").read_text(encoding="utf-8").strip(),
        descriptions={entry["column"]: entry["description"] for entry in dictionary},
        table=table,
    )
    problem = CausalProblem.from_edges(
        [tuple(edge) for edge in key["edges"]],
        key["treatment"],
        key["outcome"],
        unobserved=key["unobserved"],
        extra_nodes=[*table.columns, *key["unobserved"]],
    )
    return SavedWorld(
        id=key["name"],
        folder=folder,
        theory=key["theory"],
        language=about["language"],
        level=about["level"],
        task=task,
        problem=problem,
        truth=key["truth"],
        twin=key["twin"],
    )


def load_worlds(folder: Path) -> list[SavedWorld]:
    """Every world saved under a folder, in a fixed order."""
    return [load_world(home) for home in sorted(folder.iterdir()) if (home / "hidden").is_dir()]


_estimate_lock = threading.Lock()


def runner_estimate(world: SavedWorld, chosen: frozenset[str]) -> dict | None:
    """What the runner computes with the chosen columns. Kept beside the world, since many answers repeat."""
    columns = {card.column for card in world.task.columns}
    if chosen & {world.task.treatment, world.task.outcome} or not chosen <= columns:
        return None  # the runner refuses the intervention, the outcome, and what is not a column
    cache = world.folder / "estimates.json"
    key = ",".join(sorted(chosen))
    with _estimate_lock:
        known = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    if key not in known:
        estimate = estimate_effect(world.table(), world.task.treatment, world.task.outcome, chosen, seed=0)
        with _estimate_lock:
            known = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
            known[key] = {"effect": estimate.effect, "low": estimate.low, "high": estimate.high}
            cache.write_text(json.dumps(known, indent=1) + "\n", encoding="utf-8")
    return known[key]


def record_of(world: SavedWorld, label: str, checkpoint: str | None, reply: Reply, *, estimate: bool = True) -> dict:
    """Read, score and write down one answer."""
    try:
        answer, invalid = parse_answer(reply.text, world.task), None
    except InvalidAnswer as error:
        answer, invalid = None, str(error)
    judgement = judge(world.problem, answer, invalid=invalid)

    record = {
        "world": world.id,
        "theory": world.theory,
        "language": world.language,
        "level": world.level,
        "model": label,
        "checkpoint": checkpoint,
        "world_identifiable": judgement.world_identifiable,
        "outcome": judgement.outcome.value,
        "score": judgement.score,
        "reason": judgement.reason,
        "answer": None,
        "roles_right": None,
        "estimate": None,
        "true_effect": world.truth["true_effect"],
        "raw": reply.text,
        "seconds": round(reply.seconds, 2),
        "output_tokens": reply.output_tokens,
    }
    if answer is None:
        return record

    record["answer"] = {
        "identifiable": answer.identifiable,
        "adjustment_set": sorted(answer.adjustment_set),
        "roles": {role.column: role.role for role in answer.roles},
        "reasons": {role.column: role.reason for role in answer.roles},
        "missing": list(answer.missing),
        "assumptions": list(answer.assumptions),
        "complete": answer.complete,
    }
    true_roles = {
        name: ("neutral" if role in NEUTRAL else role)
        for name, role in (world.truth.get("roles") or {}).items()
        if name in world.task.covariates
    }
    if true_roles and answer.roles:  # a fixed rule gives no roles: nothing to score
        said = record["answer"]["roles"]
        record["roles_right"] = sum(said.get(name) == role for name, role in true_roles.items()) / len(true_roles)
    if answer.identifiable and estimate:
        record["estimate"] = runner_estimate(world, answer.adjustment_set)
    return record


def run(
    responder: Responder,
    worlds: list[SavedWorld],
    out: Path,
    *,
    checkpoint: str | None = None,
    workers: int = 4,
    estimate: bool = True,
    batch: int = 32,
) -> list[dict]:
    """Answer every world not yet in ``out`` and append the records to it. Returns all of them.

    A responder with a ``many`` method (a model on the local GPU) is handed ``batch``
    worlds at a time and answers them together; the others answer one world at a time,
    ``workers`` of them in parallel.

    A failure of the machinery is never written down as an answer: the world is left
    without a record, to be asked again in the next run, and after ``MAX_FAILURES`` of
    them the run stops with ``BackendFailure``. What was answered before stays recorded.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    done = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()] if out.exists() else []
    seen = {record["world"] for record in done}
    lock = threading.Lock()
    failures: list[str] = []

    def answer(world: SavedWorld) -> Reply | None:
        if len(failures) >= MAX_FAILURES:
            return None
        try:
            return responder(world.task)
        except Exception as error:
            failures.append(f"{world.id}: {type(error).__name__}: {str(error).splitlines()[0][:200]}")
            return None

    def write(world: SavedWorld, reply: Reply | None) -> dict | None:
        if reply is None:
            return None
        record = record_of(world, responder.label, checkpoint, reply, estimate=estimate)
        with lock, out.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def together(group: list[SavedWorld]) -> list[Reply | None]:
        try:
            replies = list(responder.many([world.task for world in group]))
            if len(replies) != len(group):
                raise ValueError(f"{len(replies)} replies for {len(group)} worlds")
            return replies
        except Exception:  # a batch that fails (out of memory, say) is asked again, one world at a time
            return [answer(world) for world in group]

    todo = [world for world in worlds if world.id not in seen]
    with ThreadPoolExecutor(max_workers=workers) as pool:
        if hasattr(responder, "many"):
            # The model goes on to the next batch while the answers of the last one are scored.
            scoring = []
            for start in range(0, len(todo), batch):
                group = todo[start : start + batch]
                scoring += [pool.submit(write, world, reply) for world, reply in zip(group, together(group))]
                if len(failures) >= MAX_FAILURES:
                    break
            done += [record for future in scoring if (record := future.result()) is not None]
        else:
            written = pool.map(lambda world: write(world, answer(world)), todo)
            done += [record for record in written if record is not None]
    if len(failures) >= MAX_FAILURES:
        raise BackendFailure(
            f"{responder.label}: the backend failed {len(failures)} times and the run was stopped; "
            f"nothing was recorded for those worlds. First failure: {failures[0]}"
        )
    order = {world.id: index for index, world in enumerate(worlds)}
    return sorted((r for r in done if r["world"] in order), key=lambda r: order[r["world"]])
