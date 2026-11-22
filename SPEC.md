# SPEC — Generación y verificación de pruebas STARK bajo restricciones de cgroups v2

> Trabajo Final Integrador — Sistemas Operativos y Redes II (UNGS), 2do semestre 2026.
> Estado: **borrador para revisión**. Nada se implementa hasta aprobar este documento.

---

## 1. Pregunta de investigación

> ¿Cómo afectan la complejidad de ejecución de programas Cairo y las restricciones de CPU y memoria impuestas mediante cgroups v2 al tiempo de generación y verificación, al consumo de recursos y a la finalización exitosa de pruebas STARK válidas?

(Propuesta por el docente. Se usa textual.)

## 2. Objetivo general

Medir experimentalmente cómo la complejidad de un programa Cairo y los límites de CPU y memoria de un contenedor afectan la generación y verificación de pruebas STARK con el prover Stwo.

## 3. Objetivos específicos

| # | Objetivo | Sección del informe |
|---|----------|---------------------|
| O1 | Construir un entorno reproducible en Docker con Scarb, Stwo y Starknet Foundry. | Implementación |
| O2 | Implementar Fibonacci en Cairo como librería compartida, usada por un contrato Starknet (con tests en snforge) y por un programa ejecutable. | Implementación |
| O3 | Generar y verificar una prueba STARK real del ejecutable, y demostrar que una prueba o un output alterados no verifican. | Implementación / Pruebas |
| O4 | Medir tiempo, memoria pico, CPU, tamaño de prueba y finalización exitosa variando la complejidad (n), el límite de CPU y el límite de memoria. | Resultados |
| O5 | Analizar los resultados en relación al modelo de rollup (probar caro, verificar barato) y a los mecanismos de cgroups v2. | Resultados / Conclusiones |

## 4. Alcance

### Entra
- Tres paquetes Scarb independientes: `fib_core`, `fib_contract`, `fib_exec` (no workspace: el ejecutable requiere `enable-gas = false` y el contrato no).
- Tests del contrato con `snforge` (entorno Starknet simulado, **sin chain**).
- `scarb execute` → `scarb prove` → `scarb verify` sobre `fib_exec`.
- Demo de soundness: prueba alterada / output alterado ⇒ la verificación falla.
- Tres barridos experimentales (ver §7).
- Scripts para correr los barridos y volcar resultados a CSV, más gráficos.

### Queda afuera (trabajo futuro)
- Red local (Katana, starknet-devnet) y deploy real de contratos.
- L1 (Anvil), messaging L1↔L2, settlement real.
- Otros programas (Poseidon, Merkle, sorting).
- Comparación entre provers (Stone vs Stwo) o entre arquitecturas (x86 vs ARM).
- Propiedades zero-knowledge (las pruebas se tratan como pruebas de **integridad**, no de privacidad).

## 5. Arquitectura

```
┌──────────────────────── Host (macOS) ────────────────────────┐
│  Docker Desktop → VM Linux (kernel con cgroups v2)            │
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
├── docker/
│   └── Dockerfile              # scarb + stwo + snforge, versiones fijadas
├── cairo/                      # paquetes Scarb independientes
│   ├── fib_core/               # lib: fn fib(n: u32) -> felt252
│   ├── fib_contract/           # contrato Starknet + tests snforge
│   └── fib_exec/               # #[executable] que llama a fib_core
├── scripts/
│   ├── run_once.sh             # execute+prove+verify con medición, imprime 1 fila CSV
│   ├── sweep.sh                # corre los 3 barridos (llama a run_once.sh vía docker run)
│   ├── tamper.sh               # demo de prueba/output alterados
│   └── plot.py                 # CSV → gráficos
└── results/
    ├── raw/                    # CSV crudos por barrido
    └── figures/                # gráficos para el informe
```

## 7. Experimentos

Cada punto se repite **3 veces**. Se reporta media y desvío estándar.

Todas las corridas usan `--memory-swap` igual a `--memory` (sin swap). Si no, Docker deja usar swap hasta duplicar el límite y el contenedor se pone lento en vez de morir por OOM, lo que contamina E3.

| Barrido | Varía | Fijo | Pregunta que responde |
|---------|-------|------|-----------------------|
| E1 — Complejidad | n ∈ {10, 1.000, 10.000, 50.000, 100.000} (140 → 1M steps) | sin límites | ¿Cómo escalan prueba y verificación con los steps? |
| E2 — CPU | `--cpus` ∈ {4, 2, 1, 0.5} | n = 10.000 | ¿Cuánto paraleliza el prover? ¿Falla o solo tarda? |
| E3 — Memoria | `--memory` ∈ {16, 15, 14.5, 14, 13} GB | n = 10.000, CPU sin límite | ¿Cuál es el umbral de memoria donde la prueba no termina? |

n máximo = 100.000: con 16 GB en la VM es el mayor valor verificado que no muere por OOM.

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

> Dato preliminar (primer hito): fib(10) necesita ~14,2 GB de pico y fib(100.000) ~15,1 GB, con 7.000× más steps. Ver README.

## 8. Criterios de aceptación (Definition of Done)

- [ ] `docker build` produce la imagen con versiones fijadas.
- [ ] `snforge test` pasa (fib del contrato coincide con valores conocidos).
- [ ] `scarb execute` + `prove` + `verify` funciona para un n chico dentro del contenedor.
- [ ] `tamper.sh` muestra que una prueba alterada y un output alterado fallan la verificación.
- [ ] `run_once.sh` emite una fila CSV con todas las métricas de §7.
- [ ] E1, E2 y E3 completos en `results/raw/`.
- [ ] `plot.py` genera los gráficos del informe en `results/figures/`.
- [ ] README explica cómo reproducir todo en ≤ 5 comandos.

## 9. Tareas (en orden)

1. Elegir versión de Scarb con `prove`/`verify` y fijarla junto con Starknet Foundry.
2. Dockerfile con Scarb + Starknet Foundry.
3. Workspace Cairo: `fib_core` + `fib_exec`. Lograr execute → prove → verify con n chico. ← **primer hito pedido por el docente**
4. `fib_contract` + tests snforge.
5. `tamper.sh`.
6. `run_once.sh` con lectura de cgroups.
7. Calibrar rangos de n (que el n máximo tarde minutos, no horas) y el n fijo de E2/E3.
8. `sweep.sh` y correr E1, E2, E3.
9. `plot.py` y gráficos.
10. README.

## 10. Riesgos y preguntas abiertas

| Riesgo | Mitigación |
|--------|------------|
| **Docker en macOS:** macOS no tiene cgroups (es un feature del kernel Linux). Docker Desktop resuelve esto corriendo una VM Linux liviana, y los contenedores viven adentro de esa VM. Los límites `--cpus`/`--memory` se aplican como cgroups v2 dentro de la VM, pero la VM tiene su propio techo de CPU y RAM: si es menor que el límite pedido, el que manda es la VM y la medición no refleja el cgroup. | Configurar la VM (Docker Desktop → Settings → Resources) con más CPU y RAM que el máximo usado en los barridos, y documentarlo en el informe como limitación del entorno. |
| El prover necesita ~14 GB aun para programas mínimos; la Mac tiene 18 GB y la VM 16 GB, así que el margen para n grandes y para el barrido de memoria es chico. | Calibrar el n máximo para que no supere 16 GB. E3 barre límites en el rango ~13–16 GB. Si no alcanza, correr en una máquina con más RAM. |
| Probar n grandes puede tardar demasiado. | Calibración (tarea 7) antes de los barridos. |
| Arquitectura del host (Apple Silicon = ARM). | Documentar; los resultados son de ARM64. |

## 11. Reglas del repo

- No se hacen commits sin aprobación explícita del autor.
