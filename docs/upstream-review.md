# Upstream review: n8n

**Reviewed:** 2026-10-07

**Repository:** <https://github.com/n8n-io/n8n>

**Default branch:** `master`

**Reviewed revision:** [`0e1c7549997f43053fda83534b597875b0310df6`](https://github.com/n8n-io/n8n/commit/0e1c7549997f43053fda83534b597875b0310df6)

## What the project is

n8n is a mature, source-available workflow automation platform: a visual workflow editor and execution engine, a large set of integrations, AI tooling, a CLI/server, documentation, and deployment/build infrastructure. It is a substantial monorepo rather than a starter app. The reviewed Git tree contains about **30,360 tracked paths** across `packages/`, `docker/`, `docs/`, `scripts/`, and related tooling.

## Setup and operations findings

- The root `package.json` at the reviewed revision identifies n8n **2.43.0** and requires **Node.js 24+** and **pnpm 12.4.2+** for a source checkout. The current environment provides Node 22, but Docker is not available here, so building/running the upstream source or Compose stack could not be tested.
- The upstream README recommends the official `docker.n8n.io/n8nio/n8n` image for a quick self-hosted start. n8n supports PostgreSQL as well as its default SQLite mode; its `.n8n` data directory remains important even when PostgreSQL is used because it contains instance state and credential encryption material.
- A reliable deployment needs stable storage, a persistent encryption key, backups, public webhook/editor URL configuration, and TLS when exposed beyond a private machine/network.
- The repository's licensing is not a blanket permissive open-source license: the main source is under the Sustainable Use License and enterprise-specific `.ee` files/directories have separate Enterprise License restrictions. Review the current upstream terms before copying, redistributing, modifying, or offering n8n as a service.

## Decisions in Baiita-n8n

This repository began as a nearly empty starter. Rather than import tens of thousands of upstream files (including files with separate enterprise licensing terms), Baiita-n8n keeps the upstream application as the official, version-pinned container image and adds:

1. an original, interactive Baiita workspace preview (local sample data only);
2. Docker Compose with the official n8n image and PostgreSQL;
3. generated secrets, persistent volumes, health checks, and loopback-only host port bindings;
4. setup, security, backup, and upgrade instructions.

This means **Baiita-n8n is a deployment/demo wrapper, not a byte-for-byte fork or source mirror**. The editor and demo dashboard are separate. The preview's “run” button simulates an execution in browser storage; real workflows and credentials are handled by the official n8n editor.

## References

- [n8n repository](https://github.com/n8n-io/n8n)
- [Upstream README](https://github.com/n8n-io/n8n/blob/master/README.md)
- [Official Docker hosting guide](https://docs.n8n.io/hosting/installation/docker/)
- [n8n licensing](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)
- [Sustainable Use License documentation](https://docs.n8n.io/sustainable-use-license/)
