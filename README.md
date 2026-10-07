# Baiita n8n

A polished, hands-on workspace preview for **Baiita** plus a secure-by-default Docker Compose stack for the real, self-hosted [n8n](https://github.com/n8n-io/n8n) editor.

> **What this repo is:** a lightweight launcher, deployment configuration, and interactive browser demo. The n8n application source is not vendored here; Compose runs the official n8n container image. Preview workflows are local simulations and do not connect to third-party apps.

[Upstream n8n](https://github.com/n8n-io/n8n) · [n8n docs](https://docs.n8n.io/)

## What you get

- **A lively workspace preview** — workflow cards, an animated flow canvas, sample activity, templates, keyboard search, import previews, and browser-only run simulations.
- **The actual n8n editor** — launched as the official Docker image, with PostgreSQL for durable workflow and execution data.
- **Safer local defaults** — generated encryption/database secrets, persistent volumes, health checks, pinned n8n version, and ports bound to `127.0.0.1` by default.
- **No frontend install required** — the preview is a zero-dependency Node.js app; all demo changes are saved in the browser's local storage.

## Quick start: interactive preview

Requires Node.js 22 or newer.

```sh
npm run dev
```

Open <http://localhost:4173>. The preview is served on `0.0.0.0:4173` so it can also be viewed through a development preview. Set `PORT` or `HOST` to override the defaults.

The preview is intentionally honest about its scope: creating, toggling, importing, and running flows only changes local demo data. Imported JSON is reduced to a safe visual preview; credentials and executable settings are never stored. Use the real n8n editor for live automations.

## Start the real self-hosted stack

Requires Docker Engine, the Docker Compose plugin, and Node.js 22 or newer for the setup helper.

```sh
npm run setup                 # Creates a private .env with random secrets
# Review .env, especially the timezone and URL values.
docker compose up --build -d
```

- **Baiita workspace preview:** <http://localhost:4173>
- **Real n8n editor:** <http://localhost:5678>

The first visit to the n8n editor guides you through creating the owner account. PostgreSQL and n8n instance data are kept in persistent Docker volumes. The demo dashboard is a separate application, and its preview changes stay in your browser's local storage.

Useful commands:

```sh
docker compose ps                 # Check service health
docker compose logs -f n8n        # Follow n8n logs
docker compose down               # Stop services; keep data
npm test                          # Run the app's HTTP/security tests
npm run check                     # Syntax checks plus tests
```

> **Keep your encryption key safe.** Back up `.env` securely alongside your database and n8n data volume. If you lose `N8N_ENCRYPTION_KEY`, saved credentials can no longer be decrypted. Never commit or share `.env`.

## Configuration

`npm run setup` creates `.env` from `.env.example` and refuses to overwrite an existing file. Review these values before starting:

| Variable | Default | Purpose |
| --- | --- | --- |
| `N8N_IMAGE` | `docker.n8n.io/n8nio/n8n:2.43.0` | Pinned n8n release; update deliberately after reviewing release notes. |
| `N8N_ENCRYPTION_KEY` | Generated secret | Encrypts saved n8n credentials. Keep it stable and backed up. |
| `POSTGRES_PASSWORD` | Generated secret | Password for the private Postgres service. |
| `N8N_PORT` | `5678` | Host port for the real n8n editor. |
| `DASHBOARD_PORT` | `4173` | Host port for the Baiita preview. |
| `N8N_BIND_ADDRESS` | `127.0.0.1` | Bind address for the editor port. |
| `DASHBOARD_BIND_ADDRESS` | `127.0.0.1` | Bind address for the preview port. |
| `GENERIC_TIMEZONE` | `Etc/UTC` | Timezone used by workflow schedules. |
| `N8N_HOST`, `N8N_PROTOCOL` | `localhost`, `http` | Public hostname/protocol used by n8n. |
| `N8N_EDITOR_BASE_URL`, `WEBHOOK_URL` | Local HTTP URLs | Set to the public HTTPS URLs when operating behind a trusted TLS proxy. |

For a public deployment, **do not expose the default HTTP ports directly to the internet**. Put n8n behind a trusted TLS reverse proxy, configure `N8N_HOST`, `N8N_PROTOCOL=https`, `N8N_EDITOR_BASE_URL`, and `WEBHOOK_URL` to match the public hostname, set `N8N_SECURE_COOKIE=true`, and restrict proxy/network access to the containers. Use strong account authentication, backups, and a reviewed upgrade plan.

## Backups and upgrades

PostgreSQL stores workflows and execution records; the `n8n_data` volume also contains instance settings and key material. Take coordinated backups of the database, the `n8n_data` volume, and the private `.env` file before upgrading. Store backups somewhere access-controlled.

A database dump can be created with:

```sh
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > n8n-postgres.sql
```

For an upgrade, change the pinned `N8N_IMAGE` in `.env` only after reviewing the official release notes, then run:

```sh
docker compose pull n8n
docker compose up -d
```

Avoid `docker compose down -v` unless you intentionally want to delete persistent workflow data.

## Upstream review

See [`docs/upstream-review.md`](docs/upstream-review.md) for the review notes, runtime requirements, licensing boundaries, and why this repository uses the official container instead of copying the entire upstream monorepo.

## License and attribution

n8n is a separate upstream project. Its source-available distribution uses the Sustainable Use License, with enterprise-specific files governed by the n8n Enterprise License; see the [official license](https://github.com/n8n-io/n8n/blob/master/LICENSE.md) and [license documentation](https://docs.n8n.io/sustainable-use-license/). This repository does not include upstream n8n source files. The upstream container retains its own license and notices. n8n and its marks belong to their respective owners; this Baiita preview is an independent deployment/demo wrapper and is not an official n8n product.
