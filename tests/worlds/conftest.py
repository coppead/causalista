"""The tests of the world factory run once per theory card in ``theories/``."""

from __future__ import annotations

import pytest

from causalista.worlds import Theory, load_theory
from causalista.worlds.theory import THEORIES_DIR

# Only the names are read here, so a card that is being written does not break the
# collection of the tests of the other themes (``pytest -k varejo`` loads only varejo).
THEORY_IDS = sorted(path.stem for path in THEORIES_DIR.glob("*.yaml"))


@pytest.fixture(scope="session", params=THEORY_IDS)
def theory(request: pytest.FixtureRequest) -> Theory:
    return load_theory(request.param)
