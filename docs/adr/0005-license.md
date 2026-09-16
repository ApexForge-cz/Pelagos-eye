# ADR-0005: Source-code license

- Status: Accepted
- Date: 2026-09-17
- Owners: Repository maintainer

## Context

The project is intended for a public GitHub portfolio and non-commercial development, but
those statements do not define what other people may do with the source. A license is a
legal permission grant and should not be inferred from the technical plan.

## Decision

Use the MIT License already selected by the repository owner in the remote repository. It
permits broad reuse, including commercial reuse, while preserving copyright and warranty
notices. The owner's own development and deployment remain non-commercial.

Third-party datasets remain under their own terms regardless of the code license.

## Consequences

- The repository is open source and other people may use the original code commercially.
- Dataset retention, display, and redistribution still require separate source reviews.

## Alternatives considered

- Apache-2.0 for an explicit patent grant.
- AGPL-3.0 for network copyleft.
- A custom non-commercial license for restricted reuse.
