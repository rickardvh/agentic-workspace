FROM docker/sandbox-templates:codex-docker

USER root
RUN mkdir -p /tmp/agentic-workspace-fixture-venv /tmp/uv-cache \
    && chown -R agent:agent /tmp/agentic-workspace-fixture-venv /tmp/uv-cache

USER agent
ENV PYTHONUNBUFFERED=1 \
    UV_PROJECT_ENVIRONMENT=/tmp/agentic-workspace-fixture-venv \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/tmp/uv-cache

WORKDIR /home/agent/workspace
