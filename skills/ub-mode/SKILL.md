---
name: ub-mode
description: >
  Robert C. Martin's reduced principles (ub-mode, Oct 2026) with the ub-kit gate. Every change
  follows First Make it Work, then Make it Right, then Follow Practice, and ends with a green
  `just gate` and an answered `just review`. Use for every task in this repository, when the
  user runs /ub-mode, or asks for the reduced principles.
---
# ub-mode

Source: Robert C. Martin, `ub-mode` (github.com/unclebob/ub-mode, Oct 2026), with the ub-kit
gate (`.ub/`). The project's own rules and architecture (`AGENTS.md`, `CLAUDE.md`, ADRs,
architecture docs) come first: this skill is how you work, they say what the project is. When
the two disagree, ask the owner. The block managed by ub-kit in AGENTS.md / CLAUDE.md names
the gate's mode and the exact commands (`just gate`, or `just ub gate` when the project's
justfile already had those names).

Every time you are asked to make a change follow:
* First Make it Work.
* Then Make it Right.
* Follow Practice.

The task is done when `just gate` is green, every finding of `just review` is answered, and the
owner has tried the behaviour by hand.

# First Make it Work

## Read before you write
* Restate the task as the behaviour a user will see and how the owner will check it.
* An ambiguous requirement is not yours to settle: ask. Do not guess.

## Laziness Protocol
* One decision lives in one place.
* Ship the smallest edit that solves the problem.

## Foundational Thinking
* Get the data shape right before you write the logic.
* Do first whatever helps every later phase.
* If a concurrent writer would matter, do not share state.

## TDD
* Write the failing test before you change the code.
* See it fail for the reason you expect.
* Make the smallest change that makes it pass.
* If an honest test is impractical, do not write a bad one — say so in the log.
* The proof is the gate, not the ritual: mutation and CRAP judge the tests you leave behind
  (Martin, 27 Oct 2026).

## Redesign From First Principles
* Do not bolt a new requirement onto the old design.
* Ask what you would have built if it had been there from the start, think that through, and
  deliver it in pieces.

## Attack the Premise
* When two fixes that share one premise fail the same gate, write that premise in one sentence
  and count which actors hold the imbalance.
* Remove the assignment.
* Do not start another fix until you have done that.

## Subtract Before You Add
* Take complexity out before you add anything.

## Outcome-Oriented Execution
* Aim at the end state you can check (`just gate` green).
* A break in the middle is allowed when you planned it and can undo it.

## Build the Lever
* If the work is not obvious at a glance, build the tool that does it.
* Do one unit by hand, then make the tool match that unit.

## Architecture
### Model the Domain
* Put the domain in a structure that makes the illegal states impossible.
* Keep the domain's terms in the project's glossary, if it keeps one.
* If the code is already clear and local, leave it.

### Boundary Discipline
* Check the data where it enters (HTTP, CLI, queue, file, env).
* Inside, trust it.
* Keep the business logic in pure functions, away from IO and frameworks.
* Dependencies point inward only. The project's boundary check (in verify) and the diagram's
  `:levels` (`.ub/uml/policy.edn`) enforce it; changing either is the owner's decision.

### Type System Discipline
* Make the illegal value impossible to write.
* Parse outside data once, where it comes in.
* Do not silence the compiler, the type checker or the linter without a written reason.

### Make Operations Idempotent
* Running it twice, or running it after a crash halfway through, ends in the same state.

### Separate Before Serializing Shared State
* If they do not need the same mutable thing, give each its own.
* If they do, allow one writer, and enforce that in the structure.

# Then Make it Right

## Fix Root Causes
* Reproduce it (a failing test).
* Fix the cause.
* A guard that only hides the crash is not a fix.

## Sequence work into verifiable units
* Finish one small unit and check it with `just gate`.
* Then start the next.

## Test Behavior, Not Implementation
* The test calls the code the way its user does and checks the result that user would see.
* If the test would still pass when every function returned nothing, throw it out.
* Never weaken or delete a test to make it pass. The gate reruns every mutant when tests change
  and is red when one the tests used to kill survives.

## Crapper
* `just gate` runs crapper on the changed files.
* Reduce each function under CRAP 10 by splitting it, by testing it, or both.
* Consider whether case statements are worth reducing.

## Dryer
* `just gate` runs dryer (threshold 0.8).
* Eliminate duplication that touches the code you changed.

## Mutator
* `just gate` runs mutator on the changed files, and on the code whose tests you changed.
* Cover the uncovered.
* Kill the survivors.
* Delete dead code.
* An equivalent mutant: explain it in the log; the reviewer judges it.

## Old debt (ratchet mode)
* In ratchet mode only new debt is red. `DEBT:` lines in `.ub/out/gate/summary.txt` are old
  debt in the code you touched.
* Leave it lower than you found it when that is cheap and safe; never higher. Say in the log
  what you lowered and what you left.
* The baseline (`.ub/baseline/`) changes only with the owner.

## Refactoring
* Pin what the code does.
* Change the structure.
* Prove the behavior did not change.

## Look above the code
* When the structure changed, `just gate` checks the Dependency Rule on the diagram
  (`just uml` to see it); say in the log which modules and dependencies appeared or moved.

## Review by another model
* Run `just review` (Grok, else Codex, reads the diff; read-only).
* Exit 2 means no other model answered: the task is not reviewed — say so, do not merge.
* Answer every finding: fix it, or write why it is wrong. After two rounds of disagreement, ask
  the owner.

# Practice

## Keep a Log
* Keep a log of every action you take and the reason you took it in `docs/log/<task>.md`.
* Report that log upon completion, with the `just gate` summary and the `just review` verdict.

## Audit the Run
* Before you report, audit your own run: what the task asked for that is not done, what you
  skipped or stubbed, which tests are missing, which `GATE_SKIP` you used and why.
* Put it at the top of the report under «Не зроблено». An empty list must be earned.

## Read the Critical Code
* Money, security (sessions, passwords, permissions) and anything lives depend on are not
  accepted on metrics alone.
* Name the changed critical functions in the report, so the reviewer and the owner read them
  line by line.

## Never Game the Gate
* `.ub/`, `.metrics/`, the skills and the boundary rules are not yours to edit to get past a
  red gate; editing them asks the owner, and the reviewer looks for it.
* A `GATE_SKIP` needs a reason in the log.

## Guard the Context Window
* Keep the main thread small.
* Send the bulk elsewhere (subagents, `.ub/out/gate/*.log`), and keep the summary.

## Worktree Cleanup
* Find what is safe to remove, confirm nothing still in use needs it, then reclaim the disk.
* Uncommitted work waits for a decision.

## Commit and Push
* Commit often, in small ordered commits, with the `.metrics/mutate/` snapshots the gate wrote.
* Each commit says why, what changed, and how you proved it.
* Push to the main line at the end, when the owner agrees.
