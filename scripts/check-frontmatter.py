#!/usr/bin/env python3
"""Frontmatter and reference checks for the plugin marketplace.

Called by scripts/check.sh and follows the same output contract:

    FAIL <check-id> <path>: <what is wrong>
    ok   <check-id> (<n> items)

These checks live in Python rather than bash because a frontmatter description can be a YAML block
scalar, which bash cannot parse. Exits 1 if any FAIL line was printed.

Usage: scripts/check-frontmatter.py [check-id]   -- with an id, run only that check.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent

# Keys Claude Code understands in skill, command and agent frontmatter. Anything else is silently
# ignored at runtime, which makes a typo look like a working setting.
ALLOWED_KEYS = {
    "name", "description", "allowed-tools", "model", "tools", "color", "argument-hint",
    "trigger-keywords", "disable-model-invocation", "user-invocable", "skills", "license",
    "compatibility", "metadata",
}

DESCRIPTION_LIMIT = 1024

AGENT_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

CHECK_IDS = ["frontmatter-parse", "frontmatter-keys", "description", "skill-name", "references"]

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
PLUGIN_ROOT_RE = re.compile(r"\$\{CLAUDE_PLUGIN_ROOT\}/\S+")
BACKTICK_PREFIXES = ("references/", "scripts/", "assets/", "${CLAUDE_PLUGIN_ROOT}/")
PLACEHOLDER_CHARS = ("<", ">", "…", "*")
# Punctuation a reference picks up from the prose or the allowed-tools syntax around it,
# e.g. Bash(${CLAUDE_PLUGIN_ROOT}/scripts/x.sh:*)".
TRAILING_JUNK = "*:\"'`),"

failures = 0


def fail(check_id: str, path: Path | str, message: str) -> None:
    global failures
    failures += 1
    rel = path if isinstance(path, str) else path.relative_to(ROOT).as_posix()
    print(f"FAIL {check_id} {rel}: {message}")


def report(check_id: str, before: int, items: int) -> None:
    if failures == before:
        print(f"ok {check_id} ({items} items)")


def targets() -> list[tuple[Path, str, Path]]:
    """Every frontmatter-carrying file, as (path, kind, plugin root)."""
    found: list[tuple[Path, str, Path]] = []
    for plugin in sorted((ROOT / "plugins").iterdir()):
        if not plugin.is_dir():
            continue
        found += [(p, "skill", plugin) for p in sorted(plugin.glob("skills/*/SKILL.md"))]
        found += [(p, "command", plugin) for p in sorted(plugin.glob("commands/**/*.md"))]
        found += [(p, "agent", plugin) for p in sorted(plugin.glob("agents/*.md"))]
    return found


def split_frontmatter(text: str) -> tuple[str | None, str, str | None]:
    """Return (frontmatter block, body, error). The block is None when the file has no usable one."""
    if not text.startswith("---\n"):
        return None, text, "does not start with a --- frontmatter fence"
    end = text.find("\n---", 3)
    if end == -1:
        return None, text, "frontmatter fence is never closed"
    # The closing fence must be a line of its own.
    line_end = text.find("\n", end + 1)
    if text[end + 1:line_end if line_end != -1 else len(text)].strip() != "---":
        return None, text, "frontmatter fence is never closed"
    body = text[line_end + 1:] if line_end != -1 else ""
    return text[4:end + 1], body, None


def load() -> list[dict]:
    """Parse every target once. Records with meta None failed to parse."""
    records = []
    for path, kind, plugin in targets():
        text = path.read_text(encoding="utf-8")
        block, body, error = split_frontmatter(text)
        meta = None
        if error is None:
            try:
                parsed = yaml.safe_load(block)
            except yaml.YAMLError as exc:
                error = f"frontmatter is not valid YAML: {str(exc).splitlines()[0]}"
            else:
                if not isinstance(parsed, dict):
                    error = f"frontmatter is a {type(parsed).__name__}, not a mapping"
                else:
                    meta = parsed
        records.append({"path": path, "kind": kind, "plugin": plugin, "meta": meta, "body": body, "error": error})
    return records


def check_frontmatter_parse(records: list[dict]) -> None:
    before = failures
    for rec in records:
        if rec["error"]:
            fail("frontmatter-parse", rec["path"], rec["error"])
    report("frontmatter-parse", before, len(records))


def check_frontmatter_keys(records: list[dict]) -> None:
    before = failures
    items = 0
    for rec in records:
        if rec["meta"] is None:
            continue
        for key in rec["meta"]:
            items += 1
            if key not in ALLOWED_KEYS:
                fail("frontmatter-keys", rec["path"], f"unknown key \"{key}\"")
    report("frontmatter-keys", before, items)


def check_description(records: list[dict]) -> None:
    before = failures
    items = 0
    for rec in records:
        if rec["meta"] is None:
            continue
        items += 1
        value = rec["meta"].get("description")
        if value is None:
            fail("description", rec["path"], "no description")
        elif not isinstance(value, str):
            fail("description", rec["path"], f"description is a {type(value).__name__}, not a string")
        elif not " ".join(value.split()):
            fail("description", rec["path"], "description is empty")
        elif len(value) > DESCRIPTION_LIMIT:
            fail("description", rec["path"], f"description is {len(value)} characters, limit is {DESCRIPTION_LIMIT}")
    report("description", before, items)


def check_skill_name(records: list[dict]) -> None:
    before = failures
    items = 0
    for rec in records:
        if rec["meta"] is None:
            continue
        items += 1
        name = rec["meta"].get("name")
        if rec["kind"] == "skill":
            expected = rec["path"].parent.name
            if name is None:
                fail("skill-name", rec["path"], f"no name, expected \"{expected}\"")
            elif name != expected:
                fail("skill-name", rec["path"], f"name is \"{name}\", directory is \"{expected}\"")
        elif rec["kind"] == "agent":
            if name is None:
                fail("skill-name", rec["path"], "agent has no name")
            elif not isinstance(name, str) or not AGENT_NAME_RE.match(name):
                fail("skill-name", rec["path"], f"agent name \"{name}\" is not lower-case-hyphenated")
        elif name is not None:
            fail("skill-name", rec["path"], "command must not set name; the filename is the command name")
    report("skill-name", before, items)


def candidate_references(body: str) -> list[str]:
    """Relative paths the body claims to point at. Fenced code blocks are scanned too, because that is
    where the real script invocations live."""
    found: list[str] = []
    for match in MD_LINK_RE.findall(body):
        target = match.split("#", 1)[0]
        if not target or target.startswith("#") or "://" in target or target.startswith("mailto:"):
            continue
        if target.startswith("/"):
            continue  # absolute, not a repo-relative reference
        found.append(target)
    for span in BACKTICK_RE.findall(body):
        if span.startswith(BACKTICK_PREFIXES):
            found.append(span)
    found += PLUGIN_ROOT_RE.findall(body)
    return found


def clean(reference: str) -> str:
    return reference.strip().rstrip(TRAILING_JUNK)


def check_references(records: list[dict]) -> None:
    before = failures
    items = 0
    for rec in records:
        seen = set()
        for raw in candidate_references(rec["body"]):
            target = clean(raw)
            if not target or any(c in target for c in PLACEHOLDER_CHARS):
                continue
            if target in seen:
                continue
            seen.add(target)
            items += 1
            if target.startswith("${CLAUDE_PLUGIN_ROOT}/"):
                paths = [rec["plugin"] / target[len("${CLAUDE_PLUGIN_ROOT}/"):]]
            else:
                paths = [rec["path"].parent / target, rec["plugin"] / target]
            if not any(p.exists() for p in paths):
                fail("references", rec["path"], f"missing target for `{raw}`")
    report("references", before, items)


CHECKS = {
    "frontmatter-parse": check_frontmatter_parse,
    "frontmatter-keys": check_frontmatter_keys,
    "description": check_description,
    "skill-name": check_skill_name,
    "references": check_references,
}


def main() -> int:
    only = sys.argv[1] if len(sys.argv) > 1 else None
    if only is not None and only not in CHECKS:
        print(f"unknown check id: {only}", file=sys.stderr)
        print(f"known ids: {' '.join(CHECK_IDS)}", file=sys.stderr)
        return 2
    records = load()
    for check_id in CHECK_IDS:
        if only is None or only == check_id:
            CHECKS[check_id](records)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
