"""Elevated cookie-extraction helper.

Invoked by win_elevate.extract_cookies_elevated() as:

  Frozen exe:
    course-downloader.exe --_cookie-helper ORG_DOMAIN BROWSER OUTPUT_PATH

  Development:
    python maingui.py --_cookie-helper ORG_DOMAIN BROWSER OUTPUT_PATH

Runs elevated (admin), reads browser cookies for all Udemy domain variants,
writes a JSON result file, then exits.  The calling process reads that file
and continues the download at normal (non-elevated) privilege.
"""
from __future__ import annotations

import json


def run_cookie_helper(org_domain: str, browser: str, output_path: str) -> int:
    """Extract cookies and write result to *output_path*. Returns exit code."""
    try:
        from downloader_core.providers.udemy_auth import _load_all_udemy_cookies
        cookies, errors = _load_all_udemy_cookies(browser, org_domain)
        result: dict = {"ok": True, "cookies": cookies, "errors": errors}
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "cookies": {}, "errors": [str(exc)]}

    try:
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(result, fh)
        return 0
    except Exception:
        return 1
