"""
Codex CLI hook installer.
Installs the Critter hook into OpenAI Codex CLI configuration.
Codex uses a hooks system nearly identical to Claude Code.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import stat
from pathlib import Path

logger = logging.getLogger("critter.hooks")

# Codex hook script - same protocol as Claude Code hook (Unix socket to Critter)
# but with Codex-specific field name mappings
CODEX_HOOK_SCRIPT = r'''#!/usr/bin/env python3
"""
Critter Hook for Codex CLI
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
    """Get the TTY of the Codex process (parent)"""
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
    return None


def send_event(state):
    """Send event to Critter app, return response if any"""
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

    codex_pid = os.getppid()
    tty = get_tty()

    # Prefix session ID to distinguish from Claude Code sessions
    state = {
        "session_id": f"codex-{session_id}",
        "cwd": cwd,
        "event": event,
        "pid": codex_pid,
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

    elif event == "Stop":
        state["status"] = "waiting_for_input"

    elif event == "SessionStart":
        state["status"] = "waiting_for_input"

    elif event == "SessionEnd":
        state["status"] = "ended"

    else:
        state["status"] = "unknown"

    send_event(state)


if __name__ == "__main__":
    main()
'''

HOOK_MARKER = "critter-codex-hook.py"


def _codex_dir() -> Path:
    """Codex CLI config directory."""
    return Path.home() / ".codex"


def _detect_python() -> str:
    if shutil.which("python3"):
        return "python3"
    return "python"


def install_if_needed():
    """Install the hook script and register it in Codex CLI config."""
    codex_dir = _codex_dir()

    # Only install if Codex appears to be installed
    if not codex_dir.exists():
        logger.debug("Codex dir not found at %s, skipping", codex_dir)
        return False

    hooks_dir = codex_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)

    script_path = hooks_dir / "critter-codex-hook.py"
    script_path.write_text(CODEX_HOOK_SCRIPT)
    script_path.chmod(script_path.stat().st_mode | stat.S_IEXEC)

    config_path = codex_dir / "config.json"
    _update_config(config_path)
    logger.info("Codex hooks installed")
    return True


def _update_config(config_path: Path):
    """Register hooks in Codex config.json."""
    config: dict = {}
    if config_path.exists():
        try:
            config = json.loads(config_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass

    python = _detect_python()
    command = f"{python} ~/.codex/hooks/critter-codex-hook.py"

    hook_entry = [{"type": "command", "command": command}]
    hook_entry_timeout = [{"type": "command", "command": command, "timeout": 86400}]
    with_matcher = [{"matcher": "*", "hooks": hook_entry}]
    with_matcher_timeout = [{"matcher": "*", "hooks": hook_entry_timeout}]
    without_matcher = [{"hooks": hook_entry}]

    hooks = config.get("hooks", {})

    hook_events = [
        ("UserPromptSubmit", without_matcher),
        ("PreToolUse", with_matcher),
        ("PostToolUse", with_matcher),
        ("PermissionRequest", with_matcher_timeout),
        ("Stop", without_matcher),
        ("SessionStart", without_matcher),
        ("SessionEnd", without_matcher),
    ]

    for event_name, event_config in hook_events:
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
            existing.extend(event_config)
            hooks[event_name] = existing

    config["hooks"] = hooks
    config_path.write_text(json.dumps(config, indent=2, sort_keys=True))


def is_installed() -> bool:
    """Check if Codex hooks are currently installed."""
    config_path = _codex_dir() / "config.json"
    if not config_path.exists():
        return False
    try:
        config = json.loads(config_path.read_text())
        hooks = config.get("hooks", {})
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
    """Remove Codex hooks and delete the script."""
    codex_dir = _codex_dir()
    script_path = codex_dir / "hooks" / "critter-codex-hook.py"
    if script_path.exists():
        script_path.unlink()

    config_path = codex_dir / "config.json"
    if not config_path.exists():
        return

    try:
        config = json.loads(config_path.read_text())
    except (json.JSONDecodeError, OSError):
        return

    hooks = config.get("hooks", {})
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
        config.pop("hooks", None)
    else:
        config["hooks"] = hooks

    config_path.write_text(json.dumps(config, indent=2, sort_keys=True))
    logger.info("Codex hooks uninstalled")
