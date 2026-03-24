#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
HOOK="$SCRIPT_DIR/check-blocked-paths.sh"

PASS=0
FAIL=0

run_test() {
  local description="$1"
  local expected_exit="$2"
  local json_input="$3"

  local actual_exit=0
  echo "$json_input" | bash "$HOOK" >/dev/null 2>/dev/null || actual_exit=$?

  if [[ "$actual_exit" -eq "$expected_exit" ]]; then
    echo "  PASS: $description (exit=$actual_exit)"
    PASS=$((PASS + 1))
  else
    echo "  FAIL: $description (expected exit=$expected_exit, got exit=$actual_exit)"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Bash: blocked (source extraction) ==="

run_test "jar tf in .m2/repository → blocked" 2 \
  '{"tool_name":"Bash","tool_input":{"command":"jar tf ~/.m2/repository/cz/rohlik/foo/1.0/foo-1.0.jar"}}'

run_test "jar xf in .m2/repository → blocked" 2 \
  '{"tool_name":"Bash","tool_input":{"command":"jar xf ~/.m2/repository/cz/rohlik/foo/1.0/foo-1.0.jar"}}'

run_test "unzip in .m2/repository → blocked" 2 \
  '{"tool_name":"Bash","tool_input":{"command":"unzip -p ~/.m2/repository/cz/rohlik/foo/1.0/foo-1.0.jar META-INF/services/com.google.errorprone.bugpatterns.BugChecker"}}'

run_test "zipinfo in .m2/repository → blocked" 2 \
  '{"tool_name":"Bash","tool_input":{"command":"zipinfo ~/.m2/repository/cz/rohlik/foo/1.0/foo-1.0.jar"}}'

echo ""
echo "=== Bash: allowed (reads, cleanup, no .m2) ==="

run_test "grep in .m2/repository POM → allowed" 0 \
  '{"tool_name":"Bash","tool_input":{"command":"grep -n lombok ~/.m2/repository/org/springframework/boot/pom.xml"}}'

run_test "cat .m2/repository POM → allowed" 0 \
  '{"tool_name":"Bash","tool_input":{"command":"cat ~/.m2/repository/org/hibernate/pom.xml"}}'

run_test "find in .m2/repository → allowed" 0 \
  '{"tool_name":"Bash","tool_input":{"command":"find /home/user/.m2/repository -name \"*.jar\""}}'

run_test "ls in .m2/repository → allowed" 0 \
  '{"tool_name":"Bash","tool_input":{"command":"ls ~/.m2/repository/org/springframework/"}}'

run_test "rm -rf .m2/repository artifact → allowed" 0 \
  '{"tool_name":"Bash","tool_input":{"command":"rm -rf ~/.m2/repository/cz/rohlik/commercial-orders-errorprone-checks"}}'

run_test "git status (no .m2) → allowed" 0 \
  '{"tool_name":"Bash","tool_input":{"command":"git status"}}'

run_test "mvn package (no .m2) → allowed" 0 \
  '{"tool_name":"Bash","tool_input":{"command":"./mvnw package -pl :my-module"}}'

echo ""
echo "=== Read: blocked (source/binary files) ==="

run_test "Read .java in .m2/repository → blocked" 2 \
  '{"tool_name":"Read","tool_input":{"file_path":"/home/user/.m2/repository/org/hibernate/core/Session.java"}}'

run_test "Read .class in .m2/repository → blocked" 2 \
  '{"tool_name":"Read","tool_input":{"file_path":"/home/user/.m2/repository/org/hibernate/core/Session.class"}}'

run_test "Read .jar in .m2/repository → blocked" 2 \
  '{"tool_name":"Read","tool_input":{"file_path":"/home/user/.m2/repository/org/hibernate/hibernate-core/6.4.1/hibernate-core-6.4.1.jar"}}'

echo ""
echo "=== Read: allowed (POMs, other files, outside .m2) ==="

run_test "Read POM in .m2/repository → allowed" 0 \
  '{"tool_name":"Read","tool_input":{"file_path":"/home/user/.m2/repository/org/hibernate/hibernate-core/6.4.1/hibernate-core-6.4.1.pom"}}'

run_test "Read .xml in .m2/repository → allowed" 0 \
  '{"tool_name":"Read","tool_input":{"file_path":"/home/user/.m2/repository/org/hibernate/hibernate-core/6.4.1/maven-metadata-local.xml"}}'

run_test "Read file outside .m2 → allowed" 0 \
  '{"tool_name":"Read","tool_input":{"file_path":"/home/user/project/src/main/java/Foo.java"}}'

echo ""
echo "=== Other tools: always allowed (no opinion) ==="

run_test "Glob in .m2/repository → allowed" 0 \
  '{"tool_name":"Glob","tool_input":{"path":"/home/user/.m2/repository","pattern":"**/*.jar"}}'

run_test "Grep in .m2/repository → allowed" 0 \
  '{"tool_name":"Grep","tool_input":{"path":"/home/user/.m2/repository","pattern":"lombok"}}'

run_test "Write → allowed" 0 \
  '{"tool_name":"Write","tool_input":{"file_path":"/tmp/foo"}}'

echo ""
echo "==============================="
echo "Results: $PASS passed, $FAIL failed"

if [[ "$FAIL" -gt 0 ]]; then
  exit 1
fi
