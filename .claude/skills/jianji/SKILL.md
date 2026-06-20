---
name: jianji
description: "鉴技 / SkillScope —— 当你（或用户）不确定「这个活该用哪个 skill / 用哪个技能 / which skill should I use / 有没有现成的 skill 干这个」时，用自然语言查询本地 skill 库并给出可解释的推荐。CJK 感知（中/日/英都行）、零网络、确定性、只读。Use this WHENEVER the user asks which skill/技能 to use for a task, asks if a skill exists for X, wants to browse/list installed skills by domain, or when you yourself are unsure which skill to route a task to. Also use to audit skill-context bloat (how many skills, token weight, tier distribution)."
allowed-tools:
  - Bash
  - Read
metadata:
  tier: default-min
  cost: light
  side_effects: none
  domains: [meta]
  argument-hint: "[自然语言任务，如 '把这本书做成skill' / 'which skill to review code']"
---

# 鉴技 / SkillScope —— skill 推荐与编目

自然语言 → 该用哪个 skill。背后是 `note/jianji/` 的零依赖 Node CLI：一个 CJK 感知的**确定性词法推荐器**，扫本机两个 skill 根（`~/.claude/skills` + `note/.claude/skills`），把查询与每个 skill 的描述都做中日英分词后打分排序，给出可解释 reasons。**只读、零网络、不调模型。**

## CLI 路径（绝对路径，固定）

```
node C:/Users/1/Desktop/note/jianji/bin/jianji.js <command> [args]
```

## 何时用这个 skill

- 用户问「这个该用哪个 skill / 用哪个技能 / which skill for X / 有没有现成 skill 干这个」。
- **你自己**拿不准把一个任务路由到哪个 skill 时——先查一下，别凭记忆瞎猜。
- 用户想按域/档位浏览已装 skill，或盘点 skill 上下文体量。

## 怎么用

1. **推荐**（最常用）。把用户的任务原话当查询，跑：
   ```bash
   node C:/Users/1/Desktop/note/jianji/bin/jianji.js consult "<用户任务原话>" --json
   ```
   解析 `matches[]`（已按分数排序，每条带 `name/score/tier/cost/side_effects/domains/reasons`）。给用户**最多前 3 条**，每条一句话说清「为什么推它」（用 reasons）。若有 `cautions`（opt-in / 有副作用 / 重型），提示一句。
   - 命中分数都很低 / `matched` 为 0 → 诚实说「没有特别贴合的现成 skill」，别硬塞。

2. **浏览**：`list`（全部）、`list --domain trading`、`list --tier opt-in`、`show <name>`。

3. **盘点**：`stats`（多少 skill、估算 token、按域分布）——回答「skill 太多了吗 / 上下文多重」。

## 输出给用户的姿势

- 先一句话给结论（「这个活用 X」），再列候选 + 理由。
- 推荐 ≠ 自动调用：把决定权留给用户/上层（除非用户已明确要直接开干）。
- 别复述 CLI 细节，直接给路由结论。

## 红线

本 skill 只读本机自己的 skill 目录，零网络、零写入，**绝不**触碰 `note/第三方参考/ECC`（它的设计被吸收，但运行时绝不安装/运行）。维护见 `note/jianji/CLAUDE.md`。
