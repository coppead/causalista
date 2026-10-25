"""Asking about a table of one's own: the task is built, the answer read, the effect estimated."""

import numpy as np
import pandas as pd
import pytest

from causalista.harness import OllamaModel, ask, format_consultation, responder_of
from causalista.harness.backends import Reply
from causalista.task import Answer, ColumnRole, render_answer


def toy_table(seed: int = 0, n: int = 3000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    prior = rng.poisson(3, n)
    email = rng.binomial(1, 1 / (1 + np.exp(-(prior - 3) * 0.6)), n)
    visited = rng.binomial(1, 0.2 + 0.4 * email, n)
    bought = rng.binomial(1, np.clip(0.05 + 0.04 * prior + 0.10 * email + 0.15 * visited, 0, 1), n)
    return pd.DataFrame({"email": email, "bought": bought, "prior_purchases": prior, "visited_site": visited})


DESCRIPTIONS = {
    "email": "Received the campaign e-mail (1 = yes).",
    "bought": "Bought in the 14 days after the campaign (1 = yes).",
    "prior_purchases": "Purchases in the 12 months before the campaign.",
    "visited_site": "Visited the website in the 14 days after the campaign (1 = yes).",
}
STORY = "Frequent buyers were more likely to get the e-mail and buy more anyway; the e-mail drove visits, and visits drive purchases."


class CannedResponder:
    """Answers with a fixed Answer, rendered in the format the model is asked for."""

    label = "canned"

    def __init__(self, answer: Answer, text: str | None = None) -> None:
        self.text = text if text is not None else render_answer(answer)

    def __call__(self, task) -> Reply:
        return Reply(self.text, 0.01)


def test_an_identifiable_answer_is_estimated_with_the_chosen_columns():
    answer = Answer(
        True, frozenset({"prior_purchases"}),
        (ColumnRole("prior_purchases", "confounder", "drives both"), ColumnRole("visited_site", "mediator", "after the e-mail")),
        (), ("no unmeasured confounding",), True,
    )
    result = ask(toy_table(), "email", "bought", STORY, DESCRIPTIONS, CannedResponder(answer))
    assert result.answer is not None and result.error is None
    assert result.estimate is not None and result.estimate.adjustment_set == ("prior_purchases",)
    assert result.naive is not None and result.naive.effect > result.estimate.effect  # the naive difference is inflated by the confounder
    report = format_consultation(result, "en")
    assert "Adjust for: prior_purchases" in report and "Adjusted effect" in report
    assert "Ajustar por" in format_consultation(result, "pt")


def test_a_not_identifiable_answer_estimates_nothing():
    answer = Answer(False, frozenset(), (ColumnRole("prior_purchases", "confounder", "x"),), ("loyalty_tier",), ("a confounder is missing",), True)
    result = ask(toy_table(), "email", "bought", STORY, DESCRIPTIONS, CannedResponder(answer))
    assert result.answer is not None and not result.answer.identifiable
    assert result.estimate is None and result.naive is None
    assert "What is missing: loyalty_tier" in format_consultation(result)


def test_names_outside_the_table_are_ignored_and_reported():
    answer = Answer(True, frozenset({"prior_purchases", "region"}), (), (), (), False)
    result = ask(toy_table(), "email", "bought", STORY, DESCRIPTIONS, CannedResponder(answer))
    assert result.estimate is not None and result.estimate.adjustment_set == ("prior_purchases",)
    assert result.ignored == ("region",)


def test_unreadable_text_is_reported_not_raised():
    result = ask(toy_table(), "email", "bought", STORY, DESCRIPTIONS, CannedResponder(None, text="I am not sure."))
    assert result.answer is None and result.error and "could not be read" in format_consultation(result)


def test_a_column_without_description_is_refused():
    with pytest.raises(ValueError):
        ask(toy_table(), "email", "bought", STORY, {k: v for k, v in DESCRIPTIONS.items() if k != "visited_site"}, CannedResponder(None, text=""))


def test_specs_name_the_published_paths():
    hub = responder_of("ollama:hf.co/coppead/causalista-4b-GGUF:nothink")
    assert isinstance(hub, OllamaModel) and hub.model == "hf.co/coppead/causalista-4b-GGUF" and hub.think is False
    local = responder_of("ollama:causalista:0.1")
    assert local.model == "causalista:0.1" and local.think is None
    assert responder_of("rule:tudo").label and responder_of("rule:nada").label
    with pytest.raises(SystemExit):
        responder_of("magic:thing")
