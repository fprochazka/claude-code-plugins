#!/usr/bin/env python3
"""
Scans ~/.claude/skills/*/SKILL.md for trigger-keywords frontmatter.
If any keywords match the user prompt, injects a reminder to load the skill.
"""

import json
import os
import re
import sys
from glob import glob
from pathlib import Path


def parse_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from markdown content."""
    match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return {}

    frontmatter = {}
    for line in match.group(1).split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            frontmatter[key.strip()] = value.strip()
    return frontmatter


def get_trigger_keywords(frontmatter: dict) -> list[str]:
    """Extract trigger-keywords as a list, splitting by comma with optional whitespace."""
    raw = frontmatter.get('trigger-keywords', '')
    if not raw:
        return []
    return [kw.strip() for kw in re.split(r'\s*,\s*', raw.strip()) if kw.strip()]


def build_keyword_pattern(keywords: list[str]) -> re.Pattern:
    """Build regex pattern that matches keywords as whole words.

    Matches when keyword is preceded by start-of-string or non-alphanumeric,
    and followed by end-of-string or non-alphanumeric.
    E.g., 'linear' matches in 'https://linear.app/' but not in 'nonlinear'.
    """
    escaped = [re.escape(kw) for kw in keywords]
    pattern = r'(?:^|[^a-zA-Z0-9])(' + '|'.join(escaped) + r')(?:$|[^a-zA-Z0-9])'
    return re.compile(pattern, re.IGNORECASE)


def prompt_contains_keyword(prompt: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in the prompt as a whole word (case-insensitive)."""
    if not keywords:
        return False
    pattern = build_keyword_pattern(keywords)
    return bool(pattern.search(prompt))


def scan_skills(skills_dir: Path) -> dict[str, dict]:
    """Scan all SKILL.md files and return {skill_name: {keywords, has_references}}."""
    skills = {}
    pattern = str(skills_dir / '*/SKILL.md')

    for skill_path in glob(pattern):
        try:
            skill_dir = Path(skill_path).parent
            with open(skill_path, 'r', encoding='utf-8') as f:
                content = f.read()
            frontmatter = parse_frontmatter(content)
            name = frontmatter.get('name', skill_dir.name)
            keywords = get_trigger_keywords(frontmatter)
            if keywords:
                has_references = (skill_dir / 'references').is_dir()
                skills[name] = {'keywords': keywords, 'has_references': has_references}
        except Exception:
            continue

    return skills


def main():
    try:
        input_data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(0)

    prompt = input_data.get('prompt', '')
    if not prompt:
        sys.exit(0)

    # Allow override via env var for testing
    skills_dir = Path(os.environ.get('SKILLS_DIR', str(Path.home() / '.claude' / 'skills')))
    if not skills_dir.exists():
        sys.exit(0)

    skills = scan_skills(skills_dir)
    matched_skills = []

    for skill_name, info in skills.items():
        if prompt_contains_keyword(prompt, info['keywords']):
            matched_skills.append((skill_name, info['has_references']))

    if not matched_skills:
        sys.exit(0)

    def format_reminder(skill_name: str, has_references: bool) -> str:
        if has_references:
            return f"\nIMPORTANT: don't forget to load {skill_name} skill and relevant references in it"
        return f"\nIMPORTANT: don't forget to load {skill_name} skill"

    reminders = ''.join(
        format_reminder(skill, has_refs)
        for skill, has_refs in matched_skills
    )

    output = {
        'hookSpecificOutput': {
            'hookEventName': 'UserPromptSubmit',
            'additionalContext': reminders
        }
    }

    print(json.dumps(output))


if __name__ == '__main__':
    main()
