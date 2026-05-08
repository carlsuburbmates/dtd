from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from typing import Mapping, Literal


LoopOwner = Literal["api", "worker", "none"]
ProcessRole = Literal["api", "worker"]

LOOP_OWNER_ENV = "AUTONOMY_LOOP_OWNER"
LEGACY_RUN_IN_API_ENV = "RUN_AUTONOMY_IN_API"
LEASE_ENABLED_ENV = "AUTONOMY_LOOP_LEASE_ENABLED"
LEASE_TTL_ENV = "AUTONOMY_LOOP_LEASE_TTL_S"
LEASE_RENEW_ENV = "AUTONOMY_LOOP_LEASE_RENEW_S"


@dataclass(frozen=True)
class LoopRuntimeConfig:
    process_role: ProcessRole
    loop_owner: LoopOwner
    source: str
    should_schedule_loops: bool
    lease_enabled: bool
    lease_ttl_s: int
    lease_renew_s: int
    owner_id: str


def _bool_from_env(raw: str | None, *, default: bool) -> bool:
    if raw is None:
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"Invalid boolean env value '{raw}'.")


def _int_from_env(raw: str | None, *, default: int, key: str) -> int:
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError as exc:
        raise RuntimeError(f"{key} must be an integer. Got '{raw}'.") from exc
    if value <= 0:
        raise RuntimeError(f"{key} must be > 0. Got '{raw}'.")
    return value


def _resolve_owner_from_legacy(raw: str | None) -> LoopOwner | None:
    if raw is None:
        return None
    return "api" if _bool_from_env(raw, default=True) else "worker"


def resolve_loop_runtime(process_role: ProcessRole, *, env: Mapping[str, str] | None = None) -> LoopRuntimeConfig:
    if process_role not in {"api", "worker"}:
        raise RuntimeError(f"Invalid process_role '{process_role}'.")

    values: Mapping[str, str] = env if env is not None else os.environ
    explicit_owner_raw = (values.get(LOOP_OWNER_ENV) or "").strip().lower()
    legacy_raw = values.get(LEGACY_RUN_IN_API_ENV)
    legacy_owner = _resolve_owner_from_legacy(legacy_raw)

    if explicit_owner_raw:
        if explicit_owner_raw not in {"api", "worker", "none"}:
            raise RuntimeError(
                f"{LOOP_OWNER_ENV} must be one of: api, worker, none. Got '{explicit_owner_raw}'."
            )
        explicit_owner: LoopOwner = explicit_owner_raw  # type: ignore[assignment]
        if legacy_owner is not None and explicit_owner != legacy_owner:
            raise RuntimeError(
                f"Conflicting loop-owner env: {LOOP_OWNER_ENV}={explicit_owner} "
                f"but {LEGACY_RUN_IN_API_ENV} implies {legacy_owner}."
            )
        owner = explicit_owner
        source = LOOP_OWNER_ENV
    elif legacy_owner is not None:
        owner = legacy_owner
        source = LEGACY_RUN_IN_API_ENV
    else:
        owner = "api"
        source = "default"

    disable_autonomy = _bool_from_env(values.get("DISABLE_AUTONOMY"), default=False)
    should_schedule = (owner == process_role) and (owner != "none") and (not disable_autonomy)
    lease_enabled = _bool_from_env(values.get(LEASE_ENABLED_ENV), default=True) and (owner != "none")
    lease_ttl_s = _int_from_env(values.get(LEASE_TTL_ENV), default=120, key=LEASE_TTL_ENV)
    lease_renew_s = _int_from_env(values.get(LEASE_RENEW_ENV), default=30, key=LEASE_RENEW_ENV)
    if lease_renew_s >= lease_ttl_s:
        raise RuntimeError(f"{LEASE_RENEW_ENV} must be smaller than {LEASE_TTL_ENV}.")

    owner_id = (
        (values.get("AUTONOMY_OWNER_ID") or "").strip()
        or f"{process_role}@{socket.gethostname()}:{os.getpid()}"
    )
    return LoopRuntimeConfig(
        process_role=process_role,
        loop_owner=owner,
        source=source,
        should_schedule_loops=should_schedule,
        lease_enabled=lease_enabled,
        lease_ttl_s=lease_ttl_s,
        lease_renew_s=lease_renew_s,
        owner_id=owner_id,
    )
