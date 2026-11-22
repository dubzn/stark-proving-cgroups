#!/usr/bin/env bash
# Runs INSIDE the container: execute -> prove -> verify fib(n) once and print
# one CSV row with timings and cgroup v2 metrics.
#
# Usage: run_once.sh <n>
# Expects the fib_exec package at /work/fib_exec.
# Uses a target dir inside the container so every run starts clean
# (execution id is always 1 and nothing is left on the host).
set -uo pipefail

N="${1:?usage: run_once.sh <n>}"
CG=/sys/fs/cgroup
export SCARB_TARGET_DIR=/tmp/target
EXEC_DIR="$SCARB_TARGET_DIR/execute/fib_exec/execution1"
cd /work/fib_exec

now() { date +%s.%N; }
elapsed() { echo "$(now) - $1" | bc; }
cpu_stat() { awk -v k="$1" '$1 == k { print $2 }' "$CG/cpu.stat"; }

# Build outside the measured window.
scarb build -q || { echo "build failed" >&2; exit 1; }

# 1. Execute (bootloader target: the only one scarb prove accepts).
t0=$(now)
exec_out=$(scarb execute --no-build --target bootloader --output standard \
  --arguments "$N" --print-resource-usage 2>&1)
exec_rc=$?
t_execute=$(elapsed "$t0")
steps=$(echo "$exec_out" | awk '/steps:/ { gsub(",", "", $2); print $2 }')

# 2. Prove. cpu.stat deltas isolate the prover's CPU usage and throttling.
cpu0=$(cpu_stat usage_usec); thr0=$(cpu_stat nr_throttled); thru0=$(cpu_stat throttled_usec)
t0=$(now)
scarb prove --execution-id 1 -q >/dev/null 2>&1
prove_rc=$?
t_prove=$(elapsed "$t0")
cpu_usage_usec=$(( $(cpu_stat usage_usec) - cpu0 ))
nr_throttled=$(( $(cpu_stat nr_throttled) - thr0 ))
throttled_usec=$(( $(cpu_stat throttled_usec) - thru0 ))

# 3. Verify (only if a proof was produced).
proof="$EXEC_DIR/proof/proof.json"
t_verify=""; verified=false; proof_size=""
if [ "$prove_rc" -eq 0 ] && [ -f "$proof" ]; then
  proof_size=$(stat -c %s "$proof")
  t0=$(now)
  scarb verify --execution-id 1 -q >/dev/null 2>&1 && verified=true
  t_verify=$(elapsed "$t0")
fi

# Container-wide peaks (the prover dominates them).
mem_peak=$(cat "$CG/memory.peak")
swap_peak=$(cat "$CG/memory.swap.peak" 2>/dev/null || echo 0)
oom_kill=$(awk '$1 == "oom_kill" { print $2 }' "$CG/memory.events")
cpu_max=$(tr ' ' '/' < "$CG/cpu.max")
mem_max=$(cat "$CG/memory.max")

if [ "${HEADER:-0}" = 1 ]; then
  echo "n,steps,cpu_max,mem_max,exec_rc,prove_rc,verified,t_execute,t_prove,t_verify,proof_size,mem_peak,swap_peak,oom_kill,cpu_usage_usec,nr_throttled,throttled_usec"
fi
echo "$N,$steps,$cpu_max,$mem_max,$exec_rc,$prove_rc,$verified,$t_execute,$t_prove,$t_verify,$proof_size,$mem_peak,$swap_peak,$oom_kill,$cpu_usage_usec,$nr_throttled,$throttled_usec"
