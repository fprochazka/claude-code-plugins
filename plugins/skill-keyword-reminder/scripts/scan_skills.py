#!/usr/bin/env python3
"""
Scans for SKILL.md files with trigger-keywords frontmatter.
If any keywords match the user prompt, injects a reminder to load the skill.

Skills are loaded from (in order, later overrides earlier):
1. ~/.claude/skills/*/SKILL.md (user-level skills)
2. .claude/skills/*/SKILL.md walking up from cwd to home dir (project-level skills)
"""

import json
import os
import re
import sys
from glob import glob
from pathlib import Path


def find_skills_directories(cwd: Path, home: Path, project_dir: Path | None) -> list[Path]:
    """Find all .claude/skills directories.

    If project_dir is provided (from CLAUDE_PROJECT_DIR), uses only:
    - ~/.claude/skills (user-level)
    - project_dir/.claude/skills (project-level)

    Otherwise, walks from cwd up to home collecting .claude/skills dirs.

    Returns directories in order: user-level first, then project-level.
    This means project-level skills take precedence over user-level.
    """
    dirs = []

    # User-level skills first (lowest precedence)
    user_skills = home / '.claude' / 'skills'
    if user_skills.is_dir():
        dirs.append(user_skills)

    # If CLAUDE_PROJECT_DIR is set, use it directly
    if project_dir is not None:
        project_skills = project_dir / '.claude' / 'skills'
        if project_skills.is_dir():
            dirs.append(project_skills)
        return dirs

    # Otherwise, walk from cwd up to (but not including) home
    project_dirs = []
    current = cwd.resolve()
    home_resolved = home.resolve()

    while current != current.parent:  # Stop at root
        # Stop before home directory (user-level skills already added above)
        if current == home_resolved:
            break

        skills_dir = current / '.claude' / 'skills'
        if skills_dir.is_dir():
            project_dirs.append(skills_dir)

        current = current.parent

    # Reverse so that dirs closer to cwd come later (higher precedence)
    dirs.extend(reversed(project_dirs))

    return dirs


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


def get_loaded_skills(transcript_path: str | None) -> set[str]:
    """Read transcript and extract already-loaded skill names."""
    if not transcript_path:
        return set()

    path = Path(transcript_path)
    if not path.exists():
        return set()

    loaded = set()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    # Navigate to content array in message
                    message = entry.get('message', {})
                    content = message.get('content', [])
                    for item in content:
                        if isinstance(item, dict) and item.get('name') == 'Skill':
                            skill_input = item.get('input', {})
                            skill_name = skill_input.get('skill', '')
                            if skill_name:
                                loaded.add(skill_name)
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return loaded


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

    cwd = Path(input_data.get('cwd', os.getcwd()))
    home = Path.home()

    # Use CLAUDE_PROJECT_DIR if available, otherwise walk up from cwd
    project_dir_env = os.environ.get('CLAUDE_PROJECT_DIR', '').strip()
    project_dir = Path(project_dir_env) if project_dir_env else None

    # Find all skills directories
    skills_dirs = find_skills_directories(cwd, home, project_dir)
    if not skills_dirs:
        sys.exit(0)

    # Scan all directories, later ones override earlier ones
    skills = {}
    for skills_dir in skills_dirs:
        skills.update(scan_skills(skills_dir))

    matched_skills = []

    for skill_name, info in skills.items():
        if prompt_contains_keyword(prompt, info['keywords']):
            matched_skills.append((skill_name, info['has_references']))

    # Filter out skills already loaded in this session
    transcript_path = input_data.get('transcript_path')
    loaded_skills = get_loaded_skills(transcript_path)
    if loaded_skills:
        matched_skills = [
            (skill, has_refs) for skill, has_refs in matched_skills
            if skill not in loaded_skills
        ]

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
