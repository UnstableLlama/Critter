"""
Configuration system for Critter.
Loads backend definitions from ~/.config/critter/config.yml
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger("critter.config")

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "critter"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.yml"


@dataclass
class BackendConfig:
    """Configuration for a single LLM API backend proxy."""

    name: str
    url: str
    provider: str  # "openai" or "anthropic"
    proxy_port: int
    api_key: str | None = None
    api_key_env: str | None = None
    enabled: bool = True

    @property
    def resolved_api_key(self) -> str | None:
        """Resolve the API key from direct value or environment variable."""
        if self.api_key:
            return self.api_key
        if self.api_key_env:
            return os.environ.get(self.api_key_env)
        return None


@dataclass
class CritterConfig:
    """Top-level Critter configuration."""

    backends: list[BackendConfig] = field(default_factory=list)
    claude_code_hooks: bool = True
    codex_hooks: bool = True
    hermes_hooks: bool = True

    @staticmethod
    def load(path: Path | None = None) -> CritterConfig:
        """Load config from YAML file, falling back to defaults."""
        config_path = path or DEFAULT_CONFIG_PATH
        if not config_path.exists():
            logger.info("No config at %s, using defaults", config_path)
            return CritterConfig()

        try:
            raw = yaml.safe_load(config_path.read_text())
            if not raw or not isinstance(raw, dict):
                return CritterConfig()
            return CritterConfig._parse(raw)
        except Exception:
            logger.exception("Failed to load config from %s", config_path)
            return CritterConfig()

    @staticmethod
    def _parse(raw: dict) -> CritterConfig:
        backends = []
        for i, b in enumerate(raw.get("backends", []) or []):
            if not isinstance(b, dict):
                continue
            backends.append(
                BackendConfig(
                    name=b.get("name", f"backend-{i}"),
                    url=b.get("url", ""),
                    provider=b.get("provider", "openai"),
                    proxy_port=b.get("proxy_port", 9990 + i),
                    api_key=b.get("api_key"),
                    api_key_env=b.get("api_key_env"),
                    enabled=b.get("enabled", True),
                )
            )
        return CritterConfig(
            backends=backends,
            claude_code_hooks=raw.get("claude_code_hooks", True),
            codex_hooks=raw.get("codex_hooks", True),
            hermes_hooks=raw.get("hermes_hooks", True),
        )

    @staticmethod
    def create_default_config():
        """Write a default example config file if none exists."""
        DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if DEFAULT_CONFIG_PATH.exists():
            return
        DEFAULT_CONFIG_PATH.write_text(DEFAULT_EXAMPLE_CONFIG)
        logger.info("Created default config at %s", DEFAULT_CONFIG_PATH)


def detect_local_backends() -> list[BackendConfig]:
    """
    Probe common local ports for running LLM services.
    Returns BackendConfig entries for any detected services.
    """
    import socket

    probes = [
        ("Ollama", "http://localhost:11434", "openai", 11434, 9992),
        ("llama.cpp", "http://localhost:8080", "openai", 8080, 9993),
        ("TabbyAPI", "http://localhost:5000", "openai", 5000, 9994),
    ]

    found = []
    for name, url, provider, check_port, proxy_port in probes:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.3)
            result = sock.connect_ex(("127.0.0.1", check_port))
            sock.close()
            if result == 0:
                found.append(
                    BackendConfig(
                        name=name,
                        url=url,
                        provider=provider,
                        proxy_port=proxy_port,
                    )
                )
                logger.info("Detected local backend: %s on port %d", name, check_port)
        except Exception:
            pass

    return found


DEFAULT_EXAMPLE_CONFIG = """\
# Critter Configuration
# Add LLM API backends here. Critter will proxy requests and react to the stream.
# Point your client at 127.0.0.1:<proxy_port> instead of the backend URL.

# Enable/disable hook-based integrations
claude_code_hooks: true
codex_hooks: true
hermes_hooks: true

# API backends (each gets its own transparent proxy)
backends:
  # Example: OpenAI API
  # - name: "OpenAI"
  #   url: "https://api.openai.com"
  #   provider: "openai"
  #   proxy_port: 9990
  #   api_key_env: "OPENAI_API_KEY"

  # Example: Anthropic API
  # - name: "Anthropic"
  #   url: "https://api.anthropic.com"
  #   provider: "anthropic"
  #   proxy_port: 9991
  #   api_key_env: "ANTHROPIC_API_KEY"

  # Example: Ollama (local, auto-detected if running)
  # - name: "Ollama"
  #   url: "http://localhost:11434"
  #   provider: "openai"
  #   proxy_port: 9992

  # Example: llama.cpp (local)
  # - name: "llama.cpp"
  #   url: "http://localhost:8080"
  #   provider: "openai"
  #   proxy_port: 9993

  # Example: TabbyAPI / exllamav3 (local)
  # - name: "TabbyAPI"
  #   url: "http://localhost:5000"
  #   provider: "openai"
  #   proxy_port: 9994

  # Tip: Hermes Agent can also be monitored through the proxy!
  # In your Hermes config.yaml, point the provider URL at the proxy:
  #   e.g. api_base: "http://127.0.0.1:9990" (for OpenAI-format backends)
  # The Hermes plugin (auto-installed) also provides hook-based tracking.
"""
