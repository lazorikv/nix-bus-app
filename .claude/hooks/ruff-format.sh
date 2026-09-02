#!/usr/bin/env bash
# PostToolUse(Edit|Write) hook: auto-format backend Python after edits so lint
# stays green. No-op if the edited file is not backend Python or ruff is absent.

input=$(cat)
file=$(printf '%s' "$input" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('tool_input',{}).get('file_path',''))" \
  2>/dev/null)

case "$file" in
  *backend/*.py)
    command -v ruff >/dev/null 2>&1 || exit 0
    ruff format "$file" >/dev/null 2>&1
    ruff check --fix "$file" >/dev/null 2>&1
    ;;
esac
exit 0
