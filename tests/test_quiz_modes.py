"""
Unit tests for utils.quiz_engine.

Covers the three ordering strategies (Strategy pattern), the
create_quiz_mode Factory, and the QuizSession scorekeeper.
"""

import random

import pytest

from utils.flashcard_loader import Flashcard
from utils.quiz_engine import (
    AdaptiveMode,
    QuizMode,
    QuizSession,
    RandomMode,
    SequentialMode,
    available_modes,
    create_quiz_mode,
)


@pytest.fixture
def deck():
    """A small, predictable three-card deck."""
    return [
        Flashcard("Q1", "A1"),
        Flashcard("Q2", "A2"),
        Flashcard("Q3", "A3"),
    ]


def drain(mode, is_correct):
    """Pull every card from a mode until exhausted.

    ``is_correct`` is called with each card; its bool result is fed
    back via ``record_result``. Returns the fronts served, in order.
    Fails if the mode serves more than 100 cards (non-termination).
    """
    served = []
    for _ in range(100):
        card = mode.next_card()
        if card is None:
            return served
        served.append(card.front)
        mode.record_result(card, is_correct(card))
    raise AssertionError("mode did not terminate within 100 cards")


# --- QuizMode base -------------------------------------------------------


def test_quizmode_is_abstract(deck):
    """QuizMode itself cannot be instantiated."""
    with pytest.raises(TypeError):
        QuizMode(deck)


def test_mode_rejects_empty_deck():
    """Building a mode with no cards raises ValueError."""
    with pytest.raises(ValueError, match="at least one flashcard"):
        SequentialMode([])


# --- SequentialMode ----------------------------------------------------


def test_sequential_mode_preserves_order(deck):
    """Serves every card once, in deck order."""
    assert drain(SequentialMode(deck), lambda c: True) == ["Q1", "Q2", "Q3"]


def test_sequential_mode_ignores_results(deck):
    """Wrong answers change neither order nor length."""
    assert drain(SequentialMode(deck), lambda c: False) == ["Q1", "Q2", "Q3"]


# --- RandomMode ------------------------------------------------------


def test_random_mode_serves_all_cards_once(deck):
    """Every card appears exactly once (order may differ)."""
    served = drain(RandomMode(deck, rng=random.Random(0)), lambda c: True)
    assert sorted(served) == ["Q1", "Q2", "Q3"]


def test_random_mode_is_deterministic_with_seed(deck):
    """The same seed yields the same order."""
    a = drain(RandomMode(deck, rng=random.Random(42)), lambda c: True)
    b = drain(RandomMode(deck, rng=random.Random(42)), lambda c: True)
    assert a == b


def test_random_mode_without_seed_still_works(deck):
    """The default unseeded RNG path runs without error."""
    served = drain(RandomMode(deck), lambda c: True)
    assert sorted(served) == ["Q1", "Q2", "Q3"]


# --- AdaptiveMode --------------------------------------------------


def test_adaptive_mode_behavior(deck):
    """A missed card is repeated; a correct one is not."""
    mode = AdaptiveMode(deck, max_repeats=2)
    served = drain(mode, lambda c: c.front != "Q2")  # always miss Q2
    assert served.count("Q1") == 1
    assert served.count("Q3") == 1
    assert served.count("Q2") == 3  # first pass + 2 repeats


def test_adaptive_mode_stops_after_max_repeats(deck):
    """Repeats are capped, so the quiz ends even if nothing is right."""
    served = drain(AdaptiveMode(deck, max_repeats=1), lambda c: False)
    assert served.count("Q1") == 2  # first pass + 1 repeat, then stop
    assert served.count("Q2") == 2
    assert served.count("Q3") == 2


def test_adaptive_mode_all_correct_is_single_pass(deck):
    """All-correct adaptive behaves like one pass through the deck."""
    assert drain(AdaptiveMode(deck), lambda c: True) == ["Q1", "Q2", "Q3"]


def test_adaptive_record_result_correct_is_noop(deck):
    """record_result(card, True) does not re-queue the card."""
    mode = AdaptiveMode(deck)
    first = mode.next_card()
    mode.record_result(first, True)
    assert first.front not in drain(mode, lambda c: True)


def test_adaptive_ignores_unknown_card(deck):
    """A card not from this deck is safely ignored, not re-queued."""
    mode = AdaptiveMode(deck)
    mode.record_result(Flashcard("stranger", "danger"), False)
    assert "stranger" not in drain(mode, lambda c: True)


# --- Factory --------------------------------------------------------


@pytest.mark.parametrize(
    "name, expected_class",
    [
        ("sequential", SequentialMode),
        ("random", RandomMode),
        ("adaptive", AdaptiveMode),
        ("ADAPTIVE", AdaptiveMode),  # names are case-insensitive
    ],
)
def test_quiz_mode_factory(deck, name, expected_class):
    """create_quiz_mode returns the right class for each name."""
    mode = create_quiz_mode(name, deck)
    assert isinstance(mode, expected_class)
    assert isinstance(mode, QuizMode)


def test_quiz_mode_factory_rejects_unknown(deck):
    """An unknown name raises ValueError naming the bad mode."""
    with pytest.raises(ValueError, match="Unknown quiz mode 'banana'"):
        create_quiz_mode("banana", deck)


def test_available_modes_is_sorted():
    """available_modes lists the three names in sorted order."""
    assert available_modes() == ["adaptive", "random", "sequential"]


# --- QuizSession ---------------------------------------------------


def test_session_tracks_score(deck):
    """submit() tallies correct/wrong and returns the per-answer verdict."""
    session = QuizSession(SequentialMode(deck))

    assert session.submit(session.next_card(), "a1") is True  # casefold
    assert session.submit(session.next_card(), "nope") is False
    assert session.submit(session.next_card(), "  A3  ") is True  # trimmed

    assert (session.total, session.correct, session.wrong) == (3, 2, 1)


def test_session_accuracy_and_stats(deck):
    """accuracy is a percent; stats() bundles the summary dict."""
    session = QuizSession(SequentialMode(deck))
    session.submit(session.next_card(), "a1")

    assert session.accuracy == 100.0
    assert session.stats() == {
        "total_questions": 1,
        "correct": 1,
        "wrong": 0,
        "accuracy_percent": 100.0,
    }


def test_session_accuracy_zero_before_any_answer(deck):
    """accuracy is 0.0, not a ZeroDivisionError, before any answer."""
    assert QuizSession(SequentialMode(deck)).accuracy == 0.0


def test_session_feeds_results_to_adaptive_mode(deck):
    """A wrong answer through submit() makes AdaptiveMode repeat the card."""
    session = QuizSession(AdaptiveMode(deck, max_repeats=1))

    first = session.next_card()
    session.submit(first, "definitely wrong")

    later = []
    while (card := session.next_card()) is not None:
        later.append(card.front)
        session.submit(card, "whatever")

    assert first.front in later  # the missed card came back around
