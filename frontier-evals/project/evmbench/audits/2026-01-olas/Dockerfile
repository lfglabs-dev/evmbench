FROM evmbench/base:latest

# The evmbench-org mirror has not been published yet; retain the immutable
# Code4rena audit repository as a functional fallback.
RUN git clone --recurse-submodules https://github.com/evmbench-org/2026-01-olas.git $AUDIT_DIR \
    || git clone --recurse-submodules https://github.com/code-423n4/2026-01-olas.git $AUDIT_DIR

# Keep the fallback reproducible even if the public contest repository advances.
RUN git -C $AUDIT_DIR checkout f8ad8df420d54fdd5143c387cbfe46cc58578fea \
    && git -C $AUDIT_DIR submodule update --init --recursive

RUN corepack enable
RUN for repo in autonolas-governance autonolas-registries autonolas-tokenomics; do \
        cd "$AUDIT_DIR/$repo" \
        && yarn install --frozen-lockfile --ignore-scripts \
        && forge build; \
    done

WORKDIR $AGENT_DIR
