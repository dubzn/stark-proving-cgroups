# SPEC — Generación y verificación de pruebas STARK bajo restricciones de cgroups v2

> Trabajo Final Integrador — Sistemas Operativos y Redes II (UNGS), 2do semestre 2026.
> Estado: **aprobado**. Implementación y barridos completos. Sigue el informe.

---

## 1. Pregunta de investigación

> ¿Cómo afectan la complejidad de ejecución de programas Cairo y las restricciones de CPU y memoria impuestas mediante cgroups v2 al tiempo de generación y verificación, al consumo de recursos y a la finalización exitosa de pruebas STARK válidas?

(Propuesta por el docente. Se usa textual.)

## 2. Objetivo general

Medir experimentalmente cómo la complejidad de un programa Cairo y los límites de CPU y memoria de un contenedor afectan la generación y verificación de pruebas STARK con el prover Stwo.

Cairo se trata como un lenguaje de propósito general para cómputo verificable: cualquier programa escrito en Cairo deja una traza de ejecución que se puede probar. Starknet (una L2 de Ethereum cuyos contratos se escriben en Cairo) aparece solo como contexto y motivación: es el sistema que usa este mecanismo de "probar caro, verificar barato" para escalar.

## 3. Objetivos específicos

| # | Objetivo | Sección del informe |
|---|----------|---------------------|
| O1 | Construir un entorno reproducible en Docker con Scarb y Stwo. | Implementación |
| O2 | Implementar Fibonacci en Cairo como librería con tests, usada por un programa ejecutable. | Implementación |
| O3 | Generar y verificar una prueba STARK real del ejecutable, y demostrar que una prueba o un output alterados no verifican. | Implementación / Pruebas |
| O4 | Medir tiempo, memoria pico, CPU, tamaño de prueba y finalización exitosa variando la complejidad (n), el límite de CPU y el límite de memoria. | Resultados |
| O5 | Analizar los resultados en relación al modelo de rollup (probar caro, verificar barato) y a los mecanismos de cgroups v2. | Resultados / Conclusiones |

## 4. Alcance

### Entra
- Dos paquetes Scarb: `fib_core` (librería + tests con `scarb test`) y `fib_exec` (programa `#[executable]`).
- `scarb execute` → `scarb prove` → `scarb verify` sobre `fib_exec`.
- Demo de soundness: prueba alterada / output alterado ⇒ la verificación falla.
- Tres barridos experimentales (ver §7).
- Scripts para correr los barridos y volcar resultados a CSV, más gráficos.

### Queda afuera (trabajo futuro)
- Contratos Starknet (y sus tests con snforge), red local (Katana, starknet-devnet) y deploy de contratos.
- L1 (Anvil), messaging L1↔L2, settlement real.
- Otros programas (Poseidon, Merkle, sorting).
- Comparación entre provers (Stone vs Stwo) o entre arquitecturas (x86 vs ARM).
- Propiedades zero-knowledge (las pruebas se tratan como pruebas de **integridad**, no de privacidad).

## 5. Arquitectura

```
┌──────────── Host: VM Ubuntu Server 24.04 (x86-64) ───────────┐
│  Docker Engine nativo (kernel con cgroups v2)                 │
│                                                               │
│   ┌──────────── contenedor `prover` ────────────┐             │
│   │  límites: --cpus=X  --memory=Y  (cgroups v2) │             │
│   │                                              │             │
│   │  scarb execute  → traza de ejecución + output│             │
│   │  scarb prove    → prueba STARK (Stwo)        │             │
│   │  scarb verify   → OK / FAIL                  │             │
│   │                                              │             │
│   │  medición: /sys/fs/cgroup/memory.peak,       │             │
│   │            cpu.stat, tiempo, exit code       │             │
│   └──────────────────────────────────────────────┘             │
│                                                               │
│   scripts/ (host) → orquestan barridos → results/*.csv        │
└───────────────────────────────────────────────────────────────┘
```

Una sola imagen Docker. Cada corrida de medición es un `docker run` nuevo, así cada medición tiene su propio cgroup y `memory.peak` arranca de cero.

## 6. Estructura del repo

```
stark-proving-cgroups/
├── SPEC.md
├── README.md
├── Makefile                    # comandos: make build / prove / tamper / sweep / plots
├── docker/
│   └── Dockerfile              # scarb (execute / prove / verify con stwo), versión fijada
├── cairo/                      # paquetes Scarb
│   ├── fib_core/               # lib: fn fib(n: u32) -> felt252 + tests
│   └── fib_exec/               # #[executable] que llama a fib_core
├── scripts/
│   ├── run_once.sh             # execute+prove+verify con medición, imprime 1 fila CSV
│   ├── sweep.sh                # corre los 3 barridos (llama a run_once.sh vía docker run)
│   ├── tamper.sh               # demo de prueba/output alterados
│   └── plot.py                 # CSV → gráficos
└── results/
    ├── raw/                    # CSV crudos por barrido
    ├── proofs/                 # una prueba de ejemplo (fib(10), gzip)
    └── figures/                # gráficos para el informe
```

## 7. Experimentos

Cada punto se repite **3 veces**. Se reporta media y desvío estándar.

Todas las corridas usan `--memory-swap` igual a `--memory` (sin swap). Si no, Docker deja usar swap hasta duplicar el límite y el contenedor se pone lento en vez de morir por OOM, lo que contamina E3.

| Barrido | Varía | Fijo | Pregunta que responde |
|---------|-------|------|-----------------------|
| E1 — Complejidad | n ∈ {10, 1.000, 10.000, 50.000, 100.000} (5.172 → 1.005.072 steps, con bootloader) | sin límites | ¿Cómo escalan prueba y verificación con los steps? |
| E2 — CPU | `--cpus` ∈ {4, 2, 1, 0.5} | n = 10.000 | ¿Cuánto paraleliza el prover? ¿Falla o solo tarda? |
| E3 — Memoria | `--memory` ∈ {16, 15, 14.5, 14, 13} GB | n = 10.000, CPU sin límite | ¿Cuál es el umbral de memoria donde la prueba no termina? |

n máximo = 100.000: calibrado en la Mac con 16 GB para la VM de Docker, es el mayor valor verificado que no muere por OOM.

### Métricas por corrida

| Métrica | Fuente |
|---------|--------|
| `n`, `steps` | input / salida de `scarb execute` |
| `t_execute`, `t_prove`, `t_verify` (s) | reloj de pared alrededor de cada comando |
| `mem_peak` (bytes) | `/sys/fs/cgroup/memory.peak` |
| `cpu_usage_usec`, `nr_throttled`, `throttled_usec` | `/sys/fs/cgroup/cpu.stat` |
| `oom_kill` | `/sys/fs/cgroup/memory.events` |
| `proof_size` (bytes) | tamaño del archivo de prueba |
| `exit_code` | 0 = OK, 137 = OOM kill |
| `verified` | resultado de `scarb verify` |

### Hipótesis
- H1: `t_prove` crece con `steps`, de forma sublineal en el rango medido (hay un costo fijo alto).
- H2: `proof_size` y `t_verify` crecen mucho más lento que `t_prove`. Existe un n a partir del cual verificar es más barato que re-ejecutar.
- H3: limitar CPU aumenta `t_prove` pero no causa fallas.
- H4: limitar memoria por debajo de un umbral causa OOM kill (exit 137). El umbral está dominado por un costo fijo del prover y crece poco con n.

### Resultados (22/11/2026)

Medias de 3 repeticiones. Detalle y entorno en `results/README.md`.

| Hipótesis | Resultado |
|-----------|-----------|
| H1 | **Se confirma.** `t_prove` es casi plano: 24,2 s con 5.172 steps y 25,5 s con 1.005.072 (≈200× más steps, +5 %). Anomalía: fib(10) tarda más que fib(1.000) (24,2 s vs 21,9 s) en las 3 repeticiones. |
| H2 | **Se confirma.** `proof_size` ≈ 11,3 MB y `t_verify` ≈ 0,12 s para todo n. Verificar es más barato que re-ejecutar entre n = 1.000 y 10.000; en n = 100.000, 8× más barato (0,12 s vs 0,95 s). |
| H3 | **Se confirma.** `t_prove` ∝ 1/cpus: 38,5 s (4), 70 s (2), 141 s (1), 268 s (0,5). Ninguna falla; la memoria no cambia (~13,7 GiB). Casi sin throttling salvo en 0,5: el prover parece lanzar tantos hilos como permite `cpu.max`. Sin límite usa ~255 s de CPU contra ~138 s limitado: paralelizar en 14 vCPU cuesta ~1,8× más trabajo total. |
| H4 | **Se confirma.** Con 14 GiB o más termina igual que sin límite (~21,9 s); con 13 GiB muere por OOM en las 3 corridas (exit 137, a los ~17 s). Umbral entre 13 y 14 GiB para n = 10.000. El pico crece poco con n: 13,8 GiB (n = 10) → 15,0 GiB (n = 100.000). |

## 8. Criterios de aceptación (Definition of Done)

- [x] `docker build` produce la imagen con versiones fijadas.
- [x] `scarb test` pasa en `fib_core` (fib coincide con valores conocidos).
- [x] `scarb execute` + `prove` + `verify` funciona para un n chico dentro del contenedor.
- [x] `tamper.sh` muestra que una prueba alterada y un output alterado fallan la verificación.
- [x] `run_once.sh` emite una fila CSV con todas las métricas de §7.
- [x] E1, E2 y E3 completos en `results/raw/`.
- [x] `plot.py` genera los gráficos del informe en `results/figures/`.
- [x] README explica cómo reproducir todo en ≤ 5 comandos (`make build`, `make prove`, `make tamper`, `make sweep`, `make plots`).

## 9. Tareas (en orden)

1. [x] Elegir versión de Scarb con `prove`/`verify` y fijarla (2.21.0).
2. [x] Dockerfile con Scarb.
3. [x] `fib_core` + `fib_exec`: execute → prove → verify con n chico. ← **primer hito pedido por el docente**
4. [x] `tamper.sh`.
5. [x] `run_once.sh` con lectura de cgroups.
6. [x] Calibrar rangos de n y el n fijo de E2/E3.
7. [x] `sweep.sh` y correr E1, E2, E3 (VM Ubuntu Server, 22/11/2026).
8. [x] `plot.py` y gráficos.
9. [x] README final, con `Makefile`.

## 10. Riesgos y preguntas abiertas

| Riesgo | Mitigación |
|--------|------------|
| **Docker en macOS:** macOS no tiene cgroups (es un feature del kernel Linux). Docker Desktop corre una VM Linux liviana y los contenedores viven adentro; además, la Mac de desarrollo (18 GB) termina usando swap con una VM de 16 GB, y el mismo fib(10) tarda entre 13 y 54 s. | Las mediciones se corrieron en una VM Ubuntu Server 24.04 con Docker Engine nativo y 24 GiB de RAM fija. La Mac se usa solo para desarrollo. |
| El prover necesita ~14 GB aun para programas mínimos. | n máximo calibrado en 100.000 (pico 15,0 GiB). E3 barre límites en el rango 13–16 GiB. |
| Probar n grandes puede tardar demasiado. | Calibración (tarea 6): n = 100.000 tarda ~25 s. |
| Arquitectura del host. | Los resultados son de x86-64. La prueba de ejemplo, generada en x86-64, verifica también en ARM64 (Apple Silicon). |

## 11. Reglas del repo

- No se hacen commits sin aprobación explícita del autor.
