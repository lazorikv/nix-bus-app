#!/usr/bin/env bash
# PreToolUse(Bash) guardrail: block direct `git commit` on the main branch so
# work ships through pull requests (see CLAUDE.md > Delivery workflow).
# Exit code 2 tells the harness to block the tool call and show stderr.

input=$(cat)
cmd=$(printf '%s' "$input" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('command',''))" \
  2>/dev/null)

case "$cmd" in
  *"git commit"*)
    branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
    if [ "$branch" = "main" ]; then
      echo "Guardrail: direct commits to 'main' are blocked. Create a feature branch and open a PR (see CLAUDE.md > Delivery workflow)." >&2
      exit 2
    fi
    ;;
esac
exit 0
