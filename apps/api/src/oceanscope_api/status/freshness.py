from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from oceanscope_api.provenance.models import SourceState
from oceanscope_api.status.contracts import (
    FreshnessSnapshot,
    IngestionRunSnapshot,
    SourceVersionSnapshot,
)


@dataclass(frozen=True)
class FreshnessPolicy:
    live_ttl: timedelta
    delayed_ttl: timedelta
    cache_ttl: timedelta | None

    def __post_init__(self) -> None:
        if self.live_ttl.total_seconds() < 0:
            raise ValueError("live_ttl cannot be negative")
        if self.delayed_ttl < self.live_ttl:
            raise ValueError("delayed_ttl cannot be shorter than live_ttl")
        if self.cache_ttl is not None and self.cache_ttl < self.delayed_ttl:
            raise ValueError("cache_ttl cannot be shorter than delayed_ttl")


@dataclass(frozen=True)
class FreshnessEvaluation:
    state: str
    available: bool
    cache_age_seconds: int | None
    snapshot: FreshnessSnapshot


DEFAULT_POLICY = FreshnessPolicy(
    live_ttl=timedelta(days=1),
    delayed_ttl=timedelta(days=7),
    cache_ttl=timedelta(days=30),
)

SOURCE_POLICIES = {
    "unece-unlocode": FreshnessPolicy(
        live_ttl=timedelta(days=200),
        delayed_ttl=timedelta(days=240),
        cache_ttl=timedelta(days=400),
    ),
    "nga-world-port-index": FreshnessPolicy(
        live_ttl=timedelta(days=35),
        delayed_ttl=timedelta(days=65),
        cache_ttl=timedelta(days=180),
    ),
    "usgs-earthquakes": FreshnessPolicy(
        live_ttl=timedelta(minutes=5),
        delayed_ttl=timedelta(minutes=15),
        cache_ttl=timedelta(hours=1),
    ),
    "open-meteo-marine": FreshnessPolicy(
        live_ttl=timedelta(hours=6),
        delayed_ttl=timedelta(hours=24),
        cache_ttl=timedelta(hours=48),
    ),
    # Historical archives are immutable for their declared date and checksum.
    "noaa-marinecadastre-ais": FreshnessPolicy(
        live_ttl=timedelta(days=1),
        delayed_ttl=timedelta(days=1),
        cache_ttl=None,
    ),
}


def policy_for(source_slug: str) -> FreshnessPolicy:
    return SOURCE_POLICIES.get(source_slug, DEFAULT_POLICY)


def evaluate_freshness(
    *,
    policy: FreshnessPolicy,
    latest_run: IngestionRunSnapshot | None,
    usable_run: IngestionRunSnapshot | None,
    usable_version: SourceVersionSnapshot | None,
    now: datetime,
) -> FreshnessEvaluation:
    if usable_run is None or usable_version is None:
        return FreshnessEvaluation(
            state=SourceState.OFFLINE.value,
            available=False,
            cache_age_seconds=None,
            snapshot=_snapshot(policy, None),
        )

    age_seconds = _effective_age_seconds(usable_run, usable_version, now)
    within_cache = policy.cache_ttl is None or age_seconds <= policy.cache_ttl.total_seconds()
    if not within_cache:
        return FreshnessEvaluation(
            state=SourceState.OFFLINE.value,
            available=False,
            cache_age_seconds=None,
            snapshot=_snapshot(policy, age_seconds),
        )

    fallback = latest_run is None or latest_run.id != usable_run.id
    if fallback or usable_run.source_state in {
        SourceState.CACHED.value,
        SourceState.OFFLINE.value,
    }:
        state = SourceState.CACHED.value
    elif age_seconds <= policy.live_ttl.total_seconds():
        state = SourceState.LIVE.value
    elif age_seconds <= policy.delayed_ttl.total_seconds():
        state = SourceState.DELAYED.value
    else:
        state = SourceState.CACHED.value

    return FreshnessEvaluation(
        state=state,
        available=True,
        cache_age_seconds=age_seconds if state == SourceState.CACHED.value else None,
        snapshot=_snapshot(policy, age_seconds),
    )


def _effective_age_seconds(
    run: IngestionRunSnapshot,
    version: SourceVersionSnapshot,
    now: datetime,
) -> int:
    retrieval_age = max(0, int((now - version.retrieved_at).total_seconds()))
    if run.cache_age_seconds is None:
        return retrieval_age
    elapsed_since_run = max(0, int((now - run.started_at).total_seconds()))
    return max(retrieval_age, run.cache_age_seconds + elapsed_since_run)


def _snapshot(policy: FreshnessPolicy, age_seconds: int | None) -> FreshnessSnapshot:
    return FreshnessSnapshot(
        age_seconds=age_seconds,
        live_ttl_seconds=int(policy.live_ttl.total_seconds()),
        delayed_ttl_seconds=int(policy.delayed_ttl.total_seconds()),
        cache_ttl_seconds=(
            int(policy.cache_ttl.total_seconds()) if policy.cache_ttl is not None else None
        ),
    )
