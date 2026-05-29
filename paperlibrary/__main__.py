import threading
import time
import webbrowser
from pathlib import Path

import uvicorn

from paperlibrary.core.setup_wizard import needs_setup, run_wizard

_ENV_PATH = Path(".env")


def _open_browser(port: int) -> None:
    """Open the browser after a short delay so the server is ready."""
    time.sleep(1.5)
    webbrowser.open(f"http://localhost:{port}")


def main() -> None:
    # First-run: guide the user through provider / key / model selection.
    if needs_setup(_ENV_PATH):
        run_wizard(_ENV_PATH)

    # Import settings *after* the wizard may have written .env.
    from paperlibrary.core.config import get_settings  # noqa: PLC0415

    settings = get_settings()

    # Open the browser automatically so users don't have to copy the URL.
    threading.Thread(target=_open_browser, args=(settings.port,), daemon=True).start()

    print(f"paperlibrary running → http://localhost:{settings.port}")
    print("Press Ctrl+C to stop.\n")

    uvicorn.run(
        "paperlibrary.api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=False,
        log_level="warning",   # quieter output; errors still shown
    )


if __name__ == "__main__":
    main()
