# ai-tool-use-validator

AI-powered tool use validation for Claude Code using LLM backends (Vertex AI, etc.) to evaluate command safety and correctness.

## What it does

Uses a PermissionRequest hook to intercept tool calls before they execute and evaluates them with an LLM backend:

1. **Allow** - Safe commands within the working directory or `/tmp` are auto-approved
2. **Deny with correction** - Safe but suboptimal commands are blocked with feedback so Claude generates better commands
3. **Ask user** - Potentially unsafe commands pass through to the user for manual approval

## Requirements

- Python 3.11+
- pipx (for installing the validator binary)
- Google Cloud SDK with Vertex AI access (for Vertex AI backend)

## Installation

### 1. Add the marketplace and install the plugin

```bash
claude plugin marketplace add fprochazka/claude-code-plugins
claude plugin install ai-tool-use-validator@fprochazka-claude-code-plugins
```

### 2. Install the validator binary

The plugin requires a Python CLI tool. Clone the repo and install with pipx:

```bash
git clone https://github.com/fprochazka/claude-code-plugins.git
pipx install ./claude-code-plugins/plugins/ai-tool-use-validator
```

### 3. Configure GCP authentication

```bash
gcloud auth application-default login
```

### 4. Create config file

```bash
mkdir -p ~/.config/claude-code-tool-use-validator
cat > ~/.config/claude-code-tool-use-validator/config.toml << 'EOF'
project_id = "your-gcp-project-id"
region = "europe-west1"
model = "claude-opus-4-5@20251101"
EOF
```

### 5. Verify the configuration

```bash
claude-code-tool-use-validator --verify
```

This will test the API connection and display the response.

## Example

Once installed, the validator evaluates tool calls automatically:

```
● Bash(npm test 2>&1 | tail -n 50)
  ⎿  Error: Don't truncate test output with `| tail` - if you need to see
     more context later, you'd have to re-run the entire test suite.
  ⎿  Denied by PermissionRequest hook

● Bash(rm -rf node_modules)
  ⎿  (No content)
  ⎿  Allowed by PermissionRequest hook
```

## Configuration

The config file is located at `~/.config/claude-code-tool-use-validator/config.toml`.

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `project_id` | Yes | - | Your GCP project ID with Vertex AI access |
| `region` | No | `global` | Vertex AI region (`global`, `us-east5`, `europe-west1`, etc.) |
| `model` | No | `claude-opus-4-5@20251101` | Model to use for validation |

### Example model IDs

Check [Google Cloud documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/partner-models/use-claude) for available models in your project.

| Model | Example Model ID |
|-------|------------------|
| Claude Opus 4.5 | `claude-opus-4-5@20251101` |
| Claude Sonnet 4.5 | `claude-sonnet-4-5@20250929` |
| Claude Haiku 3 | `claude-3-haiku@20240307` |

### Troubleshooting

If you get a 404 error:
1. Try `region = "us-east5"` instead of `"global"`
2. Verify the model is available in your project
3. Run `gcloud auth application-default set-quota-project YOUR_PROJECT_ID`

## How it works

The plugin uses a `PermissionRequest` hook that invokes the `claude-code-tool-use-validator` binary for every tool call that would normally show a permission dialog. The validator:

1. Receives the tool name, input parameters, and current working directory via stdin (JSON)
2. Reads the session transcript for context (last user prompt, recent operations)
3. Sends the context to an LLM backend for evaluation
4. Returns one of three decisions:
   - `allow` - Auto-approve the tool use
   - `deny` with message - Block and provide feedback to Claude
   - `ask` or no output - Show the normal permission dialog to the user

All decisions are logged to syslog. Monitor with:

```bash
tail -f /var/log/syslog | grep claude-code-tool-validator
```

## CLI Usage

```bash
# Verify API configuration
claude-code-tool-use-validator --verify

# Normal mode (reads JSON from stdin, used by the hook)
echo '{"tool_name": "Bash", "tool_input": {"command": "ls -la"}, "cwd": "/tmp"}' | claude-code-tool-use-validator
```

## Supported backends

- [x] Vertex AI (Claude via Google Cloud)
- [ ] OpenAI API
- [ ] Local models (Ollama)

## Development

### Testing locally

```bash
# Clone the repository
git clone https://github.com/fprochazka/claude-code-plugins.git
cd claude-code-plugins

# Install in development mode (editable)
pipx install -e ./plugins/ai-tool-use-validator

# Run Claude with the plugin loaded locally
claude --plugin-dir ./plugins/ai-tool-use-validator

# Watch syslog for decisions
tail -f /var/log/syslog | grep claude-code-tool-validator
```

### Reinstalling after changes

```bash
pipx install -e -f ./plugins/ai-tool-use-validator
```

## Author

Filip Procházka

## License

MIT
