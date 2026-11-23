# Contexto del proyecto

TP Final de Sistemas Operativos y Redes II (UNGS, 2do semestre 2026, prof. Benjamín Chuquimango). Individual, con informe (≥ 20 páginas, APA 7) y presentación oral.

Pregunta de investigación (propuesta por el docente, usar textual):
> ¿Cómo afectan la complejidad de ejecución de programas Cairo y las restricciones de CPU y memoria impuestas mediante cgroups v2 al tiempo de generación y verificación, al consumo de recursos y a la finalización exitosa de pruebas STARK válidas?

Toda la planificación está en [SPEC.md](SPEC.md); cómo correr todo, en [README.md](README.md).

## Reglas

- **No hacer commits ni push sin que el autor lo pida explícitamente.**
- Commits en inglés, agrupados por archivos con sentido. Documentación del TP en español.
- Scope chico: no agregar programas, contratos, chains, L1 ni otros provers. Eso es trabajo futuro.

## Decisiones tomadas

- Sin chain (ni Katana ni devnet): el objeto de estudio es el prover. El docente pidió separar ejecución de transacciones de generación de pruebas.
- Sin contratos: Cairo se presenta como lenguaje de propósito general para cómputo verificable. Starknet (L2 cuyos contratos se escriben en Cairo) queda solo como contexto en el informe.
- Prover: Stwo vía `scarb prove` (Scarb 2.21.0). No se usa Stone.
- Dos paquetes Cairo independientes: `fib_core` (librería + tests) y `fib_exec` (`#[executable]`, con `enable-gas = false`).
- `scarb prove` solo acepta ejecuciones con `--target bootloader`. El bootloader suma steps: fib(10) pasa de 140 a 5.172 steps.
- Barridos: E1 n ∈ {10, 1.000, 10.000, 50.000, 100.000}; E2 `--cpus` ∈ {4, 2, 1, 0.5} con n = 10.000; E3 `--memory` ∈ {16, 15, 14.5, 14, 13} GB con n = 10.000. 3 repeticiones. Siempre `--memory-swap` = `--memory`.

## Hallazgos hasta ahora

- El prover tiene un piso de memoria de ~14 GB, casi independiente de n: fib(10) ~14,2–14,8 GB de pico; fib(100.000) ~15,1 GB.
- Limitar hilos (`RAYON_NUM_THREADS`) no baja la memoria.
- Con 8 GB de límite el prover muere por OOM (exit 137, `oom_kill=1`).
- La verificación tarda ~0,2–0,35 s y la prueba pesa ~11 MB (JSON) sin importar n.

## Entorno de medición

- La Mac de desarrollo (M3 Pro, 18 GB) **no sirve para medir tiempos**: la VM de Docker necesita 16 GB y macOS termina usando swap, así que el mismo fib(10) tarda entre 13 y 54 s. Sirve para desarrollar y para E3 (que solo mira si termina o muere).
- Las mediciones de tiempo (E1, E2) se corren en una VM Ubuntu Server 24.04 sobre una máquina Windows de 32 GB: 24 GB de RAM fija para la VM, todos los núcleos menos 2, Docker Engine nativo, cgroups v2.
- Antes de los barridos, control de estabilidad: tres corridas de `run_once.sh 10`. Si `t_prove` varía menos de 10 %, se larga `scripts/sweep.sh all`.

## Estado de las tareas (SPEC §9)

- [x] 1. Versión fijada (Scarb 2.21.0)
- [x] 2. Dockerfile
- [x] 3. `fib_core` + `fib_exec`: execute → prove → verify funcionando
- [x] 4. `tamper.sh` (usa la prueba de ejemplo de `results/proofs/`)
- [x] 5. `run_once.sh`
- [x] 6. Calibración (n máx = 100.000)
- [x] 7. `sweep.sh` y barridos E1–E3 corridos (resultados en `results/`, resumen en SPEC §7)
- [x] 8. `plot.py` (corre en un contenedor python:3.12-slim, ver README)
- [x] 9. README final + `Makefile` (`make` lista los comandos)

Informe: la versión final está en Google Docs (copia de la plantilla de la cátedra, Arial 11, estructura exacta de la consigna). `informe/informe.md` es su fuente en markdown y se mantiene sincronizada con el doc. `make informe` (markdown -> .docx) queda como alternativa sin conector.
