"""
Load and validate flashcard decks from JSON files.

This module is the data layer for the quiz app. It reads a deck file,
accepts either of the two supported JSON shapes (a bare array of cards
or an object with a "cards" key), and rejects anything malformed with a
clear, human-readable message instead of a raw Python traceback.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FlashcardError(Exception):
    """Raised when a deck file cannot be read or is not valid.

    The message is meant to be shown directly to the user, so it must
    never contain a stack trace or internal jargon.
    """


@dataclass(frozen=True)
class Flashcard:
    """A single question/answer pair.

    ``frozen=True`` makes instances immutable: once a card is loaded,
    nothing elsewhere in the program can change it by accident.
    """

    front: str
    back: str


def load_flashcards(filepath: str) -> list[Flashcard]:
    """Read a deck file and return a list of ``Flashcard`` objects.

    Args:
        filepath: Path to a ``.json`` deck file.

    Returns:
        A non-empty list of validated flashcards.

    Raises:
        FlashcardError: If the file is missing, is not valid JSON, does
            not match a supported shape, or contains an invalid card.
    """
    path = Path(filepath)

    try:
        raw_text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FlashcardError(f"Could not find a deck file at: {filepath}") from exc
    except OSError as exc:
        raise FlashcardError(f"Could not read {filepath}: {exc}") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise FlashcardError(
            f"{filepath} is not valid JSON (line {exc.lineno}, column {exc.colno})."
        ) from exc

    return _parse_cards(data, filepath)


def _parse_cards(data: Any, source: str) -> list[Flashcard]:
    """Turn already-parsed JSON data into a list of flashcards.

    Kept separate from file reading so the validation rules can be
    tested without touching the filesystem.
    """
    if isinstance(data, dict):
        if "cards" not in data:
            raise FlashcardError(f"{source} is a JSON object but has no 'cards' key.")
        raw_cards = data["cards"]
    elif isinstance(data, list):
        raw_cards = data
    else:
        raise FlashcardError(
            f"{source} must be a JSON array or an object with a "
            f"'cards' key, not {type(data).__name__}."
        )

    if not isinstance(raw_cards, list):
        raise FlashcardError(f"The 'cards' value in {source} must be a list.")

    if not raw_cards:
        raise FlashcardError(f"{source} does not contain any flashcards.")

    cards: list[Flashcard] = []
    for position, item in enumerate(raw_cards, start=1):
        cards.append(_build_card(item, position, source))
    return cards


def _build_card(item: Any, position: int, source: str) -> Flashcard:
    """Validate one raw card and return a ``Flashcard``."""
    if not isinstance(item, dict):
        raise FlashcardError(
            f"Card {position} in {source} must be an object, "
            f"not {type(item).__name__}."
        )

    for field in ("front", "back"):
        if field not in item:
            raise FlashcardError(
                f"Card {position} in {source} is missing the "
                f"required field '{field}'."
            )
        if not isinstance(item[field], str) or not item[field].strip():
            raise FlashcardError(
                f"Card {position} in {source} has an empty or "
                f"non-text '{field}' value."
            )

    return Flashcard(front=item["front"].strip(), back=item["back"].strip())
