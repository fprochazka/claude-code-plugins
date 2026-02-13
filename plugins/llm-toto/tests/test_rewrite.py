#!/usr/bin/env python3
"""Tests for the hook rewrite logic."""

import sys
import os

# Add parent dirs to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "hooks"))

from importlib.machinery import SourceFileLoader

# Load the module with a hyphen in the filename
rewrite = SourceFileLoader("rewrite_bash", os.path.join(os.path.dirname(__file__), "..", "hooks", "rewrite-bash.py")).load_module()

SESSION = "test-session"


def assert_passthrough(command: str, msg: str = ""):
    """Assert that the command is NOT rewritten."""
    result = rewrite.rewrite_command(command, SESSION)
    assert result is None, f"Expected passthrough for '{command}'{' (' + msg + ')' if msg else ''}, got: {result}"


def assert_rewritten(command: str, expected_inner: str | None = None, msg: str = ""):
    """Assert that the command IS rewritten."""
    result = rewrite.rewrite_command(command, SESSION)
    assert result is not None, f"Expected rewrite for '{command}'{' (' + msg + ')' if msg else ''}, got None"
    if expected_inner:
        assert expected_inner in result, f"Expected '{expected_inner}' in rewritten command, got: {result}"


def test_passthrough_file_operations():
    """Simple file operations should not be wrapped."""
    assert_passthrough("cat file.txt")
    assert_passthrough("head -50 file.txt")
    assert_passthrough("tail -20 file.txt")
    assert_passthrough("less file.txt")
    assert_passthrough("wc -l file.txt")


def test_passthrough_file_management():
    """File management commands should not be wrapped."""
    assert_passthrough("mkdir -p /tmp/test")
    assert_passthrough("cp file1.txt file2.txt")
    assert_passthrough("mv old.txt new.txt")
    assert_passthrough("rm -f temp.txt")
    assert_passthrough("chmod +x script.sh")
    assert_passthrough("ln -s target link")
    assert_passthrough("touch file.txt")


def test_passthrough_echo():
    """Echo and printf should not be wrapped."""
    assert_passthrough("echo hello")
    assert_passthrough('echo "test output"')
    assert_passthrough("printf '%s\\n' test")


def test_passthrough_git_write():
    """Git write operations should not be wrapped."""
    assert_passthrough("git add .")
    assert_passthrough("git commit -m 'fix bug'")
    assert_passthrough("git push origin main")
    assert_passthrough("git checkout -b new-branch")
    assert_passthrough("git stash")
    assert_passthrough("git rebase main")
    assert_passthrough("git merge feature")
    assert_passthrough("git cherry-pick abc123")
    assert_passthrough("git pull")
    assert_passthrough("git fetch")
    assert_passthrough("git tag v1.0")


def test_passthrough_package_install():
    """Package installation should not be wrapped."""
    assert_passthrough("pip install requests")
    assert_passthrough("npm install lodash")
    assert_passthrough("npm ci")
    assert_passthrough("yarn add react")
    assert_passthrough("pnpm install")
    assert_passthrough("cargo install ripgrep")
    assert_passthrough("uv pip install flask")
    assert_passthrough("brew install jq")


def test_passthrough_grep_specific_file():
    """Grep on specific files (not recursive) should not be wrapped."""
    assert_passthrough("grep pattern file.txt")
    assert_passthrough("grep -n 'error' log.txt")
    assert_passthrough("grep -i 'test' output.log")


def test_passthrough_sed_awk():
    """Sed and awk on files should not be wrapped."""
    assert_passthrough("sed 's/old/new/g' file.txt")
    assert_passthrough("awk '{print $1}' data.csv")
    assert_passthrough("sort file.txt")
    assert_passthrough("diff file1.txt file2.txt")


def test_passthrough_shell_builtins():
    """Shell builtins should not be wrapped."""
    assert_passthrough("export FOO=bar")
    assert_passthrough("cd /tmp")
    assert_passthrough("source ~/.bashrc")
    assert_passthrough("true")
    assert_passthrough("false")


def test_passthrough_variable_assignment():
    """Variable assignments should not be wrapped."""
    assert_passthrough("FOO=bar")
    assert_passthrough("MY_VAR=123")


def test_passthrough_docker_build():
    """Docker build/push should not be wrapped."""
    assert_passthrough("docker build -t myimage .")
    assert_passthrough("docker push myimage:latest")
    assert_passthrough("docker tag img:v1 img:v2")


def test_passthrough_already_wrapped():
    """Commands already using llm-toto should not be wrapped."""
    assert_passthrough("llm-toto ./mvnw package")
    assert_passthrough("llm-toto --session x make build")


def test_rewrite_build_commands():
    """Build commands should be wrapped."""
    assert_rewritten("make build", "make build")
    assert_rewritten("./mvnw package", "./mvnw package")
    assert_rewritten("./gradlew build", "./gradlew build")
    assert_rewritten("cargo build", "cargo build")
    assert_rewritten("go build ./...", "go build ./...")


def test_rewrite_test_commands():
    """Test commands should be wrapped."""
    assert_rewritten("pytest", "pytest")
    assert_rewritten("pytest tests/", "pytest tests/")
    assert_rewritten("cargo test", "cargo test")
    assert_rewritten("go test ./...", "go test ./...")
    assert_rewritten("npx jest", "npx jest")


def test_rewrite_git_read_operations():
    """Git read operations should be wrapped."""
    assert_rewritten("git status", "git status")
    assert_rewritten("git diff", "git diff")
    assert_rewritten("git diff --cached", "git diff --cached")
    assert_rewritten("git log --oneline -20", "git log --oneline -20")
    assert_rewritten("git show HEAD", "git show HEAD")
    assert_rewritten("git branch -a", "git branch -a")


def test_rewrite_container_runtime():
    """Container runtime commands should be wrapped."""
    assert_rewritten("kubectl get pods", "kubectl get pods")
    assert_rewritten("kubectl logs pod-name", "kubectl logs pod-name")
    assert_rewritten("docker run ubuntu ls", "docker run ubuntu ls")
    assert_rewritten("docker logs container", "docker logs container")
    assert_rewritten("docker exec container ls", "docker exec container ls")


def test_rewrite_cli_tools():
    """CLI tools should be wrapped."""
    assert_rewritten("glab mr view 123", "glab mr view 123")
    assert_rewritten("gh pr view 456", "gh pr view 456")
    assert_rewritten("curl https://example.com", "curl https://example.com")
    assert_rewritten("terraform plan", "terraform plan")


def test_rewrite_recursive_grep():
    """Recursive grep should be wrapped (it's a search, not a file read)."""
    assert_rewritten("grep -r pattern .", "grep -r pattern .")
    assert_rewritten("grep -R 'error' src/", "grep -R 'error' src/")


def test_rewrite_find():
    """Find should be wrapped."""
    assert_rewritten("find . -name '*.py'", "find . -name '*.py'")


def test_rewrite_interpreters():
    """Interpreter commands should be wrapped."""
    assert_rewritten("python3 script.py", "python3 script.py")
    assert_rewritten("node app.js", "node app.js")


def test_strip_trailing_grep():
    """Trailing grep pipes should be stripped."""
    result = rewrite.rewrite_command("./mvnw package 2>&1 | grep ERROR", SESSION)
    assert result is not None
    assert "grep" not in result
    assert "2>&1" not in result
    assert "./mvnw package" in result


def test_strip_trailing_tail():
    """Trailing tail pipes should be stripped."""
    result = rewrite.rewrite_command("./mvnw package 2>&1 | tail -5", SESSION)
    assert result is not None
    assert "tail" not in result
    assert "2>&1" not in result
    assert "./mvnw package" in result


def test_strip_trailing_head():
    """Trailing head pipes should be stripped."""
    result = rewrite.rewrite_command("kubectl get pods | head -20", SESSION)
    assert result is not None
    assert "head" not in result
    assert "kubectl get pods" in result


def test_strip_chained_filters():
    """Chained trailing filter pipes should all be stripped."""
    result = rewrite.rewrite_command("./mvnw package 2>&1 | grep ERROR | head -20", SESSION)
    assert result is not None
    assert "grep" not in result
    assert "head" not in result
    assert "2>&1" not in result
    assert "./mvnw package" in result


def test_strip_trailing_sort():
    """Trailing sort should be stripped."""
    result = rewrite.rewrite_command("find . -name '*.py' | sort", SESSION)
    assert result is not None
    assert "sort" not in result
    assert "find . -name '*.py'" in result


def test_strip_stderr_redirect():
    """2>&1 should be stripped from commands."""
    result = rewrite.rewrite_command("./mvnw package 2>&1", SESSION)
    assert result is not None
    assert "2>&1" not in result
    assert "./mvnw package" in result


def test_strip_stderr_redirect_standalone():
    """2>&1 without pipes should also be stripped."""
    result = rewrite.rewrite_command("cargo build 2>&1", SESSION)
    assert result is not None
    assert "2>&1" not in result
    assert "cargo build" in result


def test_no_strip_semantic_pipes():
    """Semantic pipes (jq, python processing) should NOT be stripped."""
    result = rewrite.rewrite_command("curl https://api.example.com | jq .", SESSION)
    assert result is not None
    assert "jq" in result


def test_compound_command_passthrough():
    """Compound commands where the last part is passthrough should pass through."""
    assert_passthrough("cd /tmp && cat file.txt", "last command is cat")
    assert_passthrough("cd /tmp && echo hello", "last command is echo")


def test_compound_command_rewrite():
    """Compound commands where the last part should be wrapped."""
    assert_rewritten("cd /project && make build", "make build")
    assert_rewritten("cd /project && ./mvnw package", "./mvnw package")


def test_session_id_in_output():
    """Session ID should appear in the rewritten command."""
    result = rewrite.rewrite_command("make build", "my-session-123")
    assert result is not None
    assert "--session my-session-123" in result


def test_output_format():
    """Rewritten command should have the expected format."""
    result = rewrite.rewrite_command("make build", SESSION)
    assert result is not None
    assert result.startswith("python3 ")
    assert "llm-toto.py" in result
    assert f"--session {SESSION}" in result
    assert "-- make build" in result


if __name__ == "__main__":
    test_functions = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    errors = []

    for test_fn in test_functions:
        try:
            test_fn()
            passed += 1
            print(f"  PASS  {test_fn.__name__}")
        except AssertionError as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"  FAIL  {test_fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            errors.append((test_fn.__name__, str(e)))
            print(f"  ERROR {test_fn.__name__}: {e}")

    print(f"\n{passed} passed, {failed} failed")
    if errors:
        print("\nFailures:")
        for name, err in errors:
            print(f"  {name}: {err}")
        sys.exit(1)
