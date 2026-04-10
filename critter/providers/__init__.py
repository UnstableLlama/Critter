"""Provider registry for LLM API stream parsers."""

from .anthropic import AnthropicProvider
from .base import BaseProvider, StreamEvent, StreamPhase
from .openai_compat import OpenAIProvider

PROVIDERS: dict[str, type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
}


def get_provider(name: str) -> BaseProvider:
    """Get a fresh provider instance by name."""
    cls = PROVIDERS.get(name)
    if not cls:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDERS)}")
    return cls()
