# Resultados

Mediciones del 22/11/2026 con `scripts/sweep.sh all` (3 repeticiones por punto).

## Entorno

- Host: Windows 11, Intel Xeon W-11955M (8 núcleos, 16 hilos), 32 GB de RAM.
- VM: VMware Workstation, Ubuntu Server 24.04, 14 vCPU, 24 GiB de RAM fija, swap de 7 GiB.
- Docker Engine 29.10 nativo, cgroups v2 (driver `systemd`). Arquitectura x86-64.
- Imagen `stark-proving:dev` (Scarb 2.21.0, Stwo vía `scarb prove`).

## Archivos

- `raw/stability.csv`: control previo, tres corridas de `run_once.sh 10`. La primera
  (54 s) incluye el costo de que VMware le asigne a la VM, al primer uso, la memoria
  que pide el prover; las siguientes tardan ~24 s (diferencia ~1,6 %). Antes del barrido
  se hizo una corrida de calentamiento que no se registró.
- `raw/E1.csv`: complejidad, n ∈ {10, 1.000, 10.000, 50.000, 100.000}, sin límites.
- `raw/E2.csv`: `--cpus` ∈ {4, 2, 1, 0.5}, n = 10.000.
- `raw/E3.csv`: `--memory` = `--memory-swap` ∈ {16g, 15g, 14.5g, 14g, 13g}, n = 10.000.
  Docker interpreta `g` como GiB: `mem_max` está en bytes.
- `figures/`: gráficos generados con `scripts/plot.py` (media de 3 repeticiones, barras de error = 1 desvío).
  `e1_prove_time`, `e1_verify_vs_execute`, `e1_memory_peak`, `e2_cpu_limit`, `e3_memory_limit`.
- `proofs/fib10_proof.json.gz`: una prueba STARK de fib(10) como ejemplo del formato
  (11,3 MB sin comprimir). Las demás no se guardan: pesan lo mismo y no aportan.

Las columnas están descritas en SPEC.md §7.

## Verificar la prueba de ejemplo

La prueba se puede verificar en cualquier máquina, sin el costo de generarla:

```bash
gunzip -k results/proofs/fib10_proof.json.gz
docker run --rm -v "$PWD":/repo -w /repo/cairo/fib_exec stark-proving:dev \
  scarb verify --proof-file /repo/results/proofs/fib10_proof.json
```
