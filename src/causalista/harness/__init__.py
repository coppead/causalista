"""The evaluation harness: run models over saved worlds, record every answer, and add up."""

from causalista.harness.ask import Consultation, ask, format_consultation
from causalista.harness.cases import case_worlds
from causalista.harness.backends import (
    ADJUST_FOR_EVERYTHING,
    ADJUST_FOR_NOTHING,
    OllamaModel,
    OpenAIModel,
    Reply,
    chatml_prompt,
    Responder,
    Rule,
)
from causalista.harness.hf import HFModel
from causalista.harness.metrics import by, summarise
from causalista.harness.specs import responder_of
from causalista.harness.run import (
    BackendFailure,
    SavedWorld,
    load_world,
    load_worlds,
    record_of,
    run,
    runner_estimate,
)

__all__ = [
    "ADJUST_FOR_EVERYTHING",
    "Consultation",
    "ask",
    "case_worlds",
    "ADJUST_FOR_NOTHING",
    "BackendFailure",
    "HFModel",
    "OllamaModel",
    "OpenAIModel",
    "Reply",
    "Responder",
    "Rule",
    "SavedWorld",
    "by",
    "chatml_prompt",
    "load_world",
    "load_worlds",
    "format_consultation",
    "record_of",
    "responder_of",
    "run",
    "runner_estimate",
    "summarise",
]
