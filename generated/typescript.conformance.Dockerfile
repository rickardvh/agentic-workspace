FROM node:22-bookworm-slim

WORKDIR /work

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && find /usr/lib/python3/dist-packages -name '*.pyc' -delete \
    && python3 -m pip install --break-system-packages --no-cache-dir jsonschema "command-generation @ git+https://github.com/rickardvh/command-generation.git@234c80cf546d233851af9ee4e1e9fc444879c8e3"

COPY src ./src
COPY scripts ./scripts
COPY packages ./packages
COPY generated ./generated

ENV PYTHONPATH=/work/src:/work/packages/planning/src:/work/packages/memory/src
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python3", "scripts/check/check_generated_command_packages.py", "--conformance", "--require-node"]
