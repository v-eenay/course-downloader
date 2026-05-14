"""Windows UAC elevation utilities.

Used by udemy_auth to spawn an elevated sub-process that can decrypt
Edge/Chrome 127+ app-bound cookie encryption without running the whole
app as administrator.
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
import tempfile


def is_admin() -> bool:
    """Return True if the current process has administrator privileges."""
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def extract_cookies_elevated(
    org_domain: str, browser: str
) -> tuple[dict[str, str], list[str], str | None]:
    """Spawn an elevated copy of this process via UAC to extract browser cookies.

    Only the cookie-extraction step runs elevated; the main app stays at normal
    user privilege, which avoids triggering Edge's elevated-access session reset.

    Returns (cookies_dict, backend_errors, fatal_error_or_None).
    """
    if sys.platform != "win32":
        return {}, [], "Elevation is only supported on Windows."

    # Temp file the helper writes its JSON result to
    fd, output_path = tempfile.mkstemp(suffix=".json", prefix="cookie_extract_")
    os.close(fd)
    try:
        os.unlink(output_path)  # helper will create it fresh
    except OSError:
        pass

    # Build the command to re-invoke this same executable in helper mode
    if getattr(sys, "frozen", False):
        # PyInstaller .exe — add hidden flag to our own executable
        exe = sys.executable
        params = f'--_cookie-helper "{org_domain}" "{browser}" "{output_path}"'
    else:
        # Development: python maingui.py --_cookie-helper …
        exe = sys.executable
        main_script = _find_main_script()
        params = f'"{main_script}" --_cookie-helper "{org_domain}" "{browser}" "{output_path}"'

    # SHELLEXECUTEINFOW structure for ShellExecuteExW
    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [
            ("cbSize",         ctypes.c_ulong),
            ("fMask",          ctypes.c_ulong),
            ("hwnd",           ctypes.c_void_p),
            ("lpVerb",         ctypes.c_wchar_p),
            ("lpFile",         ctypes.c_wchar_p),
            ("lpParameters",   ctypes.c_wchar_p),
            ("lpDirectory",    ctypes.c_wchar_p),
            ("nShow",          ctypes.c_int),
            ("hInstApp",       ctypes.c_void_p),
            ("lpIDList",       ctypes.c_void_p),
            ("lpClass",        ctypes.c_wchar_p),
            ("hkeyClass",      ctypes.c_void_p),
            ("dwHotKey",       ctypes.c_ulong),
            ("hIconOrMonitor", ctypes.c_void_p),
            ("hProcess",       ctypes.c_void_p),
        ]

    SEE_MASK_NOCLOSEPROCESS = 0x00000040  # keep process handle open so we can wait
    SW_HIDE = 0

    sei = SHELLEXECUTEINFOW()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = SEE_MASK_NOCLOSEPROCESS
    sei.lpVerb = "runas"
    sei.lpFile = exe
    sei.lpParameters = params
    sei.nShow = SW_HIDE

    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei)):
        win_err = ctypes.GetLastError()
        if win_err == 1223:  # ERROR_CANCELLED — user clicked "No" on UAC prompt
            return {}, [], "Administrator access was declined (UAC cancelled)."
        return {}, [], f"Could not launch elevated helper (Windows error {win_err})."

    # Wait up to 30 s for the elevated helper to finish
    kernel32 = ctypes.windll.kernel32
    WAIT_TIMEOUT = 0x00000102
    wait_result = kernel32.WaitForSingleObject(sei.hProcess, 30_000)
    kernel32.CloseHandle(sei.hProcess)

    if wait_result == WAIT_TIMEOUT:
        return {}, [], "Cookie extraction timed out after 30 seconds."

    if not os.path.exists(output_path):
        return {}, [], (
            "Elevated helper produced no output. "
            "UAC may have been denied, or the helper process crashed."
        )

    try:
        with open(output_path, encoding="utf-8") as fh:
            data = json.load(fh)
        cookies: dict[str, str] = data.get("cookies", {})
        errors: list[str] = data.get("errors", [])
        if data.get("ok"):
            return cookies, errors, None
        return {}, errors, data.get("error", "Unknown error in elevated helper.")
    except Exception as exc:
        return {}, [], f"Failed to parse elevated helper output: {exc}"
    finally:
        try:
            os.unlink(output_path)
        except OSError:
            pass


def _find_main_script() -> str:
    """Locate maingui.py for the non-frozen (development) case."""
    # __file__ is  downloader_core/win_elevate.py
    # maingui.py   is one directory above downloader_core/
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(pkg_dir)
    candidate = os.path.join(root, "maingui.py")
    if os.path.exists(candidate):
        return candidate
    # Fallback: use the script that launched this process
    return os.path.abspath(sys.argv[0])
