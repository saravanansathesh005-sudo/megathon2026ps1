"""Organisational steering rules.

A security team owns what the agent may do, and should not have to edit Python to
change it. This module loads a declarative rules file and turns it into a decision
*floor* the policy engine applies alongside its own reasoning.

**Steering can only restrict.**

That is the whole design. A rule can raise ALLOW to REQUIRE_CONFIRMATION, or
either of those to BLOCK. Nothing in this file can grant an action the registry
forbids, satisfy an authorization check, or turn a BLOCK into an ALLOW. A config
file that can weaken security is not a feature, it is a vulnerability - anyone who
can write the file would otherwise own the system.

Two failure modes, deliberately different:

    file absent   -> no steering configured. Normal operation, no rules applied.
    file invalid  -> the intended restrictions are unknown, so every action
                     degrades to REQUIRE_CONFIRMATION until it is fixed.

The second follows the architecture's fail-safe direction: degrade toward
confirmation, never toward allow. Silently ignoring a malformed rules file would
mean a typo quietly disables the organisation's policy.

The file's SHA-256 is recorded in the audit chain when it loads, so a change to
the rules is itself a tamper-evident event.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.security.registry import ACTIONS, ROLES

logger = logging.getLogger(__name__)

DEFAULT_PATH = "aegis.steering.yaml"

ALLOW = "ALLOW"
REQUIRE_CONFIRMATION = "REQUIRE_CONFIRMATION"
BLOCK = "BLOCK"
_RANK = {ALLOW: 0, REQUIRE_CONFIRMATION: 1, BLOCK: 2}

_OFFSET = re.compile(r"^([+-])(\d{2}):?(\d{2})$")
_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


@dataclass
class Steering:
    """A loaded rules file. `status` says whether it may be trusted."""

    status: str = "absent"          # absent | active | invalid
    path: str = ""
    sha256: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    never: set[str] = field(default_factory=set)
    always_confirm: set[str] = field(default_factory=set)
    block_blast_at_least: float | None = None
    confirm_blast_at_least: float | None = None
    max_records_per_action: int | None = None
    max_trajectory_score: int | None = None
    confirm_categories: set[str] = field(default_factory=set)
    role_never: dict[str, set[str]] = field(default_factory=dict)
    resource_never: dict[str, set[str]] = field(default_factory=dict)
    resource_confirm: dict[str, set[str]] = field(default_factory=dict)
    hours_start: str | None = None
    hours_end: str | None = None
    hours_offset_minutes: int = 0
    hours_label: str = "UTC"
    outside_hours: str = REQUIRE_CONFIRMATION

    @property
    def active(self) -> bool:
        return self.status == "active"

    def summary(self) -> dict:
        """What the admin terminal shows. No secrets, no file contents."""
        return {
            "status": self.status,
            "path": self.path,
            "sha256": self.sha256,
            "errors": self.errors,
            "warnings": self.warnings,
            "rule_count": self.rule_count(),
            "rules": {
                "never": sorted(self.never),
                "always_confirm": sorted(self.always_confirm),
                "block_blast_at_least": self.block_blast_at_least,
                "confirm_blast_at_least": self.confirm_blast_at_least,
                "max_records_per_action": self.max_records_per_action,
                "max_trajectory_score": self.max_trajectory_score,
                "confirm_categories": sorted(self.confirm_categories),
                "role_never": {r: sorted(a) for r, a in sorted(self.role_never.items())},
                "resource_never": {r: sorted(a) for r, a in sorted(self.resource_never.items())},
                "resource_confirm": {r: sorted(a) for r, a in sorted(self.resource_confirm.items())},
                "allowed_hours": (
                    {"start": self.hours_start, "end": self.hours_end,
                     "timezone": self.hours_label, "outside": self.outside_hours}
                    if self.hours_start else None),
            },
        }

    def rule_count(self) -> int:
        counts = [
            len(self.never), len(self.always_confirm), len(self.confirm_categories),
            sum(len(v) for v in self.role_never.values()),
            sum(len(v) for v in self.resource_never.values()),
            sum(len(v) for v in self.resource_confirm.values()),
        ]
        singles = [self.block_blast_at_least, self.confirm_blast_at_least,
                   self.max_records_per_action, self.max_trajectory_score,
                   self.hours_start]
        return sum(counts) + sum(1 for s in singles if s is not None)


# --------------------------------------------------------------------------- loading

def _as_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def _parse_offset(text: str) -> int | None:
    match = _OFFSET.match(text.strip())
    if not match:
        return None
    sign, hours, minutes = match.groups()
    total = int(hours) * 60 + int(minutes)
    return -total if sign == "-" else total


def _resolve_timezone(value: str, steering: Steering) -> None:
    """Accept a UTC offset, or an IANA name where the platform has the tz database."""
    offset = _parse_offset(value)
    if offset is not None:
        steering.hours_offset_minutes = offset
        steering.hours_label = value
        return
    try:
        from zoneinfo import ZoneInfo

        zone = ZoneInfo(value)
        now = datetime.now(zone)
        steering.hours_offset_minutes = int(now.utcoffset().total_seconds() // 60)
        steering.hours_label = value
    except Exception:
        # Missing tz database is a deployment fact, not a rules error. Say so and
        # fall back to UTC rather than refusing to load the whole file.
        steering.warnings.append(
            "timezone '" + str(value) + "' could not be resolved on this host; "
            "hours are being evaluated in UTC. Use an offset such as '+05:30' "
            "to make this explicit.")
        steering.hours_offset_minutes = 0
        steering.hours_label = "UTC (fallback)"


def _validate_actions(names, where: str, steering: Steering) -> set[str]:
    out: set[str] = set()
    for name in names:
        text = str(name)
        if text not in ACTIONS:
            steering.errors.append(
                where + ": '" + text + "' is not a registered action")
            continue
        out.add(text)
    return out


def _number(value, where: str, steering: Steering, cast=float):
    try:
        return cast(value)
    except (TypeError, ValueError):
        steering.errors.append(where + ": '" + str(value) + "' is not a number")
        return None


def parse(data: dict, steering: Steering) -> Steering:
    """Turn a parsed document into rules, collecting every error rather than the first."""
    if not isinstance(data, dict):
        steering.errors.append("the rules file must contain a mapping at the top level")
        return steering

    unknown = set(data) - {
        "never", "always_confirm", "block_when", "confirm_when",
        "max_records_per_action", "max_trajectory_score", "confirm_categories",
        "roles", "resources", "allowed_hours", "version", "description",
    }
    for key in sorted(unknown):
        steering.errors.append("unknown rule '" + str(key) + "'")

    steering.never = _validate_actions(_as_list(data.get("never")), "never", steering)
    steering.always_confirm = _validate_actions(
        _as_list(data.get("always_confirm")), "always_confirm", steering)

    block_when = data.get("block_when") or {}
    if isinstance(block_when, dict) and "blast_radius_at_least" in block_when:
        steering.block_blast_at_least = _number(
            block_when["blast_radius_at_least"], "block_when.blast_radius_at_least", steering)

    confirm_when = data.get("confirm_when") or {}
    if isinstance(confirm_when, dict) and "blast_radius_at_least" in confirm_when:
        steering.confirm_blast_at_least = _number(
            confirm_when["blast_radius_at_least"], "confirm_when.blast_radius_at_least", steering)

    if data.get("max_records_per_action") is not None:
        steering.max_records_per_action = _number(
            data["max_records_per_action"], "max_records_per_action", steering, int)

    if data.get("max_trajectory_score") is not None:
        steering.max_trajectory_score = _number(
            data["max_trajectory_score"], "max_trajectory_score", steering, int)

    for category in _as_list(data.get("confirm_categories")):
        text = str(category).upper()
        if text not in ("NORMAL", "RISKY", "PRIVILEGED", "FORBIDDEN"):
            steering.errors.append("confirm_categories: '" + text + "' is not a T&C band")
            continue
        steering.confirm_categories.add(text)

    roles = data.get("roles") or {}
    if isinstance(roles, dict):
        for role, spec in roles.items():
            if role not in ROLES:
                steering.errors.append("roles: '" + str(role) + "' is not a known role")
                continue
            actions = _validate_actions(
                _as_list((spec or {}).get("never")), "roles." + str(role) + ".never", steering)
            if actions:
                steering.role_never[role] = actions

    resources = data.get("resources") or {}
    if isinstance(resources, dict):
        for name, spec in resources.items():
            spec = spec or {}
            never = _validate_actions(
                _as_list(spec.get("never")), "resources." + str(name) + ".never", steering)
            confirm = _validate_actions(
                _as_list(spec.get("always_confirm")),
                "resources." + str(name) + ".always_confirm", steering)
            if never:
                steering.resource_never[str(name)] = never
            if confirm:
                steering.resource_confirm[str(name)] = confirm

    hours = data.get("allowed_hours") or {}
    if isinstance(hours, dict) and hours:
        start, end = str(hours.get("start", "")), str(hours.get("end", ""))
        if not _HHMM.match(start) or not _HHMM.match(end):
            steering.errors.append(
                "allowed_hours: start and end must be 24-hour HH:MM, got '"
                + start + "' and '" + end + "'")
        else:
            steering.hours_start, steering.hours_end = start, end
            _resolve_timezone(str(hours.get("timezone", "+00:00")), steering)
        outside = str(hours.get("outside", "confirm")).lower()
        if outside not in ("confirm", "block"):
            steering.errors.append(
                "allowed_hours.outside must be 'confirm' or 'block', got '" + outside + "'")
        else:
            steering.outside_hours = BLOCK if outside == "block" else REQUIRE_CONFIRMATION

    return steering


def load(path: str | None = None) -> Steering:
    """Read and validate the rules file. Never raises."""
    path = path or os.environ.get("AEGIS_STEERING_FILE") or DEFAULT_PATH
    steering = Steering(path=path)

    if not os.path.isfile(path):
        steering.status = "absent"
        logger.info("steering.absent", extra={"context": {"path": path}})
        return steering

    try:
        with open(path, "rb") as handle:
            payload = handle.read()
    except OSError as exc:
        steering.status = "invalid"
        steering.errors.append("the rules file could not be read: " + str(exc))
        return steering

    steering.sha256 = hashlib.sha256(payload).hexdigest()

    try:
        import yaml

        data = yaml.safe_load(payload.decode("utf-8")) or {}
    except Exception as exc:
        steering.status = "invalid"
        steering.errors.append("the rules file is not valid YAML: " + str(exc))
        logger.error("steering.invalid", extra={"context": {"path": path, "error": str(exc)}})
        return steering

    steering.raw = data if isinstance(data, dict) else {}
    parse(data, steering)
    steering.status = "invalid" if steering.errors else "active"

    logger.info("steering." + steering.status, extra={"context": {
        "path": path, "sha256": steering.sha256[:16],
        "rules": steering.rule_count(), "errors": len(steering.errors)}})
    return steering


# ------------------------------------------------------------------------ evaluation

def _within_hours(steering: Steering, now: datetime | None = None) -> bool:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    local = now + timedelta(minutes=steering.hours_offset_minutes)
    minutes = local.hour * 60 + local.minute
    start_h, start_m = (int(x) for x in steering.hours_start.split(":"))
    end_h, end_m = (int(x) for x in steering.hours_end.split(":"))
    start, end = start_h * 60 + start_m, end_h * 60 + end_m
    if start <= end:
        return start <= minutes < end
    # A window that crosses midnight, e.g. 22:00 to 06:00.
    return minutes >= start or minutes < end


def evaluate(steering: Steering, *, action: str, resource: str, role: str,
             blast: float, category: str, affected_records: int,
             trajectory_score: int, now: datetime | None = None) -> dict:
    """Return the restriction floor these rules impose, and why.

    The floor is only ever ALLOW, REQUIRE_CONFIRMATION or BLOCK. The caller raises
    its own decision to meet it and never lowers anything to match.
    """
    if steering.status == "absent":
        return {"floor": ALLOW, "reasons": [], "matched": [], "status": "absent"}

    if steering.status == "invalid":
        return {
            "floor": REQUIRE_CONFIRMATION,
            "reasons": ["the steering file is invalid, so every action requires "
                        "confirmation until it is corrected"],
            "matched": ["fail-safe"],
            "status": "invalid",
        }

    floor, reasons, matched = ALLOW, [], []

    def raise_to(level: str, reason: str, rule: str) -> None:
        nonlocal floor
        if _RANK[level] > _RANK[floor]:
            floor = level
        reasons.append(reason)
        matched.append(rule)

    if action in steering.never:
        raise_to(BLOCK, "steering rule: '" + action + "' is never permitted here", "never")

    if role in steering.role_never and action in steering.role_never[role]:
        raise_to(BLOCK, "steering rule: role '" + role + "' may never " + action,
                 "roles." + role + ".never")

    if resource and action in steering.resource_never.get(resource, set()):
        raise_to(BLOCK, "steering rule: '" + action + "' is never permitted on "
                 + resource, "resources." + resource + ".never")

    if steering.block_blast_at_least is not None and blast >= steering.block_blast_at_least:
        raise_to(BLOCK, "steering rule: blast radius " + str(blast) + " reaches the "
                 "configured limit of " + str(steering.block_blast_at_least),
                 "block_when.blast_radius_at_least")

    if steering.max_records_per_action is not None \
            and affected_records > steering.max_records_per_action:
        raise_to(BLOCK, "steering rule: " + str(affected_records) + " records exceeds "
                 "the configured maximum of " + str(steering.max_records_per_action)
                 + " per action", "max_records_per_action")

    if steering.max_trajectory_score is not None \
            and trajectory_score > steering.max_trajectory_score:
        raise_to(BLOCK, "steering rule: trajectory score " + str(trajectory_score)
                 + " exceeds the configured maximum of "
                 + str(steering.max_trajectory_score), "max_trajectory_score")

    if action in steering.always_confirm:
        raise_to(REQUIRE_CONFIRMATION,
                 "steering rule: '" + action + "' always requires confirmation",
                 "always_confirm")

    if resource and action in steering.resource_confirm.get(resource, set()):
        raise_to(REQUIRE_CONFIRMATION, "steering rule: actions on " + resource
                 + " require confirmation", "resources." + resource + ".always_confirm")

    if category in steering.confirm_categories:
        raise_to(REQUIRE_CONFIRMATION, "steering rule: the " + category
                 + " band requires confirmation", "confirm_categories")

    if steering.confirm_blast_at_least is not None and blast >= steering.confirm_blast_at_least:
        raise_to(REQUIRE_CONFIRMATION, "steering rule: blast radius " + str(blast)
                 + " reaches the configured confirmation threshold of "
                 + str(steering.confirm_blast_at_least),
                 "confirm_when.blast_radius_at_least")

    if steering.hours_start and not _within_hours(steering, now):
        raise_to(steering.outside_hours,
                 "steering rule: outside the permitted window "
                 + steering.hours_start + "-" + steering.hours_end + " "
                 + steering.hours_label, "allowed_hours")

    return {"floor": floor, "reasons": reasons, "matched": matched, "status": "active"}


# ------------------------------------------------------------------------- singleton

_current: Steering | None = None


def current() -> Steering:
    """The rules loaded at start-up.

    Deliberately not reloadable through the API. The Admin Security Terminal is
    read-only by design: an observer who could reload rules could change outcomes,
    which is exactly what that screen promises it cannot do. Changing the rules
    means editing the file and restarting the service, which leaves a start-up
    audit event carrying the new file's hash.
    """
    global _current
    if _current is None:
        _current = load()
    return _current


def set_current(steering: Steering) -> None:
    """Used by start-up and by tests."""
    global _current
    _current = steering
