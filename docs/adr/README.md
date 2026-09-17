# Architecture Decision Records

Accepted decisions describe the engineering foundation that exists in the repository.
Proposed decisions remain open and must not be treated as final.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-repository-layout.md) | Repository layout and modular-monolith boundaries | Accepted |
| [0002](0002-toolchain-and-package-management.md) | Runtime and package-management baseline | Accepted |
| [0003](0003-runtime-contracts.md) | Configuration, logging, health, and errors | Accepted |
| [0004](0004-local-infrastructure.md) | Local infrastructure and initial deployment posture | Accepted |
| [0005](0005-license.md) | Source-code license | Accepted — MIT |
| [0006](0006-provenance-schema.md) | Source catalog and ingestion provenance foundation | Accepted |
| [0007](0007-official-port-source-ingestion.md) | Official port-source ingestion and source-record boundary | Accepted |
| [0008](0008-usgs-event-revisions.md) | USGS feed versioning and latest-event revision semantics | Accepted |
| [0009](0009-open-meteo-forecast-snapshots.md) | Bounded Open-Meteo marine forecast snapshots | Accepted |
| [0010](0010-bounded-marinecadastre-history.md) | Bounded NOAA MarineCadastre historical AIS imports | Accepted |

Later GIS, live-event durability, AIS retention, raw artifact storage, and authentication
decisions remain deferred until the relevant phase has evidence.
