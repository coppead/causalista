"""Check a file of written cases: it loads, every answer follows from the edges, and no story gives a role away.

    uv run python scripts/check_cases.py cases/fase0.yaml cases/simulados/*.yaml
"""

from __future__ import annotations

import sys
from pathlib import Path

from causalista.worlds.narrative import ROLE_WORDS
from causalista.written_cases import disagreements, load_written_cases


def main() -> None:
    bad = 0
    for file in map(Path, sys.argv[1:]):
        cases = load_written_cases(file)
        ids = [case.id for case in cases]
        if len(set(ids)) != len(ids):
            print(f"{file}: repeated ids")
            bad += 1
        for case in cases:
            problems = disagreements(case)
            seen = " ".join([case.story, *case.columns.values(), *case.not_in_table.values()]).lower()
            problems += [f"the story or a column uses the word {word!r}" for word in ROLE_WORDS if word in seen]
            if case.twin and case.twin not in ids:
                problems.append(f"twin {case.twin!r} is not in this file")
            for problem in problems:
                print(f"{file} / {case.id}: {problem}")
            bad += bool(problems)
        print(f"{file}: {len(cases)} cases, {sum(not c.identifiable for c in cases)} not identifiable")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
