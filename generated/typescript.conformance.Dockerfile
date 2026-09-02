FROM node:22-bookworm-slim

WORKDIR /work

RUN apt-get update \
    && apt-get install -y --no-install-recommends git python3 python3-pip \
    && find /usr/lib/python3/dist-packages -name '*.pyc' -delete \
    && python3 -m pip install --break-system-packages --no-cache-dir jsonschema "command-generation @ git+https://github.com/rickardvh/command-generation.git@ac1b9c00bf41352010929de196e7d45e20014615"

COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
COPY uv.lock ./uv.lock
COPY LICENSE ./LICENSE
COPY tests/test_workspace_packaging.py ./tests/test_workspace_packaging.py
COPY tests/test_external_consumer_profile.py ./tests/test_external_consumer_profile.py
COPY tests/test_runtime_compatibility.py ./tests/test_runtime_compatibility.py
COPY tests/fixtures/external_consumer/consumer.py ./tests/fixtures/external_consumer/consumer.py
COPY .agentic-workspace/planning/decompositions/python-generated-cli.decomposition.json ./.agentic-workspace/planning/decompositions/python-generated-cli.decomposition.json
COPY src ./src
COPY scripts ./scripts
COPY packages ./packages
COPY generated ./generated
COPY .github/release-ownership.json ./.github/release-ownership.json

RUN python3 -m pip install --break-system-packages --no-cache-dir --no-deps \
    ./packages/planning ./packages/memory ./packages/verification .

ENV PYTHONPATH=/work:/work/src:/work/packages/planning/src:/work/packages/memory/src:/work/packages/verification/src
ENV PYTHONDONTWRITEBYTECODE=1
ENV AGENTIC_GENERATED_CONFORMANCE_CONTAINER=typescript

CMD ["python3", "scripts/check/check_generated_command_packages.py", "--conformance", "--require-node"]
