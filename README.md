# stark-proving-cgroups

Generación y verificación de pruebas STARK (prover Stwo) de un programa Cairo, bajo límites de CPU y memoria impuestos con cgroups v2 en Docker.

Trabajo Final de Sistemas Operativos y Redes II (UNGS). La planificación está en [SPEC.md](SPEC.md).

## Requisitos

- Docker con cgroups v2, y `make`.
- **Al menos 16 GB de RAM disponibles para Docker.** El prover necesita ~14 GB incluso para programas mínimos.
  En macOS: Docker Desktop → Settings → Resources → Memory.

## Uso

Todo corre dentro de Docker. `make` a secas lista los comandos:

```bash
make build              # construye la imagen (Scarb 2.21.0 con el prover Stwo)
make test               # tests de fib_core
make run N=10           # ejecuta fib(10), sin prueba
make prove N=10         # ejecuta fib(10), genera la prueba STARK y la verifica (~20 s)
make tamper             # demo: las pruebas alteradas no verifican (~3 s)
make measure N=10000    # una corrida medida: tiempos y métricas de cgroups en CSV
make sweep EXP=all      # barridos E1, E2 y E3 -> results/raw/*.csv (~45 min)
make plots              # results/raw/*.csv -> results/figures/*.png
make informe            # informe/informe.md -> informe/informe.docx (para Google Docs)
make shell              # shell en el contenedor, con el repo en /repo
```

`N` es el n de Fibonacci (por defecto 10). `EXP` puede ser `E1`, `E2`, `E3` o `all`, y `REPS` cambia las repeticiones (por defecto 3).

## Qué hace cada experimento

| Barrido | Varía | Fijo |
|---------|-------|------|
| E1, complejidad | n ∈ {10, 1.000, 10.000, 50.000, 100.000} | sin límites |
| E2, CPU | `--cpus` ∈ {4, 2, 1, 0,5} | n = 10.000 |
| E3, memoria | `--memory` = `--memory-swap` ∈ {16, 15, 14,5, 14, 13} GiB | n = 10.000 |

Cada medición es un contenedor nuevo (cgroup propio, así `memory.peak` arranca de cero). Ver [SPEC.md §7](SPEC.md) para métricas e hipótesis.

## Resultados

VM Ubuntu Server 24.04 (14 vCPU, 24 GiB) sobre un Xeon W-11955M, medias de 3 repeticiones. Detalle en [results/README.md](results/README.md) y figuras en [results/figures/](results/figures/).

- **E1:** el tiempo de prueba es casi constante, ~22–25 s, de 5.172 a 1.005.072 steps. La prueba pesa ~11,3 MB y se verifica en ~0,12 s para todo n.
- **E2:** el tiempo escala como 1/cpus: 38,5 s con 4 CPUs y 268 s con 0,5. Nunca falla.
- **E3:** con 14 GiB o más termina igual que sin límite; con 13 GiB el kernel mata al prover por OOM (exit 137).

Demo de soundness (`make tamper`):

| caso | resultado | motivo |
|------|-----------|--------|
| original | OK | |
| re-serializada con jq, sin cambios | OK | control: jq no rompe la prueba |
| output alterado (55 → 56) | FAIL | Proof of work verification failed |
| hash del programa alterado | FAIL | Proof of work verification failed |
| 1 byte de un commitment | FAIL | Proof of work verification failed |
| 1 valor consultado | FAIL | Root mismatch (Merkle) |

El claim (output, hash del programa) y los commitments entran al transcript de Fiat–Shamir: cualquier cambio cambia los desafíos y el proof-of-work deja de coincidir. Los valores consultados se leen después, y los atrapa la verificación de Merkle.

## Estructura

```
Makefile               comandos del proyecto
docker/Dockerfile      imagen con Scarb (execute / prove / verify)
cairo/fib_core/        librería: fib(n) + tests
cairo/fib_exec/        programa #[executable] que se prueba con Stwo
scripts/run_once.sh    una corrida medida (dentro del contenedor)
scripts/sweep.sh       barridos E1–E3 (en el host, un contenedor por medición)
scripts/tamper.sh      demo de pruebas alteradas
scripts/plot.py        gráficos
results/               CSV, figuras y una prueba de ejemplo
informe/               borrador del informe (markdown) y diagramas
```

## Notas

- `scarb prove` solo prueba ejecuciones con target `bootloader` (el default). El bootloader suma ~5.000 steps fijos: fib(10) pasa de 140 a 5.172 steps.
- Limitar los hilos del prover (`RAYON_NUM_THREADS`) no reduce la memoria pico.
- Docker Desktop en macOS sirve para desarrollar, pero no para medir tiempos: con 18 GB de RAM la Mac termina usando swap y el mismo fib(10) tarda entre 13 y 54 s.
