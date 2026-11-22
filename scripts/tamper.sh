#!/usr/bin/env bash
# Runs INSIDE the container: soundness demo. Verifies an honest proof and
# tampered copies of it; only the unmodified ones must pass.
#
# Usage: tamper.sh [proof.json | proof.json.gz]
#   Default: the example fib(10) proof in results/proofs/ (no proving needed).
# Expects the repo mounted at /repo.
set -uo pipefail

SRC="${1:-/repo/results/proofs/fib10_proof.json.gz}"
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
export SCARB_TARGET_DIR="$TMP/target"
cd /repo/cairo/fib_exec

case "$SRC" in
  *.gz) gunzip -c "$SRC" > "$TMP/honest.json" ;;
  *)    cp "$SRC" "$TMP/honest.json" ;;
esac

# Public output written by the bootloader:
#   [n_tasks, task_output_size, program_hash, fib(n)]
# Each value is a felt252 stored as 8 u32 limbs (least significant first).
OUT='.claim.public_data.public_memory.output'
echo "fib(n) declarado en la prueba: $(jq "$OUT[-1][1][0]" "$TMP/honest.json")"
echo

# name | expected result | jq filter applied to the honest proof
CASES=(
  "original|OK|"
  "re-serializada con jq, sin cambios|OK|."
  "output alterado (fib(n) + 1)|FAIL|$OUT[-1][1][0] += 1"
  "hash del programa alterado|FAIL|$OUT[2][1][0] |= (. + 1) % 4294967296"
  "prueba alterada (1 byte de un commitment)|FAIL|.stark_proof.commitments[0][0] |= (. + 1) % 256"
  "prueba alterada (1 valor consultado)|FAIL|.stark_proof.queried_values[0][0][0] |= (. + 1) % 2147483647"
)

# Changes to the claim or the commitments alter the Fiat-Shamir transcript, so
# the proof-of-work no longer matches. Queried values are read after the
# proof-of-work, so tampering them is caught by the Merkle check instead.
fails=0
printf '%-44s %-8s %-8s %s\n' "caso" "esperado" "obtenido" "motivo"
for c in "${CASES[@]}"; do
  IFS='|' read -r name expected filter <<< "$c"
  f="$TMP/case.json"
  if [ -z "$filter" ]; then cp "$TMP/honest.json" "$f"; else jq -c "$filter" "$TMP/honest.json" > "$f"; fi
  if out=$(scarb verify --proof-file "$f" 2>&1); then got=OK; why=""
  else got=FAIL; why=$(echo "$out" | sed -n 's/^error: failed to verify proof: //p' | tail -1); fi
  [ "$got" = "$expected" ] || { why="INESPERADO ${why}"; fails=$((fails + 1)); }
  printf '%-44s %-8s %-8s %s\n' "$name" "$expected" "$got" "$why"
done

exit "$fails"
