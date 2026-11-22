#!/usr/bin/env bash
# Runs on the HOST: launches one fresh container per measurement (fresh cgroup,
# so memory.peak starts at zero) and appends the CSV row to results/raw/<exp>.csv.
#
# Usage: scripts/sweep.sh E1|E2|E3|all
# Env:   REPS (default 3), IMAGE (default stark-proving:dev)
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${IMAGE:-stark-proving:dev}"
REPS="${REPS:-3}"
OUT="$ROOT/results/raw"
mkdir -p "$OUT"

# Experiment parameters (see SPEC.md §7).
E1_N=(10 1000 10000 50000 100000)
E2_N=10000; E2_CPUS=(4 2 1 0.5)
E3_N=10000; E3_MEM=(16g 15g 14.5g 14g 13g)

# run <csv> <n> [docker limit flags...]
run() {
  local csv="$1" n="$2"; shift 2
  local header=0; [ -s "$csv" ] || header=1
  docker run --rm -e HEADER="$header" "$@" \
    -v "$ROOT/cairo":/work -v "$ROOT/scripts":/scripts:ro \
    "$IMAGE" bash /scripts/run_once.sh "$n" | tee -a "$csv"
}

e1() {
  for n in "${E1_N[@]}"; do for r in $(seq "$REPS"); do
    echo "# E1 n=$n rep=$r" >&2
    run "$OUT/E1.csv" "$n"
  done; done
}

e2() {
  for c in "${E2_CPUS[@]}"; do for r in $(seq "$REPS"); do
    echo "# E2 cpus=$c rep=$r" >&2
    run "$OUT/E2.csv" "$E2_N" --cpus="$c"
  done; done
}

e3() {
  for m in "${E3_MEM[@]}"; do for r in $(seq "$REPS"); do
    echo "# E3 memory=$m rep=$r" >&2
    # memory-swap == memory: no swap, so hitting the limit means OOM kill.
    run "$OUT/E3.csv" "$E3_N" --memory="$m" --memory-swap="$m"
  done; done
}

case "${1:-}" in
  E1) e1 ;; E2) e2 ;; E3) e3 ;;
  all) e1; e2; e3 ;;
  *) echo "usage: $0 E1|E2|E3|all" >&2; exit 1 ;;
esac
