"""PreToolUse(Bash) guard: block git commits that carry Claude attribution.

Global policy: no Claude attribution may appear in any repo's commit messages.
This blocks the common signatures (Co-Authored-By: Claude / Generated with
Claude Code / claude.com/claude-code / the robot-emoji "Generated" line).
It intentionally does NOT block legitimate commits that merely mention the
word "claude" (e.g. committing code about the Claude API).
"""

import sys
import json
import re

MARKERS = [
    r"co-authored-by:\s*claude",
    r"generated with .{0,40}claude",
    r"claude\.com/claude-code",
    r"\U0001f916 generated with",
]


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return  # don't block on parse error
    cmd = ((data.get("tool_input") or {}).get("command") or "")
    low = cmd.lower()
    if "commit" not in low or "git" not in low:
        return
    if any(re.search(m, low) for m in MARKERS):
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    "全局策略：提交信息中不得包含任何 Claude 署名"
                    "（Co-Authored-By: Claude / Generated with Claude Code / "
                    "claude.com/claude-code / 🤖）。请删除这些行后重试。"
                ),
            }
        }))


if __name__ == "__main__":
    main()
