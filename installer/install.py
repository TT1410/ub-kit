#!/usr/bin/env python3
"""Install ub-kit into a repository, new or existing, or upgrade it there.

  install.sh [REPO] [--langs python,go,typescript] [--mode strict|ratchet] [--main BRANCH]
             [--ci] [--upgrade] [--dry-run]

REPO defaults to the current directory; a missing directory becomes a new git repository.
Languages, their roots, the main branch, the verify command and the mode are detected; what
cannot be detected is marked TODO(ub-setup) in .ub/config for the ub-setup skill.
--upgrade rewrites only the kit's own files (.ub/ub, ub.just, snippets, skills, managed blocks)
and keeps .ub/config, .ub/review.md, .ub/uml/policy.edn and .ub/baseline/.
"""
from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
VERSION = (KIT / "VERSION").read_text().strip()
KIT_FILES = ["ub", "ub.just", "snippets/vitest-mutator-overlay.ts.txt"]
SKILLS = ["ub-mode", "ub-setup"]
SKIP_DIRS = {"node_modules", "vendor", "dist", "build", "target", "venv", "testdata", "e2e"}
EXT = {"python": (".py",), "go": (".go",), "typescript": (".ts", ".tsx")}
TEST_RE = re.compile(r"(^|/)(tests?|__tests__|testdata)/|(^|/)test_[^/]*\.py$|_test\.(py|go)$|\.(test|spec)\.tsx?$|\.d\.ts$")
OUR_RECIPES = {"gate", "review", "uml", "ub-baseline", "ub-doctor", "ub-tools"}
BEGIN, END = "<!-- ub-kit:start", "<!-- ub-kit:end -->"


def norm(path: str) -> str:
    path = (path or "").strip().strip("/")
    while path.startswith("./"):
        path = path[2:]
    return "" if path in (".", "") else path


def sh(args, cwd, check=False) -> str:
    r = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"install: {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip() if r.returncode == 0 else ""


class Plan:
    """Every write goes through here, so --dry-run shows the same list without writing."""

    def __init__(self, repo: Path, dry: bool):
        self.repo, self.dry, self.done = repo, dry, []

    def write(self, path: str, text: str, why: str) -> None:
        target = self.repo / path
        if target.exists() and target.read_text(encoding="utf-8", errors="ignore") == text:
            return
        self.done.append(f"{path} — {why}")
        if not self.dry:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            if path in (".ub/ub",):
                target.chmod(0o755)

    def once(self, path: str, text: str, why: str) -> None:
        if not (self.repo / path).exists():
            self.write(path, text, why)

    def read(self, path: str) -> str:
        p = self.repo / path
        return p.read_text(encoding="utf-8", errors="ignore") if p.exists() else ""


# ---------------------------------------------------------------- detection


def walk_dirs(repo: Path, depth: int = 2):
    for dirpath, dirnames, filenames in os.walk(repo):
        d = Path(dirpath)
        level = len(d.relative_to(repo).parts)
        dirnames[:] = sorted(n for n in dirnames if n not in SKIP_DIRS and not n.startswith(".")) if level < depth else []
        yield d, set(filenames)


def relpath(repo: Path, d: Path) -> str:
    r = str(d.relative_to(repo))
    return "" if r == "." else r


def package_json(d: Path) -> dict:
    try:
        return json.loads((d / "package.json").read_text())
    except (OSError, ValueError):
        return {}


def deps(pkg: dict) -> dict:
    return {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}


def detect(repo: Path, only: list | None) -> dict:
    """language -> {rel, src, notes}; the shallowest root of each language wins."""
    found: dict = {}
    others: dict = {}
    for d, files in walk_dirs(repo):
        rel = relpath(repo, d)
        hits = []
        if files & {"pyproject.toml", "setup.py", "setup.cfg", "requirements.txt"}:
            hits.append("python")
        if "go.mod" in files:
            hits.append("go")
        if "package.json" in files and ({"typescript", "vitest"} & set(deps(package_json(d)))):
            hits.append("typescript")
        for lang in hits:
            if only and lang not in only:
                continue
            if lang not in found:
                found[lang] = {"rel": rel}
            else:
                others.setdefault(lang, []).append(rel or ".")
    for lang, info in found.items():
        root = repo / info["rel"] if info["rel"] else repo
        info["src"] = guess_src(lang, root)
        info["others"] = others.get(lang, [])
    return found


def guess_src(lang: str, root: Path) -> str:
    if lang == "python":
        if (root / "src").is_dir():
            return "src"
        pkgs = [p.name for p in root.iterdir() if p.is_dir() and (p / "__init__.py").exists()
                and not p.name.startswith(("test", "."))]
        return pkgs[0] if len(pkgs) == 1 else ""
    if lang == "go":
        return "internal" if (root / "internal").is_dir() else ""
    return "src" if (root / "src").is_dir() else ""


def main_branch(repo: Path) -> str:
    head = sh(["git", "symbolic-ref", "--short", "-q", "refs/remotes/origin/HEAD"], repo)
    if head:
        return head.split("/", 1)[1]
    for b in ("main", "master"):
        if sh(["git", "rev-parse", "-q", "--verify", f"refs/heads/{b}"], repo):
            return b
    return sh(["git", "branch", "--show-current"], repo) or "main"


def product_files(repo: Path, langs: dict) -> int:
    listed = sh(["git", "ls-files"], repo).splitlines()
    count = 0
    for lang, info in langs.items():
        prefix = f"{info['rel']}/" if info["rel"] else ""
        count += sum(1 for f in listed if f.startswith(prefix) and f.endswith(EXT[lang])
                     and not TEST_RE.search(f) and "node_modules/" not in f and "vendor/" not in f)
    return count


def pm(root: Path) -> tuple:
    """(run a script, run a binary) for this JS project."""
    d = root
    while True:
        if (d / "pnpm-lock.yaml").exists():
            return "pnpm run", "pnpm exec"
        if (d / "yarn.lock").exists():
            return "yarn", "yarn"
        if (d / "bun.lock").exists() or (d / "bun.lockb").exists():
            return "bun run", "bunx"
        if (d / ".git").exists() or d.parent == d:
            return "npm run", "npx --no-install"
        d = d.parent


def guess_verify(repo: Path, langs: dict) -> tuple:
    """(command, sure): the project's own `just verify` when it has one, else a guess per language."""
    jf = justfile(repo)
    if jf and re.search(r"^@?verify\b[^\n:=]*:(?!=)", jf.read_text(errors="ignore"), re.M):
        return "just verify", True
    parts = []
    for lang, info in langs.items():
        root = repo / info["rel"] if info["rel"] else repo
        cd = f"cd {info['rel']} && " if info["rel"] else ""
        if lang == "python":
            py = (root / "pyproject.toml").read_text(errors="ignore") if (root / "pyproject.toml").exists() else ""
            run = "uv run " if (root / "uv.lock").exists() else "poetry run " if (root / "poetry.lock").exists() \
                else ".venv/bin/python -m " if (root / ".venv").exists() else "python3 -m "
            steps = []
            if "[tool.ruff" in py:
                steps.append(f"{run}ruff check .")
            mypy = re.search(r"^\[tool\.mypy\]\s*\n(.*?)(?=^\[|\Z)", py, re.M | re.S)
            if mypy:
                targets = re.search(r"^\s*(files|packages|modules)\s*=", mypy[1], re.M)
                steps.append(f"{run}mypy" + ("" if targets else " ."))
            if "[tool.importlinter" in py:
                steps.append(("PYTHONPATH=src " if info["src"] == "src" else "") + f"{run}lint-imports")
            steps.append(f"{run}pytest -q")
            parts.append(cd + " && ".join(steps))
        elif lang == "go":
            parts.append(f"{cd}go vet ./... && go test ./...")
        elif lang == "typescript":
            script, binary = pm(root)
            scripts = package_json(root).get("scripts", {})
            steps = [f"{script} {s}" for s in ("lint", "typecheck", "type-check") if s in scripts]
            steps.append(f"{binary} vitest run" if "vitest" in deps(package_json(root)) else f"{script} test")
            parts.append(cd + " && ".join(steps))
    if not parts:
        return "", False
    return " && ".join(f"({p})" if p.startswith("cd ") and len(parts) > 1 else p for p in parts), False


def justfile(repo: Path):
    return next((repo / n for n in ("justfile", "Justfile", ".justfile") if (repo / n).exists()), None)


# ---------------------------------------------------------------- rendering


def render_config(main: str, mode: str, verify: str, sure: bool, langs: dict) -> str:
    todo_verify = "" if sure else (
        "# TODO(ub-setup): a guess — make it lint, types, module boundaries and the tests.\n")
    out = f"""# ub-kit settings. Edits ask the owner (.claude/settings.json). One line per value;
# a `;` or `#` after a space starts a comment, so join commands with &&.

[ub]
# The branch tasks start from; the gate judges what changed since the merge-base with it.
main = {main}
# strict:  everything in a changed file must be clean (new projects).
# ratchet: only new debt is red — mutants and duplicates on the changed lines, functions at
#          CRAP >= crap_max that are not in .ub/baseline/crap.tsv or got worse; old debt in
#          touched files is listed as DEBT (existing projects; run `just ub-baseline` once).
mode = {mode}
# The check every change passes, from the repo root: lint, types, module boundaries, tests.
{todo_verify}verify = {verify}
crap_max = 10
dry_threshold = 0.8
# Regex of repo paths the gate does not judge (generated code without a "do not edit" header).
exclude =
# auto: check the Dependency Rule on the uml-viewer diagram when .ub/uml/policy.edn exists; off.
structure = auto
# mutator's workers per file.
workers = 4
# Review by another model, in order; when one fails the next answers. grok, codex, claude
# (claude only when the author is not Claude).
reviewers = grok codex
review_turns = 30
"""
    for lang, info in langs.items():
        out += f"\n[{lang}]\n# The language root (from the repo root) and its product sources (from the language root).\n"
        if info.get("others"):
            out += f"# TODO(ub-setup): other {lang} roots found: {', '.join(info['others'])} — one root per language.\n"
        out += f"root = {info['rel'] or '.'}\nsrc = {info['src']}\n"
        if lang == "python":
            out += ("; test = uv run pytest -x -q        mutator's test command (default: pytest from .venv)\n"
                    "; coverage =                        crapper's and mutator's coverage command\n")
        elif lang == "go":
            out += ("; tree = ^(internal/modules/[^/]+)/   group 1: the directory whose tests judge a file\n"
                    ";                                     (default: the file's own package)\n"
                    "; test =                            mutator's test command (default: go test of that package)\n")
        out += "; setup =                             run before the gate judges this language (a test database, …)\n"
    if not langs:
        out += ("\n# No language yet. The ub-setup skill adds one of these when the stack is chosen:\n"
                "# [python]  root = .  src = src\n# [go]  root = .  src = internal\n# [typescript]  root = .  src = src\n")
    return out


def render_policy(repo: Path, langs: dict) -> str:
    lang = next(iter(langs), None)
    if lang is None:
        return ""
    info = langs[lang]
    root = repo / info["rel"] if info["rel"] else repo
    src = "/".join(p for p in (info["rel"], info["src"]) if p) or "."
    prefix, todo = "", ""
    if lang == "python":
        base = root / info["src"] if info["src"] else root
        pkgs = sorted(p.name for p in base.iterdir() if p.is_dir() and (p / "__init__.py").exists()) if base.is_dir() else []
        if info["src"] == "src" and len(pkgs) == 1:
            src, prefix = f"{src}/{pkgs[0]}", pkgs[0]
        else:
            prefix = info["src"] or ""
            todo = "TODO(ub-setup): check :src and :prefix (the package root)"
    elif lang == "go":
        m = re.search(r"^module\s+(\S+)", (root / "go.mod").read_text(), re.M)
        module = m[1] if m else ""
        prefix = ".".join(p for p in (module.replace("/", "."), info["src"].replace("/", ".")) if p)
    else:
        prefix = re.sub(r"^@[^/]+/", "", package_json(root).get("name", "")) or root.name
        todo = "TODO(ub-setup): check :prefix — run `just uml ir` and look at the ids"
    return f""";; uml-viewer policy (ub-kit). `just uml` regenerates .ub/uml/project.edn from it and opens the
;; viewer; the gate's structure stage counts the edges marked :violating. Edits ask the owner.
;; :levels — the Dependency Rule by the first segment after :prefix, inner (higher-level) first;
;; an edge from an inner segment to an outer one is a violation.
;; TODO(ub-setup): set :levels to the project's layers, e.g. [[domain] [application] [adapters]].
{(';; ' + todo) if todo else ''}
{{:title "{repo.name}"
 :src "{src}"
 :prefix "{prefix}"
 :lang :{lang}
 :out ".ub/uml/project.edn"
 :hierarchical true
 :foreign []}}
"""


def render_block(mode: str, main: str, j: str) -> str:
    modes = {
        "strict": "everything in a changed file must be clean.",
        "ratchet": "only new debt is red; `DEBT:` lines in the summary are old debt you touched — leave it lower than you found it, never higher.",
    }
    return f"""{BEGIN} — managed by ub-kit (install.sh --upgrade rewrites it); keep your own rules outside -->
## How tasks are worked here

One task, one agent, the `ub-mode` skill (`.claude/skills/ub-mode/SKILL.md` — agents without
skills: read it before the first change). A task is done when:
- `{j}gate` is green: verify, CRAP < 10, no duplication (dryer 0.8), no surviving or uncovered
  mutants, the Dependency Rule — for what changed since the merge-base with `{main}`.
  Mode {mode}: {modes[mode]}
- every finding of `{j}review` (another model, read-only) is answered; exit 2 means nobody
  reviewed it — say so, do not merge;
- the owner has tried the behaviour, and `docs/log/<task>.md` starts with «Не зроблено».

`.ub/`, `.metrics/` and the skills are guarded: never edit them to get past the gate; ask.
Ask when a requirement is ambiguous. Commit in small steps; push only on the owner's word.
{END}
"""


def with_block(text: str, block: str) -> str:
    if BEGIN in text and END in text:
        start, end = text.index(BEGIN), text.index(END) + len(END)
        return text[:start] + block.rstrip("\n") + text[end:]
    return (text.rstrip("\n") + "\n\n" if text.strip() else "") + block


def render_ci(repo: Path, main: str, langs: dict) -> str:
    steps = ["      - uses: actions/checkout@v4\n        with:\n          fetch-depth: 0",
             "      - uses: actions/setup-python@v5\n        with:\n          python-version: \"3.12\"",
             "      - uses: extractions/setup-just@v3"]
    for lang, info in langs.items():
        root = repo / info["rel"] if info["rel"] else repo
        wd = f"\n        working-directory: {info['rel']}" if info["rel"] else ""
        if lang == "python":
            if (root / "uv.lock").exists():
                steps += ["      - uses: astral-sh/setup-uv@v6", f"      - run: uv sync{wd}"]
            else:
                steps.append(f"      - run: python -m venv .venv && .venv/bin/pip install -e '.[dev]' pytest coverage{wd}"
                             "\n        # TODO: the project's own install; never editable if mutation matters")
        elif lang == "go":
            steps.append(f"      - uses: actions/setup-go@v5\n        with:\n          go-version-file: {(info['rel'] + '/') if info['rel'] else ''}go.mod")
        elif lang == "typescript":
            script, _ = pm(root)
            if script.startswith("pnpm"):
                steps.append("      - uses: pnpm/action-setup@v4")
            steps.append("      - uses: actions/setup-node@v4\n        with:\n          node-version: 22")
            install = {"pnpm run": "pnpm install --frozen-lockfile", "yarn": "yarn install --frozen-lockfile",
                       "bun run": "bun install"}.get(script, "npm ci")
            steps.append(f"      - run: {install}{wd}")
    steps.append(f"""      - name: gate against the merge-base with {main}
        run: |
          git fetch -q origin {main}
          base=$(git merge-base HEAD origin/{main})
          if [ "$base" = "$(git rev-parse HEAD)" ]; then base=$(git rev-parse HEAD~1); fi
          GATE_SKIP=structure python3 .ub/ub gate "$base\"""")
    steps.append("      - if: always()\n        uses: actions/upload-artifact@v4\n        with:\n          name: ub-gate\n          path: .ub/out/gate/")
    return (f"# ub-kit: the gate on every pull request and push to {main} — the constraint holds even when\n"
            "# an agent forgets to run it. Review by another model and uml-viewer stay local.\n"
            f"name: ub-gate\non:\n  pull_request:\n  push:\n    branches: [{main}]\n\njobs:\n  gate:\n"
            "    runs-on: ubuntu-latest\n    steps:\n" + "\n".join(steps) + "\n")


# ---------------------------------------------------------------- wiring


def ask_rules(langs: dict, ci: bool) -> list:
    paths = ["/.ub/**", "/.claude/skills/ub-mode/**", "/.claude/skills/ub-setup/**", "/.metrics/**"]
    paths += [f"/{info['rel']}/.metrics/**" for info in langs.values() if info["rel"]]
    if ci:
        paths.append("/.github/workflows/**")
    return [f"{tool}({p})" for p in dict.fromkeys(paths) for tool in ("Edit", "Write")]


def merged_settings(text: str, rules: list) -> str:
    try:
        data = json.loads(text) if text.strip() else {}
    except ValueError:
        sys.exit("install: .claude/settings.json is not valid JSON; fix it and run again")
    ask = data.setdefault("permissions", {}).setdefault("ask", [])
    ask += [r for r in rules if r not in ask]
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def wire_justfile(plan: Plan, verify: str) -> str:
    """Import the kit's recipes; returns how to call them ('just ' or 'just ub ')."""
    jf = justfile(plan.repo)
    if jf is None:
        if plan.dry:
            return "just "
        sys.exit("install: no justfile to wire (it is written with the config)")
    text = plan.read(jf.name) if not plan.dry else jf.read_text(errors="ignore")
    if ".ub/ub.just" in text:
        return "just ub " if re.search(r"^mod\s+ub\b", text, re.M) else "just "
    names = set(re.findall(r"^@?([A-Za-z_][\w-]*)\b[^\n:=]*:(?!=)", text, re.M))
    names |= set(re.findall(r"^alias\s+([\w-]+)", text, re.M))
    clash = sorted(names & OUR_RECIPES)
    if clash:
        plan.write(jf.name, text.rstrip("\n") + f"\n\n# ub-kit (its recipes clash with {', '.join(clash)}: just ub gate, …)\nmod ub '.ub/ub.just'\n",
                   f"`mod ub`: the project already has {', '.join(clash)}")
        return "just ub "
    plan.write(jf.name, text.rstrip("\n") + "\n\n# ub-kit: gate, review, uml, ub-baseline, ub-doctor, ub-tools\nimport '.ub/ub.just'\n",
               "import the kit's recipes")
    return "just "


def wire_gitignore(plan: Plan, langs: dict) -> None:
    text = plan.read(".gitignore")
    if "# ub-kit" in text:
        return
    lines = ["# ub-kit: logs, the generated diagram, tool scratch. .metrics/mutate/ is committed:",
             "# it is mutator's memory of killed mutants, so the next run is differential.",
             "/.ub/out/", "/.ub/uml/project.edn", "/.ub/uml/.metrics/", ".metrics/crap.edn", ".metrics/dry.edn",
             "target/mutation-workers/", "target/mutator-backup/", "target/coverage/"]
    lines += [f"/{info['rel']}/coverage/" if info["rel"] else "/coverage/" for lang, info in langs.items() if lang == "typescript"]
    plan.write(".gitignore", (text.rstrip("\n") + "\n\n" if text.strip() else "") + "\n".join(lines) + "\n", "ignore the kit's scratch")


def wire_agents(plan: Plan, block: str) -> None:
    claude, agents = plan.read("CLAUDE.md"), plan.read("AGENTS.md")
    if not claude and not agents:
        plan.write("AGENTS.md", "# Rules for agents\n\nKeep this file short; the gate holds the rules.\n\n" + block, "rules for every agent")
        plan.write("CLAUDE.md", "@AGENTS.md\n", "Claude Code reads AGENTS.md")
        return
    # CLAUDE.md that imports AGENTS.md gets the block through it, not twice.
    if agents or "@AGENTS.md" in claude:
        plan.write("AGENTS.md", with_block(agents or "# Rules for agents\n", block), "the kit's block")
    if claude and "@AGENTS.md" not in claude:
        plan.write("CLAUDE.md", with_block(claude, block), "the kit's block")


def install(repo: Path, args) -> None:
    if not repo.exists():
        if args.dry_run:
            sys.exit(f"install: {repo} does not exist (it would be created without --dry-run)")
        repo.mkdir(parents=True)
    if not (repo / ".git").exists():
        if args.dry_run:
            print(f"would run git init -b main in {repo}")
        else:
            sh(["git", "init", "-q", "-b", "main"], repo, check=True)
    plan = Plan(repo, args.dry_run)
    existing = configparser.ConfigParser(inline_comment_prefixes=(";", "#"), interpolation=None)
    existing.read(repo / ".ub" / "config")
    upgrade = args.upgrade or existing.has_section("ub")

    if upgrade and existing.has_section("ub"):
        main = existing["ub"].get("main", "main").strip()
        mode = existing["ub"].get("mode", "strict").strip()
        verify = existing["ub"].get("verify", "").strip()
        langs = {name: {"rel": norm(existing[name].get("root", ".")), "src": norm(existing[name].get("src", ""))}
                 for name in EXT if existing.has_section(name)}
        how = "upgrade: .ub/config, review prompt, policy and baseline kept"
    else:
        only = args.langs.split(",") if args.langs else None
        langs = detect(repo, only)
        main = args.main or main_branch(repo)
        files = product_files(repo, langs)
        mode = args.mode or ("ratchet" if files > 15 else "strict")
        verify, sure = guess_verify(repo, langs)
        how = "--mode" if args.mode else f"{files} product files already here"
        if justfile(repo) is None:
            # verify lives in one place: the new justfile's recipe, which .ub/config calls.
            plan.write("justfile", "# Project tasks; `just --list` shows them.\n\nimport '.ub/ub.just'\n\n"
                       + ("" if sure else "# TODO(ub-setup): a guess — make it lint, types, module boundaries and the tests.\n"
                          if verify else "# TODO(ub-setup): no stack yet — its lint, types, module boundaries and tests go here.\n")
                       + "# Lint, types, module boundaries, tests: the check every change passes\nverify:\n    "
                       + (verify or "echo 'no verify yet' && exit 1") + "\n", "tasks: the kit's recipes and verify")
            verify, sure = "just verify", True
        plan.write(".ub/config", render_config(main, mode, verify, sure, langs), "the project's settings")
        if langs:
            plan.once(".ub/uml/policy.edn", render_policy(repo, langs), "uml-viewer policy (levels: TODO)")

    for f in KIT_FILES:
        plan.write(f".ub/{f}", (KIT / "kit" / f).read_text(), "kit")
    plan.write(".ub/VERSION", VERSION + "\n", "kit version")
    plan.once(".ub/review.md", (KIT / "kit" / "defaults" / "review.md").read_text(), "the reviewer's prompt")
    for skill in SKILLS:
        plan.write(f".claude/skills/{skill}/SKILL.md", (KIT / "skills" / skill / "SKILL.md").read_text(), "skill")
    ci = args.ci or (repo / ".github" / "workflows" / "ub-gate.yml").exists()
    plan.write(".claude/settings.json", merged_settings(plan.read(".claude/settings.json"), ask_rules(langs, ci)),
               "ask the owner before edits of the gate, its settings and the skills")
    j = wire_justfile(plan, verify)
    wire_gitignore(plan, langs)
    wire_agents(plan, render_block(mode, main, j))
    if args.ci:
        plan.write(".github/workflows/ub-gate.yml", render_ci(repo, main, langs), "the gate in CI")

    print(f"ub-kit {VERSION} → {repo}{' (dry run)' if args.dry_run else ''}")
    print("  languages: " + (", ".join(f"{l} ({'/'.join(p for p in (i['rel'], i['src']) if p) or '.'})" for l, i in langs.items())
                             or "none yet — the ub-setup skill adds them with the stack"))
    print(f"  main branch: {main}; mode: {mode} ({how})")
    if any(i.get("others") for i in langs.values()):
        print("  more roots of a language: " + "; ".join(f"{l}: {', '.join(i['others'])}" for l, i in langs.items() if i.get("others"))
              + " — one root per language is judged (TODO in .ub/config)")
    print(f"  verify: {verify or 'TODO'}")
    for line in plan.done:
        print(f"  wrote {line}")
    if not plan.done:
        print("  nothing to change")
    print(f"""
Next:
  1. Open Claude Code in {repo} and run /ub-setup — it finishes the setup with you
     (verify, module boundaries, the diagram's layers{', the baseline' if mode == 'ratchet' else ''}{', the stack' if not langs else ''}).
  2. Or by hand: {j}ub-doctor{f'; {j}ub-baseline' if mode == 'ratchet' else ''}; then on a task branch {j}gate and {j}review.
  Commit .ub/, .claude/ and the edited files on a branch; nothing was committed.""")


def main() -> None:
    p = argparse.ArgumentParser(description="Install or upgrade ub-kit in a repository.")
    p.add_argument("repo", nargs="?", default=".")
    p.add_argument("--langs", help="python,go,typescript (default: detected)")
    p.add_argument("--mode", choices=["strict", "ratchet"], help="default: ratchet when code exists")
    p.add_argument("--main", help="the main branch (default: detected)")
    p.add_argument("--ci", action="store_true", help="add .github/workflows/ub-gate.yml")
    p.add_argument("--upgrade", action="store_true", help="rewrite only the kit's own files")
    p.add_argument("--dry-run", action="store_true", help="show what would change")
    args = p.parse_args()
    install(Path(args.repo).expanduser().resolve(), args)


if __name__ == "__main__":
    main()
