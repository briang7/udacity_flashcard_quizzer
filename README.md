# Flashcard Quizzer

A command-line flashcard quiz. Loads a deck from JSON, asks questions one
at a time, scores you, and repeats the cards you miss.

## Features

- Two deck formats: a bare JSON array, or `{"cards": [...]}` with metadata.
- Three quiz modes (Strategy pattern): `sequential`, `random`, `adaptive`.
- Adaptive mode re-asks missed cards, capped so the quiz always ends.
- Coloured feedback: green for correct, red for wrong.
- Graceful exit: type `exit` or press Ctrl+C - no traceback, score still shown.
- `--stats` end-of-quiz summary table.
- `--export PATH` writes the results to a JSON file.
- Friendly errors for missing files, malformed JSON, and invalid cards.

## Requirements

- Python 3.10 or newer.
- Dependencies in `requirements.txt`:
  - runtime: `colorama`
  - development: `pytest`, `pytest-cov`, `black`, `isort`, `flake8`

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

## Usage

```bash
python main.py -f data/python_basics.json -m adaptive
python main.py -f data/trivia.json --stats
python main.py -f data/python_basics.json -m random --export results.json
```

| Flag | Meaning | Default |
|------|---------|---------|
| `-f`, `--file` | path to a JSON deck (required) | - |
| `-m`, `--mode` | `sequential`, `random`, or `adaptive` | `sequential` |
| `--stats` | print a summary table at the end | off |
| `--export PATH` | save the stats as JSON to `PATH` | off |
| `--no-color` | disable coloured output | off |

Type `exit` at any prompt to stop early. Ctrl+C does the same, and still
prints your score.

## Deck format

Array:

```json
[
  {"front": "What is 2 + 2?", "back": "4"}
]
```

Object:

```json
{
  "deck_name": "Math",
  "cards": [
    {"front": "What is 2 + 2?", "back": "4"}
  ]
}
```

Every card needs a non-empty string `front` and `back`. Sample decks are
in `data/`; `data/invalid_example.json` is broken on purpose to
demonstrate error handling.

## Testing

```bash
python -m pytest                              # run all tests
python -m pytest --cov=. --cov-report=html    # coverage -> htmlcov/index.html
```

54 tests, 100% line coverage.

## Code quality

```bash
python -m isort .
python -m black .
python -m flake8 .
```

`setup.cfg` aligns flake8 with Black at 88 columns and excludes the
`__main__` guard from coverage.

## Design patterns

- **Strategy** - `QuizMode` (abstract) with `SequentialMode`,
  `RandomMode`, and `AdaptiveMode`. See `utils/quiz_engine.py`.
- **Factory** - `create_quiz_mode(name, cards)` turns a CLI string into
  the matching mode object. Same file.

## Layout

```
main.py                       CLI: argparse, game loop, colour, exit
utils/flashcard_loader.py     load and validate a deck
utils/quiz_engine.py          QuizMode strategies, Factory, QuizSession
utils/file_handler.py         JSON read/write (used by --export)
data/                         sample decks
tests/                        pytest suite
docs/                         AI log, final report, patterns guide
```

## License

See [LICENSE.txt](LICENSE.txt).
