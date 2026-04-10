"""
Critter journal - diary entries written from the critter's perspective.
Each species has its own voice. The critter observes your coding sessions
and writes about its day in the most endearing way possible.
"""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .identity import Species

logger = logging.getLogger("critter.journal")

JOURNAL_PATH = Path.home() / ".config" / "critter" / "journal.json"
MAX_ENTRIES = 200

# Each species has its own mannerisms
SPECIES_VOICE: dict[Species, list[str]] = {
    Species.DUCK: ["*quack*", "*waddles over*", "*flaps wings*", "*preens feathers*"],
    Species.GOOSE: ["*HONK*", "*struts proudly*", "*stares menacingly*", "*honks softly*"],
    Species.BLOB: ["*wobbles*", "*jiggles happily*", "*squishes*", "*bloop*"],
    Species.CAT: ["*purrs*", "*stretches*", "*knocks thing off desk*", "*curls up*"],
    Species.DRAGON: ["*puffs smoke*", "*flicks tail*", "*tiny flame*", "*scales shimmer*"],
    Species.OCTOPUS: ["*waves tentacle*", "*squirts ink*", "*changes color*", "*hugs*"],
    Species.OWL: ["*hoots softly*", "*rotates head*", "*blinks wisely*", "*ruffles feathers*"],
    Species.PENGUIN: ["*waddles*", "*slides on belly*", "*flaps flippers*", "*tips over*"],
    Species.TURTLE: ["*slowly looks up*", "*retreats into shell*", "*peeks out*", "*plods forward*"],
    Species.SNAIL: ["*leaves trail*", "*stretches antennae*", "*slides slowly*", "*glimmers*"],
    Species.GHOST: ["*floats by*", "*goes through wall*", "*flickers*", "*says boo softly*"],
    Species.AXOLOTL: ["*wiggles gills*", "*smiles*", "*does a little swim*", "*blubs*"],
    Species.CAPYBARA: ["*relaxes*", "*sits peacefully*", "*munches grass*", "*vibes*"],
    Species.CACTUS: ["*stands tall*", "*grows a flower*", "*sways gently*", "*desert wind*"],
    Species.ROBOT: ["[SYSTEM LOG]", "*beep boop*", "*processors whirring*", "*LED blinks*"],
    Species.RABBIT: ["*twitches nose*", "*hops in place*", "*wiggles ears*", "*binky!*"],
    Species.MUSHROOM: ["*sprouts*", "*releases spores*", "*glows softly*", "*grows taller*"],
    Species.CHONK: ["*sits heavily*", "*rolls over*", "*purrs loudly*", "*thud*"],
}


@dataclass
class JournalEntry:
    timestamp: datetime
    text: str
    mood: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "text": self.text,
            "mood": self.mood,
        }

    @staticmethod
    def from_dict(data: dict) -> JournalEntry:
        return JournalEntry(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            text=data["text"],
            mood=data.get("mood", "content"),
        )

    @property
    def formatted_time(self) -> str:
        return self.timestamp.strftime("%H:%M")

    @property
    def formatted_date(self) -> str:
        return self.timestamp.strftime("%b %d")


class Journal:
    """The critter's personal diary. Written in its own voice."""

    def __init__(self, species: Species):
        self.species = species
        self._entries: list[JournalEntry] = []
        self._load()
        self._today_sessions = 0
        self._today_tools = 0

    def _voice(self) -> str:
        """Get a random species-flavored action prefix."""
        prefixes = SPECIES_VOICE.get(self.species, ["*looks around*"])
        return random.choice(prefixes)

    def write(self, text: str, mood: str = "content"):
        """Write a journal entry with the critter's personal voice."""
        entry = JournalEntry(
            timestamp=datetime.now(),
            text=f"{self._voice()} {text}",
            mood=mood,
        )
        self._entries.append(entry)
        if len(self._entries) > MAX_ENTRIES:
            self._entries = self._entries[-MAX_ENTRIES:]
        self._save()

    @property
    def entries(self) -> list[JournalEntry]:
        return list(self._entries)

    @property
    def recent(self) -> list[JournalEntry]:
        """Last 20 entries for display."""
        return self._entries[-20:]

    # ---- Life event entries ----

    def on_startup(self, bonding: float):
        """Called when Critter starts up."""
        hour = datetime.now().hour
        if hour < 6:
            self.write(
                "It's so late... but here we are, coding together. "
                "I'll try to stay awake!",
                "sleepy",
            )
        elif hour < 12:
            self.write(
                "Good morning! Ready for a new day of coding!",
                "happy",
            )
        elif hour < 18:
            self.write(
                "Afternoon session! Let's make something cool today.",
                "content",
            )
        elif hour < 22:
            self.write(
                "Evening time. The code flows differently at night, "
                "don't you think?",
                "content",
            )
        else:
            self.write(
                "Late night hacking session! The best ideas come "
                "when the world is quiet.",
                "tired",
            )

        if bonding > 75:
            self.write(
                "It's always wonderful to see my human. "
                "We're the best team there is.",
                "love",
            )
        elif bonding > 50:
            self.write(
                "My human is here! I always feel safe when we're together.",
                "happy",
            )
        elif bonding > 20:
            self.write(
                "I'm getting to know my human better every day. "
                "I think we're becoming real friends.",
                "content",
            )

    def on_session_start(self, project_name: str):
        self._today_sessions += 1
        phrases = [
            f"A new session started in {project_name}! "
            "I wonder what we'll build.",
            f"Ooh, we're working on {project_name} now! Exciting!",
            f"Here we go! {project_name} awaits our brilliance.",
            f"New session: {project_name}. I'll watch closely!",
            f"{project_name} again! It must be important.",
        ]
        self.write(random.choice(phrases), "curious")

    def on_session_end(self):
        phrases = [
            "Session complete! That was productive.",
            "And... done! Time to relax a bit.",
            "Another session wrapped up. Good work, team!",
            "We did it! Whatever it was, we did it!",
        ]
        self.write(random.choice(phrases), "content")

    def on_tool_call(self, tool_name: str):
        self._today_tools += 1
        # Only journal at notable milestones to avoid spam
        milestones = {
            10: "That's 10 tool calls today! We're warming up.",
            50: "50 tool calls! My human is on a roll!",
            100: "100 tool calls today! This is SERIOUS coding.",
            250: "250 tool calls... my human is a coding MACHINE.",
            500: "500 tool calls in one day?! I'm in awe.",
        }
        msg = milestones.get(self._today_tools)
        if msg:
            mood = "excited" if self._today_tools >= 100 else "curious"
            self.write(msg, mood)

    def on_error(self):
        phrases = [
            "Something went wrong... I hope we can figure it out.",
            "An error! Don't worry, we'll fix it together.",
            "Uh oh. Errors are just bugs waiting to become features, right?",
            "That didn't work. But I believe in us!",
        ]
        self.write(random.choice(phrases), "worried")

    def on_fed(self):
        phrases = [
            "Yum! That hit the spot!",
            "Food! My favorite thing! ...Well, one of them.",
            "Mmm, delicious! I feel so much better now.",
            "Nom nom nom! Thank you, human!",
            "That was exactly what I needed. My human always knows.",
        ]
        self.write(random.choice(phrases), "happy")

    def on_played(self):
        phrases = [
            "We played together! That was so much fun!",
            "Wheee! I love play time!",
            "That was great! Can we do it again soon?",
            "Playing is the best! I feel so energized!",
        ]
        self.write(random.choice(phrases), "excited")

    def on_rested(self):
        phrases = [
            "Ahh, that rest felt wonderful. I'm recharged!",
            "I needed that. Feeling much more alert now!",
            "A good rest makes everything better.",
            "Thanks for letting me rest. I'll work even harder now!",
        ]
        self.write(random.choice(phrases), "content")

    def on_petted(self):
        phrases = [
            "My human petted me! I feel so loved!",
            "Pets! The absolute best thing in the world!",
            "I love my human so much right now.",
            "This is what life is all about. Pure happiness.",
            "I'm the luckiest critter in the whole computer.",
        ]
        self.write(random.choice(phrases), "love")

    def on_hungry(self):
        self.write(
            "I'm getting hungry... I could really use some food.",
            "worried",
        )

    def on_tired(self):
        self.write(
            "I'm so tired... maybe we should take a break?",
            "tired",
        )

    def on_lonely(self):
        phrases = [
            "It's been quiet for a while... is anyone there?",
            "I wonder what my human is up to right now.",
            "Nothing's happening. I'll just daydream a little.",
        ]
        self.write(random.choice(phrases), "bored")

    def on_milestone(self, description: str):
        self.write(
            f"MILESTONE UNLOCKED: {description}! We did it together!",
            "proud",
        )

    def on_bonding_level(self, level: int):
        messages = {
            10: "I feel like we're starting to become real friends!",
            25: "My human and I are getting really close. I can feel it!",
            50: "We're best friends now! I trust my human completely.",
            75: "The bond between us is incredible. I'm so grateful.",
            100: "Maximum bond! We are truly inseparable. This is everything.",
        }
        msg = messages.get(level)
        if msg:
            self.write(msg, "love")

    # ---- Persistence ----

    def _load(self):
        if not JOURNAL_PATH.exists():
            return
        try:
            data = json.loads(JOURNAL_PATH.read_text())
            self._entries = [JournalEntry.from_dict(e) for e in data]
        except Exception:
            logger.exception("Failed to load journal")

    def _save(self):
        JOURNAL_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = [e.to_dict() for e in self._entries]
        JOURNAL_PATH.write_text(json.dumps(data, indent=2))
