FROM node:22-alpine

WORKDIR /work
COPY generated/typescript ./generated/typescript

CMD ["sh", "-c", "for package in generated/typescript/*-cli; do (cd \"$package\" && npm test); done"]
