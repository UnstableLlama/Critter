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
from pathlib import Path

logger = logging.getLogger("critter.hooks")

# The hook script content (same as buddi-hook.py but with critter socket path)
HOOK_SCRIPT = r'''#!/usr/bin/env python3
"""
Critter Hook
- Sends session state to Critter via Unix socket
- For PermissionRequest: waits for user decision from the app
"""
import json
import os
import socket
import sys

SOCKET_PATH = "/tmp/critter.sock"
TIMEOUT_SECONDS = 300  # 5 minutes for permission decisions


def get_tty():
    """Get the TTY of the Claude process (parent)"""
    import subprocess

    ppid = os.getppid()
    try:
        result = subprocess.run(
            ["ps", "-p", str(ppid), "-o", "tty="],
            capture_output=True,
            text=True,
            timeout=2,
        )
        tty = result.stdout.strip()
        if tty and tty != "??" and tty != "-":
            if not tty.startswith("/dev/"):
                tty = "/dev/" + tty
            return tty
    except Exception:
        pass
    try:
        return os.ttyname(sys.stdin.fileno())
    except (OSError, AttributeError):
        pass
    try:
        return os.ttyname(sys.stdout.fileno())
    except (OSError, AttributeError):
        pass
    return None


def send_event(state):
    """Send event to app, return response if any"""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT_SECONDS)
        sock.connect(SOCKET_PATH)
        sock.sendall(json.dumps(state).encode())

        if state.get("status") == "waiting_for_approval":
            response = sock.recv(4096)
            sock.close()
            if response:
                return json.loads(response.decode())
        else:
            sock.close()
        return None
    except (socket.error, OSError, json.JSONDecodeError):
        return None


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        sys.exit(1)

    session_id = data.get("session_id", "unknown")
    event = data.get("hook_event_name", "")
    cwd = data.get("cwd", "")
    tool_input = data.get("tool_input", {})

    claude_pid = os.getppid()
    tty = get_tty()

    state = {
        "session_id": session_id,
        "cwd": cwd,
        "event": event,
        "pid": claude_pid,
        "tty": tty,
    }

    if event == "UserPromptSubmit":
        state["status"] = "processing"

    elif event == "PreToolUse":
        state["status"] = "running_tool"
        state["tool"] = data.get("tool_name")
        state["tool_input"] = tool_input
        tool_use_id = data.get("tool_use_id")
        if tool_use_id:
            state["tool_use_id"] = tool_use_id

    elif event == "PostToolUse":
        state["status"] = "processing"
        state["tool"] = data.get("tool_name")
        state["tool_input"] = tool_input
        tool_use_id = data.get("tool_use_id")
        if tool_use_id:
            state["tool_use_id"] = tool_use_id

    elif event == "PermissionRequest":
        state["status"] = "waiting_for_approval"
        state["tool"] = data.get("tool_name")
        state["tool_input"] = tool_input

        response = send_event(state)
        if response:
            decision = response.get("decision", "ask")
            reason = response.get("reason", "")

            if decision == "allow":
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PermissionRequest",
                        "decision": {"behavior": "allow"},
                    }
                }
                print(json.dumps(output))
                sys.exit(0)
            elif decision == "deny":
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PermissionRequest",
                        "decision": {
                            "behavior": "deny",
                            "message": reason or "Denied by user via Critter",
                        },
                    }
                }
                print(json.dumps(output))
                sys.exit(0)
        sys.exit(0)

    elif event == "Notification":
        notification_type = data.get("notification_type")
        if notification_type == "permission_prompt":
            sys.exit(0)
        elif notification_type == "idle_prompt":
            state["status"] = "waiting_for_input"
        else:
            state["status"] = "notification"
        state["notification_type"] = notification_type
        state["message"] = data.get("message")

    elif event == "Stop":
        state["status"] = "waiting_for_input"

    elif event == "SubagentStop":
        state["status"] = "waiting_for_input"

    elif event == "SessionStart":
        state["status"] = "waiting_for_input"

    elif event == "SessionEnd":
        state["status"] = "ended"

    elif event == "PreCompact":
        state["status"] = "compacting"

    else:
        state["status"] = "unknown"

    send_event(state)


if __name__ == "__main__":
    main()
'''

HOOK_MARKER = "critter-hook.py"


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
    script_path.write_text(HOOK_SCRIPT)
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

    settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True))


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

    settings_path.write_text(json.dumps(settings, indent=2, sort_keys=True))
    logger.info("Hooks uninstalled")
