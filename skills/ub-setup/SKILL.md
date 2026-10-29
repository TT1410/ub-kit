---
name: ub-setup
description: >
  Finish setting up ub-kit (.ub/) in this repository with the owner: the stack of a new project,
  the verify command, module boundaries, the diagram's layers, the ratchet baseline, the
  reviewer — until `just ub-doctor` is clean and `just gate` runs end to end. Use once after
  install.sh, when the user runs /ub-setup, or when ub-doctor reports problems.
---
# ub-setup

The installer copied the kit and guessed what it could; everything it could not know is marked
`TODO(ub-setup)` in `.ub/config` and `.ub/uml/policy.edn`. Your job is to settle those with the
owner, not to guess them. Work on a branch (`ub-setup`), commit in small steps, do not push.

Edits under `.ub/`, `.claude/skills/` and `.metrics/` ask the owner by design — say what you are
changing and why before each one.

## 0. Look first
* Run `just ub-doctor` (or `python3 .ub/ub doctor`) and read `.ub/config`.
* Read the README, the build files, the CI config and the test layout, so your proposals fit
  the project as it is.
* Tell the owner in a few lines what you found and what is left, then go through the steps
  below; skip a step that is already done.

## 1. A new project: the stack first (no language in `.ub/config`)
* Ask the owner for the language, the kind of application, the framework if any, and the layers
  they want (for example domain / application / adapters, or modules by feature). Do not assume
  Python, a layering or a framework.
* Build the smallest skeleton that matches the answer: the build file, one source file in the
  innermost layer with one real function, its test next to the project's test convention, the
  boundary check (step 3). Nothing speculative.
* Add the language section to `.ub/config` (`root`, `src`) and switch the mode to `strict`.
* Python: keep the project importable from `src/` by the tests (pytest `pythonpath`) and do not
  install it into `.venv` (uv: `[tool.uv] package = false`); an editable install makes every
  mutant survive. Add `pytest` and `coverage` to the dev dependencies.
* TypeScript: vitest with `@vitest/coverage-v8`; other runners are not supported by the gate.

## 2. verify
* `[ub] verify` is the check every change passes: lint, types, module boundaries, tests — with
  the project's own commands, from the repo root. Prefer an existing `just verify`, `make check`
  or package script; otherwise write a `verify` recipe in the justfile and point verify at it.
* Run it. It must pass on the main branch before the gate means anything; if it does not, tell
  the owner and stop here.

## 3. Module boundaries
* If the project already checks them (import-linter, depguard, an architecture test,
  eslint-plugin-boundaries, dependency-cruiser), make sure verify runs it.
* If not, propose one for the language and ask before adding a dependency:
  Python — import-linter `layers` contract; Go — depguard rules in golangci-lint plus a small
  test over `go list -deps`; TypeScript — dependency-cruiser or eslint-plugin-boundaries.
* Write the layers the owner named, not a textbook set.

## 4. Language details
* Python: `just ub-doctor` must show no editable install. If `crapper` cannot find pytest or
  coverage, add them, or set `[python] test` / `coverage`.
* Go: if a package's code is tested from elsewhere (a module tested as a whole), set
  `[go] tree` to a regex whose group 1 is that directory. If tests need a database or other
  service, set `[go] setup` to the command that starts it.
* TypeScript: paste `.ub/snippets/vitest-mutator-overlay.ts.txt` into the vitest config and add
  `plugins: [mutatorOverlay(here)]`; without it every mutant survives. Specs live beside the
  module (`name.spec.ts`, `name.test.ts`, or `__tests__/`).
* Generated code: if it has no "Code generated … do not edit" header, add its paths to
  `[ub] exclude` (a regex).

## 5. The diagram (`.ub/uml/policy.edn`)
* Set `:levels` to the owner's layers, inner first, and fix `:src` / `:prefix` if the TODO
  says so. Run `just uml ir`; the summary line counts violating edges. Needs Java 21 and the
  Clojure CLI; without them the gate skips this stage and says so — tell the owner.
* Existing violations are architecture debt: list them for the owner; do not hide them with
  `:omit`.

## 6. Ratchet mode (an existing project)
* Run `just ub-baseline`. It scores every function and counts duplicate groups; show the owner
  `.ub/baseline/summary.txt`. The owner decides whether to commit it as the starting line.
* Mutation needs no baseline: in ratchet mode the gate mutates only the changed lines.

## 7. Prove it runs
* On a scratch branch, make a tiny real change with its test and run `just gate`. It must run
  every stage to a verdict; a red verdict on real problems is fine, a crash or a skipped stage
  is not. Throw the scratch branch away.
* Run `just review` once. If it exits 2, tell the owner which reviewer needs a login or credits
  (`grok`, `codex login`); the order is `[ub] reviewers`.

## 8. Record it
* If the project keeps ADRs, write one: one disciplined agent per task (ub-mode), the gate and
  its thresholds, the mode and why, the reviewer, what the owner still checks by hand.
* Commit on the branch: `.ub/`, `.claude/`, the justfile, `.gitignore`, `AGENTS.md`/`CLAUDE.md`,
  the boundary config, the baseline if approved. Report what is done, and under «Не зроблено»
  what is not (for example: no Java, so no structure stage; reviewer without credits).
