"""Theory cards: what a management theory says about one theme.

A card lists the variables of a theme, the roles each variable may play, and the sign
with which it acts. Worlds are only ever built from what a card allows. The cards are
YAML files in ``theories/`` at the root of the repository, written to be read and
edited by a person.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, replace
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any

import yaml

THEORIES_DIR = Path(__file__).resolve().parents[3] / "theories"
# The cards are written in Portuguese; the other languages are translations of them.
LANGUAGES = ("pt", "en", "es", "fr", "de")
_COLUMN = re.compile(r"^[a-z][a-z0-9_]*$")


class InvalidTheoryError(ValueError):
    """A theory card is malformed."""


class Role(StrEnum):
    """The part a variable plays with respect to the treatment and the outcome."""

    CONFOUNDER = "confounder"
    MEDIATOR = "mediator"
    COLLIDER = "collider"
    OUTCOME_CAUSE = "outcome_cause"
    TREATMENT_CAUSE = "treatment_cause"
    UNRELATED = "unrelated"


class Kind(StrEnum):
    """How the values of a variable look in the table."""

    BINARY = "binary"
    COUNT = "count"
    CONTINUOUS = "continuous"
    SCORE = "score"


# The causal links each role is made of, in the order they are told in a narrative.
LINKS_OF_ROLE: Mapping[Role, tuple[str, ...]] = MappingProxyType(
    {
        Role.CONFOUNDER: ("to_treatment", "to_outcome"),
        Role.MEDIATOR: ("from_treatment", "to_outcome"),
        Role.COLLIDER: ("from_treatment", "from_outcome"),
        Role.OUTCOME_CAUSE: ("to_outcome",),
        Role.TREATMENT_CAUSE: ("to_treatment",),
        Role.UNRELATED: (),
    }
)
# The one number that sets the typical size of a variable of each kind.
SCALE_KEY: Mapping[Kind, str] = MappingProxyType(
    {Kind.BINARY: "rate", Kind.COUNT: "mean", Kind.CONTINUOUS: "median", Kind.SCORE: "mean"}
)


@dataclass(frozen=True)
class Link:
    """One causal relation asserted by the theory: its direction of action and its sentence."""

    sign: int
    fact: str


@dataclass(frozen=True)
class RoleSpec:
    role: Role
    dictionary: str
    """How the column is described in the table; this is what says "before" or "after"."""
    links: Mapping[str, Link]
    fact: str | None
    """For an unrelated variable: the sentence saying so."""


@dataclass(frozen=True)
class Variable:
    name: str
    label: str
    kind: Kind
    scale: Mapping[str, float]
    roles: Mapping[Role, RoleSpec]
    hidden_fact: str | None
    """If present, the variable may be left out of the table, and this sentence says so."""

    @property
    def hideable(self) -> bool:
        return self.hidden_fact is not None


@dataclass(frozen=True)
class Endpoint:
    """The treatment or the outcome of a theme."""

    column: str
    label: str
    kind: Kind
    dictionary: str
    range: tuple[float, float]
    """Treatment: the share treated. Outcome: the typical rate or size."""


@dataclass(frozen=True)
class Theory:
    id: str
    status: str
    title: str
    name: str
    statement: str
    references: tuple[str, ...]
    context: str
    randomized: str
    closing: str
    treatment: Endpoint
    outcome: Endpoint
    effect_sign: int
    variables: Mapping[str, Variable]
    language: str = "pt"
    translation: str | None = None
    """For a translated card: "rascunho" until a person has read the translation, then "revisada"."""

    @property
    def approved(self) -> bool:
        """Whether worlds made from this card may be used for training: the card and its translation."""
        return self.status == "aprovada" and self.translation in (None, "revisada")


def _need(where: str, given: Mapping[str, Any], required: set[str], optional: set[str] = frozenset()) -> None:
    if not isinstance(given, Mapping):
        raise InvalidTheoryError(f"{where}: expected a mapping, got {type(given).__name__}")
    missing = required - given.keys()
    unknown = given.keys() - required - optional
    if missing or unknown:
        raise InvalidTheoryError(
            f"{where}: missing keys {sorted(missing)}, unknown keys {sorted(unknown)}"
        )


def _sign(where: str, value: Any) -> int:
    if value not in ("+", "-"):
        raise InvalidTheoryError(f'{where}: sign must be "+" or "-", got {value!r}')
    return 1 if value == "+" else -1


def _text(where: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidTheoryError(f"{where}: expected a non-empty text")
    return " ".join(value.split())


def _column(where: str, value: Any) -> str:
    if not isinstance(value, str) or not _COLUMN.match(value):
        raise InvalidTheoryError(
            f"{where}: a column name must be lowercase letters, digits and underscores, got {value!r}"
        )
    return value


def _range(where: str, value: Any) -> tuple[float, float]:
    if isinstance(value, int | float):
        return float(value), float(value)
    if not (isinstance(value, list) and len(value) == 2 and value[0] <= value[1]):
        raise InvalidTheoryError(f"{where}: expected a number or [low, high], got {value!r}")
    return float(value[0]), float(value[1])


def _parse_role(where: str, role: Role, raw: Mapping[str, Any]) -> RoleSpec:
    expected = set(LINKS_OF_ROLE[role])
    required = {"dictionary"} | expected | ({"fact"} if role is Role.UNRELATED else set())
    _need(where, raw, required)
    links = {}
    for name in LINKS_OF_ROLE[role]:
        _need(f"{where}.{name}", raw[name], {"sign", "fact"})
        links[name] = Link(
            _sign(f"{where}.{name}", raw[name]["sign"]), _text(f"{where}.{name}.fact", raw[name]["fact"])
        )
    return RoleSpec(
        role=role,
        dictionary=_text(f"{where}.dictionary", raw["dictionary"]),
        links=MappingProxyType(links),
        fact=_text(f"{where}.fact", raw["fact"]) if role is Role.UNRELATED else None,
    )


def _parse_variable(name: str, raw: Mapping[str, Any]) -> Variable:
    where = f"variables.{name}"
    _column(where, name)
    _need(where, raw, {"label", "kind", "scale", "roles"}, {"hidden_fact"})
    try:
        kind = Kind(raw["kind"])
    except ValueError:
        raise InvalidTheoryError(f"{where}: unknown kind {raw['kind']!r}") from None
    _need(f"{where}.scale", raw["scale"], {SCALE_KEY[kind]}, {"min", "max"})
    scale = {key: float(value) for key, value in raw["scale"].items()}
    if kind is Kind.BINARY and not 0 < scale["rate"] < 1:
        raise InvalidTheoryError(f"{where}.scale.rate must be strictly between 0 and 1")

    if not raw["roles"]:
        raise InvalidTheoryError(f"{where}: at least one role is required")
    roles = {}
    for role_name, role_raw in raw["roles"].items():
        try:
            role = Role(role_name)
        except ValueError:
            raise InvalidTheoryError(f"{where}: unknown role {role_name!r}") from None
        roles[role] = _parse_role(f"{where}.roles.{role_name}", role, role_raw)

    hidden_fact = raw.get("hidden_fact")
    if hidden_fact is not None and Role.CONFOUNDER not in roles:
        raise InvalidTheoryError(
            f"{where}: hidden_fact only makes sense for a variable that can be a confounder"
        )
    return Variable(
        name=name,
        label=_text(f"{where}.label", raw["label"]),
        kind=kind,
        scale=MappingProxyType(scale),
        roles=MappingProxyType(roles),
        hidden_fact=None if hidden_fact is None else _text(f"{where}.hidden_fact", hidden_fact),
    )


def parse_theory(raw: Mapping[str, Any]) -> Theory:
    """Build a theory from the content of a card, failing loudly on anything malformed."""
    _need(
        "theory card",
        raw,
        {"id", "status", "title", "theory", "context", "randomized", "closing",
         "treatment", "outcome", "effect", "variables"},
    )  # fmt: skip
    _need("theory", raw["theory"], {"name", "statement"}, {"references"})
    _need("treatment", raw["treatment"], {"column", "label", "dictionary", "share"})
    _need("outcome", raw["outcome"], {"column", "label", "kind", "dictionary", "scale"})
    _need("effect", raw["effect"], {"sign"})

    outcome_kind = Kind(raw["outcome"]["kind"])
    _need("outcome.scale", raw["outcome"]["scale"], {SCALE_KEY[outcome_kind]})
    treatment = Endpoint(
        column=_column("treatment.column", raw["treatment"]["column"]),
        label=_text("treatment.label", raw["treatment"]["label"]),
        kind=Kind.BINARY,
        dictionary=_text("treatment.dictionary", raw["treatment"]["dictionary"]),
        range=_range("treatment.share", raw["treatment"]["share"]),
    )
    outcome = Endpoint(
        column=_column("outcome.column", raw["outcome"]["column"]),
        label=_text("outcome.label", raw["outcome"]["label"]),
        kind=outcome_kind,
        dictionary=_text("outcome.dictionary", raw["outcome"]["dictionary"]),
        range=_range("outcome.scale", raw["outcome"]["scale"][SCALE_KEY[outcome_kind]]),
    )
    if not 0 < treatment.range[0] <= treatment.range[1] < 1:
        raise InvalidTheoryError("treatment.share must lie strictly between 0 and 1")

    variables = {name: _parse_variable(name, item) for name, item in raw["variables"].items()}
    taken = {treatment.column, outcome.column}
    if len(taken) < 2 or taken & variables.keys():
        raise InvalidTheoryError("treatment, outcome and variables must all have different names")

    effect_sign = _sign("effect", raw["effect"]["sign"])
    for name, variable in variables.items():
        mediator = variable.roles.get(Role.MEDIATOR)
        if mediator is None:
            continue
        route = mediator.links["from_treatment"].sign * mediator.links["to_outcome"].sign
        if route != effect_sign:
            # Otherwise the sign of the true effect would depend on the sizes drawn.
            raise InvalidTheoryError(
                f"variables.{name}.roles.mediator: the route through a mediator must act "
                "in the direction of effect.sign"
            )

    return Theory(
        id=_column("id", raw["id"]),
        status=_text("status", raw["status"]),
        title=_text("title", raw["title"]),
        name=_text("theory.name", raw["theory"]["name"]),
        statement=_text("theory.statement", raw["theory"]["statement"]),
        references=tuple(_text("theory.references", item) for item in raw["theory"].get("references", ())),
        context=_text("context", raw["context"]),
        randomized=_text("randomized", raw["randomized"]),
        closing=_text("closing", raw["closing"]),
        treatment=treatment,
        outcome=outcome,
        effect_sign=effect_sign,
        variables=MappingProxyType(variables),
    )


def translate_theory(theory: Theory, raw: Mapping[str, Any]) -> Theory:
    """The same theory told in another language.

    A translation carries only words: labels, column descriptions and sentences. It must
    mirror the card exactly (same variables, same roles, same links); signs, kinds, sizes
    and column names always come from the card.
    """
    _need("translation", raw, {"language", "status", "title", "context", "randomized", "closing",
                               "treatment", "outcome", "variables"})  # fmt: skip
    language = raw["language"]
    if language not in LANGUAGES or language == theory.language:
        raise InvalidTheoryError(f"translation: unknown language {language!r}")
    if raw["status"] not in ("rascunho", "revisada"):
        raise InvalidTheoryError('translation: status must be "rascunho" or "revisada"')
    _need("translation.variables", raw["variables"], set(theory.variables))

    def endpoint(name: str, given: Endpoint) -> Endpoint:
        _need(f"translation.{name}", raw[name], {"label", "dictionary"})
        return replace(
            given,
            label=_text(f"translation.{name}.label", raw[name]["label"]),
            dictionary=_text(f"translation.{name}.dictionary", raw[name]["dictionary"]),
        )

    variables = {}
    for name, variable in theory.variables.items():
        where = f"translation.variables.{name}"
        said = raw["variables"][name]
        _need(where, said, {"label", "roles"} | ({"hidden_fact"} if variable.hideable else set()))
        _need(f"{where}.roles", said["roles"], {role.value for role in variable.roles})
        roles = {}
        for role, spec in variable.roles.items():
            there = f"{where}.roles.{role.value}"
            words = said["roles"][role.value]
            _need(there, words, {"dictionary"} | set(spec.links) | ({"fact"} if spec.fact else set()))
            roles[role] = RoleSpec(
                role=role,
                dictionary=_text(f"{there}.dictionary", words["dictionary"]),
                links=MappingProxyType(
                    {link: Link(given.sign, _text(f"{there}.{link}", words[link])) for link, given in spec.links.items()}
                ),
                fact=_text(f"{there}.fact", words["fact"]) if spec.fact else None,
            )
        variables[name] = replace(
            variable,
            label=_text(f"{where}.label", said["label"]),
            roles=MappingProxyType(roles),
            hidden_fact=_text(f"{where}.hidden_fact", said["hidden_fact"]) if variable.hideable else None,
        )

    return replace(
        theory,
        language=language,
        translation=raw["status"],
        title=_text("translation.title", raw["title"]),
        context=_text("translation.context", raw["context"]),
        randomized=_text("translation.randomized", raw["randomized"]),
        closing=_text("translation.closing", raw["closing"]),
        treatment=endpoint("treatment", theory.treatment),
        outcome=endpoint("outcome", theory.outcome),
        variables=MappingProxyType(variables),
    )


def load_theory(theory_id: str, language: str = "pt", folder: Path = THEORIES_DIR) -> Theory:
    """Read ``<folder>/<theory_id>.yaml``, and its translation from ``<folder>/i18n/<language>/``."""
    path = folder / f"{theory_id}.yaml"
    try:
        theory = parse_theory(yaml.safe_load(path.read_text(encoding="utf-8")))
    except InvalidTheoryError as error:
        raise InvalidTheoryError(f"{path.name}: {error}") from None
    if theory.id != theory_id:
        raise InvalidTheoryError(f"{path.name}: the id inside the card is {theory.id!r}")
    if language == theory.language:
        return theory

    path = folder / "i18n" / language / f"{theory_id}.yaml"
    try:
        theory = translate_theory(theory, yaml.safe_load(path.read_text(encoding="utf-8")))
    except InvalidTheoryError as error:
        raise InvalidTheoryError(f"i18n/{language}/{path.name}: {error}") from None
    if theory.language != language:
        raise InvalidTheoryError(f"i18n/{language}/{path.name}: the language inside is {theory.language!r}")
    return theory
