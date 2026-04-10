"""
Buddy detector - generates a deterministic identity from the user's Claude config.
Ported from Buddi's BuddyDetector.swift.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from .identity import BuddyIdentity, Eye, Hat, Rarity, Species
from .mulberry32 import Mulberry32
from .wyhash import hash_str

DEFAULT_SALT = "friend-2026-401"


def _config_candidates() -> list[Path]:
    candidates: list[Path] = []

    custom = os.environ.get("CLAUDE_CONFIG_DIR", "")
    if custom:
        p = Path(custom).expanduser()
        if p.suffix == ".json":
            candidates.append(p)
        else:
            candidates.append(p / ".claude.json")
            candidates.append(p / ".config.json")
            candidates.append(p / "config.json")

    home = Path.home()
    candidates.append(home / ".claude.json")
    candidates.append(home / ".claude" / ".config.json")

    # Deduplicate while preserving order
    seen: set[str] = set()
    unique: list[Path] = []
    for c in candidates:
        key = str(c)
        if key not in seen:
            seen.add(key)
            unique.append(c)
    return unique


def _load_config() -> dict | None:
    for path in _config_candidates():
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _detect_user_id() -> str:
    config = _load_config()
    if config is None:
        return "anon"
    # oauthAccount.accountUuid or userID
    oauth = config.get("oauthAccount", {})
    uid = oauth.get("accountUuid") or config.get("userID")
    return uid or "anon"


def _roll_rarity(rng: Mulberry32) -> Rarity:
    total = sum(r.weight for r in Rarity)
    roll = rng.next() * total
    for rarity in Rarity:
        roll -= rarity.weight
        if roll < 0:
            return rarity
    return Rarity.COMMON


def _pick(rng: Mulberry32, values: list):
    index = int(math.floor(rng.next() * len(values)))
    return values[min(index, len(values) - 1)]


def roll(user_id: str, salt: str = DEFAULT_SALT) -> BuddyIdentity:
    """Roll a deterministic buddy identity from user_id + salt."""
    h = hash_str(user_id + salt)
    seed = h & 0xFFFFFFFF  # truncate to u32
    rng = Mulberry32(seed)

    rarity = _roll_rarity(rng)
    species = _pick(rng, list(Species))
    eye = _pick(rng, list(Eye))
    hat = Hat.NONE if rarity == Rarity.COMMON else _pick(rng, list(Hat))

    return BuddyIdentity(species=species, rarity=rarity, eye=eye, hat=hat)


def detect(salt: str = DEFAULT_SALT) -> BuddyIdentity:
    """Detect identity from the user's Claude config."""
    config = _load_config()
    user_id = "anon"
    name = None

    if config:
        oauth = config.get("oauthAccount", {})
        user_id = oauth.get("accountUuid") or config.get("userID") or "anon"
        companion = config.get("companion", {})
        name = companion.get("name") if companion else None

    identity = roll(user_id, salt)
    identity.name = name
    return identity
