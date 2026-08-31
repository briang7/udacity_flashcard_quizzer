"""
Integration tests: drive main() end to end with canned input.

These exercise the whole stack - argparse, the loader, the quiz
engine, scoring, and the printed summary - with no real terminal.
The last few tests cover main.py's small colour helpers directly.
"""

import json

import main as app


def write_deck(tmp_path, cards):
    """Write a bare-array deck to tmp_path; return its path as a string."""
    path = tmp_path / "deck.json"
    path.write_text(json.dumps(cards), encoding="utf-8")
    return str(path)


def fake_input(answers):
    """Build an input() replacement that returns queued answers.

    When the queue runs out it raises EOFError, exactly as a real
    closed stdin would, so an under-supplied test ends gracefully
    instead of raising StopIteration.
    """
    queue = iter(answers)

    def _input(prompt=""):
        try:
            return next(queue)
        except StopIteration:
            raise EOFError

    return _input


THREE_CARDS = [
    {"front": "2 + 2", "back": "4"},
    {"front": "capital of France", "back": "Paris"},
    {"front": "opposite of up", "back": "down"},
]


# --- full end-to-end runs ---------------------------------------------


def test_full_session(tmp_path, monkeypatch, capsys):
    """Answer 3 questions (2 right, 1 wrong); stats must show 66.7%."""
    deck = write_deck(tmp_path, THREE_CARDS)
    monkeypatch.setattr("builtins.input", fake_input(["4", "wrong", "down"]))

    exit_code = app.main(["-f", deck, "-m", "sequential", "--stats"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Score: 2/3 (66.7%)" in out
    assert "Total questions: 3" in out
    assert "Correct: 2" in out
    assert "Wrong: 1" in out
    assert "Accuracy percent: 66.7" in out


def test_exit_command_stops_early(tmp_path, monkeypatch, capsys):
    """Typing 'exit' ends the quiz but still prints a summary."""
    deck = write_deck(tmp_path, THREE_CARDS)
    monkeypatch.setattr("builtins.input", fake_input(["4", "exit"]))

    exit_code = app.main(["-f", deck])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Exiting early" in out
    assert "Score: 1/1 (100.0%)" in out


def test_missing_file_reports_error(tmp_path, capsys):
    """A bad deck path exits 1 with a friendly stderr message."""
    exit_code = app.main(["-f", str(tmp_path / "ghost.json")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Error: Could not find a deck file" in captured.err


def test_keyboard_interrupt_is_graceful(tmp_path, monkeypatch, capsys):
    """Ctrl+C during input ends cleanly with a summary, no traceback."""
    deck = write_deck(tmp_path, THREE_CARDS)

    def boom(prompt=""):
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", boom)

    exit_code = app.main(["-f", deck])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "Interrupted" in out
    assert "Score: 0/0 (0.0%)" in out


def test_adaptive_mode_repeats_wrong_answer(tmp_path, monkeypatch, capsys):
    """End to end: a wrong answer in adaptive mode causes a repeat."""
    deck = write_deck(tmp_path, THREE_CARDS)
    answers = ["x", "Paris", "down", "x", "4"]  # miss "2 + 2" twice
    monkeypatch.setattr("builtins.input", fake_input(answers))

    exit_code = app.main(["-f", deck, "-m", "adaptive"])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert out.count("2 + 2") >= 2


# --- colour helpers -------------------------------------------------


def test_paint_wraps_text_when_enabled():
    """paint() adds a colour code and a reset when enabled."""
    from colorama import Fore

    result = app.paint("hi", Fore.RED, True)
    assert result.startswith(Fore.RED)
    assert result.endswith(app.Style.RESET_ALL)
    assert "hi" in result


def test_paint_passthrough_when_disabled():
    """paint() returns the text untouched when disabled."""
    assert app.paint("hi", "irrelevant", False) == "hi"


def test_color_enabled_false_with_no_color_flag():
    """--no-color always wins, regardless of terminal."""
    assert app.color_enabled(True) is False


def test_color_enabled_true_on_a_real_terminal(monkeypatch):
    """Without --no-color and with a tty, colour is on."""
    monkeypatch.setattr(app.sys.stdout, "isatty", lambda: True)
    assert app.color_enabled(False) is True


# --- --export -------------------------------------------------------


def test_export_writes_stats_file(tmp_path, monkeypatch, capsys):
    """--export saves the stats dict as JSON that round-trips."""
    deck = write_deck(tmp_path, THREE_CARDS)
    monkeypatch.setattr("builtins.input", fake_input(["4", "wrong", "down"]))
    out_path = tmp_path / "results.json"

    exit_code = app.main(["-f", deck, "-m", "sequential", "--export", str(out_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert out_path.exists()
    assert "Saved results to" in out

    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert saved == {
        "total_questions": 3,
        "correct": 2,
        "wrong": 1,
        "accuracy_percent": 66.7,
    }


def test_export_failure_reports_error(tmp_path, monkeypatch, capsys):
    """A write failure during export exits 1 with a friendly message."""
    deck = write_deck(tmp_path, THREE_CARDS)
    monkeypatch.setattr("builtins.input", fake_input(["4", "wrong", "down"]))

    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(app.FileHandler, "save_data", boom)

    exit_code = app.main(["-f", deck, "--export", str(tmp_path / "r.json")])

    assert exit_code == 1
    assert "Error: disk full" in capsys.readouterr().err
