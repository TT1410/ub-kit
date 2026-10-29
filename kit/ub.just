# ub-kit: one disciplined agent per task, checked by Robert C. Martin's tools.
# Imported by the project's justfile; settings in .ub/config, logs in .ub/out.

# The task's gate for what changed since base (default: merge-base with the main branch): verify, CRAP, DRY, mutation, Dependency Rule; GATE_SKIP=verify,crap,dry,mutation,structure skips stages
gate base="":
    python3 "{{source_directory()}}/ub" gate {{quote(base)}}

# Another model reviews the task's diff, read-only (grok, then codex); exit 2 = nobody answered, the task is not reviewed
review base="" card="":
    python3 "{{source_directory()}}/ub" review {{quote(base)}} {{quote(card)}}

# uml-viewer: modules, dependencies, Dependency Rule violations, CRAP and mutation colours; action: open, install, metrics, ir
uml action="open":
    python3 "{{source_directory()}}/ub" uml {{action}}

# Ratchet mode: record today's CRAP debt, so only new debt is red (with the owner)
ub-baseline:
    python3 "{{source_directory()}}/ub" baseline

# Check the tools and the configuration
ub-doctor:
    python3 "{{source_directory()}}/ub" doctor

# Martin's crapper, mutator and dryer at their pinned commits (shared cache)
ub-tools:
    python3 "{{source_directory()}}/ub" tools install
