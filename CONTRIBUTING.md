# Contributing

Thanks for helping make Baiita n8n more useful. This repository is a lightweight UI preview and deployment wrapper around the official n8n container; it is not the n8n source monorepo.

## Before you start

- Use Node.js 22 or newer (including for the local secret setup helper).
- Keep the preview clearly labelled as a browser-only demo. Do not imply its sample flows, metrics, or credentials are connected to a real n8n instance.
- Do not commit `.env`, database dumps, credentials, access tokens, or other secrets.
- For changes to the upstream n8n image, review the official release notes, source license, and migration requirements.

## Validate a change

```sh
npm run check
```

The project has no third-party runtime dependencies. A GitHub Actions CI template is in `.github/ci-workflow.example.yml`; place it under `.github/workflows/ci.yml` to activate it when repository workflow permissions are available. If you change the Compose stack, review the port bindings, persistent volumes, encryption key handling, and TLS notes in the README. Docker Compose validation is also recommended where Docker is available:

```sh
npm run setup
docker compose config
docker compose up --build -d
```

Do not commit the generated `.env` file.

## Pull requests

Keep changes focused, explain the user-facing impact, and include or update tests and docs where appropriate. Report n8n application bugs to the [upstream n8n repository](https://github.com/n8n-io/n8n), not as if this wrapper owns the upstream code.
