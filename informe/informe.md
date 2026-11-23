<!--
Borrador del informe del TP Final. Se pega en la copia de la plantilla en Google Docs.
Estructura: la de la consigna (§3), en el mismo orden.
-->

# Portada

**Universidad Nacional de General Sarmiento**
Instituto de Industria — Licenciatura en Sistemas

**Trabajo Final Integrador — Sistemas Operativos y Redes II**

## Generación y verificación de pruebas STARK bajo límites de CPU y memoria impuestos con cgroups v2: un estudio experimental con Cairo y el prover Stwo en contenedores Docker

- Alumno: Santiago Galván — Legajo 38692907/2016
- Docente: Prof. Benjamín Chuquimango
- Materia: Sistemas Operativos y Redes II
- Segundo semestre de 2026
- Fecha de entrega: [COMPLETAR]

---

# 1. Resumen ejecutivo

Las redes de segunda capa de Ethereum que usan pruebas criptográficas, como Starknet, trasladan el costo de verificar transacciones a un proceso intensivo en recursos: la generación de pruebas de integridad. Este trabajo mide cómo ese proceso responde a la complejidad del programa probado y a los límites de procesador y memoria que el sistema operativo impone a un contenedor.

Se implementó un programa de Fibonacci en Cairo, un lenguaje diseñado para que cualquier ejecución pueda probarse, y se generaron y verificaron pruebas STARK (argumentos de conocimiento escalables y transparentes) con el prover Stwo dentro de contenedores Docker. Los límites se aplicaron con grupos de control versión 2 (cgroups v2) del kernel Linux, y cada medición registró tiempos, memoria pico, consumo de procesador y resultado de la verificación. Se hicieron tres barridos, con tres repeticiones: complejidad, límite de procesador y límite de memoria.

El tiempo de generación de la prueba resultó casi constante, entre 22 y 25 segundos, aun con 200 veces más pasos de ejecución, mientras que verificar tomó 0,12 segundos y la prueba pesó 11 megabytes en todos los casos. Limitar el procesador alargó el tiempo en proporción inversa a los núcleos disponibles, sin fallas. Limitar la memoria produjo un corte abrupto: en el caso medido, con 14 gibibytes o más la prueba se completó sin demoras, y con 13 el kernel terminó el proceso.

La contribución es un entorno reproducible y una caracterización cuantitativa del costo fijo del prover, útil para dimensionar su contenedor.

---

# Índice de contenidos

1. Resumen ejecutivo
2. Planteamiento del problema
3. Pregunta de investigación y objetivos
4. Marco teórico
5. Metodología y stack tecnológico
6. Análisis según capas del SO
7. Implementación y desarrollo
8. Resultados y análisis
9. Conclusiones y trabajo futuro
10. Referencias bibliográficas
11. Anexos

---

# 2. Planteamiento del problema

Ethereum es una red distribuida en la que cada nodo vuelve a ejecutar cada transacción para validar el estado. Ese diseño da garantías fuertes de integridad, pero limita la capacidad de toda la red a lo que puede procesar un nodo individual. Gudgeon et al. (2020) sistematizan las propuestas de "segunda capa" que buscan sortear ese límite moviendo la ejecución fuera de la cadena principal, y Thibault et al. (2022) muestran que, entre ellas, los *rollups* se consolidaron como la alternativa dominante: agrupan muchas transacciones fuera de la cadena y publican en Ethereum solo un resumen.

Dentro de los rollups, los llamados *ZK-rollups* o *validity rollups* acompañan cada lote con una prueba criptográfica de que fue ejecutado correctamente. Ethereum ya no re-ejecuta las transacciones: solo verifica la prueba, lo que es órdenes de magnitud más barato. Gogol et al. (2024) analizan un pico real de actividad de 2023, en el que más del 99 % del aumento de transacciones se debió a la emisión de inscripciones, y observan que las tarifas por transacción bajaron: el costo fijo de cada lote se repartió entre más transacciones. Starknet es un rollup de este tipo: sus programas se escriben en Cairo y sus pruebas son STARK (Goldberg et al., 2021).

El problema es que el costo no desaparece, sino que se traslada al *prover*, el proceso que genera la prueba. La literatura de benchmarking lo documenta como un cuello de botella de recursos. Sheybani et al. (2025) evalúan 25 frameworks de pruebas de conocimiento cero en un mismo equipo de 128 GB de RAM: para multiplicar dos matrices de 32 × 32, la máquina virtual RISC Zero, basada en STARK, tardó 57,3 s en generar la prueba y 0,06 s en verificarla, casi mil veces menos; algunos frameworks ni siquiera completaron las pruebas porque se quedaron sin memoria. Ernstberger et al. (2024) encuentran mejoras de hasta 40 % con hardware optimizado para memoria y de hasta 50 % con hardware optimizado para cómputo, según la herramienta: el recurso limitante cambia de un sistema a otro. Además, Sheybani et al. (2025) entregan sus entornos como contenedores Docker, lo que muestra que el contenedor es la unidad natural de despliegue de estos procesos.

Esto genera una pregunta práctica para quien opera la infraestructura: ¿cuántos recursos hay que asignarle al contenedor del prover, y qué pasa si se le asignan menos? En sistemas operativos Linux, esos recursos se asignan con *control groups* (cgroups), el mecanismo del kernel que usan Docker y Kubernetes para limitar CPU y memoria (Daichendt et al., 2023). Un límite demasiado alto desperdicia hardware caro; uno demasiado bajo puede alargar los tiempos o directamente impedir que la prueba termine.

Quienes sufren el problema son los operadores de provers (los equipos que corren la infraestructura de un rollup y, cada vez más, terceros que ofrecen generación de pruebas como servicio). Las consecuencias de dimensionar mal son concretas: costos de infraestructura innecesarios, demoras en la publicación de lotes en la cadena principal o pruebas que nunca se completan. Vale la pena estudiarlo porque los provers más recientes, como Stwo (Carmon et al., 2026), cambian el perfil de costo respecto de las generaciones anteriores, y hay poca evidencia publicada sobre cómo se comportan bajo límites de recursos impuestos por el sistema operativo.

---

# 3. Pregunta de investigación y objetivos

## 3.1 Pregunta de investigación

> ¿Cómo afectan la complejidad de ejecución de programas Cairo y las restricciones de CPU y memoria impuestas mediante cgroups v2 al tiempo de generación y verificación, al consumo de recursos y a la finalización exitosa de pruebas STARK válidas?

## 3.2 Objetivo general

Medir experimentalmente cómo la complejidad de un programa Cairo y los límites de CPU y memoria de un contenedor afectan la generación y verificación de pruebas STARK con el prover Stwo.

## 3.3 Objetivos específicos

**Tabla 1.** Objetivos específicos y sección del informe donde se cumple cada uno.

| # | Objetivo específico | Sección |
|---|---|---|
| O1 | Construir un entorno reproducible en Docker con Scarb y el prover Stwo, con la versión de Scarb fijada. | 7. Implementación |
| O2 | Implementar Fibonacci en Cairo como librería con tests, usada por un programa ejecutable probable. | 7. Implementación |
| O3 | Generar y verificar una prueba STARK real, y comprobar que una prueba o un resultado alterados no verifican. | 7. Implementación |
| O4 | Medir tiempo, memoria pico, CPU, tamaño de la prueba y finalización exitosa variando la complejidad, el límite de CPU y el límite de memoria. | 8. Resultados |
| O5 | Analizar los resultados en relación con el modelo "probar caro, verificar barato" y con los mecanismos de cgroups v2. | 8. Resultados y 9. Conclusiones |

*Fuente: elaboración propia.*

## 3.4 Hipótesis

- **H1.** El tiempo de generación de la prueba crece con la cantidad de pasos de ejecución, de forma sublineal en el rango medido, porque hay un costo fijo alto.
- **H2.** El tamaño de la prueba y el tiempo de verificación crecen mucho más lento que el tiempo de generación. Existe un tamaño de programa a partir del cual verificar es más barato que re-ejecutar.
- **H3.** Limitar la CPU aumenta el tiempo de generación pero no causa fallas.
- **H4.** Limitar la memoria por debajo de un umbral causa la terminación del proceso por falta de memoria. Ese umbral está dominado por un costo fijo del prover y crece poco con la complejidad.

---

# 4. Marco teórico

Esta sección analiza las referencias que fundamentan el trabajo en tres ejes: las pruebas STARK y su implementación actual, el contexto de escalabilidad en el que se usan, y los mecanismos del sistema operativo con los que se limitan los recursos. Para cada referencia se indica qué aporta y qué limitaciones tiene respecto de este trabajo.

## 4.1 Pruebas de integridad computacional: STARK

Una prueba de integridad computacional permite que una parte (el *prover*) convenza a otra (el *verificador*) de que un cómputo se ejecutó correctamente, sin que el verificador tenga que repetirlo. Ben-Sasson et al. (2018) presentan los STARK (*Scalable Transparent ARguments of Knowledge*), cuya característica central es que el tiempo de verificación crece de forma polilogarítmica con el tamaño del cómputo, mientras que el del prover crece de forma casi lineal. Además son *transparentes* (no requieren una configuración inicial de confianza) y se basan solo en funciones de hash, lo que los hace candidatos resistentes a ataques cuánticos.

El esquema funciona, a grandes rasgos, así: la ejecución se representa como una tabla (la *traza*) y la corrección de la ejecución se expresa como restricciones polinomiales sobre esa tabla, llamadas AIR (*Algebraic Intermediate Representation*). El prover se compromete con la traza mediante árboles de Merkle y demuestra, con el protocolo FRI, que los polinomios involucrados tienen grado bajo. El protocolo, interactivo en origen, se vuelve no interactivo con la transformación de Fiat–Shamir: los desafíos que enviaría el verificador se derivan de un hash de todo lo que el prover ya comprometió (el *transcript*).

*Aporte:* es el fundamento teórico de la propiedad que este trabajo mide empíricamente (H2). *Limitaciones:* es de 2018 y precede tanto a Cairo como a los provers actuales; sus cifras de rendimiento corresponden a otra implementación y otro hardware, por lo que no sirven para predecir los valores de Stwo.

## 4.2 Cairo: un lenguaje de propósito general para cómputo probable

Escribir restricciones AIR a mano para cada programa es impracticable. Goldberg et al. (2021) resuelven ese problema con Cairo: una arquitectura de CPU cuya ejecución se describe con una única AIR. En lugar de diseñar restricciones para cada cómputo, el desarrollador escribe un programa en Cairo, y la prueba demuestra que esa CPU ejecutó ese programa correctamente. Cairo usa una memoria de solo lectura no determinística (cada celda toma un único valor durante toda la ejecución), no tiene registros de propósito general y tiene un conjunto de instrucciones mínimo. Es Turing-completo, por lo que cualquier cómputo puede expresarse en él.

Este trabajo trata a Cairo como lo que los autores proponen: un lenguaje de propósito general para cómputo verificable. Starknet lo usa para sus contratos inteligentes, pero el mecanismo no depende de ellos, y por eso el programa estudiado es un cómputo simple (Fibonacci) cuyo costo se controla con un solo parámetro.

*Aporte:* define el modelo de ejecución y de costo que se mide (la cantidad de pasos de la CPU de Cairo). *Limitaciones:* el paper describe la versión original del lenguaje y supone un campo finito de más de 63 bits, mientras que Stwo trabaja sobre un campo de 31 bits; los detalles de la AIR cambiaron, aunque el modelo conceptual se mantiene.

## 4.3 Circle STARKs y el prover Stwo

Haböck et al. (2024) proponen los *Circle STARKs*: una construcción de STARK sobre la curva circular x² + y² = 1 definida sobre el primo de Mersenne p = 2³¹ − 1 (M31). La aritmética en M31 es muy eficiente en procesadores actuales porque los valores caben en 32 bits, y la construcción circular evita el requisito de los STARK tradicionales de que el campo tenga un subgrupo multiplicativo grande de orden potencia de dos. Los autores reportan en sus pruebas preliminares una mejora de 1,4 veces respecto de un STARK tradicional sobre otro primo pequeño.

Carmon et al. (2026) documentan S-two (Stwo), el prover de StarkWare construido sobre Circle STARKs y M31, que es el que usa este trabajo a través de la herramienta Scarb. El documento formaliza la seguridad de la versión de FRI sobre múltiples tablas que usa el prover.

*Aporte:* explica por qué Stwo es el prover representativo del estado del arte y da el marco para interpretar la estructura de la prueba (componentes, tablas, FRI). *Limitaciones:* ambos documentos se enfocan en la construcción criptográfica y en la seguridad; no caracterizan el consumo de memoria ni el comportamiento bajo recursos limitados, que es justamente lo que este trabajo aporta. Además, ambos son de autores vinculados a las empresas que desarrollan la tecnología.

## 4.4 Escalabilidad de blockchains: segunda capa y rollups

Gudgeon et al. (2020) sistematizan los protocolos de segunda capa (canales de pago y de estado, *commit-chains* y protocolos de delegación arbitrada) y analizan sus garantías de seguridad y sus supuestos. Thibault et al. (2022) actualizan ese panorama centrándose en los rollups, distinguen entre rollups optimistas (que asumen validez y permiten impugnar) y rollups de validez (que prueban cada lote), y discuten sus ventajas, desventajas y líneas de investigación abiertas.

*Aporte:* sitúan el problema: el prover existe porque los rollups de validez reemplazan la re-ejecución por la verificación de una prueba. *Limitaciones:* son trabajos de revisión; Gudgeon et al. (2020) es anterior a la adopción masiva de rollups, y ninguno de los dos cuantifica el costo de generar pruebas.

## 4.5 Rendimiento de sistemas de pruebas

Ernstberger et al. (2024) presentan zk-Bench, un marco de benchmarking para sistemas de pruebas que mide tiempo de ejecución y consumo de memoria, y que compara herramientas en distintos tipos de hardware. Uno de sus resultados es que el recurso limitante varía según la herramienta: algunas se benefician de máquinas optimizadas para cómputo y otras de máquinas optimizadas para memoria. Sheybani et al. (2025) evalúan 25 frameworks de pruebas de conocimiento cero con dos cargas de trabajo (SHA-256 y multiplicación de matrices) y publican los entornos como contenedores Docker.

*Aporte:* respaldan la metodología (medir tiempo y memoria por separado, en entornos contenedorizados y reproducibles) y la relevancia de la memoria como recurso crítico. *Limitaciones:* se centran mayormente en SNARK y frameworks de circuitos; ninguno evalúa Stwo ni el efecto de límites de recursos impuestos por el sistema operativo, sino que comparan herramientas sobre hardware fijo. Gogol et al. (2024) aportan datos de costos de rollups en producción, pero desde la perspectiva de las tarifas al usuario, no del costo de cómputo del prover.

## 4.6 Control de recursos en Linux: cgroups v2

Los *control groups* son el mecanismo del kernel Linux que agrupa procesos y les asigna, limita y contabiliza recursos como CPU, memoria y E/S. Daichendt et al. (2023) comparan la versión original (v1) con la versión 2 (v2), que reemplaza las múltiples jerarquías independientes de v1 por una jerarquía unificada montada en `/sys/fs/cgroup`, uniforma la nomenclatura de los archivos de control (por ejemplo, `memory.limit_in_bytes` pasa a ser `memory.max`) y prohíbe que haya procesos en nodos internos del árbol. Sus experimentos con contenedores LXC muestran que ambas versiones logran el mismo grado de aislamiento, pero v1 tiene latencias de cola mayores, lo que atribuyen a una implementación de v2 que ejecuta un 2,4 % menos de instrucciones. Por eso recomiendan v2.

La documentación del kernel (The Linux Kernel Documentation, s.f.) define los dos controladores que usa este trabajo:

- **Controlador `cpu`:** con `cpu.max` fija una cuota de tiempo de CPU por período (por defecto, 100 ms). Cuando el grupo agota la cuota, sus procesos se suspenden hasta el período siguiente (*throttling*). Las estadísticas quedan en `cpu.stat`.
- **Controlador `memory`:** con `memory.max` fija un límite duro. Si el grupo lo alcanza y el kernel no puede recuperar memoria, invoca al *OOM killer* (*Out Of Memory*), que termina un proceso del grupo con la señal SIGKILL. El evento queda registrado en `memory.events`, y el máximo alcanzado, en `memory.peak`.

Docker traduce las opciones `--cpus` y `--memory` a esos archivos (Docker Inc., s.f.).

*Aporte:* da el modelo de los dos mecanismos que se estudian y justifica el uso de v2. *Limitaciones:* el trabajo de Daichendt et al. (2023) es un artículo de seminario académico, se enfoca en latencia de red y no en cargas intensivas en CPU y memoria, y no estudia el comportamiento ante el agotamiento de memoria.

## 4.7 Síntesis

El marco teórico fundamenta el enfoque en tres pasos. Primero, la teoría de los STARK (Ben-Sasson et al., 2018) predice que verificar es mucho más barato que probar, y que el costo de probar crece con el tamaño de la traza; Cairo (Goldberg et al., 2021) permite controlar ese tamaño con un programa común. Segundo, los provers actuales como Stwo (Haböck et al., 2024; Carmon et al., 2026) cambiaron la aritmética y la estructura de las pruebas, y la literatura de benchmarking (Ernstberger et al., 2024; Sheybani et al., 2025) muestra que su costo en memoria no se puede deducir de la teoría, sino que hay que medirlo. Tercero, el entorno real de despliegue es un contenedor con límites de cgroups v2 (Daichendt et al., 2023), un aspecto que ninguno de los trabajos anteriores evalúa. Este trabajo cubre esa intersección: mide un prover del estado del arte bajo los mecanismos de control de recursos del sistema operativo.

---

# 5. Metodología y stack tecnológico

## 5.1 Enfoque metodológico


El trabajo es una **implementación real con diseño experimental**. Se construye un entorno reproducible, se valida que produce pruebas correctas, y luego se varía un factor por vez manteniendo los demás fijos (diseño de un factor por vez). Cada punto experimental se repite tres veces y se reporta la media y el desvío estándar. En total, los tres barridos suman 42 corridas (15 + 12 + 15), a las que se suman las tres del control de estabilidad.

**Tabla 2.** Diseño de los barridos experimentales.

| Barrido | Factor que varía | Valores | Fijo |
|---|---|---|---|
| E1, complejidad | n de Fibonacci | 10; 1.000; 10.000; 50.000; 100.000 | sin límites de cgroup |
| E2, CPU | `--cpus` | 4; 2; 1; 0,5 | n = 10.000, memoria sin límite |
| E3, memoria | `--memory` = `--memory-swap` | 16; 15; 14,5; 14; 13 GiB | n = 10.000, CPU sin límite |

*Fuente: elaboración propia.*

Los rangos se calibraron antes de los barridos: n = 100.000 es el mayor valor que entra en el entorno de desarrollo sin quedarse sin memoria, y el rango de E3 se eligió alrededor del pico de memoria observado (~14 GiB). En todas las corridas `--memory-swap` es igual a `--memory`, lo que deja al contenedor sin swap: de lo contrario, Docker permite usar swap hasta duplicar el límite y el proceso se vuelve lento en lugar de terminar, lo que mezclaría los dos efectos en E3.

### Métricas


**Tabla 3.** Métricas registradas por corrida y su fuente.

| Métrica | Fuente |
|---|---|
| `steps` (pasos de ejecución) | salida de `scarb execute --print-resource-usage` |
| `t_execute`, `t_prove`, `t_verify` (s) | reloj de pared alrededor de cada comando |
| `mem_peak` (bytes) | `/sys/fs/cgroup/memory.peak` |
| `cpu_usage_usec`, `nr_throttled`, `throttled_usec` | `/sys/fs/cgroup/cpu.stat` (diferencia antes y después de probar) |
| `oom_kill` | `/sys/fs/cgroup/memory.events` |
| `proof_size` (bytes) | tamaño del archivo de la prueba |
| `prove_rc` | código de salida del prover (0 = éxito; 137 = terminado por SIGKILL) |
| `verified` | resultado de `scarb verify` |

*Fuente: elaboración propia.*

Las métricas de cgroups se leen desde adentro del contenedor, que ve su propio cgroup como raíz. Cada medición corre en un contenedor nuevo, de modo que `memory.peak` arranca de cero y no arrastra el pico de una corrida anterior. Ese contador es el máximo de todo el contenedor durante la corrida (compilación, ejecución, prueba y verificación) e incluye la caché de páginas, así que no aísla la memoria del prover: se reporta como memoria pico del contenedor. La sección 8.3 discute qué etapa lleva al contenedor a su límite.

### Entorno de medición


Las mediciones se hicieron en una máquina virtual Ubuntu Server 24.04 (VMware Workstation) con 14 vCPU y 24 GiB de RAM fija, sobre un host Windows 11 con un procesador Intel Xeon W-11955M (8 núcleos, 16 hilos) y 32 GB de RAM. Docker Engine 29.10 corre de forma nativa en la VM, con cgroups v2 y el driver `systemd`. La arquitectura es x86-64 y el kernel es Linux 6.8 (`6.8.0-139-generic`).

El desarrollo se hizo en una Mac con Apple Silicon y Docker Desktop, pero ese entorno se descartó para medir tiempos: Docker Desktop corre los contenedores dentro de una VM Linux, y con 18 GB de RAM física y 16 GB asignados a esa VM, macOS terminaba usando swap, de modo que la misma corrida tardaba entre 13 y 54 segundos. Antes de los barridos en la VM Ubuntu se hizo un control de estabilidad con tres corridas de fib(10): la primera tardó 54 s (posiblemente porque VMware asignaba memoria a la VM por primera vez; sección 6.1) y las dos siguientes, ~24 s, con una diferencia de 1,6 % entre sí. Se hizo además una corrida de calentamiento no registrada.

### Validación


La validez de las pruebas se comprueba en cada corrida con `scarb verify`. Que el verificador rechaza pruebas alteradas se comprueba con un conjunto de alteraciones (sección 7.3). La validez de las mediciones se apoya en el control de estabilidad, en las tres repeticiones por punto (el desvío del tiempo de prueba fue menor al 2 % en casi todos los puntos) y en la lectura directa de las métricas del kernel.

---

## 5.2 Herramientas y justificación

**Tabla 4.** Herramientas utilizadas y justificación de su elección.

| Herramienta | Uso | Por qué se eligió sobre las alternativas |
|---|---|---|
| Cairo (lenguaje) | programa a probar | Es el lenguaje nativo de Starknet y fue diseñado para que cualquier programa sea probable con una única AIR. Las alternativas (zkVMs basadas en RISC-V) prueban ejecuciones de otra arquitectura y no se vinculan con Starknet. |
| Scarb 2.21.0 | compila, ejecuta, prueba y verifica | Es el gestor oficial de paquetes de Cairo e integra `execute`, `prove` y `verify` con Stwo en una sola herramienta con versión fijable. Evita compilar el prover por separado. |
| Stwo (vía Scarb) | prover y verificador | Es el prover actual de StarkWare (Circle STARKs sobre M31). Stone, el prover anterior, fue reemplazado y su uso habría medido una tecnología en retirada. |
| Fibonacci | carga de trabajo | Su cantidad de pasos crece linealmente con n (≈ 10 pasos por iteración), lo que permite controlar la complejidad con un solo parámetro y sin efectos de entrada/salida. |
| Docker Engine | contenedores | Es la forma estándar de desplegar provers y traduce `--cpus`/`--memory` directamente a cgroups v2. Una VM por medición sería mucho más pesada y no aislaría el efecto del cgroup. |
| cgroups v2 | límites y métricas | Es la versión actual del mecanismo, con jerarquía unificada y métricas como `memory.peak` que v1 no tiene (Daichendt et al., 2023). |
| Ubuntu Server 24.04 en VMware Workstation | entorno de medición | Docker Engine nativo sobre Linux, sin la VM intermedia de Docker Desktop. La versión sin entorno gráfico deja más memoria libre y menos procesos de fondo. |
| Bash, jq, bc | scripts de medición | Están disponibles en cualquier imagen Linux y leen los archivos de cgroups sin dependencias. |
| Python + matplotlib | gráficos | Corre en un contenedor descartable, así que no requiere instalar nada en el host. |
| Make | interfaz de comandos | Expone cada operación como un objetivo declarativo (`make prove`, `make sweep`) y documenta su uso con `make help`. |

*Fuente: elaboración propia.*

# 6. Análisis según capas del SO

El proyecto es de sistemas operativos: estudia cómo el kernel aplica límites de recursos a un proceso intensivo en CPU y memoria. Esta sección recorre las capas involucradas, de abajo hacia arriba, describe los mecanismos del sistema operativo que se usan en cada una y las políticas de seguridad aplicadas.

**Figura 1.** Capas del sistema involucradas en una medición.

[INSERTAR FIGURA: informe/figuras/capas.png]

*Fuente: elaboración propia.*

## 6.1 Hardware y virtualización

El hardware físico es un Xeon W-11955M de 8 núcleos con hyper-threading (16 hilos) y 32 GB de RAM. Sobre él, VMware Workstation presenta a Ubuntu 14 procesadores virtuales y 24 GiB de memoria. Esta capa introduce dos efectos que se observan en los resultados:

- Los 14 vCPU se mapean sobre 16 hilos de hardware que comparten 8 núcleos físicos, por lo que dos vCPU pueden competir por las mismas unidades de ejecución. Esto puede explicar en parte que el paralelismo efectivo del prover sea menor que el número de vCPU (sección 8.2).
- El hipervisor puede asignar memoria física a la VM de forma perezosa: la primera vez que la VM toca 14 GiB, tiene que conseguirlos en el host. Es una explicación posible de la primera corrida lenta del control de estabilidad, aunque no se verificó directamente.

*Seguridad:* la VM aísla el experimento del sistema operativo del host: un fallo dentro de la VM no compromete a Windows. El aislamiento no es total, porque la VM comparte con el host el procesador y la memoria física, y una carga intensa dentro de ella puede afectar el rendimiento del host.

## 6.2 Kernel: cgroups v2, namespaces y OOM killer

Es la capa central del trabajo; la VM corre Linux 6.8. Docker no implementa límites ni aislamiento: los delega en tres mecanismos del kernel Linux.

**Namespaces.** Al crear el contenedor, el runtime crea namespaces nuevos (PID, montaje, red, UTS, IPC) con la llamada al sistema `clone` o `unshare`. El proceso del prover ve un árbol de procesos propio, un sistema de archivos propio (la imagen más los directorios montados) y su propio cgroup como raíz de `/sys/fs/cgroup`. Esto último es lo que permite que los scripts lean las métricas desde adentro del contenedor sin ver las del resto del sistema.

**Controlador `cpu` de cgroups v2.** `--cpus=X` se traduce en `cpu.max = "X·100000 100000"`: una cuota de X·100 ms de CPU cada 100 ms. El planificador lleva la cuenta del tiempo de CPU que consumen todos los hilos del grupo; cuando se agota la cuota, deja de planificarlos hasta el período siguiente. Este mecanismo se sigue llamando *CFS bandwidth control*, aunque desde Linux 6.6 el planificador por defecto es EEVDF. Las métricas `nr_throttled` (cantidad de períodos en que el grupo fue frenado) y `throttled_usec` (tiempo total frenado) en `cpu.stat` permiten observar el mecanismo directamente.

**Controlador `memory` de cgroups v2.** `--memory=M` se traduce en `memory.max = M`, y `--memory-swap=M` deja `memory.swap.max` en cero. Cada página que el proceso reserva se carga al cgroup. Cuando el uso se acerca al límite, el kernel primero intenta recuperar memoria del propio grupo (caché de páginas); si no puede, invoca al OOM killer acotado a ese cgroup, que elige un proceso del grupo y le envía SIGKILL. El proceso no puede capturar esa señal ni liberar memoria para evitarla. El kernel incrementa el contador `oom_kill` en `memory.events`, y el shell informa el código de salida 137 (128 + 9, el número de SIGKILL).

**Diferencia de política entre ambos controladores.** El tiempo de CPU es un recurso *compresible*: si se da menos, el proceso tarda más pero sigue funcionando. La memoria es *incompresible*: un proceso no puede seguir sin la memoria que ya necesita, y sin swap la única respuesta del kernel es terminarlo. Esta diferencia de diseño del kernel es la que explica la diferencia cualitativa entre los resultados de E2 y E3.

*Seguridad:* los límites de cgroups funcionan como mitigación de denegación de servicio. Un prover que consume 15 GiB sin límite podría agotar la memoria de la VM y provocar que el OOM killer global termine otros procesos del sistema; con `memory.max`, el daño queda confinado al contenedor. Los namespaces impiden que el proceso del contenedor vea o envíe señales a procesos del host.

## 6.3 Servicios del sistema: Docker Engine, containerd, runc y systemd

Cuando se ejecuta `docker run`, el cliente le pide al demonio `dockerd` que cree el contenedor. `dockerd` delega en `containerd`, que a su vez invoca a `runc`, el runtime de bajo nivel que efectivamente hace las llamadas al sistema: crea los namespaces, configura los montajes y escribe los límites en los archivos de cgroups. Con el driver `systemd`, el cgroup del contenedor lo administra systemd como una unidad *scope* (`docker-<id>.scope`) dentro de `system.slice`, de modo que systemd sigue siendo el único dueño de la jerarquía de cgroups, como recomienda la documentación del kernel.

*Seguridad:* los scripts de medición se montan como solo lectura (`:ro`), de modo que el proceso medido no puede alterar el código que lo mide. Una limitación es que el contenedor corre como usuario root dentro de su namespace y con acceso a la red; para este experimento no hace falta red, y una mejora sería ejecutarlo con `--network none` y un usuario no privilegiado.

## 6.4 Aplicaciones: Scarb, la VM de Cairo y Stwo

En el espacio de usuario corren tres componentes, todos invocados a través de Scarb:

1. **La VM de Cairo** (`scarb execute`) ejecuta el programa con un *bootloader*, que es un programa Cairo que carga y ejecuta el programa del usuario y escribe en la salida pública el hash del programa y su resultado. Produce la traza de ejecución y la entrada del prover. Es un proceso de un solo hilo y liviano.
2. **El prover Stwo** (`scarb prove`) es el proceso que se estudia. Es multihilo: reparte el trabajo (interpolación de polinomios, construcción de árboles de Merkle, FRI) entre hilos de trabajo. Es el que concentra el uso de CPU y memoria.
3. **El verificador** (`scarb verify`) recorre la prueba, recalcula los desafíos de Fiat–Shamir y comprueba las consultas. Es de un solo hilo y muy liviano.

*Seguridad:* en esta capa la política de seguridad es criptográfica: la prueba garantiza la integridad del cómputo frente a un prover deshonesto (sección 7.3). En el Dockerfile está fijada la versión de Scarb (2.21.0), que incluye el prover y el verificador; la imagen base y los paquetes del sistema no tienen versión fija. Además, el binario de Scarb se descarga de GitHub por HTTPS sin verificar su suma de comprobación, lo que deja abierto un riesgo de cadena de suministro.

---

# 7. Implementación y desarrollo

## 7.1 Diseño de la solución


**Figura 2.** Arquitectura del entorno experimental.

[INSERTAR FIGURA: informe/figuras/arquitectura.png]

*Fuente: elaboración propia.*

El host (la VM Ubuntu) contiene el repositorio y los scripts de orquestación. Por cada medición, `sweep.sh` lanza un contenedor nuevo de la imagen `stark-proving:dev` con los límites del punto experimental, monta el código Cairo y los scripts, y el contenedor ejecuta `run_once.sh`, que corre ejecución, prueba y verificación, lee las métricas de su cgroup e imprime una fila CSV. `sweep.sh` agrega esa fila al archivo del barrido. Al terminar, `plot.py` convierte los CSV en gráficos.

---

El código completo está en el repositorio https://github.com/dubzn/stark-proving-cgroups y en el Anexo A. Todas las operaciones se exponen como objetivos de `make`.

**Tabla 5.** Comandos del proyecto.

| Comando | Qué hace |
|---|---|
| `make build` | Construye la imagen Docker. |
| `make test` | Corre los tests de la librería. |
| `make run N=10` | Ejecuta fib(10) sin generar prueba. |
| `make prove N=10` | Ejecuta fib(10), genera la prueba STARK y la verifica. |
| `make tamper` | Verifica pruebas alteradas (prueba de rechazo de alteraciones). |
| `make measure N=10000` | Una corrida medida; imprime una fila CSV. |
| `make sweep EXP=all` | Corre los barridos E1, E2 y E3. |
| `make plots` | Genera los gráficos a partir de los CSV. |

*Fuente: elaboración propia.*

## 7.2 Implementación por componente

### Imagen Docker

La imagen parte de `debian:bookworm-slim` e instala Scarb 2.21.0 descargando el binario oficial para la arquitectura del host (x86-64 o ARM64), lo que permite usar la misma definición en la Mac de desarrollo y en la VM de medición. Scarb incluye los subcomandos `execute`, `prove` y `verify`, y este último par integra el prover y el verificador Stwo. Se agregan `jq` y `bc`, que usan los scripts.

```dockerfile
FROM debian:bookworm-slim
ARG SCARB_VERSION=2.21.0
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git jq bc
RUN ... curl -fsSL ".../scarb-v${SCARB_VERSION}-${TRIPLE}.tar.gz" | tar xz ...
WORKDIR /work
```

### Programa Cairo

El código Cairo se divide en dos paquetes de Scarb. `fib_core` es una librería con la función y sus tests:

```cairo
pub fn fib(n: u32) -> felt252 {
    let mut a: felt252 = 0;
    let mut b: felt252 = 1;
    let mut i: u32 = 0;
    while i != n {
        let next = a + b;
        a = b;
        b = next;
        i += 1;
    }
    a
}
```

Los cálculos se hacen sobre `felt252`, el tipo nativo de Cairo (un elemento de un campo finito de 252 bits), por lo que para n grandes el resultado se reduce módulo el primo del campo. No es un problema para el experimento: lo que importa es que la cantidad de pasos crece linealmente con n. Los tests comparan contra valores conocidos (fib(10) = 55, fib(20) = 6765) y pasan con `make test`.

`fib_exec` es el programa que se prueba. Declara un punto de entrada `#[executable]` y desactiva el cálculo de gas (`enable-gas = false`), que es un requisito de los ejecutables:

```cairo
#[executable]
fn main(n: u32) -> felt252 {
    fib_core::fib(n)
}
```

La entrada `n` y el resultado son públicos: la prueba afirma "este programa, con esta entrada, devolvió este valor".

### Ejecución, prueba y verificación

`make prove N=10` corre el ciclo completo. La salida muestra las tres etapas:

```
   Proving fib_exec
Saving proof to: target/execute/fib_exec/execution1/proof/proof.json
   Verifying fib_exec
    Verified proof successfully
-rw-r--r-- 1 root root 11M ... proof.json
```

Un hallazgo de la implementación es que `scarb prove` solo acepta ejecuciones con el *bootloader*. El bootloader agrega un costo fijo de ejecución: fib(10) tiene 140 pasos ejecutado directamente y 5.172 con el bootloader. A partir de ahí, cada iteración suma 10 pasos (fib(100.000) tiene 1.005.072 pasos).

La prueba es un archivo JSON de ~11,3 MB (1,4 MB comprimido). Su campo `claim.public_data.public_memory.output` contiene la salida pública que escribe el bootloader: la cantidad de tareas (1), el tamaño de la salida de la tarea, el hash del programa y el resultado (55). La configuración de la prueba usa 70 consultas FRI, un factor de expansión de 2 y 26 bits de proof-of-work.

### Medición de una corrida: `run_once.sh`

El script corre dentro del contenedor. Compila fuera de la ventana de medición y luego mide cada etapa por separado. Para aislar el consumo de CPU del prover, lee `cpu.stat` antes y después de probar y registra la diferencia:

```bash
cpu0=$(cpu_stat usage_usec); thr0=$(cpu_stat nr_throttled)
t0=$(now)
scarb prove --execution-id 1 -q
prove_rc=$?
t_prove=$(elapsed "$t0")
cpu_usage_usec=$(( $(cpu_stat usage_usec) - cpu0 ))
```

Al final lee el pico de memoria, los eventos OOM y los límites efectivos del cgroup:

```bash
mem_peak=$(cat /sys/fs/cgroup/memory.peak)
oom_kill=$(awk '$1 == "oom_kill" { print $2 }' /sys/fs/cgroup/memory.events)
cpu_max=$(tr ' ' '/' < /sys/fs/cgroup/cpu.max)
mem_max=$(cat /sys/fs/cgroup/memory.max)
```

Leer los límites desde el cgroup, en lugar de copiarlos de los parámetros, sirve como verificación de que Docker los aplicó. Si el prover muere por OOM, el script no intenta verificar y registra `verified=false` y el código 137. Un ejemplo de salida de `make measure N=10000`:

```
n,steps,cpu_max,mem_max,exec_rc,prove_rc,verified,t_execute,t_prove,...
10000,105072,max/100000,max,0,0,true,.22,22.08,...
```

### Barridos: `sweep.sh`

`sweep.sh` corre en el host y lanza un contenedor por medición. La función central es:

```bash
run() {
  local csv="$1" n="$2"; shift 2
  docker run --rm "$@" \
    -v "$ROOT/cairo":/work -v "$ROOT/scripts":/scripts:ro \
    "$IMAGE" bash /scripts/run_once.sh "$n" | tee -a "$csv"
}
```

Los argumentos extra son los límites del punto: nada en E1, `--cpus=$c` en E2 y `--memory=$m --memory-swap=$m` en E3. Con tres repeticiones, los tres barridos suman 42 corridas y tardan alrededor de 45 minutos, dominados por E2 con 0,5 CPU (~4,5 minutos por corrida).

## 7.3 Pruebas y verificación

La verificación del sistema se hizo en tres niveles: tests unitarios de la librería, verificación de cada prueba generada y un ensayo de rechazo de pruebas alteradas.

### Tests unitarios

`make test` corre los tests de `fib_core`, que comparan la función contra valores conocidos:

```
running 1 test
test fib_core::tests::known_values ... ok
test result: ok. 1 passed; 0 failed; 0 ignored; 0 filtered out;
```

### Verificación de cada prueba

Cada corrida de los barridos verifica la prueba que generó con `scarb verify` y registra el resultado en la columna `verified`. De las 42 corridas de los barridos, las 39 que terminaron (todas menos las tres de E3 con 13 GiB) produjeron pruebas que verifican, igual que las tres del control de estabilidad.

### Rechazo de pruebas alteradas: `tamper.sh`

Para comprobar que el verificador efectivamente rechaza pruebas falsas, `tamper.sh` toma una prueba válida de fib(10), genera copias con una alteración cada una y verifica todas. Las alteraciones se hacen con `jq` sobre el JSON:

```bash
OUT='.claim.public_data.public_memory.output'
CASES=(
  "original|OK|"
  "re-serializada con jq, sin cambios|OK|."
  "output alterado (fib(n) + 1)|FAIL|$OUT[-1][1][0] += 1"
  "hash del programa alterado|FAIL|$OUT[2][1][0] |= (. + 1) % 4294967296"
  "prueba alterada (1 byte de un commitment)|FAIL|.stark_proof.commitments[0][0] |= (. + 1) % 256"
  "prueba alterada (1 valor consultado)|FAIL|.stark_proof.queried_values[0][0][0] |= (. + 1) % 2147483647"
)
```

**Tabla 6.** Resultado de `make tamper`.

| Caso | Esperado | Obtenido | Motivo informado por el verificador |
|---|---|---|---|
| Original | OK | OK | |
| Re-serializada con jq, sin cambios | OK | OK | (control) |
| Resultado alterado (55 → 56) | FAIL | FAIL | Proof of work verification failed |
| Hash del programa alterado | FAIL | FAIL | Proof of work verification failed |
| 1 byte de un commitment | FAIL | FAIL | Proof of work verification failed |
| 1 valor consultado | FAIL | FAIL | Root mismatch |

*Fuente: elaboración propia.*

El caso de control descarta que las fallas se deban a la manipulación del archivo. Los motivos de rechazo coinciden con la teoría de la sección 4.1. La salida pública, el hash del programa y los commitments forman parte del transcript de Fiat–Shamir. Cambiar cualquiera de ellos cambia los desafíos que el verificador deriva del hash, y el *nonce* de proof-of-work que encontró el prover (que debía producir 26 bits en cero con el transcript original) ya no es válido; el rechazo ocurre en el primer control. Los valores consultados, en cambio, se leen después de ese paso, y los detecta la verificación de Merkle: el valor alterado ya no reproduce la raíz comprometida. En términos del caso de uso, en los casos probados un prover no logra afirmar que fib(10) = 56 ni presentar la prueba de un programa como si fuera de otro. Estos ensayos muestran que el verificador rechaza las alteraciones probadas; no son una demostración general de seguridad, que se apoya en el análisis criptográfico del protocolo (Carmon et al., 2026).

---

# 8. Resultados y análisis

Todos los valores son medias de tres repeticiones. Los datos crudos están en el Anexo B.

## 8.1 E1: complejidad

**Tabla 7.** Resultados de E1 (sin límites de cgroup).

| n | Pasos | t_prove (s) | t_execute (s) | t_verify (s) | Memoria pico (GiB) | Tamaño de la prueba (MB) |
|---|---|---|---|---|---|---|
| 10 | 5.172 | 24,2 ± 0,1 | 0,15 | 0,17 | 13,8 | 11,3 |
| 1.000 | 15.072 | 21,9 ± 0,4 | 0,18 | 0,13 | 13,9 | 11,3 |
| 10.000 | 105.072 | 22,2 ± 0,3 | 0,23 | 0,12 | 14,0 | 11,3 |
| 50.000 | 505.072 | 23,4 ± 0,2 | 0,52 | 0,14 | 14,3 | 11,3 |
| 100.000 | 1.005.072 | 25,5 ± 0,3 | 0,95 | 0,12 | 15,0 | 11,2 |

*Fuente: elaboración propia.*

**Figura 3.** Tiempo de generación de la prueba según la complejidad.

[INSERTAR FIGURA: results/figures/e1_prove_time.png]

*Fuente: elaboración propia.*

**H1 se confirma parcialmente.** Se confirma el costo fijo alto y el crecimiento sublineal: con 194 veces más pasos, el tiempo de prueba aumenta un 5 %. No se confirma que el tiempo crezca siempre con los pasos, porque fib(10) tarda más que fib(1.000) (ver abajo). En el rango medido el costo parece dominado por un componente fijo. La estructura de la prueba sugiere por qué: además de los componentes cuya cantidad de filas depende de la ejecución (en fib(10), el mayor tiene 2¹² filas), la prueba incluye decenas de tablas de búsqueda preprocesadas cuyo tamaño está dado por el rango de valores que cubren y no por el programa (por ejemplo, `range_check_20` cubre 2²⁰ valores). Para un programa chico, esas tablas son la mayor parte del trabajo.

Se observa una anomalía: fib(10) tarda más que fib(1.000) (24,2 s contra 21,9 s) y consume más CPU (288 s contra 255 s), de forma consistente en las tres repeticiones. Con los datos disponibles no se puede determinar la causa; una hipótesis es que la distribución de filas entre componentes, que depende del programa, cambia el relleno de las tablas a potencias de dos.

**Figura 4.** Tiempo de verificar la prueba comparado con el de re-ejecutar el programa.

[INSERTAR FIGURA: results/figures/e1_verify_vs_execute.png]

*Fuente: elaboración propia.*

**H2 se confirma en el rango medido.** El tamaño de la prueba es prácticamente constante (11,2–11,3 MB) y el tiempo de verificación también (~0,12 s). El tiempo de re-ejecutar crece con n: es similar al de verificar para n = 10, ya es mayor desde n = 1.000 y es 8 veces mayor para n = 100.000. Hay que notar que ambos tiempos incluyen el arranque de Scarb, del orden de una décima de segundo. Para este programa y en el rango evaluado, verificar costó lo mismo con cualquier n, mientras que re-ejecutar creció con él, lo que es consistente con el modelo de los rollups. Con estos datos no se puede afirmar cómo crecen el tamaño y la verificación fuera de ese rango.

**Figura 5.** Memoria pico del contenedor según la complejidad.

[INSERTAR FIGURA: results/figures/e1_memory_peak.png]

*Fuente: elaboración propia.*

La memoria pico del contenedor parte de 13,8 GiB para el programa mínimo y llega a 15,0 GiB para el más grande: un 9 % más con 194 veces más pasos. Es un indicio a favor de la segunda parte de H4 (el piso de memoria es mayormente un costo fijo), aunque indirecto: sin límite, `memory.peak` también cuenta caché de páginas que el kernel podría recuperar, por lo que es una cota superior de la memoria que la corrida necesita.

## 8.2 E2: límite de CPU

**Tabla 8.** Resultados de E2 (n = 10.000).

| `--cpus` | t_prove (s) | Tiempo de CPU (s) | Paralelismo efectivo | Tiempo frenado (s) | Memoria pico (GiB) |
|---|---|---|---|---|---|
| sin límite (14 vCPU) | 22,2 | 255,6 | 11,5 | 0 | 14,0 |
| 4 | 38,5 ± 0,2 | 141,7 | 3,7 | 0,12 | 13,8 |
| 2 | 70,3 ± 1,6 | 135,1 | 1,9 | 0,13 | 13,6 |
| 1 | 141,5 ± 5,9 | 141,4 | 1,0 | 0,06 | 13,7 |
| 0,5 | 267,6 ± 1,8 | 133,8 | 0,5 | 133,8 | 13,6 |

*Fuente: elaboración propia. El paralelismo efectivo es el tiempo de CPU dividido por el tiempo de pared. La fila sin límite proviene de E1.*

**Figura 6.** Tiempo de prueba según el límite de CPU, en escala logarítmica.

[INSERTAR FIGURA: results/figures/e2_cpu_limit.png]

*Fuente: elaboración propia.*

**H3 se confirma.** El tiempo escala casi exactamente como la inversa del límite (Figura 6), ninguna corrida falló y la memoria no cambió. Limitar la CPU, un recurso compresible, solo alarga el trabajo.

El resultado más interesante está en el tiempo frenado. Con 4, 2 y 1 CPU, el grupo casi no fue frenado (menos de 0,2 s en total). Esto es consistente con que el prover no haya lanzado 14 hilos para competir por la cuota, sino tantos como la cuota permite. La biblioteca estándar de Rust, en la que está escrito Stwo, calcula el paralelismo disponible teniendo en cuenta la cuota de `cpu.max` del cgroup (The Rust Project Developers, s.f.), y las bibliotecas de paralelismo suelen usar ese valor por defecto. No se contaron los hilos del prover, así que esta explicación es una inferencia a partir del throttling. Con 0,5 CPU, aun un único hilo demanda más que la cuota, y el cgroup frena al grupo en cada uno de los ~2.680 períodos de 100 ms que dura la prueba. El tiempo frenado (133,8 s) es exactamente la mitad del tiempo de pared, que es lo que predice el mecanismo de cuota.

También se observa que, sin límite, el prover consume 255 s de CPU, contra ~138 s cuando se limita. Usar 14 vCPU acelera la prueba 6,4 veces respecto de 1 CPU, pero a costa de 1,8 veces más trabajo total. Parte de esa pérdida puede deberse a la capa de hardware (14 vCPU sobre 8 núcleos físicos con hyper-threading, sección 6.1) y parte al costo de coordinar hilos.

## 8.3 E3: límite de memoria

**Tabla 9.** Resultados de E3 (n = 10.000, sin swap).

| Límite (GiB) | Resultado | t_prove (s) | Memoria pico (GiB) | `oom_kill` |
|---|---|---|---|---|
| 16 | 3/3 verifican | 21,9 | 13,9 | 0 |
| 15 | 3/3 verifican | 21,9 | 14,0 | 0 |
| 14,5 | 3/3 verifican | 21,9 | 14,0 | 0 |
| 14 | 3/3 verifican | 21,8 | 13,9 | 0 |
| 13 | 3/3 terminadas por OOM (exit 137) | 17,3 (hasta la terminación) | 13,0 | 1 |

*Fuente: elaboración propia.*

**Figura 7.** Memoria pico y resultado según el límite de memoria.

[INSERTAR FIGURA: results/figures/e3_memory_limit.png]

*Fuente: elaboración propia.*

**H4 se confirma parcialmente.** La primera parte se confirma para n = 10.000: con 14 GiB o más, las tres repeticiones de cada límite terminaron y verificaron; con 13 GiB, el kernel terminó el proceso en las tres. El umbral está entre 13 y 14 GiB. La segunda parte (que el umbral crece poco con la complejidad) no se midió directamente, porque E3 usa un solo valor de n: solo la sugiere el pico de memoria de E1.

En los límites probados no se observó degradación: con 14 GiB, a solo 0,1 GiB del pico, la prueba tarda lo mismo que sin límite. Entre 13 y 14 GiB no se midió, así que no se puede descartar una zona intermedia, aunque hay dos razones para esperar un corte abrupto. Primero, sin swap el kernel no tiene dónde mover la memoria anónima del prover. Segundo, la memoria pico no cambia al ajustar el límite (13,9–14,0 GiB en todos los casos exitosos), lo que indica que casi toda es memoria de trabajo y no caché recuperable.

En las corridas con 13 GiB la ejecución del programa terminó bien y el proceso murió durante `scarb prove` (código 137), a los ~17 s de una prueba de ~22 s. Esto identifica a la etapa de prueba como la que lleva al contenedor a su límite, pero no demuestra que toda la memoria medida sea exclusiva del prover ni indica en qué momento se alcanza el pico de una corrida exitosa.

Que E2 y E3 den resultados cualitativamente distintos no es un detalle del prover, sino del diseño del kernel descripto en la sección 6: el límite de CPU se aplica frenando, y el de memoria, terminando.

## 8.4 Comparación con los objetivos

**Tabla 10.** Cumplimiento de los objetivos específicos.

| Objetivo específico | Resultado obtenido | Estado |
|---|---|---|
| O1. Entorno reproducible en Docker con Scarb y Stwo | Imagen con la versión de Scarb fijada que funciona en x86-64 y ARM64; todas las operaciones se exponen con `make`. | Cumplido |
| O2. Fibonacci en Cairo como librería con tests, usada por un ejecutable | `fib_core` con tests que pasan y `fib_exec` como programa `#[executable]`. | Cumplido |
| O3. Generar y verificar una prueba, y mostrar que una alterada no verifica | Pruebas generadas y verificadas en todas las corridas exitosas; las 4 alteraciones de `tamper.sh` son rechazadas. | Cumplido |
| O4. Medir tiempo, memoria, CPU, tamaño y finalización variando n, CPU y memoria | 42 corridas en tres barridos con tres repeticiones (39 completas y 3 terminadas por OOM, el resultado que se buscaba), más 3 de control; métricas leídas del cgroup. | Cumplido |
| O5. Analizar los resultados respecto del modelo de rollup y de cgroups v2 | Las cuatro hipótesis se contrastan: H3 se confirma, H2 se confirma en el rango medido, y H1 y H4 se confirman parcialmente. Los resultados se explican con el diseño de los controladores de cgroups (secciones 8.1–8.3). | Cumplido |

*Fuente: elaboración propia.*

## 8.5 Limitaciones identificadas

- **Hardware y plataforma únicos.** Los resultados son de una sola máquina x86-64 virtualizada. Los valores absolutos cambiarían con otro procesador; la forma de las curvas debería mantenerse. Como verificación parcial, la prueba de ejemplo generada en x86-64 verifica también en ARM64.
- **Alcance de E3.** El umbral se ubicó entre 13 y 14 GiB para un solo valor de n, y no se refinó.
- **Memoria por contenedor, no por proceso.** `memory.peak` es el máximo de todo el contenedor e incluye caché de páginas. E3 indica que la etapa de prueba es la que alcanza el límite, pero no se midió la memoria de cada proceso por separado ni su evolución en el tiempo.
- **Hilos del prover.** La adaptación del prover a la cuota de CPU se infiere del throttling; no se contaron sus hilos.
- **Rango de n.** El rango está acotado por la memoria del entorno de desarrollo. Con 1 millón de pasos el costo todavía está dominado por el componente fijo, por lo que no se observó el régimen en el que domina el componente variable.
- **Un solo programa.** Fibonacci usa pocas instrucciones y casi ningún *builtin*. Un programa que use hashes o comprobaciones de rango tendría otra distribución entre componentes.
- **Medición de tiempos de verificación y ejecución.** Incluyen el arranque de Scarb; para comparar con más precisión habría que medir dentro del proceso.

## 8.6 Propuestas de mejora y trabajo futuro

Con el prover anterior de StarkWare (Stone), que trabaja sobre un campo de 252 bits, cabría esperar otros valores absolutos y otra proporción entre costo fijo y variable; precisamente por eso no se usó, ya que habría caracterizado una tecnología reemplazada. Con swap habilitado, E3 habría mostrado una zona de degradación en lugar de un corte, a cambio de mezclar los efectos de memoria y de E/S de disco. Con Docker Desktop en macOS, la VM intermedia habría impuesto su propio techo de memoria, y los tiempos no habrían sido confiables, como se comprobó durante el desarrollo.

**Mejora concreta propuesta: refinar el umbral de memoria y medirlo en función de n.** Repetir E3 con pasos de 0,25 GiB entre 13 y 14 GiB, y para varios valores de n. Esto permitiría ajustar un modelo "memoria mínima = piso fijo + pendiente × pasos" y dar una regla de dimensionamiento concreta. Se fundamenta en que la Tabla 7 sugiere una pendiente de ~1,2 GiB por millón de pasos, que con un solo punto de E3 no se puede confirmar.

---

# 9. Conclusiones y trabajo futuro

## 9.1 Conclusiones

Respecto de la pregunta de investigación, los resultados permiten responder por separado a cada factor:

- **Complejidad.** En el rango estudiado (5 mil a 1 millón de pasos), la complejidad del programa afectó poco al prover: el tiempo de generación varió entre 22 y 25 s, sin crecer de forma monótona, y la memoria pico del contenedor entre 13,8 y 15,0 GiB. La prueba pesó siempre ~11 MB y se verificó en ~0,12 s, mientras que re-ejecutar creció con el programa. En ese rango se cumple el principio "probar caro, verificar barato", con un costo de probar dominado por un componente fijo.
- **Límite de CPU.** El tiempo de generación escala como la inversa de la cuota y la prueba siempre termina. El comportamiento es consistente con un prover que adapta su paralelismo a la cuota del cgroup: casi no sufrió throttling, salvo con cuotas menores a una CPU.
- **Límite de memoria.** Para n = 10.000, en el entorno y la configuración evaluados, las tres corridas con 14 GiB terminaron correctamente y las tres con 13 GiB fueron terminadas por el OOM killer. En los límites probados no hubo degradación gradual: la prueba terminó sin demoras o no terminó. Como el pico crece con n (15,0 GiB para n = 100.000), ese umbral no es universal: depende del programa.

La consecuencia práctica para quien dimensiona la infraestructura es que la memoria del contenedor del prover tiene un piso alto que, en el rango medido, depende poco del tamaño del programa: hay que asignar al menos ese piso, con margen para los programas más grandes. La CPU, en cambio, se puede ajustar libremente según el tiempo de respuesta que se necesite, porque el prover la usa de forma proporcional. Además, en el rango medido el costo de una prueba casi no dependió del tamaño del programa, lo que sugiere que agrupar más trabajo en una misma prueba es más eficiente que generar muchas pruebas chicas, que es lo que hacen los rollups al agrupar transacciones.

## 9.2 Trabajo futuro

Además de la mejora propuesta en la sección 8.6, quedan abiertas estas líneas:

- **Explorar el régimen dominado por el componente variable**, con programas de decenas de millones de pasos, en una máquina con más memoria.
- **Otros programas**, que usen *builtins* (hashes, comprobaciones de rango), para ver cómo cambia la distribución entre componentes.
- **Contratos de Starknet y una red local**, para conectar estas mediciones con el flujo completo de un rollup.
- **Comparación entre provers (Stone y Stwo) y entre arquitecturas (x86-64 y ARM64).**
- **Endurecimiento del contenedor:** ejecución sin red, con usuario no privilegiado y con verificación de las sumas de comprobación de los binarios.

---

# 10. Referencias bibliográficas

Ben-Sasson, E., Bentov, I., Horesh, Y., & Riabzev, M. (2018). *Scalable, transparent, and post-quantum secure computational integrity* (Cryptology ePrint Archive, Paper 2018/046). https://eprint.iacr.org/2018/046

Carmon, D., Goldberg, L., Haböck, U., Lerer, L., Lesokhin, I., Papini, S., & Samocha, S. (2026). *S-two whitepaper* (Cryptology ePrint Archive, Paper 2026/532). https://eprint.iacr.org/2026/532

Daichendt, A., Wiedner, F., & Andre, J. (2023). LXC container between cgroups v1 and v2: A performance evaluation. En *Proceedings of the Seminar Innovative Internet Technologies and Mobile Communications (IITM), Summer Semester 2023* (pp. 13–17). Technical University of Munich. https://doi.org/10.2313/NET-2023-11-1_03

Docker Inc. (s.f.). *Resource constraints*. Docker Docs. Recuperado el 22 de noviembre de 2026 de https://docs.docker.com/engine/containers/resource_constraints/

Ernstberger, J., Chaliasos, S., Kadianakis, G., Steinhorst, S., Jovanovic, P., Gervais, A., Livshits, B., & Orrù, M. (2024). zk-Bench: A toolset for comparative evaluation and performance benchmarking of SNARKs. En C. Galdi & D. H. Phan (Eds.), *Security and Cryptography for Networks (SCN 2024)* (pp. 46–72). Springer. https://doi.org/10.1007/978-3-031-71070-4_3

Gogol, K., Messias, J., Silva, M. I., & Livshits, B. (2024). *The writing is on the wall: Analyzing the boom of inscriptions and its impact on rollup performance and cost efficiency* (arXiv:2404.11189). arXiv. https://arxiv.org/abs/2404.11189

Goldberg, L., Papini, S., & Riabzev, M. (2021). *Cairo – a Turing-complete STARK-friendly CPU architecture* (Cryptology ePrint Archive, Paper 2021/1063). https://eprint.iacr.org/2021/1063

Gudgeon, L., Moreno-Sanchez, P., Roos, S., McCorry, P., & Gervais, A. (2020). SoK: Layer-two blockchain protocols. En J. Bonneau & N. Heninger (Eds.), *Financial Cryptography and Data Security (FC 2020)* (Lecture Notes in Computer Science, Vol. 12059, pp. 201–226). Springer. https://doi.org/10.1007/978-3-030-51280-4_12

Haböck, U., Levit, D., & Papini, S. (2024). *Circle STARKs* (Cryptology ePrint Archive, Paper 2024/278). https://eprint.iacr.org/2024/278

Sheybani, N., Ahmed, A., Kinsy, M., & Koushanfar, F. (2025). *Zero-knowledge proof frameworks: A systematic survey* (arXiv:2502.07063). arXiv. https://doi.org/10.48550/arXiv.2502.07063

The Linux Kernel Documentation. (s.f.). *Control Group v2*. Recuperado el 22 de noviembre de 2026 de https://docs.kernel.org/admin-guide/cgroup-v2.html

The Rust Project Developers. (s.f.). *Function std::thread::available_parallelism*. The Rust Standard Library. Recuperado el 22 de noviembre de 2026 de https://doc.rust-lang.org/std/thread/fn.available_parallelism.html

Thibault, L. T., Sarry, T., & Hafid, A. S. (2022). Blockchain scaling using rollups: A comprehensive survey. *IEEE Access, 10*, 93039–93054. https://doi.org/10.1109/ACCESS.2022.3200051

---

---

# 11. Anexos

## Anexo A. Código fuente

Se incluyen los archivos que implementan el entorno y las mediciones. `scripts/plot.py`, que solo genera los gráficos, está en el repositorio.

### docker/Dockerfile

Imagen única del entorno: Debian con Scarb 2.21.0 (que integra el prover y el verificador Stwo) y las herramientas de los scripts.

```dockerfile
# Imagen única del TP: Scarb (execute / prove / verify con Stwo).
# Multi-arquitectura: funciona en Apple Silicon (arm64) y en x86_64.
FROM debian:bookworm-slim

ARG SCARB_VERSION=2.21.0
ARG TARGETARCH

RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates curl git jq bc \
 && rm -rf /var/lib/apt/lists/*

# Mapea la arquitectura de Docker al target triple de los binarios publicados.
RUN set -eux; \
    case "${TARGETARCH:-$(dpkg --print-architecture)}" in \
      arm64) ARCH=aarch64 ;; \
      amd64) ARCH=x86_64 ;; \
      *) echo "arquitectura no soportada: ${TARGETARCH}"; exit 1 ;; \
    esac; \
    TRIPLE="${ARCH}-unknown-linux-gnu"; \
    mkdir -p /opt/tools; cd /opt/tools; \
    curl -fsSL "https://github.com/software-mansion/scarb/releases/download/v${SCARB_VERSION}/scarb-v${SCARB_VERSION}-${TRIPLE}.tar.gz" | tar xz; \
    for d in /opt/tools/*/bin; do ln -s "$d"/* /usr/local/bin/; done

WORKDIR /work

CMD ["bash"]
```

### cairo/fib_core/src/lib.cairo

Librería con la función de Fibonacci y sus tests.

```cairo
/// Returns the n-th Fibonacci number (fib(0) = 0, fib(1) = 1).
/// Arithmetic is done over felt252, so results wrap modulo the Cairo prime
/// for large n. That is fine here: the goal is a computation whose number
/// of execution steps grows linearly with n.
pub fn fib(n: u32) -> felt252 {
    let mut a: felt252 = 0;
    let mut b: felt252 = 1;
    let mut i: u32 = 0;
    while i != n {
        let next = a + b;
        a = b;
        b = next;
        i += 1;
    }
    a
}

#[cfg(test)]
mod tests {
    use super::fib;

    #[test]
    fn known_values() {
        assert_eq!(fib(0), 0);
        assert_eq!(fib(1), 1);
        assert_eq!(fib(2), 1);
        assert_eq!(fib(10), 55);
        assert_eq!(fib(20), 6765);
    }
}
```

### cairo/fib_exec/src/lib.cairo

Programa ejecutable que se prueba; su entrada y su salida son públicas.

```cairo
/// Entry point proven by Stwo. Input `n` and the returned value are public:
/// the proof attests that fib_core::fib(n) evaluated to this output.
#[executable]
fn main(n: u32) -> felt252 {
    fib_core::fib(n)
}
```

### scripts/run_once.sh

Corre dentro del contenedor: ejecuta, prueba y verifica fib(n) una vez y emite una fila CSV con tiempos y métricas del cgroup.

```bash
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
```

### scripts/sweep.sh

Corre en el host: lanza un contenedor nuevo por medición con los límites de cada barrido.

```bash
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
```

### scripts/tamper.sh

Altera una prueba válida de distintas formas y comprueba que el verificador rechaza cada alteración.

```bash
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
```

### Makefile

Interfaz de comandos del proyecto.

```make
# Everything runs inside Docker; the host only needs Docker and make.
# `make` (or `make help`) lists the targets.

IMAGE ?= stark-proving:dev
N     ?= 10
EXP   ?= all
REPS  ?= 3

# Repo mounted at /repo; Scarb builds in a throwaway dir inside the container.
DOCKER = docker run --rm -v "$(CURDIR)":/repo -e SCARB_TARGET_DIR=/tmp/target
EXEC   = $(DOCKER) -w /repo/cairo/fib_exec $(IMAGE)

.DEFAULT_GOAL := help
.PHONY: help build test run prove measure tamper sweep plots informe shell

help: ## Muestra esta ayuda
	@echo "Uso: make <target> [N=10] [EXP=E1|E2|E3|all] [REPS=3]"
	@echo
	@awk 'BEGIN { FS = ":.*## " } /^[a-z]+:.*## / { printf "  make %-8s %s\n", $$1, $$2 }' $(MAKEFILE_LIST)

build: ## Construye la imagen Docker (Scarb 2.21.0 con el prover Stwo)
	docker build -t $(IMAGE) -f docker/Dockerfile docker

test: ## Corre los tests de fib_core
	$(DOCKER) -w /repo/cairo/fib_core $(IMAGE) scarb test

run: ## Ejecuta fib(N) sin generar prueba (rápido)
	$(EXEC) scarb execute --arguments $(N) --print-program-output --print-resource-usage

prove: ## Ejecuta fib(N), genera la prueba STARK y la verifica (Docker necesita ~16 GB)
	$(EXEC) bash -c 'scarb prove --execute --arguments $(N) && scarb verify --execution-id 1 \
	  && ls -lh /tmp/target/execute/fib_exec/execution1/proof/proof.json'

measure: ## Una corrida medida de fib(N): tiempos y métricas de cgroups en CSV
	docker run --rm -e HEADER=1 -v "$(CURDIR)/cairo":/work -v "$(CURDIR)/scripts":/scripts:ro \
	  $(IMAGE) bash /scripts/run_once.sh $(N)

tamper: ## Demo de soundness: las pruebas alteradas no verifican (~3 s)
	$(DOCKER) $(IMAGE) bash /repo/scripts/tamper.sh

sweep: ## Corre los barridos (EXP=E1|E2|E3|all) a results/raw/ (tarda)
	REPS=$(REPS) IMAGE=$(IMAGE) scripts/sweep.sh $(EXP)

plots: ## Genera los gráficos: results/raw/*.csv -> results/figures/*.png
	docker run --rm -v "$(CURDIR)":/repo -w /repo python:3.12-slim \
	  bash -c "pip install -q --root-user-action=ignore matplotlib==3.9.2 && python scripts/plot.py"

informe: ## Genera informe/informe.docx (diagramas + markdown -> Word, para subir a Google Docs)
	docker run --rm -v "$(CURDIR)":/repo -w /repo python:3.12-slim bash -c \
	  "pip install -q --root-user-action=ignore matplotlib==3.9.2 pypandoc_binary==1.14 python-docx==1.1.2 \
	  && python informe/figuras/diagramas.py && python informe/build_docx.py"

shell: ## Abre una shell en el contenedor con el repo en /repo
	docker run --rm -it -v "$(CURDIR)":/repo -w /repo $(IMAGE) bash
```

## Anexo B. Datos crudos

Cada fila es una corrida. Se muestran las columnas usadas en el análisis; los CSV completos están en `results/raw/` del repositorio. Tiempos en segundos y memoria pico del contenedor en GiB.

**Tabla B1.** Corridas de E1 (sin límites).

```
     n    Pasos  t_execute  t_prove  t_verify  Prueba (MB)  Memoria pico  CPU (s)
    10     5172       0,16    24,31      0,12         11,3         13,81    287,7
    10     5172       0,15    24,07      0,20         11,3         13,80    288,1
    10     5172       0,14    24,15      0,19         11,3         13,74    289,4
  1000    15072       0,15    21,60      0,11         11,3         13,86    253,9
  1000    15072       0,20    22,28      0,14         11,3         14,02    255,8
  1000    15072       0,18    21,73      0,12         11,3         13,84    254,7
 10000   105072       0,23    22,48      0,15         11,3         14,17    255,8
 10000   105072       0,22    22,09      0,11         11,3         13,99    255,9
 10000   105072       0,23    21,89      0,11         11,3         13,90    255,2
 50000   505072       0,49    23,62      0,14         11,3         14,33    268,1
 50000   505072       0,52    23,18      0,15         11,3         14,35    267,8
 50000   505072       0,54    23,45      0,12         11,3         14,33    266,9
100000  1005072       0,83    25,83      0,13         11,2         15,04    288,8
100000  1005072       0,95    25,26      0,12         11,2         14,95    282,6
100000  1005072       1,08    25,39      0,12         11,2         15,04    282,8
```

*Fuente: elaboración propia.*

**Tabla B2.** Corridas de E2 (n = 10.000).

```
CPU  t_prove  CPU (s)  Períodos frenados  Tiempo frenado (s)  Memoria pico  Verifica
  4    38,70    142,3                112                0,09         13,70        sí
  4    38,39    141,9                106                0,13         13,69        sí
  4    38,41    140,8                123                0,15         14,04        sí
  2    69,67    133,5                161                0,14         13,68        sí
  2    69,04    133,0                168                0,14         13,54        sí
  2    72,07    138,8                191                0,10         13,59        sí
  1   148,25    148,1                159                0,09         13,71        sí
  1   137,89    137,8                 65                0,05         13,71        sí
  1   138,23    138,2                 86                0,03         13,72        sí
0,5   268,12    134,1               2682              134,05         13,62        sí
0,5   265,69    132,9               2657              132,77         13,62        sí
0,5   269,13    134,6               2692              134,50         13,61        sí
```

*Fuente: elaboración propia.*

**Tabla B3.** Corridas de E3 (n = 10.000, sin swap).

```
Límite (GiB)  Código del prover  Verifica  t_prove  Memoria pico  oom_kill
          16                  0        sí    21,85         13,93         0
          16                  0        sí    21,91         13,91         0
          16                  0        sí    21,86         13,91         0
          15                  0        sí    21,96         13,93         0
          15                  0        sí    21,75         14,22         0
          15                  0        sí    21,96         13,90         0
        14,5                  0        sí    22,05         13,92         0
        14,5                  0        sí    22,02         13,98         0
        14,5                  0        sí    21,55         13,98         0
          14                  0        sí    21,72         13,87         0
          14                  0        sí    21,88         13,91         0
          14                  0        sí    21,88         13,91         0
          13                137        no    16,98         13,00         1
          13                137        no    17,44         13,00         1
          13                137        no    17,37         13,00         1
```

*Fuente: elaboración propia.*

**Tabla B4.** Control de estabilidad (fib(10), sin límites).

```
Corrida  t_execute  t_prove  t_verify  Memoria pico  Verifica
      1       0,14    53,98      0,12         13,85        sí
      2       0,16    24,64      0,15         13,75        sí
      3       0,16    24,23      0,13         13,74        sí
```

*Fuente: elaboración propia.*
