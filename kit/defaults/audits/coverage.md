## Concern: coverage and the tests themselves
- Saturation (Martin, 6 Nov 2026): every expression covered by a test that fails when it
  changes. Read `.metrics/mutate/` and the last gate summary: which files were never mutated,
  which survivors or uncovered sites are old debt, which modules have no tests at all.
- Tests that prove nothing: they pass if the function returns a constant; they assert import
  order, list membership of an implementation detail, or that a removed feature is absent;
  they mock the thing under test.
- Behaviour the customer cares about without an acceptance test or a written manual check.
- Excludes in `.ub/config`, `GATE_SKIP` in CI, skipped or disabled tests, and why.
