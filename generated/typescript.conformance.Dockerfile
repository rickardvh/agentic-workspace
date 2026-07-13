FROM node:22-bookworm-slim

WORKDIR /work

RUN apt-get update \
    && apt-get install -y --no-install-recommends git python3 python3-pip \
    && find /usr/lib/python3/dist-packages -name '*.pyc' -delete \
    && python3 -m pip install --break-system-packages --no-cache-dir jsonschema "command-generation @ https://github.com/rickardvh/command-generation/releases/download/v1.3.1/command_generation-1.3.1-py3-none-any.whl#sha256=5cd9cbfd99da24810534127b5328827ac8fc86427ae459f6692045935881f6c7"

COPY pyproject.toml ./pyproject.toml
COPY tests/test_workspace_packaging.py ./tests/test_workspace_packaging.py
COPY .agentic-workspace/planning/decompositions/python-generated-cli.decomposition.json ./.agentic-workspace/planning/decompositions/python-generated-cli.decomposition.json
COPY src ./src
COPY scripts ./scripts
COPY packages ./packages
COPY generated ./generated
COPY .github/release-ownership.json ./.github/release-ownership.json

ENV PYTHONPATH=/work:/work/src:/work/packages/planning/src:/work/packages/memory/src
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python3", "scripts/check/check_generated_command_packages.py", "--conformance", "--require-node"]
