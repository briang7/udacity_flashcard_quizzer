"""
Quiz engine: the rules for running a flashcard quiz.

This module holds the *ordering strategies* (Strategy pattern) that
decide which card to serve next, a Factory that builds the right
strategy from a mode name, and a QuizSession that runs a quiz and
tracks the score.
"""

import random
from abc import ABC, abstractmethod
from collections import deque

from utils.flashcard_loader import Flashcard


class QuizMode(ABC):
    """Abstract strategy: decides the order flashcards are served in.

    A mode is *pull-based*. The caller repeatedly asks for the next
    card with ``next_card()`` and reports how the user did with
    ``record_result()``. Modes that don't adapt to answers simply
    ignore the result.
    """

    #: Short identifier used by the Factory (overridden by each subclass).
    name: str = "base"

    def __init__(self, cards: list[Flashcard]) -> None:
        if not cards:
            raise ValueError("A quiz needs at least one flashcard.")
        self._cards = list(cards)

    @abstractmethod
    def next_card(self) -> Flashcard | None:
        """Return the next card to ask, or ``None`` when finished."""

    def record_result(self, card: Flashcard, correct: bool) -> None:
        """Tell the mode how the user did on ``card``.

        The base implementation does nothing. ``AdaptiveMode``
        overrides this to re-queue cards the user got wrong.
        """


class SequentialMode(QuizMode):
    """Serve every card once, in the order it appears in the deck."""

    name = "sequential"

    def __init__(self, cards: list[Flashcard]) -> None:
        super().__init__(cards)
        self._index = 0

    def next_card(self) -> Flashcard | None:
        if self._index >= len(self._cards):
            return None
        card = self._cards[self._index]
        self._index += 1
        return card


class RandomMode(QuizMode):
    """Serve every card once, in a shuffled order."""

    name = "random"

    def __init__(
        self,
        cards: list[Flashcard],
        rng: random.Random | None = None,
    ) -> None:
        super().__init__(cards)
        self._rng = rng or random.Random()
        self._queue = list(self._cards)
        self._rng.shuffle(self._queue)
        self._index = 0

    def next_card(self) -> Flashcard | None:
        if self._index >= len(self._queue):
            return None
        card = self._queue[self._index]
        self._index += 1
        return card


class AdaptiveMode(QuizMode):
    """Serve every card once, then repeat the ones answered wrong.

    A card the user misses is pushed to the back of the queue so it
    comes around again. Each card can be repeated at most
    ``max_repeats`` times, which guarantees the quiz eventually ends
    even if the user keeps missing a card.
    """

    name = "adaptive"

    def __init__(
        self,
        cards: list[Flashcard],
        max_repeats: int = 2,
    ) -> None:
        super().__init__(cards)
        self._max_repeats = max_repeats
        self._queue: deque[Flashcard] = deque(self._cards)
        self._repeats_left = {id(card): max_repeats for card in self._cards}

    def next_card(self) -> Flashcard | None:
        if not self._queue:
            return None
        return self._queue.popleft()

    def record_result(self, card: Flashcard, correct: bool) -> None:
        if correct:
            return
        remaining = self._repeats_left.get(id(card), 0)
        if remaining > 0:
            self._repeats_left[id(card)] = remaining - 1
            self._queue.append(card)


class QuizSession:
    """Runs a quiz with a given mode and tracks the score.

    Responsibilities are deliberately narrow: a mode decides card
    *order*, this class decides whether an answer is *correct*, keeps
    the running tally, and forwards each result back to the mode so
    adaptive ordering works. It does no input or output of its own.
    """

    def __init__(self, mode: QuizMode) -> None:
        self._mode = mode
        self.total = 0
        self.correct = 0
        self.wrong = 0

    def next_card(self) -> Flashcard | None:
        """Return the next card to ask, or ``None`` when finished."""
        return self._mode.next_card()

    def submit(self, card: Flashcard, answer: str) -> bool:
        """Grade ``answer`` against ``card``, update stats, tell the mode.

        Returns ``True`` if the answer was correct.
        """
        is_correct = self.check_answer(answer, card.back)
        self.total += 1
        if is_correct:
            self.correct += 1
        else:
            self.wrong += 1
        self._mode.record_result(card, is_correct)
        return is_correct

    @staticmethod
    def check_answer(given: str, expected: str) -> bool:
        """Compare answers ignoring surrounding space and letter case."""
        return given.strip().casefold() == expected.strip().casefold()

    @property
    def accuracy(self) -> float:
        """Percent correct so far; ``0.0`` before any answer is given."""
        if self.total == 0:
            return 0.0
        return self.correct / self.total * 100

    def stats(self) -> dict[str, float]:
        """Summary suitable for printing or exporting to JSON."""
        return {
            "total_questions": self.total,
            "correct": self.correct,
            "wrong": self.wrong,
            "accuracy_percent": round(self.accuracy, 1),
        }


########################################

_MODES: dict[str, type[QuizMode]] = {
    SequentialMode.name: SequentialMode,
    RandomMode.name: RandomMode,
    AdaptiveMode.name: AdaptiveMode,
}


def available_modes() -> list[str]:
    """Return the valid mode names, sorted (for CLI help and choices)."""
    return sorted(_MODES)


def create_quiz_mode(mode_name: str, cards: list[Flashcard]) -> QuizMode:
    """Factory: build the ``QuizMode`` that matches ``mode_name``.

    The CLI hands us a string like ``"adaptive"``; this returns a
    ready-to-use strategy object. Callers never import or name the
    concrete mode classes themselves.

    Raises:
        ValueError: if ``mode_name`` is not a known mode.
    """
    try:
        mode_class = _MODES[mode_name.lower()]
    except KeyError:
        valid = ", ".join(available_modes())
        raise ValueError(
            f"Unknown quiz mode '{mode_name}'. Choose one of: {valid}."
        ) from None
    return mode_class(cards)
