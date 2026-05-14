import sys

# ── Elevated cookie-extraction helper mode ────────────────────────────────────
# Invoked by downloader_core.win_elevate.extract_cookies_elevated() via UAC.
# Handled here, before any GUI initialisation, so it works in both frozen and
# development modes.
if len(sys.argv) >= 5 and sys.argv[1] == "--_cookie-helper":
    from downloader_core.cookie_extractor_helper import run_cookie_helper
    raise SystemExit(run_cookie_helper(sys.argv[2], sys.argv[3], sys.argv[4]))
# ─────────────────────────────────────────────────────────────────────────────

from app_metadata import APP_VERSION as __version__
from desktop_shell import run_desktop_shell


if __name__ == "__main__":
    raise SystemExit(run_desktop_shell())