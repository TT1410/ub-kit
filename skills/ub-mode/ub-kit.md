# ub-mode in this repository (ub-kit)

`SKILL.md` is Martin's text. This page says how it runs here; where the two seem to differ,
this page is about tools, his text about the work. The project's own rules and architecture
(`AGENTS.md`, `CLAUDE.md`, ADRs, architecture docs) come first; when they disagree with
ub-mode, ask the owner. The block ub-kit manages in AGENTS.md / CLAUDE.md names the commands
(`.ub/ub gate`; in a project that imports `.ub/ub.just`, `just gate` or `just ub gate` is the same).

## Done means
* `.ub/ub gate` is green: verify, the acceptance tests if `[ub] acceptance` is set, crapper,
  dryer and mutator on what changed since the merge-base, the Dependency Rule on the diagram.
  That is "Use the crapper / dryer / mutator tool". Logs: `.ub/out/gate/`.
* Every finding of `.ub/ub review` (another model, read-only) is answered: fixed, or why it is
  wrong. Exit 2 means nobody reviewed it — say so, do not merge. Two rounds of disagreement:
  ask the owner.
* The owner has tried the behaviour. The log is `docs/log/<task>.md` (or where the project's
  rules keep logs) and the report starts
  with «Не зроблено»: what is not done, skipped or stubbed, which `GATE_SKIP` and why. An empty
  list must be earned.

## Tests
* Saturation, not ceremony (Martin, 6 Nov 2026): every expression covered by a test that fails
  when it changes. No tests of import order, of private details, or that a removed feature is
  absent. Never weaken or delete a test to pass: changed tests make the gate rerun every
  mutant, and a mutant they used to kill that now survives is red.
* A bug gets a test that fails because of it, then the fix. When the owner reports a symptom,
  answer questions about it first: what the code does there, which test covers it.
* Agreed acceptance examples are the owner's: never change one to make it pass — ask.
* An equivalent mutant: explain it in the log; the reviewer judges it.

## Old debt (ratchet mode)
* Only new debt is red. `DEBT:` lines in the gate summary are old debt you touched: leave it
  lower than you found it when that is cheap and safe, never higher, and say which in the log.

## Concern passes
* Before a release, or when the owner asks: `.ub/ub audit architecture | coverage | concurrency
  | security | api`, and answer each finding with a test or a check. For a race: random delays
  at the critical points, then `.ub/ub soak 50` (the suite fifty times).

## Never game the gate
* `.ub/`, `.metrics/`, the skills, the boundary rules and the baseline are the owner's: editing
  them asks, and the reviewer looks for it. Money, security and anything lives depend on are
  not accepted on metrics alone — name those functions in the report for line-by-line reading.

## Commits
* Martin's format: `Why:` the problem; `What:` the change; `Proof:` the tests that failed first
  and pass now, and the gate's numbers — highest CRAP on the changed code, dryer's candidates,
  mutator's killed/survived on the changed lines. Commit the `.metrics/mutate/` snapshots.
  Push only on the owner's word.
