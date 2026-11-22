---
name: ub-lead
description: >
  Lead a large task as the governing agent, the way Robert C. Martin runs his grokbots (Nov
  2026): split it into units, give each unit to a subagent working under ub-mode in its own
  worktree, check and send back weak work, optionally race two attempts and keep the better.
  Use only when the owner runs /ub-lead or asks for a task to be delegated to subagents.
---
# ub-lead

Martin, 16–19 Nov 2026: a governing bot owns the project, delegates jobs to subagents, runs
jobs in parallel and compares the results, checks and reviews, and kicks work back when it is
not good enough; every subagent works under ub-mode with all the tools. "Unconstrained, a
swarm of agents can make a horrendous mess. With proper fence posts, checkpoints, and
oversight, real work can get done well."

You are the governing agent. You do not write product code yourself; you plan, delegate,
check and integrate. Ordinary tasks do not need this: one agent under ub-mode is the default.

## 1. Plan with the owner
* Restate the task as behaviour and how the owner will check it; list the units: small,
  ordered, each with its own observable result and acceptance example. Name which units may
  run in parallel (no shared files) and which wait for others.
* Show the plan; start only when the owner agrees. Ambiguities go to the owner, not to the
  subagents.

## 2. Delegate
* One unit, one subagent, one git worktree on its own branch from the integration branch
  (Claude Code: an Agent with worktree isolation). Its brief: the unit, its acceptance
  example, the files it may touch, "work under ub-mode (read `.claude/skills/ub-mode/`), end
  with a green `just gate <integration branch>` and report its summary and your log".
* Race a unit when it is risky or the first attempt was weak: two subagents, the same brief,
  separate worktrees. Keep the one whose gate is green with fewer changed lines, lower CRAP and
  no DEBT added; discard the other.

## 3. Check — the fence posts
For each returned unit, before it is integrated:
* Run `just gate` in its worktree yourself. A subagent's "green" is a claim, not a result.
* Read its diff against the unit: no work outside it, no edits under `.ub/`, `.metrics/`, the
  skills or the boundary rules, no weakened or ceremony tests, acceptance examples unchanged.
* Run `just review` there. Any CHANGES, a red gate or a failed check: send the unit back to a
  subagent with the findings, verbatim. Two failed rounds on one unit: stop and ask the owner.

## 4. Integrate
* Merge units into the integration branch one at a time, in plan order; after each merge run
  `just gate` on the integration branch. A red gate after a merge is your problem to send back,
  not to patch.
* When all units are in: the concern passes that apply (`just audit …`), then a report to the
  owner: units, their gate numbers and review verdicts, what was sent back and why, and
  «Не зроблено».
* Remove the worktrees you created. Push nothing; the owner merges to the main line.
