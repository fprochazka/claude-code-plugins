#!/usr/bin/env python3
"""
CLI entry point for the AI-powered tool use validator.

This script is invoked as a PermissionRequest hook and evaluates whether
tool calls should be allowed, denied with feedback, or passed to the user.

Exit behaviors:
- Exit 0 with allow JSON: Auto-approve the tool use
- Exit 0 with deny JSON: Block the tool use and provide feedback to Claude
- Exit 0 with ask JSON or no output: Show permission dialog to user
- Exit 2 with stderr: Block and show error
"""

import json
import re
import sys
import syslog
import time
import tomllib
import warnings
from dataclasses import dataclass
from pathlib import Path

# Suppress Google Cloud SDK credential warnings
warnings.filterwarnings("ignore", message=".*end user credentials.*quota project.*")

from anthropic import AnthropicVertex


CONFIG_PATH = Path.home() / ".config" / "claude-code-tool-use-validator" / "config.toml"


@dataclass
class Config:
    """Configuration for the validator."""

    project_id: str
    region: str = "global"
    model: str = "claude-opus-4-5@20251101"


def load_config() -> Config:
    """Load configuration from TOML file."""
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found: {CONFIG_PATH}\n"
            f"Please create it with the following content:\n\n"
            f'project_id = "your-gcp-project-id"\n'
            f'region = "global"  # or specific region like "us-east5"\n'
            f'model = "claude-opus-4-5@20251101"  # or other model\n'
        )

    with open(CONFIG_PATH, "rb") as f:
        data = tomllib.load(f)

    if "project_id" not in data:
        raise ValueError(f"Missing required 'project_id' in {CONFIG_PATH}")

    return Config(
        project_id=data["project_id"],
        region=data.get("region", "global"),
        model=data.get("model", "claude-opus-4-5@20251101"),
    )


VALIDATOR_SYSTEM_PROMPT = """\
You are a security and optimization gatekeeper for Claude Code tool calls. Your job is to evaluate whether a tool invocation should be allowed, denied with feedback, or escalated to the human user for decision.

You may think through your reasoning, then end your response with EXACTLY ONE of the following decision tags:

<decision action="allow" />
Use when the operation is safe and reasonable.

<decision action="denyWithReason">message for the agent</decision>
Use when you detect a suboptimal pattern that the agent should correct. The message will be shown to Claude to help it improve.

<decision action="escalateToHuman" />
Use when the operation is dangerous, uncertain, or you cannot confidently assess it. The user will see a permission dialog.

<allow_criteria>
- Read-only commands (cat, ls, grep, find, git status, git log, etc.)
- Reasonable file operations within CWD: rm -rf node_modules/, moving/deleting files during refactoring
- Build, test, lint, format commands (npm test, pytest, eslint, prettier, cargo build, etc.)
- Git operations that don't push (git add, git commit, git checkout, git branch)
- Creating/editing files within the project directory
- Installing dependencies (npm install, pip install, cargo add)
</allow_criteria>

<deny_with_reason_criteria>
Teaching moments to improve agent behavior:
- Truncating expensive command output with `| tail -n 30` or `| head -n 50` instead of redirecting to /tmp/file.txt for later analysis - this wastes compute time because the agent may need to re-run the command to see more output
- Running commands that will produce massive output without limiting it
- Other patterns that waste time, tokens, or resources
- Inefficient approaches when better alternatives exist
</deny_with_reason_criteria>

<escalate_to_human_criteria>
- Operations targeting files/directories OUTSIDE the current working directory (CWD)
- Mass deletion commands (rm -rf /, rm -rf ~, etc.)
- Production database operations
- Pushing to remote repositories (git push)
- Running commands with sudo
- Network operations to external services
- Any operation you are uncertain about
- Modifying system configuration files
</escalate_to_human_criteria>

<critical_rules>
1. Unless you are 99.9% certain the operation is safe and beneficial, choose escalateToHuman
2. When in doubt, ALWAYS escalate to human
3. The CWD is the project root - operations within it are generally safer
4. Consider the user's stated intent from their last prompt when evaluating
5. Be especially cautious with destructive operations (rm, overwrite, etc.)
</critical_rules>

Think through your reasoning, then output your decision tag at the end."""


def make_allow_response() -> dict:
    """Create a response that allows the tool use."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {"behavior": "allow"},
        }
    }


def make_deny_response(message: str, interrupt: bool = False) -> dict:
    """Create a response that denies the tool use with feedback to Claude."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": "deny",
                "message": message,
                "interrupt": interrupt,
            },
        }
    }


def make_ask_response() -> dict:
    """Create a response that shows the permission dialog to the user."""
    return {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": "ask",
            },
        }
    }


def log_to_syslog(
    tool_name: str,
    tool_input_summary: str,
    decision: str,
    duration_ms: float | None = None,
    level: int = syslog.LOG_INFO,
) -> None:
    """Log the validation decision to syslog."""
    syslog.openlog("claude-code-tool-validator", syslog.LOG_PID, syslog.LOG_USER)
    duration_str = f"duration={duration_ms:.0f}ms " if duration_ms is not None else ""
    message = f"{duration_str}tool={tool_name} decision={decision} input={tool_input_summary}"
    syslog.syslog(level, message)
    syslog.closelog()


def summarize_tool_input(tool_name: str, tool_input: dict) -> str:
    """Create a brief summary of the tool input for logging."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        # Truncate long commands
        if len(cmd) > 100:
            return f"command={cmd[:100]}..."
        return f"command={cmd}"
    elif tool_name == "Read":
        return f"file={tool_input.get('file_path', '')}"
    elif tool_name == "Write":
        path = tool_input.get("file_path", "")
        content_len = len(tool_input.get("content", ""))
        return f"file={path} content_len={content_len}"
    elif tool_name == "Edit":
        path = tool_input.get("file_path", "")
        return f"file={path}"
    elif tool_name == "Glob":
        return f"pattern={tool_input.get('pattern', '')}"
    elif tool_name == "Grep":
        return f"pattern={tool_input.get('pattern', '')}"
    else:
        # Generic summary
        keys = list(tool_input.keys())[:3]
        return f"keys={keys}"


def parse_transcript(transcript_path: str) -> tuple[str | None, list[dict]]:
    """
    Parse the JSONL transcript to extract context.

    Returns:
        - last_user_prompt: The last user message with string content
        - recent_operations: List of recent tool_use/tool_result pairs
    """
    last_user_prompt: str | None = None
    recent_operations: list[dict] = []

    try:
        with open(transcript_path, "r") as f:
            lines = f.readlines()
    except (FileNotFoundError, PermissionError, OSError):
        return None, []

    # Parse all lines into entries
    entries = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            entries.append(entry)
        except json.JSONDecodeError:
            continue

    # Find the last user prompt with string content
    for entry in reversed(entries):
        if entry.get("type") == "user":
            message = entry.get("message", {})
            content = message.get("content")
            if isinstance(content, str):
                last_user_prompt = content
                break

    # Find recent tool operations (tool_use from assistant, tool_result responses)
    tool_uses = []
    tool_results = {}

    for entry in entries:
        if entry.get("type") == "assistant":
            message = entry.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_uses.append(block)
        elif entry.get("type") == "user":
            message = entry.get("message", {})
            content = message.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        tool_id = block.get("tool_use_id")
                        if tool_id:
                            tool_results[tool_id] = block

    # Get the last ~10 tool operations with their results
    recent_tool_uses = tool_uses[-10:]
    for tool_use in recent_tool_uses:
        tool_id = tool_use.get("id")
        operation = {
            "tool_name": tool_use.get("name"),
            "tool_input": tool_use.get("input", {}),
        }
        if tool_id and tool_id in tool_results:
            result = tool_results[tool_id]
            result_content = result.get("content")
            # Truncate very long results
            if isinstance(result_content, str) and len(result_content) > 500:
                result_content = result_content[:500] + "... (truncated)"
            operation["result"] = result_content
        recent_operations.append(operation)

    return last_user_prompt, recent_operations


def format_operations_for_prompt(operations: list[dict]) -> str:
    """Format recent operations for the validator prompt."""
    if not operations:
        return "No recent operations."

    lines = []
    for i, op in enumerate(operations, 1):
        tool_name = op.get("tool_name", "Unknown")
        tool_input = op.get("tool_input", {})
        result = op.get("result", "")

        # Create a compact representation
        input_summary = summarize_tool_input(tool_name, tool_input)
        result_preview = ""
        if result:
            if isinstance(result, str):
                result_preview = result[:200] + "..." if len(result) > 200 else result
            else:
                result_preview = str(result)[:200]

        lines.append(f"{i}. {tool_name}: {input_summary}")
        if result_preview:
            lines.append(f"   Result: {result_preview}")

    return "\n".join(lines)


def build_validator_prompt(
    cwd: str,
    last_user_prompt: str | None,
    recent_operations: list[dict],
    tool_name: str,
    tool_input: dict,
) -> str:
    """Build the user prompt for the validator LLM."""
    parts = []

    parts.append(f"<cwd>{cwd}</cwd>")

    if last_user_prompt:
        parts.append(f"<last_user_prompt>\n{last_user_prompt}\n</last_user_prompt>")
    else:
        parts.append("<last_user_prompt>Not available</last_user_prompt>")

    parts.append(
        f"<recent_operations>\n{format_operations_for_prompt(recent_operations)}\n</recent_operations>"
    )

    parts.append(
        f"<current_tool_request>\n<tool_name>{tool_name}</tool_name>\n<tool_input>\n{json.dumps(tool_input, indent=2)}\n</tool_input>\n</current_tool_request>"
    )

    parts.append(
        "<task>Evaluate this tool request. Think through your reasoning, then output your decision.</task>"
    )

    return "\n\n".join(parts)


def parse_decision(response_text: str) -> tuple[str, str | None]:
    """
    Parse the decision XML from the response.

    Validates that there is exactly one valid decision tag.

    Returns:
        - action: "allow", "denyWithReason", "escalateToHuman", or "error"
        - reason: The reason text for denyWithReason, None otherwise
    """
    # Find all decision tags (any action type)
    all_decisions = re.findall(
        r'<decision\s+action="(allow|denyWithReason|escalateToHuman)"(?:\s*/>|>(.*?)</decision>)',
        response_text,
        re.DOTALL,
    )

    # Must have exactly one decision
    if len(all_decisions) != 1:
        return "error", None

    action, content = all_decisions[0]

    if action == "allow":
        return "allow", None
    elif action == "escalateToHuman":
        return "escalateToHuman", None
    elif action == "denyWithReason":
        reason = content.strip() if content else ""
        if not reason:
            # denyWithReason must have a reason
            return "error", None
        return "denyWithReason", reason

    return "error", None


def call_vertex_ai(config: Config, system_prompt: str, user_prompt: str) -> str:
    """Call Vertex AI with the given prompts and return the response text."""
    client = AnthropicVertex(project_id=config.project_id, region=config.region)
    response = client.messages.create(
        model=config.model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract text from response
    if response.content and len(response.content) > 0:
        return response.content[0].text
    return ""


def evaluate_tool_use(hook_input: dict) -> dict | None:
    """
    Evaluate the tool use and return a decision.

    Returns:
        - allow response: Auto-approve
        - deny response: Block with feedback
        - ask response or None: Show permission dialog to user
    """
    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})
    cwd = hook_input.get("cwd", "")
    transcript_path = hook_input.get("transcript_path", "")

    tool_input_summary = summarize_tool_input(tool_name, tool_input)

    # Load config
    try:
        config = load_config()
    except (FileNotFoundError, ValueError) as e:
        log_to_syslog(
            tool_name,
            tool_input_summary,
            f"escalateToHuman (config error: {e})",
            level=syslog.LOG_ERR,
        )
        return None

    # Parse transcript for context
    last_user_prompt = None
    recent_operations: list[dict] = []
    if transcript_path:
        last_user_prompt, recent_operations = parse_transcript(transcript_path)

    # Build the prompt for the validator
    user_prompt = build_validator_prompt(
        cwd=cwd,
        last_user_prompt=last_user_prompt,
        recent_operations=recent_operations,
        tool_name=tool_name,
        tool_input=tool_input,
    )

    # Call Vertex AI
    start_time = time.perf_counter()
    try:
        response_text = call_vertex_ai(config, VALIDATOR_SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        log_to_syslog(
            tool_name,
            tool_input_summary,
            f"escalateToHuman (API error: {e})",
            duration_ms=duration_ms,
            level=syslog.LOG_ERR,
        )
        return None

    duration_ms = (time.perf_counter() - start_time) * 1000

    # Parse the decision
    action, reason = parse_decision(response_text)

    if action == "allow":
        log_to_syslog(tool_name, tool_input_summary, "allow", duration_ms=duration_ms)
        return make_allow_response()
    elif action == "denyWithReason":
        log_to_syslog(
            tool_name,
            tool_input_summary,
            f"denyWithReason: {reason}",
            duration_ms=duration_ms,
            level=syslog.LOG_WARNING,
        )
        return make_deny_response(reason or "Operation denied by AI validator.")
    elif action == "escalateToHuman":
        log_to_syslog(tool_name, tool_input_summary, "escalateToHuman", duration_ms=duration_ms)
        return None
    else:
        # Parse error - escalate to human as safe fallback
        log_to_syslog(
            tool_name,
            tool_input_summary,
            "escalateToHuman (parse error)",
            duration_ms=duration_ms,
            level=syslog.LOG_WARNING,
        )
        return None


def verify_api() -> None:
    """Verify that the API can be called successfully."""
    print("Loading config...")
    try:
        config = load_config()
        print(f"  project_id: {config.project_id}")
        print(f"  region: {config.region}")
        print(f"  model: {config.model}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Config error: {e}", file=sys.stderr)
        sys.exit(1)

    print("\nTesting API call...")
    try:
        client = AnthropicVertex(project_id=config.project_id, region=config.region)
        response = client.messages.create(
            model=config.model,
            max_tokens=50,
            messages=[{"role": "user", "content": "Say 'API test successful' and nothing else."}],
        )
        if response.content and len(response.content) > 0:
            print(f"  Response: {response.content[0].text}")
            print("\nAPI verification successful!")
            sys.exit(0)
        else:
            print("  Error: Empty response from API", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"  API error: {e}", file=sys.stderr)
        print("\nTroubleshooting tips:", file=sys.stderr)
        print("  1. Check that 'gcloud auth application-default login' was run", file=sys.stderr)
        print("  2. Verify project_id is correct and has Vertex AI API enabled", file=sys.stderr)
        print("  3. Try a different region (e.g., 'us-east5' instead of 'global')", file=sys.stderr)
        print("  4. Try a different model (e.g., 'claude-sonnet-4-5@20250929')", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the CLI."""
    # Check for --verify flag
    if len(sys.argv) > 1 and sys.argv[1] in ("--verify", "-v", "verify"):
        verify_api()
        return

    # Normal hook mode: read JSON from stdin
    try:
        raw_input = sys.stdin.read()
        hook_input = json.loads(raw_input) if raw_input.strip() else {}
    except json.JSONDecodeError as e:
        print(f"Failed to parse hook input: {e}", file=sys.stderr)
        sys.exit(1)

    # Evaluate the tool use
    try:
        response = evaluate_tool_use(hook_input)
    except Exception as e:
        print(f"Evaluation error: {e}", file=sys.stderr)
        sys.exit(1)

    # Output the decision (or nothing to pass through to user)
    if response is not None:
        print(json.dumps(response))

    sys.exit(0)


if __name__ == "__main__":
    main()
