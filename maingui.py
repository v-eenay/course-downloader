from app_metadata import APP_VERSION as __version__
from desktop_shell import run_desktop_shell


if __name__ == "__main__":
    raise SystemExit(run_desktop_shell())