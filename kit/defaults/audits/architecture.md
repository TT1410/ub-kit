## Concern: architecture
- The layers and modules the project's docs (AGENTS.md, ADRs, architecture docs) and
  `.ub/uml/policy.edn` describe: does the code follow them? Which dependency points the wrong
  way, which module knows another's internals?
- Is the Dependency Rule checked by a tool in verify (import-linter, depguard, an architecture
  test, dependency-cruiser), or only described?
- Business rules away from frameworks, IO and the database; IO behind interfaces the inner
  layers own.
- Module sizes and fan-in/fan-out that make a change ripple; duplicated concepts under
  different names; a god module.
- What would break first if a second UI, a second database or a second deployment came.
