#!/usr/bin/env python3
"""
llm-toto: LLM Tool Output Tokens Optimizer

Wraps shell commands, buffers large outputs to files, and provides
compact summaries with keyword analysis and preview lines.

Usage:
    llm-toto [--session SESSION_ID] [--threshold CHARS] <command...>

If output is small (below threshold): prints output as-is.
If output is large (above threshold): saves to file, prints summary with preview.
Always propagates the wrapped command's exit code.
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_THRESHOLD = 4000

KEYWORDS = [
    "exception",
    "error",
    "fail",
    "warn",
]

# Pre-compile keyword patterns (case-insensitive, whole word)
KEYWORD_PATTERNS = [(kw, re.compile(rf"\b{kw}", re.IGNORECASE)) for kw in KEYWORDS]

PREVIEW_HEAD_LINES = 5
PREVIEW_TAIL_LINES = 10
PREVIEW_MAX_LINE_LENGTH = 200
# Don't show preview if the omitted portion is less than this fraction of total
PREVIEW_MIN_OMISSION_RATIO = 0.5


def count_keywords(text: str) -> dict[str, int]:
    """Count occurrences of each keyword in the text."""
    counts = {}
    for keyword, pattern in KEYWORD_PATTERNS:
        count = len(pattern.findall(text))
        if count > 0:
            counts[keyword] = count
    return counts


def format_keyword_summary(counts: dict[str, int]) -> str:
    """Format keyword counts as 'error 3, warning 12, fail 1'."""
    if not counts:
        return ""
    parts = [f"{kw} {count}" for kw, count in counts.items()]
    return ", ".join(parts)


def should_show_preview(lines: list[str], output_len: int) -> bool:
    """Decide whether a preview is useful for this output.

    Returns False if:
    - Any preview line exceeds PREVIEW_MAX_LINE_LENGTH (e.g. minified JSON, base64)
    - The omitted portion would be less than PREVIEW_MIN_OMISSION_RATIO of the total
      (preview shows almost everything, so it's pointless)
    """
    total = len(lines)
    head = min(PREVIEW_HEAD_LINES, total)
    tail = min(PREVIEW_TAIL_LINES, total - head)

    preview_lines = lines[:head] + lines[-tail:] if tail > 0 else lines[:head]

    # Guard: any preview line too long means preview is useless noise
    if any(len(line) > PREVIEW_MAX_LINE_LENGTH for line in preview_lines):
        return False

    # Guard: if the omitted portion is too small relative to total, skip preview
    preview_chars = sum(len(line) for line in preview_lines)
    omitted_chars = output_len - preview_chars
    if omitted_chars < output_len * PREVIEW_MIN_OMISSION_RATIO:
        return False

    return True


def make_preview(lines: list[str], head: int = PREVIEW_HEAD_LINES, tail: int = PREVIEW_TAIL_LINES) -> str:
    """Create a preview showing first N and last M lines."""
    total = len(lines)

    if total <= head + tail:
        return "\n".join(lines)

    head_lines = lines[:head]
    tail_lines = lines[-tail:]
    skipped = total - head - tail

    return "\n".join(head_lines) + f"\n... ({skipped} lines omitted) ...\n" + "\n".join(tail_lines)


def get_output_dir(session_id: str) -> Path:
    """Get or create the output directory for this session."""
    output_dir = Path("/tmp/llm-toto") / session_id
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_output(output_dir: Path, content: str) -> Path:
    """Save output to a timestamped file."""
    timestamp = int(time.time() * 1000)
    output_file = output_dir / f"{timestamp}.txt"
    output_file.write_text(content, encoding="utf-8")
    return output_file


def run_command(command: list[str]) -> tuple[str, int]:
    """Run a command as a shell command, capturing combined stdout+stderr.

    Always uses shell=True because commands may contain shell features
    like redirects (2>&1), environment variables, etc.
    Returns (output, exit_code).
    """
    shell_command = shlex.join(command) if len(command) > 1 else command[0]
    try:
        result = subprocess.run(
            shell_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
        )
        return result.stdout or "", result.returncode
    except Exception as e:
        return f"llm-toto: error running command: {e}\n", 1


def main():
    parser = argparse.ArgumentParser(
        description="LLM Tool Output Tokens Optimizer",
        usage="llm-toto [--session ID] [--threshold N] <command...>",
    )
    parser.add_argument(
        "--session", "-s",
        default=os.environ.get("LLM_TOTO_SESSION", "default"),
        help="Session ID for organizing output files (default: 'default')",
    )
    parser.add_argument(
        "--threshold", "-t",
        type=int,
        default=int(os.environ.get("LLM_TOTO_THRESHOLD", DEFAULT_THRESHOLD)),
        help=f"Character threshold for buffering (default: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to run",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Handle the '--' separator that argparse.REMAINDER might include
    command = args.command
    if command and command[0] == "--":
        command = command[1:]

    if not command:
        parser.print_help()
        sys.exit(1)

    output, exit_code = run_command(command)

    output_len = len(output)

    if output_len <= args.threshold:
        # Small output: print as-is
        if output:
            sys.stdout.write(output)
            if not output.endswith("\n"):
                sys.stdout.write("\n")
    else:
        # Large output: buffer to file and print summary
        output_dir = get_output_dir(args.session)
        output_file = save_output(output_dir, output)

        lines = output.splitlines()
        line_count = len(lines)

        keyword_counts = count_keywords(output)
        keyword_summary = format_keyword_summary(keyword_counts)

        # Print summary
        print(f"Output buffered to {output_file} ({line_count} lines)")

        if keyword_summary:
            print(f"Keyword mentions: {keyword_summary}")

        # Only show preview if it would be useful
        if should_show_preview(lines, output_len):
            preview = make_preview(lines)
            print()
            print("Preview:")
            print(preview)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
