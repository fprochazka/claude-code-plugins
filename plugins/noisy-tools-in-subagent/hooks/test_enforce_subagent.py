#!/usr/bin/env python3
"""Tests for `enforce-subagent.py` (the noisy-tools-in-subagent PreToolUse hook).

Two layers:

* **Unit** — exercise `_check_argv` (WHITELIST matching) and
  `_iter_command_argvs` (recursion into bash-classify's `inner_commands`).
  These have no external dependencies and lock in the core behaviour: the
  WHITELIST anchors on the real tool, and wrapped commands are reached by
  walking inner commands rather than by parsing wrappers ourselves.

* **End-to-end** — pipe a real hook payload through the script, which shells
  out to `bash-classify`. Skipped when `bash-classify` is not on PATH.

Run:  python3 test_enforce_subagent.py        # or: python3 -m unittest -v
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest

HOOK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "enforce-subagent.py")
HAVE_BASH_CLASSIFY = shutil.which("bash-classify") is not None


def _load_hook_module():
    """Import the hook by path (its filename has a hyphen, so no plain import)."""
    spec = importlib.util.spec_from_file_location("enforce_subagent", HOOK_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


enforce = _load_hook_module()


class CheckArgvTest(unittest.TestCase):
    """`_check_argv` matches a single command's argv against the WHITELIST."""

    BLOCK = [
        ["pytest"],
        ["pytest", "tests/"],
        ["yarn", "nx", "test"],
        ["nx", "test"],
        ["npx", "nx", "test"],
        ["nx", "run-many", "--target=test"],
        ["nx", "affected:test"],
        ["mvn", "clean", "install"],
        ["cargo", "test"],
        ["go", "build", "./..."],
        ["make"],
    ]

    PASS = [
        [],                                   # empty argv
        ["echo", "yarn", "test"],             # echo is not a runner
        ["nx", "list"],                       # cheap introspection
        ["nx", "graph"],
        ["nx", "show", "projects"],
        ["git", "status"],
        ["cat", "package.json"],
        # A wrapper's own top-level argv must NOT match: detection relies on
        # recursion into inner_commands, not on the wrapper line itself.
        ["timeout", "300", "yarn", "nx", "test"],
        ["rtk", "yarn", "test"],
    ]

    def test_blocked(self):
        for argv in self.BLOCK:
            with self.subTest(argv=argv):
                self.assertIsNotNone(enforce._check_argv(argv))

    def test_passed(self):
        for argv in self.PASS:
            with self.subTest(argv=argv):
                self.assertIsNone(enforce._check_argv(argv))


class IterCommandArgvsTest(unittest.TestCase):
    """`_iter_command_argvs` yields the entry argv plus every nested inner argv."""

    def test_flat_command(self):
        entry = {"argv": ["pytest"], "inner_commands": []}
        self.assertEqual(list(enforce._iter_command_argvs(entry)), [["pytest"]])

    def test_single_wrapper(self):
        entry = {
            "argv": ["timeout", "300", "yarn", "test"],
            "inner_commands": [{"argv": ["yarn", "test"], "inner_commands": []}],
        }
        self.assertEqual(
            list(enforce._iter_command_argvs(entry)),
            [["timeout", "300", "yarn", "test"], ["yarn", "test"]],
        )

    def test_stacked_wrappers(self):
        # rtk -> timeout -> yarn test  (nested two levels deep)
        entry = {
            "argv": ["rtk", "timeout", "300", "yarn", "test"],
            "inner_commands": [{
                "argv": ["timeout", "300", "yarn", "test"],
                "inner_commands": [{"argv": ["yarn", "test"], "inner_commands": []}],
            }],
        }
        self.assertEqual(
            list(enforce._iter_command_argvs(entry)),
            [
                ["rtk", "timeout", "300", "yarn", "test"],
                ["timeout", "300", "yarn", "test"],
                ["yarn", "test"],
            ],
        )

    def test_missing_and_malformed_keys_are_safe(self):
        self.assertEqual(list(enforce._iter_command_argvs({})), [])
        self.assertEqual(list(enforce._iter_command_argvs({"argv": ["ls"]})), [["ls"]])
        self.assertEqual(list(enforce._iter_command_argvs("not-a-dict")), [])
        # Non-string argv tokens are coerced to str.
        self.assertEqual(
            list(enforce._iter_command_argvs({"argv": ["timeout", 300]})),
            [["timeout", "300"]],
        )


def _run_hook(command: str, agent_id: str | None = None):
    """Run the hook as a subprocess; return True if it denied the call."""
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if agent_id is not None:
        payload["agent_id"] = agent_id
    result = subprocess.run(
        [sys.executable, HOOK_PATH],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
    )
    return '"permissionDecision": "deny"' in result.stdout


@unittest.skipUnless(HAVE_BASH_CLASSIFY, "bash-classify not on PATH")
class EndToEndTest(unittest.TestCase):
    """Full path through the hook script + bash-classify."""

    BLOCK = [
        "cd app && timeout 300 yarn nx test foo --testPathPattern=bar 2>&1 | tail -25",
        "rtk yarn nx test",
        "env FOO=1 pytest",
        "nice -n 10 cargo test",
        "rtk timeout 300 yarn test",          # stacked wrappers
        'env FOO=1 bash -c "yarn test"',      # wrapper around bash -c
        "nx test",
        "npx nx test",
        "yarn nx test",                       # regression
        "mvn clean install",
    ]

    PASS = [
        "echo yarn test",
        "nx list",
        "nx graph",
        "git status",
        "cat package.json",
    ]

    def test_noisy_commands_are_blocked(self):
        for command in self.BLOCK:
            with self.subTest(command=command):
                self.assertTrue(_run_hook(command), f"expected BLOCK: {command}")

    def test_benign_commands_pass(self):
        for command in self.PASS:
            with self.subTest(command=command):
                self.assertFalse(_run_hook(command), f"expected PASS: {command}")

    def test_subagent_calls_bypass(self):
        # A call originating from a subagent (agent_id present) is never blocked,
        # even for an otherwise-noisy command.
        self.assertFalse(_run_hook("pytest", agent_id="agent-123"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
