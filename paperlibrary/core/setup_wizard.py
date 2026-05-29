"""First-run setup wizard.

Runs interactively in the terminal when no .env (or an incomplete one)
is found.  Writes the result to .env next to the script so subsequent
starts skip the wizard entirely.
"""

from __future__ import annotations

from pathlib import Path

# (key, display name, llm_provider value, default model, default base_url)
_PROVIDERS = [
    ("1", "Anthropic (Claude)",        "anthropic",         "claude-haiku-4-5",  None),
    ("2", "OpenAI",                    "openai-compatible", "gpt-4o-mini",       "https://api.openai.com/v1"),
    ("3", "DeepSeek",                  "openai-compatible", "deepseek-chat",     "https://api.deepseek.com/v1"),
    ("4", "MiniMax",                   "openai-compatible", "MiniMax-M2.7",      "https://api.minimax.io/v1"),
    ("5", "Other (OpenAI-compatible)", "openai-compatible", None,                None),
]


def _ask(prompt: str, default: str | None = None) -> str:
    """Print prompt and read a non-empty answer from stdin."""
    hint = f" [{default}]" if default else ""
    while True:
        value = input(f"{prompt}{hint}: ").strip()
        if not value and default is not None:
            return default
        if value:
            return value
        print("  (required — please enter a value)")


def needs_setup(env_path: Path) -> bool:
    """Return True if .env is absent or has no API key set."""
    if not env_path.exists():
        return True
    text = env_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("PAPERLIBRARY_LLM_API_KEY="):
            value = line.split("=", 1)[1].strip()
            if value:
                return False
    return True


def run_wizard(env_path: Path) -> None:
    """Interactive first-run wizard; writes results to env_path."""
    print()
    print("=" * 56)
    print("  Welcome to paperlibrary — first-time setup")
    print("=" * 56)
    print()

    # ── Step 1: choose provider ───────────────────────────────
    print("Step 1/3  Choose your LLM provider\n")
    for key, name, *_ in _PROVIDERS:
        print(f"  {key}. {name}")
    print()

    choice = ""
    while choice not in [p[0] for p in _PROVIDERS]:
        choice = input("  Enter number [1]: ").strip() or "1"

    _, prov_name, provider, default_model, default_base_url = next(
        p for p in _PROVIDERS if p[0] == choice
    )
    print(f"  → {prov_name}\n")

    # ── Step 2: API key ───────────────────────────────────────
    print("Step 2/3  Enter your API key\n")
    api_key = _ask("  API key")
    print()

    # ── Step 3: model + (optional) base URL ──────────────────
    print("Step 3/3  Choose model\n")
    model = _ask("  Model name", default=default_model)

    base_url: str | None = default_base_url
    if provider == "openai-compatible":
        print()
        base_url = _ask("  API base URL", default=default_base_url or "")

    print()
    print("─" * 56)
    print("  Summary")
    print(f"  Provider : {prov_name}")
    print(f"  Model    : {model}")
    if base_url:
        print(f"  Base URL : {base_url}")
    print("─" * 56)
    print()

    confirm = input("  Save and start? [Y/n]: ").strip().lower()
    if confirm not in ("", "y", "yes"):
        print("  Setup cancelled. Re-run to configure.")
        raise SystemExit(0)

    # ── Write .env ────────────────────────────────────────────
    lines = [
        f"PAPERLIBRARY_LLM_PROVIDER={provider}",
        f"PAPERLIBRARY_LLM_API_KEY={api_key}",
        f"PAPERLIBRARY_LLM_MODEL={model}",
    ]
    if base_url:
        lines.append(f"PAPERLIBRARY_LLM_BASE_URL={base_url}")

    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n  Config saved to {env_path}")
    print("  Starting paperlibrary…\n")
