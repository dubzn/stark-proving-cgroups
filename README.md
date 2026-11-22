# stark-proving-cgroups

Generación y verificación de pruebas STARK (Stwo) de programas Cairo bajo restricciones de CPU y memoria impuestas con cgroups v2 en Docker.

Trabajo Final de Sistemas Operativos y Redes II (UNGS). Ver [SPEC.md](SPEC.md).

## Requisitos

- Docker con cgroups v2.
- **Al menos 16 GB de RAM asignados a Docker.** El prover necesita ~14 GB incluso para programas mínimos (ver "Resultados preliminares").
  En macOS: Docker Desktop → Settings → Resources → Memory.

## Uso

```bash
# 1. Construir la imagen (Scarb 2.21.0 + Starknet Foundry 0.64.1)
docker build -t stark-proving:dev -f docker/Dockerfile docker

# 2. Tests de la librería
docker run --rm -v "$PWD/cairo":/work -w /work/fib_core stark-proving:dev scarb test

# 3. Ejecutar fib(10)
docker run --rm -v "$PWD/cairo":/work -w /work/fib_exec stark-proving:dev \
  scarb execute --arguments 10 --print-program-output --print-resource-usage

# 4. Ejecutar + generar la prueba STARK, y verificarla
docker run --rm -v "$PWD/cairo":/work -w /work/fib_exec stark-proving:dev bash -c '
  scarb prove --execute --arguments 10 &&
  scarb verify --execution-id 1'
```

La prueba queda en `cairo/fib_exec/target/execute/fib_exec/execution<N>/proof/proof.json`.

## Estructura

```
docker/Dockerfile      imagen con Scarb (execute/prove/verify) y snforge
cairo/fib_core/        librería: fib(n) + tests
cairo/fib_exec/        programa #[executable] que se prueba con Stwo
```

Los paquetes Cairo son independientes (no un workspace): el ejecutable necesita `enable-gas = false` y un workspace solo aplica la sección `[cairo]` de la raíz, lo que chocaría con el contrato Starknet que se agrega después.

## Notas

- `scarb prove` solo prueba ejecuciones con target `bootloader` (el default). Con `--target standalone` falla.
- Limitar los hilos del prover (`RAYON_NUM_THREADS`) no reduce la memoria pico.

## Resultados preliminares

Apple M3 Pro, VM de Docker con 12 CPU y 16 GB, sin límites de cgroup, una corrida:

| n | steps | t prove | memoria pico | swap | tamaño prueba (JSON) | t verify |
|---|------:|--------:|-------------:|-----:|---------------------:|---------:|
| 10 | 140 | 17,0 s | 14.237 MiB | 0 | 11,3 MB | 0,35 s |
| 100.000 | 1.000.040 | 61,7 s | 15.136 MiB | 0 | 11,2 MB | 0,18 s |

Con 12 GB en la VM, la prueba de fib(10) muere por OOM (exit 137) en todos los casos.
