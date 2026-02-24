# Gemini CLI

A skill for using Gemini CLI with massive context windows (1M tokens) for codebase analysis and second opinions.

## Overview

This plugin provides a skill for leveraging Google's Gemini CLI in non-interactive mode. It's ideal for:

- Analyzing large codebases that exceed Claude's context limits
- Getting second opinions on complex technical decisions
- Cross-validating critical analysis
- Multi-file architecture reviews

## Requirements

- [Gemini CLI](https://github.com/google-gemini/gemini-cli) installed and authenticated

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install gemini-cli@fprochazka-claude-code-plugins
```

## Usage

The skill is automatically loaded when needed. It includes reference prompts in `references/prompt_patterns.md` for:

- Architecture reviews
- Security audits
- Performance analysis
- Migration assessments
- Second opinion prompts

### Review Agent

The `gemini-cli:review-agent` provides an autonomous code review workflow:

1. **Scope definition** - determines target path, review type, and focus areas
2. **Context collection** - maps project structure to construct effective prompts
3. **Gemini invocation** - runs Gemini with a targeted review prompt
4. **Verification** - reads actual code to confirm each finding
5. **Final report** - produces a structured report with verified findings only

Trigger it by asking for a code review with Gemini, e.g. "review this codebase with gemini" or "use gemini for a security audit".

## Author

Filip Procházka

## License

MIT
