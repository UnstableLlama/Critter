"""
Buddy identity types - species, rarity, eyes, hats.
Ported from Buddi's BuddyIdentity.swift.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Species(str, Enum):
    DUCK = "duck"
    GOOSE = "goose"
    BLOB = "blob"
    CAT = "cat"
    DRAGON = "dragon"
    OCTOPUS = "octopus"
    OWL = "owl"
    PENGUIN = "penguin"
    TURTLE = "turtle"
    SNAIL = "snail"
    GHOST = "ghost"
    AXOLOTL = "axolotl"
    CAPYBARA = "capybara"
    CACTUS = "cactus"
    ROBOT = "robot"
    RABBIT = "rabbit"
    MUSHROOM = "mushroom"
    CHONK = "chonk"


class Rarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

    @property
    def weight(self) -> int:
        return {
            Rarity.COMMON: 60,
            Rarity.UNCOMMON: 25,
            Rarity.RARE: 10,
            Rarity.EPIC: 4,
            Rarity.LEGENDARY: 1,
        }[self]

    @property
    def stat_floor(self) -> int:
        return {
            Rarity.COMMON: 5,
            Rarity.UNCOMMON: 15,
            Rarity.RARE: 25,
            Rarity.EPIC: 35,
            Rarity.LEGENDARY: 50,
        }[self]

    @property
    def stars(self) -> str:
        count = list(Rarity).index(self) + 1
        return "\u2605" * count  # filled stars


class Eye(str, Enum):
    DOT = "\u00b7"      # ·
    SPARK = "\u2726"     # ✦
    CROSS = "\u00d7"     # ×
    TARGET = "\u25c9"    # ◉
    AT = "@"
    DEGREE = "\u00b0"    # °

    @property
    def display_name(self) -> str:
        return {
            Eye.DOT: "Dot",
            Eye.SPARK: "Spark",
            Eye.CROSS: "Cross",
            Eye.TARGET: "Target",
            Eye.AT: "At",
            Eye.DEGREE: "Degree",
        }[self]


class Hat(str, Enum):
    NONE = "none"
    CROWN = "crown"
    TOPHAT = "tophat"
    PROPELLER = "propeller"
    HALO = "halo"
    WIZARD = "wizard"
    BEANIE = "beanie"
    TINYDUCK = "tinyduck"


class Task(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    READING = "reading"
    SLEEPING = "sleeping"
    COMPACTING = "compacting"
    WAITING = "waiting"
    ERROR = "error"
    SUCCESS = "success"

    @property
    def face_suffix(self) -> str:
        return {
            Task.IDLE: "",
            Task.WORKING: "...",
            Task.READING: "...",
            Task.SLEEPING: " zzz",
            Task.COMPACTING: "~",
            Task.WAITING: "?",
            Task.ERROR: "!",
            Task.SUCCESS: "\u2713",
        }[self]


@dataclass
class BuddyIdentity:
    species: Species
    rarity: Rarity
    eye: Eye
    hat: Hat
    name: str | None = None
