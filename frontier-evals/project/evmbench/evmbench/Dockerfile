FROM ploit-builder:latest AS ploit

FROM ubuntu:24.04

# Use bash (with pipefail) for every RUN
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Workspace layout
ENV WORKSPACE_BASE=/home \
    AGENT_DIR=/home/agent \
    AUDIT_DIR=/home/agent/audit \
    SUBMISSION_DIR=/home/agent/submission \
    LOGS_DIR=/home/logs \
    NVM_DIR=/home/agent/.nvm \
    FOUNDRY_DIR=/home/agent/.foundry

ENV PATH=$FOUNDRY_DIR/bin:$PATH
ENV PATH=$AGENT_DIR/.local/bin:$PATH
ENV HOME=$AGENT_DIR

ENV DEBIAN_FRONTEND=noninteractive

# Tell pip by default to "break" system protection:
ENV PIP_BREAK_SYSTEM_PACKAGES=1

# Remove Debian's PEP 668 marker so pip thinks it's free to write:
RUN find /usr/lib -name EXTERNALLY-MANAGED -delete

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates gnupg \
    zip unzip git nano vim jq bc lsof xxd \
    build-essential pkg-config libssl-dev \
    linux-libc-dev libstdc++6 \
    python3 python3-pip python3-venv python-is-python3 \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Preinstall Jupyter + ipykernel so LocalCluster doesn't need to pip-install on first kernel start.
RUN python3 -m pip install --no-cache-dir jupyter ipykernel && \
    python3 -m ipykernel install --sys-prefix

# Create directory skeleton
RUN mkdir -p "$AUDIT_DIR" "$SUBMISSION_DIR" "$LOGS_DIR"

ARG TARGETARCH
ENV CODEX_VERSION=rust-v0.98.0
RUN set -eux; \
    case "$TARGETARCH" in \
        amd64) CODEX_ARCH=x86_64 ;; \
        arm64) CODEX_ARCH=aarch64 ;; \
        *) echo "unsupported architecture: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    CODEX_URL="https://github.com/openai/codex/releases/download/${CODEX_VERSION}/codex-${CODEX_ARCH}-unknown-linux-gnu.tar.gz"; \
    mkdir -p /usr/local/src/codex; cd /usr/local/src/codex; \
    curl -L -o codex.tgz "$CODEX_URL"; \
    ENTRY="$(tar -tzf codex.tgz | grep -v '/$' | head -n1)"; \
    test -n "$ENTRY"; \
    tar -xzf codex.tgz -O "$ENTRY" > /usr/local/bin/codex; \
    chmod 0755 /usr/local/bin/codex; \
    cd /; rm -rf /usr/local/src/codex; \
    codex --version

ENV CLAUDE_CODE_VERSION=2.1.32
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

ENV GEMINI_VERSION=0.25.0
RUN npm install -g @google/gemini-cli@${GEMINI_VERSION}

ENV OPENCODE_VERSION=1.1.26
RUN npm install -g opencode-ai@${OPENCODE_VERSION}

RUN set -eux; \
    if [ "$TARGETARCH" = amd64 ]; then \
        curl -LO https://github.com/BurntSushi/ripgrep/releases/download/14.1.1/ripgrep_14.1.1-1_amd64.deb; \
        dpkg -i ripgrep_14.1.1-1_amd64.deb; \
    elif [ "$TARGETARCH" = arm64 ]; then \
        curl -L -o ripgrep.tgz https://github.com/BurntSushi/ripgrep/releases/download/14.1.1/ripgrep-14.1.1-aarch64-unknown-linux-gnu.tar.gz; \
        tar -xzf ripgrep.tgz --strip-components=1 -C /usr/local/bin ripgrep-14.1.1-aarch64-unknown-linux-gnu/rg; \
        chmod 0755 /usr/local/bin/rg; \
    else \
        echo "unsupported architecture: $TARGETARCH" >&2; exit 1; \
    fi; \
    rg --version

WORKDIR "$AGENT_DIR"

# Foundry (stable)
RUN curl -L https://foundry.paradigm.xyz | bash
RUN foundryup --install v1.3.6

# Set up git config
RUN git config --global --add safe.directory $AGENT_DIR && \
    git config --global --add safe.directory $AUDIT_DIR && \
    git config --global user.email "agent@example.com" && \
    git config --global user.name "agent"

COPY --from=ploit /ploit /usr/local/bin/ploit
COPY --from=ploit /usr/local/bin/veto /usr/local/bin/veto

CMD ["bash"]
