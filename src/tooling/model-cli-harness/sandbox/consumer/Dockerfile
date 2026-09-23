FROM ubuntu:24.04 AS base
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git curl xz-utils unzip \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 consumer
ENV HOME=/home/consumer
WORKDIR /home/consumer

FROM base AS standalone
USER 10001:10001

FROM base AS node
ARG NODE_VERSION=24.14.0
ARG PNPM_VERSION=10.30.3
RUN arch="$(dpkg --print-architecture)"; case "$arch" in amd64) arch=x64;; arm64) arch=arm64;; *) exit 1;; esac; \
    name="node-v${NODE_VERSION}-linux-${arch}"; \
    curl -fsSLO "https://nodejs.org/dist/v${NODE_VERSION}/${name}.tar.xz" && \
    curl -fsSLO "https://nodejs.org/dist/v${NODE_VERSION}/SHASUMS256.txt" && \
    grep " ${name}.tar.xz$" SHASUMS256.txt | sha256sum -c - && \
    tar -xJf "${name}.tar.xz" -C /usr/local --strip-components=1 && \
    rm "${name}.tar.xz" SHASUMS256.txt && npm install -g "pnpm@${PNPM_VERSION}"
USER 10001:10001

FROM base AS python
ARG UV_VERSION=0.8.22
RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-venv && rm -rf /var/lib/apt/lists/* && \
    python3 -m venv /opt/uv && /opt/uv/bin/pip install --no-cache-dir "uv==${UV_VERSION}" && \
    ln -s /opt/uv/bin/uv /usr/local/bin/uv
USER 10001:10001

FROM base AS cargo
ARG RUST_VERSION
RUN test -n "$RUST_VERSION" && apt-get update && apt-get install -y --no-install-recommends build-essential pkg-config libssl-dev && \
    rm -rf /var/lib/apt/lists/*
USER 10001:10001
ENV CARGO_HOME=/home/consumer/.cargo RUSTUP_HOME=/opt/rustup
USER root
RUN mkdir /opt/rustup && chown 10001:10001 /opt/rustup
USER 10001:10001
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs -o /tmp/rustup.sh && \
    sh /tmp/rustup.sh -y --profile minimal --default-toolchain "$RUST_VERSION" && rm /tmp/rustup.sh
ENV PATH=/home/consumer/.cargo/bin:$PATH
