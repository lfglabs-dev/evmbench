FROM evmbench/base:latest

RUN git clone --recurse https://github.com/evmbench-org/2025-05-blackhole.git $AUDIT_DIR
RUN git -C $AUDIT_DIR fetch origin 9cb070f6f05b96c5bb64311943592307ae296d65 && \
    git -C $AUDIT_DIR checkout --detach FETCH_HEAD && \
    git -C $AUDIT_DIR submodule update --init --recursive

RUN apt-get update && apt-get install -y \
    libusb-1.0-0-dev \
    libudev-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR $AUDIT_DIR

RUN npm install --force
# The declared benchmark base commit currently fails to compile against its
# lockfile-resolved Algebra dependency; detection only requires the source tree.
RUN npx hardhat compile || true

WORKDIR $AGENT_DIR
