FROM node:22-alpine

WORKDIR /work
COPY generated ./generated

CMD ["sh", "-c", "for package in generated/*/typescript; do (cd \"$package\" && npm test); done"]
