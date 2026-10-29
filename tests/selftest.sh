#!/usr/bin/env bash
# ub-kit's own check: installs the kit into throwaway repositories and asserts what the gate says.
#   tests/selftest.sh [python] [go] [typescript]     (default: python go; typescript needs npm)
# Needs git, just, python >= 3.11, uv (python), go (go), node + npm (typescript). Uses the shared
# tool cache (~/.cache/ub-kit). Work dir: $UB_SELFTEST_DIR or a temp dir, removed on success.
set -uo pipefail

kit="$(cd "$(dirname "$0")/.." && pwd)"
work="${UB_SELFTEST_DIR:-$(mktemp -d)}"
langs=("$@")
((${#langs[@]})) || langs=(python go)
failed=0

say() { printf '\n### %s\n' "$*"; }
ok() { printf '  ok   %s\n' "$*"; }
bad() { printf '  FAIL %s\n' "$*"; failed=$((failed + 1)); }
# expect EXIT DESCRIPTION -- COMMAND...: the command's exit code must be EXIT.
expect() {
  local want=$1 what=$2; shift 3
  "$@" >"$work/last.log" 2>&1
  local got=$?
  if [[ $got == "$want" ]]; then ok "$what (exit $got)"; else bad "$what: exit $got, want $want (log: $work/last.log)"; tail -20 "$work/last.log"; fi
}
has() { if grep -q -- "$2" "$1"; then ok "$3"; else bad "$3: no «$2» in $1"; fi; }
commit() { git add -A && git commit -qm "$1"; }

python_case() {
  say "python, ratchet: old debt is DEBT, new mutants are red, a weakened test is red"
  local r="$work/py"
  mkdir -p "$r/src/shop/domain" "$r/tests" && cd "$r" || return
  cat >pyproject.toml <<'EOF'
[project]
name = "shop"
version = "0"
requires-python = ">=3.11"
[dependency-groups]
dev = ["pytest>=8", "coverage>=7"]
[tool.uv]
package = false
[tool.pytest.ini_options]
pythonpath = ["src"]
EOF
  touch src/shop/__init__.py src/shop/domain/__init__.py
  cat >src/shop/domain/fees.py <<'EOF'
def tier(amount: int, vip: bool, region: str) -> int:
    if amount < 0:
        raise ValueError("negative")
    if vip and region == "EU":
        return 1
    if vip and region == "US":
        return 2
    if amount > 1000 and region == "EU":
        return 3
    if amount > 1000:
        return 4
    if region == "UA":
        return 5
    return 6


def fee(amount: int) -> int:
    if amount <= 0:
        return 0
    return max(amount // 100, 5)
EOF
  cat >tests/test_fees.py <<'EOF'
from shop.domain.fees import fee


def test_fee_has_a_minimum() -> None:
    assert fee(10) == 5
EOF
  printf '.venv/\n__pycache__/\n' >.gitignore
  git init -q -b main && commit "legacy shop" && uv sync -q || { bad "uv sync"; return; }
  expect 0 "install (ratchet)" -- "$kit/install.sh" . --mode ratchet
  sed -i.bak '/TODO(ub-setup)/d; s#^    .*pytest -q$#    uv run pytest -q#' justfile && rm -f justfile.bak
  expect 0 "baseline" -- just ub-baseline
  has .ub/baseline/crap.tsv "shop.domain.fees	tier" "tier() is old debt in the baseline"
  commit "ub-kit" && git checkout -qb task

  cat >>src/shop/domain/fees.py <<'EOF'


def discount(amount: int, loyal: bool) -> int:
    if loyal and amount > 500:
        return amount // 10
    return 0
EOF
  expect 1 "a new function without tests is red" -- just gate
  has .ub/out/gate/summary.txt "DEBT: CRAP" "tier() reported as DEBT, not red"
  has .ub/out/gate/summary.txt "mutants in src/shop/domain/fees.py" "new mutants are red"

  cat >>tests/test_fees.py <<'EOF'


def test_loyal_customers_get_a_tenth_off_above_500() -> None:
    from shop.domain.fees import discount

    assert discount(501, loyal=True) == 50
    assert discount(500, loyal=True) == 0
    assert discount(1000, loyal=False) == 0
EOF
  expect 0 "tested, the change is green despite old debt" -- just gate
  commit "discount" && git checkout -qb weaker
  sed -i.bak '/assert discount(500, loyal=True) == 0/d' tests/test_fees.py && rm -f tests/test_fees.py.bak
  expect 1 "a weakened test is red" -- just gate task
  has .ub/out/gate/summary.txt "killed before now survive" "the regression is named"
  expect 1 "and stays red on a rerun" -- just gate task
}

go_case() {
  say "go, strict: a module named unlike its directory, survivors red, then green"
  local r="$work/go"
  mkdir -p "$r/backend/internal/pricing" && cd "$r" || return
  printf 'module acme\n\ngo 1.22\n' >backend/go.mod
  cat >backend/internal/pricing/price.go <<'EOF'
// Package pricing computes prices.
package pricing

// Net returns the amount after a percent discount.
func Net(amount, percent int) int { return amount - amount*percent/100 }
EOF
  cat >backend/internal/pricing/price_test.go <<'EOF'
package pricing

import "testing"

func TestNet(t *testing.T) {
	if Net(1000, 10) != 900 {
		t.Fatal(Net(1000, 10))
	}
}
EOF
  git init -q -b master && commit "acme"
  expect 0 "install (strict)" -- "$kit/install.sh" .
  has .ub/config "root = backend" "the Go root is backend/"
  sed -i.bak '/TODO(ub-setup)/d' justfile && rm -f justfile.bak
  commit "ub-kit" && git checkout -qb task
  cat >backend/internal/pricing/tax.go <<'EOF'
package pricing

// Gross adds VAT in percent; a negative rate counts as zero.
func Gross(net, vat int) int { return net + net*max(vat, 0)/100 }
EOF
  cat >backend/internal/pricing/tax_test.go <<'EOF'
package pricing

import "testing"

func TestGross(t *testing.T) {
	if Gross(1000, 20) != 1200 {
		t.Fatal(Gross(1000, 20))
	}
}
EOF
  expect 1 "a weak test leaves survivors" -- just gate
  cat >backend/internal/pricing/tax_test.go <<'EOF'
package pricing

import "testing"

func TestGross(t *testing.T) {
	for _, c := range []struct{ net, vat, want int }{{1000, 20, 1200}, {1000, 0, 1000}, {1000, -5, 1000}, {1000, 1, 1010}} {
		if got := Gross(c.net, c.vat); got != c.want {
			t.Errorf("Gross(%d, %d) = %d, want %d", c.net, c.vat, got, c.want)
		}
	}
}
EOF
  expect 0 "proper tests make it green" -- just gate
}

typescript_case() {
  say "typescript, strict: no overlay plugin is red; with it survivors are real"
  local r="$work/ts"
  mkdir -p "$r/web/src" && cd "$r" || return
  cat >web/package.json <<'EOF'
{ "name": "web", "private": true, "type": "module",
  "devDependencies": { "typescript": "^5.6.0", "vite": "^6.0.0", "vitest": "^3.0.0", "@vitest/coverage-v8": "^3.0.0" } }
EOF
  printf 'export const cents = (a: number): number => Math.round(a * 100)\n' >web/src/money.ts
  printf "import { expect, it } from 'vitest'\nimport { cents } from './money'\nit('cents', () => expect(cents(1.25)).toBe(125))\n" >web/src/money.spec.ts
  printf 'node_modules/\n' >.gitignore
  (cd web && npm install --silent --no-audit --no-fund) || { bad "npm install"; return; }
  git init -q -b main && commit "web"
  expect 0 "install" -- "$kit/install.sh" .
  sed -i.bak '/TODO(ub-setup)/d' justfile && rm -f justfile.bak
  commit "ub-kit" && git checkout -qb task
  printf '\nexport function split(total: number, parts: number): number[] {\n  if (parts < 1) throw new Error("parts")\n  const share = Math.floor(total / parts)\n  return Array.from({ length: parts }, (_, i) => (i < total %% parts ? share + 1 : share))\n}\n' >>web/src/money.ts
  printf "it('split', () => expect(split(9, 3)).toEqual([3, 3, 3]))\n" >>web/src/money.spec.ts
  sed -i.bak "s#import { cents } from './money'#import { cents, split } from './money'#" web/src/money.spec.ts && rm -f web/src/money.spec.ts.bak
  expect 1 "without the overlay plugin the gate is red" -- just gate
  has .ub/out/gate/summary.txt "overlay plugin" "it says why"
  { sed -n '/^import { lstatSync }/,$p' .ub/snippets/vitest-mutator-overlay.ts.txt
    printf "import { fileURLToPath } from 'node:url'\nexport default { plugins: [mutatorOverlay(fileURLToPath(new URL('./', import.meta.url)))] }\n"; } >web/vitest.config.ts
  expect 1 "with it the weak spec leaves real survivors" -- just gate
  has .ub/out/gate/summary.txt "survived" "survivors are reported"
}

for lang in "${langs[@]}"; do "${lang}_case"; done
cd /
if ((failed)); then echo; echo "SELFTEST: $failed failure(s); work dir kept: $work"; exit 1; fi
echo; echo "SELFTEST: all green"
[[ -n "${UB_SELFTEST_DIR:-}" ]] || rm -rf "$work"
