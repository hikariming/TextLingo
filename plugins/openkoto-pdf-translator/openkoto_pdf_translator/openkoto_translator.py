"""
OpenKoto-specific translator that accepts configuration via command line or config file.
This translator wraps the OpenAI-compatible API used by OpenKoto main application.
"""

import json
import logging
import os
from pathlib import Path
from string import Template

from .translator import OpenAITranslator

logger = logging.getLogger(__name__)


# Provider to base URL mapping (matching OpenKoto's ai_service.rs)
OPENKOTO_PROVIDER_URLS = {
    "openai": "https://api.openai.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "siliconflow": "https://api.siliconflow.cn/v1",
    "302ai": "https://api.302.ai/v1",
    "google-ai-studio": "https://generativelanguage.googleapis.com/v1beta/openai",
    "ollama": "http://localhost:11434/v1",
    "lmstudio": "http://localhost:1234/v1",
}

# Default models per provider
OPENKOTO_DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "openrouter": "openai/gpt-4o-mini",
    "deepseek": "deepseek-chat",
    "siliconflow": "Qwen/Qwen2.5-7B-Instruct",
    "302ai": "gpt-4o-mini",
    "google-ai-studio": "gemini-2.0-flash",
    "ollama": "llama3.2",
    "lmstudio": "local-model",
}


class OpenKotoTranslator(OpenAITranslator):
    """
    Translator that uses OpenKoto's model configuration.
    
    Accepts configuration via:
    1. Direct parameters (api_key, provider, model, base_url)
    2. Environment variables (OPENKOTO_API_KEY, OPENKOTO_PROVIDER, etc.)
    3. Config file (~/.openkoto/translator_config.json)
    """
    
    name = "openkoto"
    envs = {
        "OPENKOTO_API_KEY": None,
        "OPENKOTO_PROVIDER": "openai",
        "OPENKOTO_MODEL": None,
        "OPENKOTO_BASE_URL": None,
    }
    CustomPrompt = True

    def __init__(
        self,
        lang_in: str,
        lang_out: str,
        model: str = None,
        api_key: str = None,
        provider: str = None,
        base_url: str = None,
        envs: dict = None,
        prompt: Template = None,
        ignore_cache: bool = False,
        config_path: str = None,
        **kwargs
    ):
        self.set_envs(envs)
        
        # Load config from file if exists
        config = self._load_config(config_path)
        
        # Priority: direct params > env vars > config file
        provider = provider or self.envs.get("OPENKOTO_PROVIDER") or config.get("provider", "openai")
        api_key = api_key or self.envs.get("OPENKOTO_API_KEY") or config.get("api_key")
        model = model or self.envs.get("OPENKOTO_MODEL") or config.get("model") or OPENKOTO_DEFAULT_MODELS.get(provider)
        base_url = base_url or self.envs.get("OPENKOTO_BASE_URL") or config.get("base_url") or OPENKOTO_PROVIDER_URLS.get(provider)
        
        if not api_key and provider not in ("ollama", "lmstudio"):
            raise ValueError(
                f"API key is required for provider '{provider}'. "
                "Set via OPENKOTO_API_KEY env var or config file."
            )
        
        logger.info(f"OpenKoto Translator: provider={provider}, model={model}, base_url={base_url}")
        
        super().__init__(
            lang_in=lang_in,
            lang_out=lang_out,
            model=model,
            base_url=base_url,
            api_key=api_key or "no-key",  # For local providers
            ignore_cache=ignore_cache,
        )
        self.provider = provider
        self.prompttext = prompt
        self.add_cache_impact_parameters("prompt", self.prompt("", self.prompttext))

    def _load_config(self, config_path: str = None) -> dict:
        """Load configuration from JSON file."""
        if config_path:
            path = Path(config_path)
        else:
            path = Path.home() / ".openkoto" / "translator_config.json"
        
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load config from {path}: {e}")
        
        return {}

    @classmethod
    def from_openkoto_config(
        cls,
        lang_in: str,
        lang_out: str,
        provider: str,
        api_key: str,
        model: str,
        base_url: str = None,
        **kwargs
    ):
        """
        Create translator from OpenKoto main app configuration.
        This method is called by the main OpenKoto app when invoking PDF translation.
        """
        return cls(
            lang_in=lang_in,
            lang_out=lang_out,
            provider=provider,
            api_key=api_key,
            model=model,
            base_url=base_url,
            **kwargs
        )


def create_translator_from_args(args) -> OpenKotoTranslator:
    """
    Create a translator from command line arguments.
    Used by the CLI interface.
    """
    return OpenKotoTranslator(
        lang_in=getattr(args, 'lang_in', 'en'),
        lang_out=getattr(args, 'lang_out', 'zh'),
        provider=getattr(args, 'provider', None),
        api_key=getattr(args, 'api_key', None),
        model=getattr(args, 'model', None),
        base_url=getattr(args, 'base_url', None),
        config_path=getattr(args, 'config', None),
    )
