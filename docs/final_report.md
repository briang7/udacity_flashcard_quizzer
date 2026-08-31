# AI-Assisted Development Project Report

**Student Name:** Brian Gease
**Project Title:** Flashcard Quizzer (command-line)
**Date:** 2026-08-31

## Executive Summary

The project is a command-line flashcard quiz. It loads a deck of
question/answer cards from a JSON file, serves the cards one at a time,
grades typed answers, tracks a score, and can repeat the cards the user
gets wrong. It reads two JSON layouts, offers three ordering modes,
colours its feedback, exits cleanly on `exit` or Ctrl+C, and can write a
results file.

The code is built on the course starter template. The starter's task
manager was removed; its `FileHandler` helper was kept and reused for the
`--export` feature. Three new modules were written: `flashcard_loader.py`
(data layer), `quiz_engine.py` (quiz rules), and a rewritten `main.py`
(CLI). The suite has 54 tests at 100% line coverage, and `flake8`,
`black`, and `isort` all pass.

AI (Claude, via Claude Code) was used throughout: to draft each module,
to reason about design choices, to generate the test suite, and to
diagnose failures. Every AI suggestion was read, run, and in several
cases corrected before it was accepted. The AI interaction log
(`ai_edit_log.md`) records six of the more consequential exchanges.

## Project Overview

### Problem Statement

Studying with paper flashcards gives no feedback loop: nothing tracks
which cards you keep missing, so review time is spent evenly instead of
where it is needed. A small CLI tool can fix that with an adaptive mode
that resurfaces weak cards, while staying fast to launch and easy to
script.

### Solution Approach

The design splits into three layers with one responsibility each:

- **Data layer** (`utils/flashcard_loader.py`) - read a file, accept
  either supported JSON shape, validate every card, and raise one
  friendly exception type on any failure.
- **Engine** (`utils/quiz_engine.py`) - decide card order (three
  interchangeable strategies), grade answers, keep score, and feed
  results back to the strategy.
- **CLI** (`main.py`) - parse flags, run the prompt loop, colour output,
  handle interrupts, print and optionally export a summary.

No layer imports a layer above it, and only the CLI does input or output.
That boundary is what makes the engine unit-testable and the CLI
integration-testable without a real terminal.

**Technology stack:** Python 3.10+, `argparse` (CLI), `colorama`
(cross-platform colour), `pytest` + `pytest-cov` (tests), `black` /
`isort` / `flake8` (quality).

### Final Features

- [x] Load a deck from a bare JSON array `[{...}]`
- [x] Load a deck from a wrapper object `{"cards": [...], "deck_name": ...}`
- [x] Friendly errors for missing file, malformed JSON, and invalid cards
- [x] Sequential, random, and adaptive quiz modes (Strategy pattern)
- [x] Adaptive mode repeats missed cards, capped by `max_repeats`
- [x] Green / red / cyan coloured feedback, with `--no-color`
- [x] Graceful exit on `exit`, Ctrl+C, or closed stdin
- [x] `--stats` summary table
- [x] `--export PATH` writes the stats as JSON (reuses starter `FileHandler`)

## AI Collaboration Experience

### AI Tools Used

- [x] Claude (Claude Code CLI)

### Collaboration Workflow

1. **Requests** were scoped to one module or one decision at a time, and
   always stated the constraint that mattered (for example: "never leak a
   traceback", "must be testable without a subprocess").
2. **Tasks given to AI:** initial implementation of each module, the full
   test suite, design questions (abstract vs concrete methods, exception
   chaining, loop termination), and failure diagnosis.
3. **Review and validation:** every file was read line by line before
   acceptance, run through `flake8`/`black`, exercised with a throwaway
   smoke script, then covered by tests. Coverage gaps were treated as
   review findings, not just numbers.
4. **Refinement:** when a suggestion was wrong or unclear, the follow-up
   named the specific line and asked why, rather than asking for a
   rewrite. This produced the `from exc` vs `from None` explanation and
   the `max_repeats` safety cap.

### Most Valuable AI Interactions

#### Example 1: Loader error boundary

**Context:** Phase 1 needed a loader that tolerates two JSON shapes and
never crashes the program.
**AI Prompt:** Build a loader for both `[...]` and `{"cards": [...]}`,
validate string `front`/`back`, and raise instead of printing.
**AI Response:** A `load_flashcards()` function, a frozen `Flashcard`
dataclass, a custom `FlashcardError`, and file reading split from
validation into `_parse_cards` / `_build_card`.
**Your Changes:** Accepted the structure; fixed the field names to
lowercase to match the spec; confirmed the I/O split was worth the extra
function.
**Outcome:** 13 tests, 100% coverage, and every later layer only had to
catch one exception type.

#### Example 2: A test that passed for the wrong reason

**Context:** First run of the loader tests: 12 passed, 1 failed.
**AI Prompt:** (none - a generated test failed)
**AI Response:** The failing test, `test_load_wrong_top_level_type`,
passed a raw string to the test helper, which writes strings verbatim.
The file was therefore invalid JSON, so the test hit the parse-error
path instead of the wrong-type path it was named for - and left one
line uncovered.
**Your Changes:** Passed a bare integer so the helper serialises it with
`json.dumps`, producing valid JSON of the wrong shape.
**Outcome:** 13/13 pass, coverage 98% to 100%. The coverage report was
what exposed the mislabelled test.

#### Example 3: Termination bound for adaptive mode

**Context:** `AdaptiveMode` re-queues missed cards, which risks an
infinite quiz.
**AI Prompt:** What stops the loop if the user never gets a card right?
**AI Response:** Add `max_repeats` (default 2), tracked per card, so a
card is re-queued at most that many times; the quiz runs for at most
`N * (1 + max_repeats)` questions.
**Your Changes:** Accepted, and added a test that answers every card
wrong and asserts the run still ends.
**Outcome:** A provable upper bound instead of an assumption.

#### Example 4: Concrete default over abstract method

**Context:** Designing the `QuizMode` base class.
**AI Prompt:** Should `record_result` be abstract?
**AI Response:** No - make it a concrete no-op. Sequential and random
modes do not use the result; only `AdaptiveMode` overrides it.
**Your Changes:** Accepted; only `next_card` is `@abstractmethod`.
**Outcome:** Two of the three modes carry no dead override code.

### Challenges with AI Collaboration

AI was strongest at producing idiomatic first drafts and at explaining a
trade-off when asked directly. It was weakest at self-checking its own
tests: the mislabelled test in Example 2 looked fine and would have gone
unnoticed without the coverage report. It also defaulted to conservative
line wrapping that `black` then undid, and it left the starter's unused
imports in place until `flake8` flagged them. The pattern: AI is reliable
for the happy path and for reasoning on request, but the human has to own
verification - run it, cover it, lint it.

## Software Engineering Practices

### Code Quality Measures

- [x] Formatting: `black` and `isort`, whole project
- [x] Linting: `flake8`, zero warnings (`setup.cfg` sets line length 88
      to match `black`, and ignores E203/W503)
- [x] Type hints on every function signature
- [x] Docstrings on every module, class, and function
- [x] Error handling: one custom exception per boundary, no bare
      `except`, no leaked tracebacks

### Testing Strategy

- **Unit tests** for the loader (every branch: both shapes, missing file,
  unreadable path, bad JSON, missing/blank/non-text fields, empty deck)
  and the engine (each mode, the factory, the score maths, the
  termination cap).
- **Integration tests** that call `main([...])` in-process with
  `monkeypatch` on `builtins.input` and `capsys` on the output, covering
  a full session, the `exit` command, Ctrl+C, a bad file, and `--export`
  (including a forced write failure).
- **Coverage:** 54 tests, 100% line coverage on all application modules;
  measured with `pytest --cov`.
- Development was test-adjacent rather than strict TDD: each module was
  drafted, smoke-tested by hand, then locked down with tests before the
  next module started.

### Design Patterns Used

- **Strategy** - `QuizMode` is an abstract base with one abstract method,
  `next_card()`. `SequentialMode`, `RandomMode`, and `AdaptiveMode` are
  interchangeable implementations. The CLI and `QuizSession` hold a
  `QuizMode` and never branch on which concrete type it is. This is a
  real fit: "choose the next card" genuinely has three algorithms, and
  adaptive ordering needs per-answer feedback that a one-shot sort could
  not express.
- **Factory** - `create_quiz_mode(name, cards)` maps the `-m` string to
  the matching class through a dictionary. Without it, the CLI would hold
  the `if/elif` chain that Strategy exists to remove. Adding a fourth
  mode is one dictionary entry.

### Code Structure and Organization

Four modules, each with a single job (CLI, loader, engine, file I/O).
Separation of concerns is enforced by the import direction and by keeping
`print`/`input` out of everything but `main.py`. The one refactor of note
was pulling `flashcard_loader`'s validation out of its file-reading
function so the rules could be tested without writing files, and pulling
`export_stats` out of `main()` for the same reason.

## Technical Challenges and Solutions

### Challenge 1: flake8 and Black disagreed on line length

**Problem:** `black` formats to 88 columns; `flake8` with no config
defaults to 79, so it flagged lines `black` had just produced.
**Solution:** A `setup.cfg` with `max-line-length = 88` and
`extend-ignore = E203, W503` (the two rules that always fight `black`).
**AI Involvement:** AI supplied the exact config and explained why those
two codes are the standard Black-compatibility set.
**Lessons Learned:** Align the tools once, at the start, or fight them on
every file.

### Challenge 2: Testing randomness and a prompt loop

**Problem:** `RandomMode` shuffles, and the CLI reads keyboard input -
both are hard to assert on.
**Solution:** `RandomMode` accepts an optional `rng`, so tests inject a
seeded `random.Random`. `main` accepts an optional `argv`, so tests pass
arguments directly and monkeypatch `input`.
**AI Involvement:** AI proposed both seams when asked to make the code
testable without subprocesses.
**Lessons Learned:** Injectable non-determinism is the difference between
a testable design and an untestable one; add the seam before the test.

## Code Quality Analysis

### Metrics

- Application code: ~300 lines across `main.py` and `utils/*.py`
- Test code: ~450 lines across 4 files
- Test coverage: 100% line coverage on application modules
- Classes: 6 (`Flashcard`, `FlashcardError`, `QuizMode` + 3 modes,
  `QuizSession`); Factory and CLI are functions
- Linting: `flake8 .` reports zero warnings

### Self-Assessment

- **Code Readability:** 5 - short functions, full docstrings and type
  hints, names that state intent.
- **Code Maintainability:** 5 - strict layer boundaries; a new mode or a
  new deck format is a localised change.
- **Test Quality:** 4 - full branch coverage and real integration paths,
  but development was test-adjacent, not strict TDD.
- **Documentation:** 4 - README, AI log, and this report are complete;
  no architecture diagram.

## Learning Outcomes

### Technical Skills Developed

Abstract base classes and `@abstractmethod`; frozen dataclasses; Python
exception chaining (`raise ... from`); `argparse` with `choices` and
`store_true`; `pytest` fixtures, `parametrize`, `monkeypatch`, `capsys`,
`tmp_path`; measuring and reading coverage; reconciling `black` and
`flake8`.

### AI Collaboration Skills

Scope a prompt to one decision and state the binding constraint. Ask
"why this line" instead of "rewrite this". Treat AI output as a pull
request: read it, run it, cover it, lint it. Trust AI for first drafts
and for reasoning on request; do not trust it to verify itself.

### Software Engineering Insights

Design patterns are only worth it when the variation is real - Strategy
earned its place here because there are genuinely three algorithms and
adaptive needs feedback. Separation of concerns is what makes tests
cheap. A feedback loop without an explicit bound is a bug.

## Reflection

### What Worked Well

Deciding the error boundary and the test seams before writing code. The
layer split meant the engine tests never touched a file and the CLI
tests never touched a terminal. Using the coverage report as a review
tool caught a test that was quietly checking the wrong thing.

### What Could Be Improved

Practise strict TDD - write the failing test first - rather than
test-adjacent development. Run `flake8` on the whole tree earlier so
starter-code warnings surface before the final pass. Add an architecture
diagram.

### Future Enhancements

Fuzzy answer matching (accept near-misses); multiple decks in one
session; a persisted history file so adaptive mode carries weak cards
across runs; a `--shuffle-within-adaptive` option; spaced-repetition
scheduling instead of a fixed repeat cap.

## Conclusion

AI made the first draft of every module fast and mostly idiomatic, and it
was a good explainer when asked pointed questions. The value came from
treating it as a fast junior pair whose work still needs review: the
bugs it did produce (a mislabelled test, leftover imports, wrapping that
`black` undid) were all caught by running the code, covering it, and
linting it. The practices worth keeping: fix the tool config and the
design seams first, keep layers from reaching upward, and let the
coverage report double as a code reviewer.

## Appendices

### Appendix A: AI Interaction Log

See `docs/ai_edit_log.md`. Key entries: the loader error boundary
(entry 1), the `from exc` vs `from None` decision (entry 2), the
mislabelled test found via coverage (entry 3), and the adaptive
termination bound (entry 5).

### Appendix B: Code Statistics

`pytest --cov=. --cov-report=term-missing`: 54 passed, 100% line coverage
on `main.py`, `utils/flashcard_loader.py`, `utils/quiz_engine.py`, and
`utils/file_handler.py`. `flake8 .`: clean. `black --check .` and
`isort --check .`: clean.

### Appendix C: Additional Resources

Python `abc`, `dataclasses`, `argparse`, and `pytest` documentation; the
course `design_patterns.md` guide; `colorama` README.
