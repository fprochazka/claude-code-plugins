# Gemini CLI

A skill for using Gemini CLI with massive context windows (1M tokens) for codebase analysis and second opinions.

## Overview

This plugin provides a skill for leveraging Google's Gemini CLI in non-interactive mode. It's ideal for:

- Analyzing large codebases that exceed Claude's context limits
- Getting second opinions on complex technical decisions
- Cross-validating critical analysis
- Multi-file architecture reviews

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install gemini-cli@fprochazka-claude-code-plugins
```

## Prerequisites

- Gemini CLI installed and configured (`gemini` command available)
- Google Cloud authentication set up

## Usage

The skill is automatically loaded when needed. It includes reference prompts in `references/prompt_patterns.md` for:

- Architecture reviews
- Security audits
- Performance analysis
- Migration assessments
- Second opinion prompts

## Author

Filip Procházka

## License

MIT
