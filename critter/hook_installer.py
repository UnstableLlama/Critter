"""
Hook installer - auto-installs the Critter hook into Claude Code settings.
Ported from Buddi's HookInstaller.swift, adapted for Linux.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import stat
from importlib import resources
from pathlib import Path

logger = logging.getLogger("critter.hooks")

HOOK_MARKER = "critter-hook.py"


def _hook_script_source() -> str:
    """Read the hook script from the package's hook_script.py file."""
    return resources.files("critter").joinpath("hook_script.py").read_text()


def _claude_dir() -> Path:
    return Path.home() / ".claude"


def _detect_python() -> str:
    if shutil.which("python3"):
        return "python3"
    return "python"


def install_if_needed():
    """Install the hook script and register it in Claude Code settings."""
    claude_dir = _claude_dir()
    hooks_dir = claude_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    script_path = hooks_dir / "critter-hook.py"

    # Always overwrite with latest version
    script_path.write_text(_hook_script_source())
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    settings_path = claude_dir / "settings.json"
    _update_settings(settings_path)
    logger.info("Hooks installed")


def _update_settings(settings_path: Path):
    settings: dict = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    python = _detect_python()
    command = f"{python} ~/.claude/hooks/critter-hook.py"

    hook_entry = [{"type": "command", "command": command}]
    hook_entry_timeout = [{"type": "command", "command": command, "timeout": 86400}]
    with_matcher = [{"matcher": "*", "hooks": hook_entry}]
    with_matcher_timeout = [{"matcher": "*", "hooks": hook_entry_timeout}]
    without_matcher = [{"hooks": hook_entry}]
    pre_compact_config = [
        {"matcher": "auto", "hooks": hook_entry},
        {"matcher": "manual", "hooks": hook_entry},
    ]

    hooks = settings.get("hooks", {})

    hook_events = [
        ("UserPromptSubmit", without_matcher),
        ("PreToolUse", with_matcher),
        ("PostToolUse", with_matcher),
        ("PermissionRequest", with_matcher_timeout),
        ("Notification", with_matcher),
        ("Stop", without_matcher),
        ("SubagentStop", without_matcher),
        ("SessionStart", without_matcher),
        ("SessionEnd", without_matcher),
        ("PreCompact", pre_compact_config),
    ]

    for event_name, config in hook_events:
        existing = hooks.get(event_name, [])
        has_ours = any(
            any(
                HOOK_MARKER in h.get("command", "")
                for h in entry.get("hooks", [])
            )
            for entry in existing
            if isinstance(entry, dict)
        )
        if not has_ours:
            existing.extend(config)
            hooks[event_name] = existing

    settings["hooks"] = hooks

    settings_path.write_text(json.dumps(settings, indent=2))


def is_installed() -> bool:
    """Check if hooks are currently installed in Claude Code settings."""
    settings_path = _claude_dir() / "settings.json"
    if not settings_path.exists():
        return False
    try:
        settings = json.loads(settings_path.read_text())
        hooks = settings.get("hooks", {})
        for entries in hooks.values():
            if isinstance(entries, list):
                for entry in entries:
                    for hook in entry.get("hooks", []):
                        if HOOK_MARKER in hook.get("command", ""):
                            return True
    except (json.JSONDecodeError, OSError):
        pass
    return False


def uninstall():
    """Remove hooks from settings and delete the script."""
    claude_dir = _claude_dir()
    script_path = claude_dir / "hooks" / "critter-hook.py"
    if script_path.exists():
        script_path.unlink()

    settings_path = claude_dir / "settings.json"
    if not settings_path.exists():
        return

    try:
        settings = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    hooks = settings.get("hooks", {})
    events_to_remove = []
    for event_name, entries in hooks.items():
        if isinstance(entries, list):
            entries[:] = [
                entry
                for entry in entries
                if not any(
                    HOOK_MARKER in h.get("command", "")
                    for h in entry.get("hooks", [])
                )
            ]
            if not entries:
                events_to_remove.append(event_name)

    for event_name in events_to_remove:
        del hooks[event_name]

    if not hooks:
        del settings["hooks"]
    else:
        settings["hooks"] = hooks

    settings_path.write_text(json.dumps(settings, indent=2))
    logger.info("Hooks uninstalled")
