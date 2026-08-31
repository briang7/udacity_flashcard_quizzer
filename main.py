"""
Command-line interface for the flashcard quizzer.

Examples:
    python main.py -f data/python_basics.json -m adaptive
    python main.py -f data/trivia.json --stats

Flags:
    -f / --file    path to a JSON deck file (required)
    -m / --mode    sequential | random | adaptive  (default: sequential)
    --stats        print a summary table when the quiz ends
    --no-color     turn off coloured output
    --export PATH  save the end-of-quiz stats to a JSON file
"""

import argparse
import sys
from pathlib import Path

from colorama import Fore, Style, just_fix_windows_console

from utils.file_handler import FileHandler
from utils.flashcard_loader import FlashcardError, load_flashcards
from utils.quiz_engine import QuizSession, available_modes, create_quiz_mode


def color_enabled(no_color_flag: bool) -> bool:
    """Colour output only when not disabled and stdout is a terminal."""
    return not no_color_flag and sys.stdout.isatty()


def paint(text: str, color: str, enabled: bool) -> str:
    """Wrap ``text`` in a colorama colour code when ``enabled``."""
    if not enabled:
        return text
    return f"{color}{text}{Style.RESET_ALL}"


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the command-line flags."""
    parser = argparse.ArgumentParser(
        prog="flashcard-quizzer",
        description="Practise flashcards from a JSON deck.",
    )
    parser.add_argument("-f", "--file", required=True, help="path to a JSON deck file")
    parser.add_argument(
        "-m",
        "--mode",
        default="sequential",
        choices=available_modes(),
        help="question ordering strategy (default: sequential)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="print a summary table when the quiz ends",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="turn off coloured output",
    )
    parser.add_argument(
        "--export",
        metavar="PATH",
        help="save the end-of-quiz stats to a JSON file at PATH",
    )

    return parser


def run_quiz(session: QuizSession, use_color: bool) -> None:
    """Ask questions until the deck is exhausted or the user types exit."""
    while True:
        card = session.next_card()
        if card is None:
            return

        print()
        print(paint(card.front, Fore.CYAN + Style.BRIGHT, use_color))
        answer = input("Your answer (or 'exit'): ").strip()

        if answer.casefold() == "exit":
            print("\nExiting early - your progress is kept.")
            return

        if session.submit(card, answer):
            print(paint("Correct!", Fore.GREEN, use_color))
        else:
            print(paint(f"Wrong - answer: {card.back}", Fore.RED, use_color))


def print_summary(session: QuizSession, use_color: bool, show_stats: bool) -> None:
    """Print the final score, plus a stats table when ``show_stats``."""
    stats = session.stats()
    score_line = (
        f"Score: {stats['correct']}/{stats['total_questions']} "
        f"({stats['accuracy_percent']}%)"
    )
    tone = Fore.GREEN if session.accuracy >= 50 else Fore.RED

    print()
    print(paint(score_line, tone, use_color))

    if show_stats:
        print(paint("--- Stats ---", Style.BRIGHT, use_color))
        for key, value in stats.items():
            label = key.replace("_", " ").capitalize()
            print(f"  {label}: {value}")


def export_stats(session: QuizSession, path: str) -> None:
    """Write ``session.stats()`` to ``path`` as JSON, reusing FileHandler.

    FileHandler works relative to a directory, so we point it at the
    export path's parent folder and hand it just the file name.
    """
    target = Path(path)
    handler = FileHandler(str(target.parent) or ".")
    handler.save_data(target.name, session.stats())


def main(argv: list[str] | None = None) -> int:
    """Program entry point. Returns a process exit code (0 = success)."""
    just_fix_windows_console()
    args = build_parser().parse_args(argv)
    use_color = color_enabled(args.no_color)

    try:
        cards = load_flashcards(args.file)
    except FlashcardError as exc:
        print(paint(f"Error: {exc}", Fore.RED, use_color), file=sys.stderr)
        return 1

    session = QuizSession(create_quiz_mode(args.mode, cards))
    print(
        paint(
            f"Loaded {len(cards)} cards - mode: {args.mode}",
            Fore.CYAN,
            use_color,
        )
    )

    try:
        run_quiz(session, use_color)
    except (KeyboardInterrupt, EOFError):
        print("\n\nInterrupted - here is how you did:")

    print_summary(session, use_color, args.stats)

    if args.export:
        try:
            export_stats(session, args.export)
        except RuntimeError as exc:
            print(
                paint(f"Error: {exc}", Fore.RED, use_color),
                file=sys.stderr,
            )
            return 1
        print(f"Saved results to {args.export}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
