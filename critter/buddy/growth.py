"""
Growth stages - the critter evolves as your bond deepens.
Higher bonding unlocks new visual elements and behaviors.
"""

from __future__ import annotations

from enum import Enum


class GrowthStage(str, Enum):
    """The critter's growth stage, determined by bonding level."""

    EGG = "egg"           # 0-5 bonding: just hatched
    BABY = "baby"         # 5-20: small and learning
    YOUNG = "young"       # 20-45: growing up
    ADULT = "adult"       # 45-70: mature
    ELDER = "elder"       # 70-90: wise
    LEGENDARY = "legendary"  # 90+: transcendent

    @staticmethod
    def from_bonding(bonding: float) -> GrowthStage:
        if bonding < 5:
            return GrowthStage.EGG
        if bonding < 20:
            return GrowthStage.BABY
        if bonding < 45:
            return GrowthStage.YOUNG
        if bonding < 70:
            return GrowthStage.ADULT
        if bonding < 90:
            return GrowthStage.ELDER
        return GrowthStage.LEGENDARY

    @property
    def display_name(self) -> str:
        return {
            GrowthStage.EGG: "Egg",
            GrowthStage.BABY: "Baby",
            GrowthStage.YOUNG: "Young",
            GrowthStage.ADULT: "Adult",
            GrowthStage.ELDER: "Elder",
            GrowthStage.LEGENDARY: "Legendary",
        }[self]

    @property
    def title_prefix(self) -> str:
        """Prefix added to the critter's name at higher stages."""
        return {
            GrowthStage.EGG: "",
            GrowthStage.BABY: "",
            GrowthStage.YOUNG: "",
            GrowthStage.ADULT: "",
            GrowthStage.ELDER: "Wise ",
            GrowthStage.LEGENDARY: "Great ",
        }[self]

    @property
    def decoration(self) -> str:
        """Extra ASCII decoration for the sprite at this stage."""
        return {
            GrowthStage.EGG: "",
            GrowthStage.BABY: "",
            GrowthStage.YOUNG: "",
            GrowthStage.ADULT: "",
            GrowthStage.ELDER: "  *",
            GrowthStage.LEGENDARY: " **",
        }[self]

    @property
    def unlocks(self) -> str:
        """Description of what this stage unlocks."""
        return {
            GrowthStage.EGG: "Your critter just hatched! Take care of it.",
            GrowthStage.BABY: "Your critter is learning the world.",
            GrowthStage.YOUNG: "Your critter is growing confident!",
            GrowthStage.ADULT: "A fully grown companion. You've come so far together.",
            GrowthStage.ELDER: "Wisdom comes with experience. Personalized observations unlocked.",
            GrowthStage.LEGENDARY: "The highest bond. Your critter is legendary.",
        }[self]


def check_growth_change(
    old_bonding: float, new_bonding: float
) -> GrowthStage | None:
    """Check if bonding change crossed a growth threshold.
    Returns the new stage if it changed, None otherwise.
    """
    old_stage = GrowthStage.from_bonding(old_bonding)
    new_stage = GrowthStage.from_bonding(new_bonding)
    if new_stage != old_stage:
        return new_stage
    return None
