#!/bin/bash
# KoroMind Safety Hook
# Blocks dangerous operations. You push when ready.

# Read the command from stdin (JSON format)
input=$(cat)
command=$(echo "$input" | jq -r '.tool_input.command // ""' 2>/dev/null)

# Block git push - user should push manually
if echo "$command" | grep -qE '(^|\s|&&|;)git\s+push'; then
    echo "BLOCKED: git push requires manual execution. You decide when to push." >&2
    exit 2
fi

# Block force operations
if echo "$command" | grep -qE 'rm\s+-rf\s+/|:(){ :|:& };:|>\s*/dev/sd'; then
    echo "BLOCKED: Dangerous operation detected." >&2
    exit 2
fi

# All clear
exit 0
