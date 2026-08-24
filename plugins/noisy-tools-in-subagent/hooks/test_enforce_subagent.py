#!/usr/bin/env python3
"""Tests for `enforce-subagent.py` (the noisy-tools-in-subagent PreToolUse hook).

Two layers:

* **Unit** — exercise `_check_argv` (WHITELIST matching), `_iter_command_argvs`
  (recursion into bash-classify's `inner_commands`), and the exempt-agent
  resolution (`_parse_exempt_option`, `_is_exempt_agent`). These have no
  external dependencies and lock in the core behaviour: the WHITELIST anchors
  on the real tool, wrapped commands are reached by walking inner commands
  rather than by parsing wrappers ourselves, and only a declared `agent_type`
  escapes the whitelist.

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
from unittest import mock

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
        # Gradle derives suffixed task names that a bare `\bcompile\b` misses.
        ["./gradlew", ":app:compileJava"],
        ["./gradlew", "compileTestJava"],
        ["./gradlew", ":coverage:testCodeCoverageReport"],
        ["./gradlew", "publishToMavenLocal"],
        ["./gradlew", ":order-scoring-harness:installDist"],
        # Static analysis tasks are not lifecycle phases.
        ["./gradlew", ":app:checkstyleMain", ":app:checkstyleTest"],
        ["./gradlew", "spotbugsMain"],
        ["./mvnw", "checkstyle:check@scrutinize-checkstyle"],
        # Wrappers reached by absolute path, e.g. from a worktree.
        ["/home/x/repo/gradlew", ":app:test"],
        ["/home/x/repo/mvnw", "clean", "install"],
        ["yarn", "tscheck"],
        ["yarn", "nx", "tscheck", "om-template-api"],
        ["npx", "prettier", "--check", "src/"],
        ["kubectl", "logs", "commercial-orders-hook-rp99d"],
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
        # `--warning-mode` must not read as the `war` phase, and a project path
        # containing "testing" must not read as the `test` phase.
        ["./gradlew", "help", "--console=plain", "--warning-mode", "all"],
        ["./gradlew", ":testing-typed-ids-hibernate-73:dependencies"],
        ["./gradlew", "tasks", "--all"],
        ["./gradlew", "projects", "-q"],
        ["./gradlew", "-q", ":app:dependencyInsight", "--configuration", "runtimeClasspath"],
        ["./mvnw", "-q", "dependency:tree", "--projects", "modules/app"],
        ["mvn", "help:effective-pom"],
        ["kubectl", "get", "pods"],
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


class ExemptAgentTest(unittest.TestCase):
    """`agent_type` is the only thing that escapes the WHITELIST."""

    def _is_exempt(self, agent_type, option=None):
        """Evaluate `_is_exempt_agent` with only the given plugin option set."""
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(enforce.EXEMPT_OPTION_ENV_VAR, None)
            if option is not None:
                os.environ[enforce.EXEMPT_OPTION_ENV_VAR] = option
            return enforce._is_exempt_agent(agent_type)

    def test_builtin_defaults(self):
        for agent_type in ("noisy-tools-in-subagent:noisy-runner", "Explore", "Plan",
                           "code-review:review-bugs", "searxngcli:agent", "web-researcher:agent"):
            with self.subTest(agent_type=agent_type):
                self.assertTrue(self._is_exempt(agent_type))

    def test_non_exempt_agents(self):
        for agent_type in (None, "", "general-purpose", "plugin-dev:agent-creator", "code-review"):
            with self.subTest(agent_type=agent_type):
                self.assertFalse(self._is_exempt(agent_type))

    def test_patterns_must_match_the_whole_agent_type(self):
        # A partial match would silently disable the plugin for that agent.
        self.assertFalse(self._is_exempt("my-team:review-bugs", option="bugs"))
        self.assertFalse(self._is_exempt("my-team:leaf-worker", option="leaf"))
        self.assertTrue(self._is_exempt("my-team:leaf-worker", option="my-team:leaf-.*"))

    def test_invalid_pattern_is_skipped_not_raised(self):
        self.assertFalse(self._is_exempt("general-purpose", option="[unclosed"))
        self.assertTrue(self._is_exempt("Explore", option="[unclosed"))

    def test_option_serializations(self):
        cases = {
            '["a:one", "b:two"]': ["a:one", "b:two"],
            '"a:one"': ["a:one"],
            "a:one\nb:two": ["a:one", "b:two"],
            "a:one,b:two": ["a:one", "b:two"],
            "  a:one  ": ["a:one"],
            "": [],
            None: [],
            "[not valid json": ["[not valid json"],
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(enforce._parse_exempt_option(raw), expected)

    def test_comma_bearing_regex_survives_on_its_own_line(self):
        # Comma splitting would corrupt `a{1,3}`, so multi-line wins over commas.
        self.assertEqual(
            enforce._parse_exempt_option('["team:a{1,3}", "team:b"]'), ["team:a{1,3}", "team:b"]
        )
        self.assertEqual(
            enforce._parse_exempt_option("team:a{1,3}\nteam:b"), ["team:a{1,3}", "team:b"]
        )


def _run_hook(command: str, agent_type: str | None = None, exempt_option: str | None = None):
    """Run the hook as a subprocess; return True if it denied the call."""
    payload = {"tool_name": "Bash", "tool_input": {"command": command}}
    if agent_type is not None:
        # A real subagent payload carries both; `agent_id` is what marks it as a
        # subagent, but only `agent_type` decides the exemption.
        payload["agent_id"] = "a0123456789abcdef"
        payload["agent_type"] = agent_type
    env = dict(os.environ)
    env.pop(enforce.EXEMPT_OPTION_ENV_VAR, None)
    if exempt_option is not None:
        env[enforce.EXEMPT_OPTION_ENV_VAR] = exempt_option
    result = subprocess.run(
        [sys.executable, HOOK_PATH],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
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
        "./gradlew :app:compileJava -q",
        "./gradlew :app:checkstyleMain :app:checkstyleTest -Pscrutinize",
        "yarn tscheck 2>&1",
        "kubectl logs my-pod --context foo | tail -50",
    ]

    PASS = [
        "echo yarn test",
        "nx list",
        "nx graph",
        "./gradlew help --console=plain --warning-mode all",
        "./gradlew :testing-typed-ids-hibernate-73:dependencies -q",
        "kubectl get pods",
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

    def test_ordinary_subagents_are_blocked(self):
        # A subagent that can delegate gets the same treatment as the main
        # thread, at every nesting depth.
        self.assertTrue(_run_hook("pytest", agent_type="general-purpose"))

    def test_exempt_agents_bypass(self):
        for agent_type in ("noisy-tools-in-subagent:noisy-runner", "Explore", "code-review:review-bugs"):
            with self.subTest(agent_type=agent_type):
                self.assertFalse(_run_hook("pytest", agent_type=agent_type))

    def test_configured_exempt_agent_bypasses(self):
        self.assertTrue(_run_hook("pytest", agent_type="my-team:leaf"))
        self.assertFalse(_run_hook("pytest", agent_type="my-team:leaf", exempt_option="my-team:.*"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
