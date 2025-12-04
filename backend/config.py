"""Configuration for the LLM Council (CLI-based).

This configuration defines which models participate in the council and how
we invoke the various provider CLIs. All model identifiers use the
"provider:model_id" convention, e.g.:
- "codex:gpt-5.1-codex"
- "claude:claude-sonnet-4-20250514"
- "gemini:gemini-2.5-pro"
- "grok:grok-4"
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Paths to CLI tools (can be overridden via environment variables)
CODEX_CLI = os.getenv("CODEX_CLI", "codex")
CLAUDE_CLI = os.getenv("CLAUDE_CLI", "claude")
GEMINI_CLI = os.getenv("GEMINI_CLI", "gemini")
GROK_CLI = os.getenv("GROK_CLI", "grok")

# Default timeout (seconds) for individual CLI calls
DEFAULT_TIMEOUT = float(os.getenv("LLM_CLI_TIMEOUT", "120"))

# Council members - list of provider-prefixed model identifiers.
# NOTE: These are examples and may need to be updated to match the models
# currently available in your Codex / Claude / Gemini / Grok setup.
COUNCIL_MODELS = [
    # Codex / OpenAI models
    "codex:gpt-5.1-codex",
    "codex:gpt-5.1-codex-mini",

    # Claude (Anthropic)
    "claude:claude-sonnet-4-20250514",

    # Gemini (Google)
    "gemini:gemini-2.5-pro",

    # Grok (xAI)
    "grok:grok-4",
]

# Chairman model - synthesizes final response
CHAIRMAN_MODEL = "codex:gpt-5.1-codex"

# Data directory for conversation storage
DATA_DIR = "data/conversations"
