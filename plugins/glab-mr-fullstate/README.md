# GitLab MR Fix

A command for fixing GitLab MR issues (failed CI, unresolved comments) using [glab-mr-fullstate](https://github.com/fprochazka/glab-mr-fullstate).

## Overview

This plugin provides the `/glab-mr-fullstate:fix` command that:

- Fetches complete MR state including CI pipeline status, job logs, and comments
- Analyzes failed CI jobs and helps fix the issues
- Reviews unresolved discussion threads and implements fixes
- Verifies resolved comments for any missed actionable feedback

## Prerequisites

Before installing this plugin, you must have the following CLIs installed:

1. **glab** - GitLab CLI for API access
   ```bash
   # See https://gitlab.com/gitlab-org/cli for installation
   brew install glab  # macOS
   ```

2. **glab-mr-fullstate** - Fetches comprehensive MR state
   ```bash
   # Install via pipx (recommended)
   pipx install git+https://github.com/fprochazka/glab-mr-fullstate.git
   ```

## Installation

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install glab-mr-fullstate@fprochazka-claude-code-plugins
```

## Usage

Run from within a Git repository with an open merge request:

```
/glab-mr-fullstate:fix
```

The command will:
1. Fetch MR state using `glab-mr-fullstate`
2. Analyze failed CI jobs and fix issues in the code
3. Review and address unresolved comments
4. Check resolved comments for missed feedback

## Author

Filip Procházka

## License

MIT
