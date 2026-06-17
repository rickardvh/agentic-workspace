FROM node:22-bookworm-slim

WORKDIR /work

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && find /usr/lib/python3/dist-packages -name '*.pyc' -delete \
    && python3 -m pip install --break-system-packages --no-cache-dir jsonschema "command-generation @ https://github.com/rickardvh/command-generation/releases/download/v0.2.0/command_generation-0.2.0-py3-none-any.whl#sha256=0c7e1ec9aa78cc95154cca6cef7cfacb2c72c5abca4fa2cfdcb404e8aba5b72e"

COPY src ./src
COPY scripts ./scripts
COPY packages ./packages
COPY generated ./generated

ENV PYTHONPATH=/work/src:/work/packages/planning/src:/work/packages/memory/src
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python3", "scripts/check/check_generated_command_packages.py", "--conformance", "--require-node"]
