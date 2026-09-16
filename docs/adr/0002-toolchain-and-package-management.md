# ADR-0002: Runtime and package-management baseline

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

The project needs reproducible dependency resolution on Windows development hosts, Linux
CI, and Linux containers while keeping contributor commands familiar.

## Decision

- Python support is `>=3.12,<3.15`; Phase 1 development and CI use Python 3.13.
- `uv` manages Python resolution, environments, and the API lockfile.
- Node.js 22.12 or newer is supported; CI and containers use Node.js 24.
- npm workspaces manage the web application and the root JavaScript lockfile.
- Strict TypeScript, Ruff, mypy, pytest, ESLint, Prettier, Vitest, and a production build
  form the local quality gate.

Large GIS and UI dependencies are deliberately deferred until their phase, so the Phase 1
lockfiles prove the toolchain rather than preinstalling unused packages.

## Consequences

- Clean environments install from committed lockfiles.
- Windows and Linux use the same package manifests and checks.
- Contributors need both uv and Node/npm.
- Runtime upgrades require a reviewed lockfile and CI/container update.

## Alternatives considered

- pip plus manually maintained requirements files: rejected in favor of one resolver/lock.
- pnpm: viable, but npm reduces tooling prerequisites for a one-app workspace.
