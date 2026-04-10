"""
Hermes Agent plugin installer for Critter.
Installs a plugin into ~/.hermes/plugins/critter/ that sends
lifecycle events to Critter via Unix socket.

Hermes Agent hooks:
  - on_session_start: session begins
  - on_session_end: session ends
  - pre_llm_call: before each LLM API call
  - post_llm_call: after each LLM response
  - post_tool_call: after each tool execution (with tool_name, args, result)
"""

from __future__ import annotations

import logging
import os
import stat
from pathlib import Path

logger = logging.getLogger("critter.hooks")

HERMES_PLUGIN_DIR = Path.home() / ".hermes" / "plugins" / "critter"
PLUGIN_MARKER = "critter-hermes-plugin"

# The plugin manifest
PLUGIN_YAML = """\
name: critter
version: "1.0.0"
description: "Critter companion - sends agent activity to the Critter desktop buddy"
author: "Critter"
"""

# The plugin __init__.py - registers hooks that forward events to Critter's Unix socket
PLUGIN_INIT = r'''"""
Critter plugin for Hermes Agent.
Forwards lifecycle events to Critter desktop companion via Unix socket.
"""

import json
import logging
import os
import socket

logger = logging.getLogger("hermes.plugins.critter")

SOCKET_PATH = "/tmp/critter.sock"
_session_id = None


def _send_event(state: dict):
    """Send an event to Critter's Unix socket. Fire-and-forget."""
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect(SOCKET_PATH)
        sock.sendall(json.dumps(state).encode())
        sock.close()
    except (socket.error, OSError):
        pass  # Critter not running, that's fine


def _get_pid():
    return os.getpid()


def _on_session_start(**kwargs):
    """Hermes hook: session started."""
    global _session_id
    _session_id = kwargs.get("task_id", kwargs.get("session_id", f"hermes-{_get_pid()}"))

    _send_event({
        "session_id": f"hermes-{_session_id}",
        "cwd": os.getcwd(),
        "event": "SessionStart",
        "status": "waiting_for_input",
        "pid": _get_pid(),
    })


def _on_session_end(**kwargs):
    """Hermes hook: session ended."""
    sid = kwargs.get("task_id", kwargs.get("session_id", _session_id or "unknown"))
    _send_event({
        "session_id": f"hermes-{sid}",
        "cwd": os.getcwd(),
        "event": "SessionEnd",
        "status": "ended",
        "pid": _get_pid(),
    })


def _on_pre_llm_call(**kwargs):
    """Hermes hook: about to call the LLM."""
    sid = _session_id or "unknown"
    _send_event({
        "session_id": f"hermes-{sid}",
        "cwd": os.getcwd(),
        "event": "UserPromptSubmit",
        "status": "processing",
        "pid": _get_pid(),
    })


def _on_post_llm_call(**kwargs):
    """Hermes hook: LLM response received."""
    sid = _session_id or "unknown"
    _send_event({
        "session_id": f"hermes-{sid}",
        "cwd": os.getcwd(),
        "event": "Stop",
        "status": "waiting_for_input",
        "pid": _get_pid(),
    })


def _on_post_tool_call(tool_name="", args=None, result=None, task_id=None, **kwargs):
    """Hermes hook: tool call completed."""
    sid = task_id or _session_id or "unknown"
    _send_event({
        "session_id": f"hermes-{sid}",
        "cwd": os.getcwd(),
        "event": "PostToolUse",
        "status": "processing",
        "tool": tool_name,
        "tool_input": args if isinstance(args, dict) else {},
        "pid": _get_pid(),
    })


def register(ctx):
    """Called by Hermes to register our hooks."""
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("post_llm_call", _on_post_llm_call)
    ctx.register_hook("post_tool_call", _on_post_tool_call)
    logger.info("Critter plugin registered - forwarding events to %s", SOCKET_PATH)
'''


def install_if_needed() -> bool:
    """Install the Critter plugin into Hermes Agent."""
    hermes_dir = Path.home() / ".hermes"

    # Only install if Hermes appears to be installed
    if not hermes_dir.exists():
        logger.debug("Hermes dir not found at %s, skipping", hermes_dir)
        return False

    HERMES_PLUGIN_DIR.mkdir(parents=True, exist_ok=True)

    # Write plugin.yaml
    manifest_path = HERMES_PLUGIN_DIR / "plugin.yaml"
    manifest_path.write_text(PLUGIN_YAML)

    # Write __init__.py
    init_path = HERMES_PLUGIN_DIR / "__init__.py"
    init_path.write_text(PLUGIN_INIT)

    logger.info("Hermes Agent plugin installed at %s", HERMES_PLUGIN_DIR)
    return True


def is_installed() -> bool:
    """Check if the Critter plugin is installed in Hermes."""
    init_path = HERMES_PLUGIN_DIR / "__init__.py"
    return init_path.exists()


def uninstall():
    """Remove the Critter plugin from Hermes."""
    import shutil

    if HERMES_PLUGIN_DIR.exists():
        shutil.rmtree(HERMES_PLUGIN_DIR)
        logger.info("Hermes Agent plugin uninstalled")
