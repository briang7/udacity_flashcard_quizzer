"""
Unit tests for utils.flashcard_loader.

Covers both supported JSON shapes (a bare array and {"cards": [...]})
plus every error path: missing file, unreadable path, malformed JSON,
wrong top-level type, missing "cards" key, a non-list "cards" value,
an empty deck, and cards with missing, blank, or non-text fields.
"""

import json

import pytest

from utils.flashcard_loader import Flashcard, FlashcardError, load_flashcards


def write_deck(tmp_path, name, content):
    """Write a deck file into tmp_path and return its path as a string.

    If ``content`` is a str it is written verbatim (so a test can make
    deliberately broken JSON); otherwise it is serialized with
    ``json.dumps``.
    """
    deck_path = tmp_path / name
    if isinstance(content, str):
        deck_path.write_text(content, encoding="utf-8")
    else:
        deck_path.write_text(json.dumps(content), encoding="utf-8")
    return str(deck_path)


# --- happy paths -----------------------------------------------------------


def test_load_valid_flashcards_array(tmp_path):
    """A bare JSON array of cards loads into a list of Flashcards."""
    path = write_deck(
        tmp_path,
        "deck.json",
        [
            {"front": "2 + 2", "back": "4"},
            {"front": "capital of France", "back": "Paris"},
        ],
    )

    cards = load_flashcards(path)

    assert isinstance(cards, list)
    assert len(cards) == 2
    assert cards[0] == Flashcard(front="2 + 2", back="4")
    assert cards[1].back == "Paris"


def test_load_valid_flashcards_wrapper_object(tmp_path):
    """The {"cards": [...]} shape loads the same as a bare array."""
    path = write_deck(
        tmp_path,
        "deck.json",
        {"deck_name": "Math", "cards": [{"front": "3 x 3", "back": "9"}]},
    )

    cards = load_flashcards(path)

    assert len(cards) == 1
    assert cards[0] == Flashcard(front="3 x 3", back="9")


def test_load_strips_surrounding_whitespace(tmp_path):
    """Leading and trailing whitespace in a field is trimmed on load."""
    path = write_deck(
        tmp_path,
        "deck.json",
        [{"front": "  spaced  ", "back": "\ttrimmed\n"}],
    )

    cards = load_flashcards(path)

    assert cards[0] == Flashcard(front="spaced", back="trimmed")


# --- error paths ---------------------------------------------------------


def test_load_missing_file(tmp_path):
    """A path that does not exist raises FlashcardError, not OSError."""
    missing = str(tmp_path / "does_not_exist.json")

    with pytest.raises(FlashcardError, match="Could not find"):
        load_flashcards(missing)


def test_load_unreadable_path(tmp_path):
    """Pointing at a directory instead of a file is a friendly error."""
    with pytest.raises(FlashcardError, match="Could not read"):
        load_flashcards(str(tmp_path))


def test_load_invalid_json(tmp_path):
    """Malformed JSON raises FlashcardError, not json.JSONDecodeError."""
    path = write_deck(tmp_path, "bad.json", '[{"front": "x", "back": "y"},]')

    with pytest.raises(FlashcardError, match="not valid JSON"):
        load_flashcards(path)


def test_load_missing_required_field(tmp_path):
    """A card without a "back" field is rejected with a clear message."""
    path = write_deck(tmp_path, "deck.json", [{"front": "no answer here"}])

    with pytest.raises(FlashcardError, match="missing the required field 'back'"):
        load_flashcards(path)


def test_load_blank_required_field(tmp_path):
    """A card whose "back" is only whitespace is rejected."""
    path = write_deck(tmp_path, "deck.json", [{"front": "q", "back": "   "}])

    with pytest.raises(FlashcardError, match="empty or non-text 'back'"):
        load_flashcards(path)


def test_load_card_is_not_an_object(tmp_path):
    """A non-object entry inside the cards list is rejected."""
    path = write_deck(tmp_path, "deck.json", ["just a string"])

    with pytest.raises(FlashcardError, match="must be an object"):
        load_flashcards(path)


def test_load_wrapper_without_cards_key(tmp_path):
    """An object with no "cards" key is a clear error."""
    path = write_deck(tmp_path, "deck.json", {"deck_name": "oops"})

    with pytest.raises(FlashcardError, match="no 'cards' key"):
        load_flashcards(path)


def test_load_cards_key_not_a_list(tmp_path):
    """The "cards" value must be a list, not a string or object."""
    path = write_deck(tmp_path, "deck.json", {"cards": "nope"})

    with pytest.raises(FlashcardError, match="must be a list"):
        load_flashcards(path)


def test_load_wrong_top_level_type(tmp_path):
    """Top-level JSON that is neither array nor object is rejected."""
    path = write_deck(tmp_path, "deck.json", 42)

    with pytest.raises(FlashcardError, match="must be a JSON array"):
        load_flashcards(path)


def test_load_empty_deck(tmp_path):
    """An empty card list is rejected because there is nothing to quiz."""
    path = write_deck(tmp_path, "deck.json", [])

    with pytest.raises(FlashcardError, match="does not contain any flashcards"):
        load_flashcards(path)
