---
name: code-craft
description: "Router/index for the software-craftsmanship skill family — 7 classic books turned into knowledge bases: clean-code, refactoring, design-patterns, solid-principles, code-complete, pragmatic-programmer, 97-things. Use when the user wants cleaner code / more disciplined, standardized engineering, asks which principle/pattern/refactoring applies, wants a code-quality or design-review rubric, or says 让代码更简洁 / 工程更规范 / 重构 / 设计模式 / 设计原则 — and you need to pick the right craftsmanship skill. Routes a task or topic to the OWNING skill with clear boundaries so they don't overlap. Distinct from dev-commons (this workspace's stack-specific recipes) and from code-review/simplify (which execute reviews); those run the work, code-craft supplies the canonical craft knowledge."
allowed-tools:
  - Read
  - Grep
metadata:
  tier: default-min
  cost: light
  side_effects: none
  argument-hint: "[a task, topic, smell, principle, or pattern — or a skill name]"
---

# code-craft — the software-craftsmanship router

Seven classics, each its own skill. This router declares **who owns what** and routes you to the right one. Load the owning skill; don't re-derive its content here.

## Route by intent

| You want to… | Go to |
|---|---|
| Name things / shape functions / comments / formatting / error handling / clean tests / a review-heuristics checklist | **clean-code** |
| Improve existing code safely — name a smell → apply a refactoring with mechanics | **refactoring** |
| Decide an OO design or diagnose rot — SOLID, design smells, package & dependency metrics | **solid-principles** |
| Pick or recall one of the 23 GoF patterns; disambiguate look-alikes | **design-patterns** |
| Construction breadth + checklists — defensive programming, variables/data, control flow, code tuning, integration, layout | **code-complete** |
| Cross-cutting pragmatic philosophy — DRY, orthogonality, tracer bullets, DBC, the 70 Tips | **pragmatic-programmer** |
| A fast maxim, or many short expert opinions across all topics | **97-things** |

## Ownership boundaries (so the skills don't overlap)

- **clean-code** (R. Martin) — code-level **standards**: what good names/functions/comments/formatting/tests look like; the Ch17 smells-&-heuristics review catalog. → Principle behind a rule → solid-principles; the step-by-step fix → refactoring.
- **refactoring** (Fowler) — owns the **smell → named-refactoring → mechanics** catalog ("how to change existing code"). → Design-scale smells/principles → solid-principles; review heuristics → clean-code; patterns as targets → design-patterns.
- **solid-principles** (Martin, PPP) — owns **SOLID + the 7 design smells + package/component principles** (REP/CCP/CRP, ADP/SDP/SAP, I/A/D metrics, Main Sequence). → The pattern *catalog* it references → design-patterns.
- **design-patterns** (GoF) — owns the **23 patterns** (intent/participants/consequences/disambiguation). → The why/when at principle level → solid-principles.
- **code-complete** (McConnell) — owns construction **breadth + checklists/thresholds** (params ≤7, nesting ≤3–4, name length, etc.). Touches every topic shallowly; for depth on one topic prefer the specialist sibling.
- **pragmatic-programmer** (Hunt & Thomas) — owns the **attitude/philosophy & cross-cutting craft** (DRY, orthogonality, reversibility, tracer bullets, DBC, knowledge portfolio, 70 Tips). → Concrete code standards → clean-code; mechanics → refactoring.
- **97-things** (Henney, ed.) — a **fast aphorism index** across all of the above; for depth on any maxim, jump to the relevant sibling.

## Overlap resolution (when two skills touch the same idea)

- **SRP / OCP / DIP** — deep home is **solid-principles**; clean-code (Ch10) has the code-level version. Prefer solid-principles for the principle itself.
- **Code smells** — three complementary catalogs by altitude: **refactoring** Ch3 (code-level → fixes), **solid-principles** Ch7 (design-rot), **clean-code** Ch17 (review heuristics).
- **Refactoring** — the catalog/mechanics live in **refactoring**; clean-code, code-complete, solid-principles, pragmatic-programmer all just reference it.
- **DRY** — named home is **pragmatic-programmer**; echoed in clean-code (Ch3) and 97-things.
- **Law of Demeter / testing / naming** — appear in several; each book's take is kept faithfully. Use this router to choose the altitude you want.

## Relationship to your other skills (NOT part of this family)

- **dev-commons** — your **stack-specific** recipes (Flask / Electron / Next.js / Python / Windows + the 15 code-conventions). That answers "how to build a route in *this* project"; code-craft is the language-agnostic craft layer above it. Do not duplicate dev-commons' convention tables here.
- **code-review / simplify / review / debug-backend** — **action** skills that execute a review or change. They are the verbs; the code-craft family supplies the criteria (load a craft skill to ground a review in named principles).
- **book-to-skill** — the converter these 7 were built with; use it to add or refresh a book.

## How to use
- Give me a **task/topic/smell/principle/pattern** → I name the owning skill and load it.
- Give me a **skill name** → I hand off directly.
- Doing a **review**? Pull the rubric from **clean-code** + **solid-principles** (+ **refactoring** for existing code), then run **code-review**/**simplify** to apply it.
