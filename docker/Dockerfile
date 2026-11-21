# Imagen única del TP: Scarb (execute / prove / verify con Stwo) + Starknet Foundry (snforge).
# Multi-arquitectura: funciona en Apple Silicon (arm64) y en x86_64.
FROM debian:bookworm-slim

ARG SCARB_VERSION=2.21.0
ARG FOUNDRY_VERSION=0.64.1
ARG USC_VERSION=2.10.3
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
    curl -fsSL "https://github.com/foundry-rs/starknet-foundry/releases/download/v${FOUNDRY_VERSION}/starknet-foundry-v${FOUNDRY_VERSION}-${TRIPLE}.tar.gz" | tar xz; \
    curl -fsSL "https://github.com/software-mansion/universal-sierra-compiler/releases/download/v${USC_VERSION}/universal-sierra-compiler-v${USC_VERSION}-${TRIPLE}.tar.gz" | tar xz; \
    for d in /opt/tools/*/bin; do ln -s "$d"/* /usr/local/bin/; done

WORKDIR /work

CMD ["bash"]
