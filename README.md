# LLM Council

![llmcouncil](header.jpg)

The idea of this repo is that instead of asking a question to your favorite LLM provider (e.g. OpenAI GPT 5.1, Google Gemini 3.0 Pro, Anthropic Claude Sonnet 4.5, xAI Grok 4, etc.), you can group them into your "LLM Council". This repo is a simple, local web app that essentially looks like ChatGPT except it uses **local CLI tools** from each provider to send your query to multiple LLMs. The LLMs then review and rank each other's work, and finally a Chairman LLM produces the final response.

**This fork has been modified** to use subscription-based CLI tools (Codex, Claude, Gemini, Grok) instead of the original OpenRouter API approach, eliminating per-token API costs.

In a bit more detail, here is what happens when you submit a query:

1. **Stage 1: First opinions**. The user query is given to all LLMs individually, and the responses are collected. The individual responses are shown in a "tab view", so that the user can inspect them all one by one.
2. **Stage 2: Review**. Each individual LLM is given the responses of the other LLMs. Under the hood, the LLM identities are anonymized so that the LLM can't play favorites when judging their outputs. The LLM is asked to rank them in accuracy and insight.
3. **Stage 3: Final response**. The designated Chairman of the LLM Council takes all of the model's responses and compiles them into a single final answer that is presented to the user.

## Vibe Code Alert

This project was 99% vibe coded as a fun Saturday hack because I wanted to explore and evaluate a number of LLMs side by side in the process of [reading books together with LLMs](https://x.com/karpathy/status/1990577951671509438). It's nice and useful to see multiple responses side by side, and also the cross-opinions of all LLMs on each other's outputs. I'm not going to support it in any way, it's provided here as is for other people's inspiration and I don't intend to improve it. Code is ephemeral now and libraries are over, ask your LLM to change it in whatever way you like.

## Setup

### 1. Install CLI Tools

This project requires the following CLI tools to be installed and authenticated:

- **Codex CLI** (for OpenAI models): [Installation docs](https://docs.codex.xyz/installation)
- **Claude CLI** (for Anthropic models): [Installation docs](https://docs.anthropic.com/claude/docs/claude-cli)
- **Gemini CLI** (for Google models): [Installation docs](https://ai.google.dev/gemini-api/docs/cli)
- **Grok One-Shot CLI** (for xAI models): Install via npm:
  ```bash
  npm install -g @xagent/one-shot
  ```

**Authentication:**

- **Codex**: Run `codex` and follow login prompts
- **Claude**: Configure via `~/.config/claude/config.json` or run `claude` for setup
- **Gemini**: Run `gemini` and follow authentication flow
- **Grok**: Set your X API key (see step 2 below)

### 2. Install Project Dependencies

The project uses [uv](https://docs.astral.sh/uv/) for Python dependency management.

**Backend:**
```bash
uv sync
```

**Frontend:**
```bash
cd frontend
npm install
cd ..
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Grok / xAI API key (get from https://console.x.ai)
GROK_API_KEY=xai-...
X_API_KEY=xai-...
XAI_API_KEY=xai-...

# Optional: Override CLI tool paths if not in standard locations
# CODEX_CLI=codex
# CLAUDE_CLI=claude
# GEMINI_CLI=gemini
# GROK_CLI=grok
```

**Note:** Codex, Claude, and Gemini CLIs manage their own authentication separately. Only Grok requires an API key in `.env`.

### 4. Configure Models (Optional)

Edit `backend/config.py` to customize the council. Models use the `provider:model_id` convention:

```python
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

CHAIRMAN_MODEL = "codex:gpt-5.1-codex"
```

**Model naming conventions:**
- `codex:<openai-model-name>` - any OpenAI model accessible via Codex CLI
- `claude:<anthropic-model-name>` - any Claude model (use full dated identifiers)
- `gemini:<google-model-name>` - any Gemini model
- `grok:<xai-model-name>` - any Grok model (e.g., `grok-4`, `grok-4.1`)

## Running the Application

**Option 1: Use the start script**
```bash
./start.sh
```

**Option 2: Run manually**

Terminal 1 (Backend):
```bash
uv run python -m backend.main
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open http://localhost:5173 in your browser.

## Tech Stack

- **Backend:** FastAPI (Python 3.10+), async subprocess calls to CLI tools
- **LLM Integration:** Codex CLI, Claude CLI, Gemini CLI, Grok One-Shot CLI
- **Frontend:** React + Vite, react-markdown for rendering
- **Storage:** JSON files in `data/conversations/`
- **Package Management:** uv for Python, npm for JavaScript

## Architecture Changes from Original

This fork replaces the OpenRouter HTTP API with direct CLI tool invocations:

- **Original:** `backend/openrouter.py` using `httpx` to call OpenRouter API
- **This fork:** `backend/cli_adapter.py` using `asyncio.create_subprocess_exec` to shell out to:
  - `codex exec "<prompt>" -m <model> --json`
  - `claude --print --output-format json --model <model> "<prompt>"`
  - `gemini -p "<prompt>" -m <model>`
  - `grok -p "<prompt>" -m <model> -q`

**Benefits:**
- No per-token API costs (uses subscription-based CLI access)
- Direct integration with provider CLIs
- Easier credential management (CLIs handle their own auth)

**Trade-offs:**
- Requires installing and authenticating 4 separate CLI tools
- CLI output parsing can be less standardized than API responses
- Subprocess overhead vs. direct HTTP calls
