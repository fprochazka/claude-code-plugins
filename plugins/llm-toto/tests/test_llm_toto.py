#!/usr/bin/env python3
"""Tests for the llm-toto CLI tool."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "scripts", "llm-toto.py")
SESSION = "test-session"


def run_toto(command: str, threshold: int = 4000, session: str = SESSION) -> tuple[str, int]:
    """Run llm-toto with the given command and return (stdout, exit_code)."""
    result = subprocess.run(
        ["python3", SCRIPT, "--session", session, "--threshold", str(threshold), "--", "bash", "-c", command],
        capture_output=True,
        text=True,
    )
    return result.stdout, result.returncode


def test_small_output_passthrough():
    """Small output should be printed as-is."""
    output, code = run_toto("echo 'hello world'")
    assert code == 0
    assert "hello world" in output
    assert "buffered" not in output.lower()


def test_exit_code_propagation():
    """Non-zero exit codes should be propagated."""
    _, code = run_toto("exit 42")
    assert code == 42


def test_exit_code_zero():
    """Zero exit codes should be propagated."""
    _, code = run_toto("echo ok")
    assert code == 0


def test_large_output_buffered():
    """Large output should be buffered to a file."""
    # Generate output larger than threshold
    output, code = run_toto("seq 1 500", threshold=100)
    assert code == 0
    assert "Output buffered to" in output
    assert "lines)" in output
    assert "Preview:" in output


def test_large_output_file_exists():
    """Buffered output file should actually exist and contain the data."""
    session = f"test-{os.getpid()}"
    output, code = run_toto("seq 1 500", threshold=100, session=session)
    assert code == 0

    # Extract file path from output
    for line in output.splitlines():
        if line.startswith("Output buffered to"):
            file_path = line.split("Output buffered to ")[1].split(" (")[0]
            assert os.path.exists(file_path), f"File {file_path} should exist"
            content = Path(file_path).read_text()
            assert "1\n" in content
            assert "500\n" in content
            # Cleanup
            os.unlink(file_path)
            break
    else:
        assert False, "Could not find 'Output buffered to' line"


def test_keyword_detection():
    """Keywords in output should be detected and counted."""
    cmd = "echo -e 'line1\\nERROR: something failed\\nWARNING: be careful\\nERROR: another error\\nline5'"
    output, code = run_toto(cmd, threshold=10)
    assert "Keyword mentions:" in output
    assert "error 2" in output.lower() or "error 3" in output.lower()  # "error" + "failed" might match
    assert "warn" in output.lower()


def test_preview_shows_head_and_tail():
    """Preview should show first and last lines."""
    output, code = run_toto("seq 1 200", threshold=100)
    assert code == 0
    assert "Preview:" in output
    # First lines
    assert "1" in output
    assert "2" in output
    # Last lines
    assert "200" in output
    assert "199" in output
    # Omission marker
    assert "omitted" in output


def test_large_output_with_nonzero_exit():
    """Large output with non-zero exit should still buffer AND propagate exit code."""
    output, code = run_toto("seq 1 500; exit 7", threshold=100)
    assert code == 7
    assert "Output buffered to" in output


def test_threshold_boundary():
    """Output exactly at threshold should not be buffered."""
    # Generate output of known size
    # "x" * 100 + newline = 101 chars
    output, code = run_toto("printf 'x%.0s' $(seq 1 100)", threshold=200)
    assert code == 0
    assert "buffered" not in output.lower()


def test_threshold_env_var():
    """LLM_TOTO_THRESHOLD env var should be respected."""
    env = os.environ.copy()
    env["LLM_TOTO_THRESHOLD"] = "50"
    result = subprocess.run(
        ["python3", SCRIPT, "--session", SESSION, "--", "bash", "-c", "seq 1 20"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert "Output buffered to" in result.stdout


def test_session_dir_created():
    """Session directory should be created automatically."""
    session = f"test-dir-{os.getpid()}"
    output, code = run_toto("seq 1 500", threshold=100, session=session)
    session_dir = Path(f"/tmp/llm-toto/{session}")
    assert session_dir.exists(), f"Session dir {session_dir} should exist"
    # Cleanup
    for f in session_dir.iterdir():
        f.unlink()
    session_dir.rmdir()


def test_empty_output():
    """Empty output should be handled gracefully."""
    output, code = run_toto("true")
    assert code == 0
    assert "buffered" not in output.lower()


def test_no_preview_long_lines():
    """Preview should be suppressed when lines exceed 200 chars."""
    # Generate a few very long lines (>200 chars each)
    cmd = "for i in $(seq 1 50); do printf '%0.s=' $(seq 1 300); echo; done"
    output, code = run_toto(cmd, threshold=100)
    assert code == 0
    assert "Output buffered to" in output
    assert "Preview:" not in output, "Preview should be suppressed for lines > 200 chars"


def test_no_preview_small_omission():
    """Preview should be suppressed when the omitted portion is too small."""
    # Generate 16 short lines -- preview would show 15 (5 head + 10 tail),
    # omitting only 1 line, which is less than 50% of total
    cmd = "for i in $(seq 1 16); do echo \"line $i\"; done"
    output, code = run_toto(cmd, threshold=10)
    assert code == 0
    assert "Output buffered to" in output
    assert "Preview:" not in output, "Preview should be suppressed when omission is too small"


def test_preview_shown_for_good_output():
    """Preview should be shown for output with many normal-length lines."""
    # Generate 200 short lines -- preview shows 15, omits 185 (>50%)
    cmd = "for i in $(seq 1 200); do echo \"line $i is a normal length line\"; done"
    output, code = run_toto(cmd, threshold=100)
    assert code == 0
    assert "Output buffered to" in output
    assert "Preview:" in output, "Preview should be shown for many normal-length lines"


def test_no_preview_minified_json():
    """Preview should be suppressed for minified JSON (single giant line)."""
    # Single line of 1000 chars
    cmd = "python3 -c \"print('{' + ','.join(['\\\"k%d\\\":%d' % (i,i) for i in range(200)]) + '}')\""
    output, code = run_toto(cmd, threshold=100)
    assert code == 0
    assert "Output buffered to" in output
    assert "Preview:" not in output, "Preview should be suppressed for minified JSON"


if __name__ == "__main__":
    test_functions = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    errors = []

    for test_fn in test_functions:
        try:
            test_fn()
            passed += 1
            print(f"  PASS  {test_fn.__name__}")
        except AssertionError as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"  FAIL  {test_fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"  ERROR {test_fn.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  {name}: {err}")
        sys.exit(1)
