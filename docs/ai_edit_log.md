## Your Log Entries

### 2026-08-30 - Flashcard loader and error boundary

**Context:** Phase 1 data layer. Load a deck from JSON.
**AI Tool Used:** Claude (Claude Code).
**Prompt/Request:** Build a loader that accepts both `[...]` and `{"cards": [...]}`, checks each card has string `front`/`back`, and never leaks a traceback.
**AI Response:** `flashcard_loader.py` with `load_flashcards()`, a frozen `Flashcard` dataclass, a custom `FlashcardError`, and file I/O split from validation (`_parse_cards`, `_build_card`).
**Changes Made:** Kept as proposed. Fixed the required field names to lowercase `front`/`back`, against the brief's prose "a Back".
**Reasoning:** One custom exception gives `main.py` a single thing to catch. Splitting I/O from validation lets `_parse_cards` be tested without touching disk.
**Outcome:** 13 tests, 100% coverage on the module.
**Lessons Learned:** Fixing the error-handling seam first made every later layer simpler.

---

### 2026-08-30 - Exception chaining: `from exc` vs `from None`

**Context:** Reviewing the `raise FlashcardError(...) from ...` lines.
**AI Tool Used:** Claude.
**Prompt/Request:** Why `from exc` on the JSON error but `from None` on the factory's bad-mode error?
**AI Response:** `from exc` keeps the original as `__cause__` when it carries something useful (the JSON error's line and column). `from None` drops the chain when the underlying error (a `KeyError`) adds nothing.
**Changes Made:** None. Applied the same rule to the file-not-found branch (`from exc`).
**Reasoning:** Keep context only when a future debugger would want it. The user sees the same message either way.
**Lessons Learned:** "Catch and re-raise" has two forms and the choice is deliberate.

---

### 2026-08-30 - Bug in an AI-written test

**Context:** Step 3, first run of `test_flashcard_loader.py`. One test failed.
**AI Tool Used:** Claude.
**Prompt/Request:** N/A - a generated test failed on first run.
**AI Response (original):** `test_load_wrong_top_level_type` passed a raw string to the `write_deck` helper. The helper writes strings verbatim, so the file was invalid JSON. The test hit the JSON-parse path, not the wrong-type path it was named for, and left one line uncovered.
**Changes Made:** Passed a bare `int` (`42`) so the helper serialises it through `json.dumps`, producing valid JSON of the wrong shape.
**Reasoning:** The helper has two input modes; the test picked the wrong one for its stated intent.
**Outcome:** 13/13 pass, coverage 98% to 100%.
**Lessons Learned:** A passing-looking test can exercise the wrong code. The coverage gap pointed straight at it.

---

### 2026-08-30 - Strategy pattern: concrete default over abstract method

**Context:** Designing the `QuizMode` base class.
**AI Tool Used:** Claude.
**Prompt/Request:** Should `record_result` be abstract?
**AI Response:** No. Make it a concrete no-op on the base. Sequential and Random modes do not adapt to answers, so forcing empty overrides is noise. `AdaptiveMode` overrides it.
**Changes Made:** Accepted. Only `next_card` is `@abstractmethod`.
**Reasoning:** Abstract should mean "no sensible default exists". Here one does.
**Lessons Learned:** Not every method on an ABC needs to be abstract.

---

### 2026-08-30 - AdaptiveMode termination bound

**Context:** `AdaptiveMode` re-queues cards the user gets wrong.
**AI Tool Used:** Claude.
**Prompt/Request:** What stops an infinite loop if a card is never answered correctly?
**AI Response:** Added `max_repeats` (default 2), tracked per card by `id()`. A card is re-queued at most that many times. Upper bound: `N * (1 + max_repeats)` questions.
**Changes Made:** Accepted. Added `test_adaptive_mode_stops_after_max_repeats`.
**Reasoning:** A quiz has to end. The cap is a guarantee, not a hope.
**Lessons Learned:** Any feedback loop needs an explicit bound.

---

### 2026-08-30 - Testability seams before tests

**Context:** Phases 2 and 3. Keeping randomness and the CLI testable.
**AI Tool Used:** Claude.
**Prompt/Request:** Make shuffling and the CLI testable without subprocesses or a fake terminal.
**AI Response:** `RandomMode(cards, rng=None)` so a test can inject a seeded `random.Random`. `main(argv=None)` so a test passes an arg list directly and `parse_args(None)` still falls back to `sys.argv`. Integration tests monkeypatch `builtins.input` and read output via `capsys`.
**Changes Made:** Kept both. Integration tests call `main([...])` in-process.
**Reasoning:** Deterministic tests need injectable non-determinism. In-process calls give real tracebacks and coverage numbers.
**Lessons Learned:** Design the seams before writing the tests, not after.

---

## Summary Statistics

- **Total AI interactions:** 6 logged; many smaller ones during iteration
- **Lines of AI-generated code used:** ~300 (`main.py`, `utils/flashcard_loader.py`, `utils/quiz_engine.py`, tests)
- **Lines of AI-generated code modified:** ~15 (one test fix, two unused-import removals, config files)
- **Most helpful AI interaction:** loader error-boundary design (entry 1)
- **Most challenging AI interaction:** the silently-wrong test (entry 3)
- **Biggest lesson learned:** decide the seams - error types, injection points - before writing code or tests
