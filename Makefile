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
