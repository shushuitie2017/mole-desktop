#!/usr/bin/env python3
"""PreToolUse 通用守卫：把各项目 CLAUDE.md 里的硬规则转成确定性拦截。

机制
- 读 stdin 的 hook JSON，取 tool_name / tool_input。
- 定位项目：Edit/Write/MultiEdit 从 file_path 所在目录、Bash 从 cwd 向上找最近的
  `.claude/rules.json`；找不到 → 静默放行（无 rules.json 的项目零影响）。
- 评估 rules.json 里的规则数组，两类：
    on=="bash"  → 正则匹配 tool_input.command
    on=="write" → 正则匹配写入内容（Write.content / Edit.new_string /
                  MultiEdit.edits[].new_string 拼接），可选 globs 限定文件，
                  且**永不**对 .claude/ 下的文件生效（避免拦到 CLAUDE.md / rules.json 自身）。
- 命中 → 输出 {"hookSpecificOutput":{...,"permissionDecision":"deny","permissionDecisionReason":msg}}。
- 任何异常 → 静默放行（fail-open，绝不卡住正常开发）。脚本总是 exit 0。

运行时软开关（env，无需改 rules.json；吸收自 ECC hooks 的 profile 分档）
- PROJECT_GUARD=off|0|false|disabled|no   → 整体关闭（调试/恢复时用），全部放行。
- PROJECT_GUARD_PROFILE=minimal|standard|strict （默认 standard）
    规则可选标 "level":"minimal"|"standard"|"strict"（默认 standard）。
    minimal 档只强制 level=minimal 的核心规则；standard 强制 minimal+standard；
    strict 强制全部（含 level=strict 的额外严规则）。未标 level 的旧规则=standard，行为不变。
- PROJECT_GUARD_DISABLED="id1,id2"         → 按规则 ID 临时禁用若干条。

规则文件 schema（.claude/rules.json）
{
  "project": "<name>",
  "rules": [
    {"id":"...", "on":"bash"|"write",
     "match":"<python 正则>",
     "level":"standard",          # 可选，默认 standard；见上 PROJECT_GUARD_PROFILE
     "globs":["**/*.js"],          # 仅 on==write 可选；不写=对所有写入文件生效
     "message":"<拦截原因，给人看>"}
  ]
}
"""
import sys
import os
import json
import re
import fnmatch


def safe_exit():
    sys.exit(0)


def find_rules(start_dir):
    """从 start_dir 向上逐级找 .claude/rules.json，返回 (rules_path, project_root) 或 (None, None)。"""
    try:
        d = os.path.abspath(start_dir)
    except Exception:
        return None, None
    seen = 0
    while d and seen < 60:
        candidate = os.path.join(d, ".claude", "rules.json")
        if os.path.isfile(candidate):
            return candidate, d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
        seen += 1
    return None, None


def load_rules(rules_path):
    try:
        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    rules = data.get("rules")
    return rules if isinstance(rules, list) else []


def write_content(tool_name, tool_input):
    """汇总一次写操作的目标内容，供 on==write 规则匹配。"""
    parts = []
    if tool_name == "Write":
        parts.append(str(tool_input.get("content") or ""))
    elif tool_name == "Edit":
        parts.append(str(tool_input.get("new_string") or ""))
    elif tool_name == "MultiEdit":
        for e in tool_input.get("edits") or []:
            if isinstance(e, dict):
                parts.append(str(e.get("new_string") or ""))
    return "\n".join(parts)


def glob_match(file_path, globs):
    """file_path 是否命中任一 glob（对完整路径和 basename 都试一遍，统一用 / 分隔）。"""
    if not globs:
        return True
    norm = file_path.replace("\\", "/")
    base = norm.rsplit("/", 1)[-1]
    for g in globs:
        gg = g.replace("\\", "/")
        if fnmatch.fnmatch(norm, gg) or fnmatch.fnmatch(base, gg) or fnmatch.fnmatch(norm, "*/" + gg.lstrip("*/")):
            return True
    return False


def deny(reason, rule_id):
    sys.stdout.write(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"[project-guard:{rule_id}] {reason}",
        }
    }, ensure_ascii=False))


_LEVELS = {"minimal": 0, "standard": 1, "strict": 2}


def main():
    # 整体软开关：调试/恢复时不删规则即可关闭
    if os.environ.get("PROJECT_GUARD", "").strip().lower() in ("off", "0", "false", "disabled", "no"):
        return safe_exit()
    try:
        data = json.load(sys.stdin)
    except Exception:
        return safe_exit()

    tool_name = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return safe_exit()

    file_path = str(tool_input.get("file_path") or tool_input.get("path") or "")
    cwd = data.get("cwd") or os.getcwd()

    # 定位规则文件：写操作以目标文件目录为基准，否则用 cwd。
    if tool_name in ("Edit", "Write", "MultiEdit") and file_path:
        start = os.path.dirname(file_path) or cwd
    else:
        start = cwd
    rules_path, _root = find_rules(start)
    if not rules_path:
        return safe_exit()

    rules = load_rules(rules_path)
    if not rules:
        return safe_exit()

    # profile 分档 + 按 ID 禁用（env 软开关）
    profile_rank = _LEVELS.get(os.environ.get("PROJECT_GUARD_PROFILE", "standard").strip().lower(), 1)
    disabled_ids = {x.strip() for x in os.environ.get("PROJECT_GUARD_DISABLED", "").split(",") if x.strip()}

    is_write = tool_name in ("Edit", "Write", "MultiEdit")
    is_bash = tool_name == "Bash"
    command = str(tool_input.get("command") or "")
    content = write_content(tool_name, tool_input) if is_write else ""

    # 写操作永不拦 .claude/ 下的文件（CLAUDE.md/rules.json 自身、设置等）
    norm_fp = file_path.replace("\\", "/")
    write_in_dotclaude = is_write and ("/.claude/" in norm_fp or norm_fp.endswith("/.claude"))

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        on = rule.get("on")
        pattern = rule.get("match")
        if not pattern:
            continue
        rid = rule.get("id") or "rule"
        msg = rule.get("message") or "违反项目硬规则。"
        # 软开关：按 ID 禁用 / 按 profile 档过滤（level 高于当前档则跳过）
        if rid in disabled_ids:
            continue
        if _LEVELS.get(str(rule.get("level", "standard")).strip().lower(), 1) > profile_rank:
            continue
        try:
            rx = re.compile(pattern)
        except Exception:
            continue

        if on == "bash" and is_bash:
            if rx.search(command):
                return (deny(msg, rid), safe_exit())[1]
        elif on == "write" and is_write:
            if write_in_dotclaude:
                continue
            if not glob_match(file_path, rule.get("globs")):
                continue
            if rx.search(content):
                return (deny(msg, rid), safe_exit())[1]

    return safe_exit()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        safe_exit()
