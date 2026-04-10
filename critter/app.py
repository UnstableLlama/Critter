"""
Critter GTK4 Application.
Wires together: hook servers, proxy servers, session store, buddy system,
emotional life (mood, stats, journal, milestones), and UI.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Adw

from .buddy.detector import detect as detect_buddy
from .buddy.dreams import DreamEngine
from .buddy.growth import GrowthStage, check_growth_change
from .buddy.journal import Journal
from .buddy.memory import CritterMemory
from .buddy.milestones import check_milestones
from .buddy.mood import Mood, MoodEngine
from .buddy.stats import CritterStats
from .codex_hook_installer import install_if_needed as install_codex_hooks
from .config import CritterConfig, detect_local_backends
from .hook_installer import install_if_needed as install_claude_hooks
from .hook_server import HookSocketServer
from .providers import get_provider
from .providers.base import StreamEvent
from .proxy import ProxyServer
from .session_state import HookEvent, PhaseKind
from .session_store import SessionStore
from .ui.main_window import MainWindow

logger = logging.getLogger("critter")

# How often to decay stats and check mood (milliseconds)
STAT_TICK_MS = 30_000  # 30 seconds
SAVE_TICK_MS = 120_000  # 2 minutes
LONELY_MINUTES = 30  # How long before the critter gets lonely


class CritterApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.critter.app")
        self.connect("activate", self._on_activate)
        self.connect("shutdown", self._on_shutdown)

        self._identity = detect_buddy()
        self._store = SessionStore()
        self._server = HookSocketServer()
        self._proxies: list[ProxyServer] = []
        self._config: CritterConfig | None = None
        self._window: MainWindow | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None

        # Emotional life
        self._stats = CritterStats.load()
        self._mood_engine = MoodEngine()
        self._journal = Journal(self._identity.species)
        self._memory = CritterMemory.load()
        self._dreams = DreamEngine(self._identity.species.value)
        self._growth_stage = GrowthStage.from_bonding(self._stats.bonding)
        self._last_lonely_check = 0
        self._stat_timer_id: int | None = None
        self._save_timer_id: int | None = None
        self._bonding_thresholds_notified: set[int] = set()
        self._observation_counter = 0

    def _on_activate(self, app):
        if self._window:
            self._window.present()
            return

        # Load config
        self._config = CritterConfig.load()
        CritterConfig.create_default_config()

        # Install hooks
        if self._config.claude_code_hooks:
            try:
                install_claude_hooks()
                logger.info("Claude Code hooks installed/verified")
            except Exception:
                logger.exception("Failed to install Claude Code hooks")

        if self._config.codex_hooks:
            try:
                install_codex_hooks()
                logger.info("Codex hooks installed/verified")
            except Exception:
                logger.exception("Failed to install Codex hooks")

        # Journal startup entry
        self._journal.on_startup(self._stats.bonding)

        # Derive initial mood
        self._update_mood()

        # Create window with all the emotional life wiring
        self._window = MainWindow(
            app=self,
            identity=self._identity,
            on_approve=self._approve_session,
            on_deny=self._deny_session,
            on_feed=self._on_feed,
            on_play=self._on_play,
            on_rest=self._on_rest,
            on_pet=self._on_pet,
            journal=self._journal,
        )
        self._window.present()
        self._window.start_animation()
        self._window.update_stats(self._stats)
        self._window.update_mood(self._mood_engine.mood)
        self._window.update_growth(self._growth_stage)

        # Wire store -> UI updates
        self._store.set_on_change(self._schedule_ui_update)

        # Start background async event loop
        self._loop = asyncio.new_event_loop()
        self._loop_thread = threading.Thread(
            target=self._run_async_loop, daemon=True
        )
        self._loop_thread.start()

        # Start Unix socket server
        asyncio.run_coroutine_threadsafe(
            self._server.start(on_event=self._on_hook_event), self._loop
        )

        # Start proxy servers
        self._start_proxies()
        self._auto_detect_backends()

        # Start stat decay timer
        self._stat_timer_id = GLib.timeout_add(STAT_TICK_MS, self._on_stat_tick)
        self._save_timer_id = GLib.timeout_add(SAVE_TICK_MS, self._on_save_tick)

        # Check for any milestones from offline progress
        self._check_milestones()

        logger.info(
            "Critter started - %s %s (%s) - bonding: %.1f - %d backend(s)",
            self._identity.species.value,
            self._identity.eye.display_name,
            self._identity.rarity.value,
            self._stats.bonding,
            len(self._proxies),
        )

    # ---- Tamagotchi button handlers ----

    def _on_feed(self):
        reaction = self._stats.feed()
        self._journal.on_fed()
        self._mood_engine.set_temporary_mood(Mood.HAPPY, ticks=12)
        self._after_button(reaction)

    def _on_play(self):
        reaction = self._stats.play()
        self._journal.on_played()
        self._mood_engine.set_temporary_mood(Mood.EXCITED, ticks=12)
        self._after_button(reaction)

    def _on_rest(self):
        reaction = self._stats.rest()
        self._journal.on_rested()
        self._mood_engine.set_temporary_mood(Mood.CONTENT, ticks=8)
        self._after_button(reaction)

    def _on_pet(self):
        old_bonding = self._stats.bonding
        reaction = self._stats.pet()
        self._journal.on_petted()
        self._mood_engine.set_temporary_mood(Mood.LOVE, ticks=15)
        self._check_bonding_levels()
        self._check_growth(old_bonding)
        self._after_button(reaction)

    def _after_button(self, reaction: str):
        """Common post-button logic: update UI, check milestones."""
        self._update_mood()
        self._check_milestones()
        if self._window:
            self._window.show_reaction(reaction)
            self._window.update_stats(self._stats)
            self._window.update_mood(self._mood_engine.mood)
        self._stats.save()

    # ---- Stat ticking ----

    def _on_stat_tick(self) -> bool:
        """Periodic stat decay and mood update."""
        is_active = any(
            s.phase.kind == PhaseKind.PROCESSING for s in self._store.sessions
        )
        self._stats.decay(is_active=is_active)
        self._mood_engine.tick()
        self._update_mood()

        if self._window:
            self._window.update_stats(self._stats)
            self._window.update_mood(self._mood_engine.mood)

        # Lonely check - journal entry if idle for too long
        self._last_lonely_check += 1
        if (
            not self._store.sessions
            and self._last_lonely_check >= (LONELY_MINUTES * 60 // (STAT_TICK_MS // 1000))
        ):
            if self._stats.happiness < 50:
                self._journal.on_lonely()
            self._last_lonely_check = 0

        # Low stat warnings (journal) - but not too frequently
        if self._stats.hunger < 20 and self._stats.hunger > 18:
            self._journal.on_hungry()
        if self._stats.energy < 20 and self._stats.energy > 18:
            self._journal.on_tired()

        # Dream check (once per night when sleepy)
        self._dreams.maybe_dream(self._stats, self._journal)

        # Periodic memory observation (elder+ critters share wisdom)
        self._observation_counter += 1
        if (
            self._observation_counter >= 60
            and self._growth_stage
            in (GrowthStage.ELDER, GrowthStage.LEGENDARY)
        ):
            observation = self._memory.generate_observation()
            if observation:
                self._journal.write(observation, "content")
            self._observation_counter = 0

        self._check_milestones()
        return True  # keep timer

    def _on_save_tick(self) -> bool:
        """Periodic save to disk."""
        self._stats.save()
        self._memory.save()
        return True

    def _update_mood(self):
        """Derive mood from current stats and activity."""
        is_active = any(
            s.phase.kind == PhaseKind.PROCESSING for s in self._store.sessions
        )
        self._mood_engine.derive(
            hunger=self._stats.hunger,
            happiness=self._stats.happiness,
            energy=self._stats.energy,
            bonding=self._stats.bonding,
            is_active=is_active,
        )

    def _check_milestones(self):
        """Check for newly achieved milestones."""
        new_milestones = check_milestones(self._stats)
        for m in new_milestones:
            logger.info("Milestone achieved: %s - %s", m.name, m.description)
            self._stats.on_milestone()
            self._journal.on_milestone(m.description)
            self._dreams.record_milestone()
            self._mood_engine.set_temporary_mood(Mood.PROUD, ticks=20)
            if self._window:
                self._window.show_milestone(f"Milestone: {m.name}!")

    def _check_growth(self, old_bonding: float):
        """Check if the critter grew to a new stage."""
        new_stage = check_growth_change(old_bonding, self._stats.bonding)
        if new_stage:
            self._growth_stage = new_stage
            logger.info("Critter grew to %s stage!", new_stage.display_name)
            self._journal.write(
                f"I feel different... I've grown! I'm a {new_stage.display_name} "
                f"now! {new_stage.unlocks}",
                "proud",
            )
            self._mood_engine.set_temporary_mood(Mood.PROUD, ticks=25)
            if self._window:
                self._window.update_growth(new_stage)
                self._window.show_milestone(
                    f"Growth: {new_stage.display_name}!"
                )

    def _check_bonding_levels(self):
        """Check if bonding crossed a notification threshold."""
        for level in (10, 25, 50, 75, 100):
            if (
                self._stats.bonding >= level
                and level not in self._bonding_thresholds_notified
            ):
                self._bonding_thresholds_notified.add(level)
                self._journal.on_bonding_level(level)

    # ---- Proxy servers ----

    def _start_proxies(self):
        if not self._config:
            return
        for backend in self._config.backends:
            if not backend.enabled or not backend.url:
                continue
            self._start_proxy(
                backend.name, backend.url, backend.provider, backend.proxy_port
            )

    def _auto_detect_backends(self):
        configured_names = set()
        if self._config:
            configured_names = {b.name for b in self._config.backends if b.enabled}
        for backend in detect_local_backends():
            if backend.name not in configured_names:
                logger.info(
                    "Auto-detected %s at %s, proxying on port %d",
                    backend.name, backend.url, backend.proxy_port,
                )
                self._start_proxy(
                    backend.name, backend.url, backend.provider, backend.proxy_port
                )

    def _start_proxy(self, name: str, url: str, provider_name: str, port: int):
        try:
            provider = get_provider(provider_name)
        except ValueError:
            logger.error("Unknown provider %s for backend %s", provider_name, name)
            return
        proxy = ProxyServer(
            backend_name=name,
            backend_url=url,
            provider=provider,
            listen_port=port,
            on_event=self._on_proxy_event,
        )
        self._proxies.append(proxy)
        asyncio.run_coroutine_threadsafe(proxy.start(), self._loop)

    # ---- Event handlers ----

    def _on_hook_event(self, event: HookEvent):
        """Called from async thread on hook event."""
        self._store.process_hook(event)

        # Track in memory
        self._memory.remember_activity()

        # Track in stats
        if event.event == "SessionStart":
            self._stats.on_session_start()
            project = event.cwd.rsplit("/", 1)[-1] if event.cwd else "unknown"
            self._journal.on_session_start(project)
            self._memory.remember_project(project)
            self._last_lonely_check = 0

        if event.event in ("PreToolUse", "PostToolUse"):
            self._stats.on_tool_call()
            if event.tool:
                self._journal.on_tool_call(event.tool)
                self._memory.remember_tool(event.tool)
                self._dreams.record_tool(event.tool)

        if event.event == "SessionEnd":
            self._journal.on_session_end()

        if event.event == "Stop":
            self._stats.on_success()
            self._server.cancel_pending(event.session_id)

        if event.event == "PostToolUse" and event.tool_use_id:
            self._server.cancel_specific(event.tool_use_id)

    def _on_proxy_event(
        self, session_id: str, backend_name: str, event: StreamEvent
    ):
        """Called from async thread on proxy stream event."""
        self._store.process_proxy_event(session_id, backend_name, event)
        self._last_lonely_check = 0

    # ---- Lifecycle ----

    def _on_shutdown(self, app):
        # Save everything on exit
        self._stats.save()
        self._memory.save()

        if self._stat_timer_id:
            GLib.source_remove(self._stat_timer_id)
        if self._save_timer_id:
            GLib.source_remove(self._save_timer_id)

        if self._window:
            self._window.stop_animation()

        if self._loop:
            asyncio.run_coroutine_threadsafe(self._server.stop(), self._loop)
            for proxy in self._proxies:
                asyncio.run_coroutine_threadsafe(proxy.stop(), self._loop)
            self._loop.call_soon_threadsafe(self._loop.stop)

    def _run_async_loop(self):
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def _schedule_ui_update(self):
        GLib.idle_add(self._update_ui)

    def _update_ui(self) -> bool:
        if self._window:
            self._window.update_sessions(self._store.sessions)
        return False

    def _approve_session(self, session_id: str):
        session = self._store.session(session_id)
        if not session or not session.active_permission:
            return
        tool_use_id = session.active_permission.tool_use_id
        self._server.respond_to_permission(tool_use_id, "allow")
        self._store.process_permission_approved(session_id, tool_use_id)
        self._memory.remember_approval()

    def _deny_session(self, session_id: str):
        session = self._store.session(session_id)
        if not session or not session.active_permission:
            return
        tool_use_id = session.active_permission.tool_use_id
        self._server.respond_to_permission(tool_use_id, "deny", "Denied via Critter")
        self._store.process_permission_denied(session_id, tool_use_id)
        self._memory.remember_denial()


def run():
    """Entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    app = CritterApp()
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, app.quit)
    app.run(None)
