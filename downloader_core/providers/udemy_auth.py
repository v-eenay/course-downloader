from __future__ import annotations

import general

UDEMY_DOMAIN = "udemy.com"


def _cookies_to_dict(cookies) -> dict[str, str]:
    """Convert a browser cookie jar (rookiepy list or browser_cookie3 jar) to a plain dict."""
    result: dict[str, str] = {}
    for cookie in cookies:
        name = getattr(cookie, "name", None)
        value = getattr(cookie, "value", None)
        if name is None and isinstance(cookie, dict):
            name = cookie.get("name")
            value = cookie.get("value")
        if name and value:
            result[name] = value
    return result


def _try_browser(browser: str) -> tuple[str, dict[str, str], str | None]:
    """Return (access_token, all_cookies_dict, error) for a single browser."""
    try:
        raw = general.load_browser_cookies(UDEMY_DOMAIN, browser)
        cookie_dict = _cookies_to_dict(raw)
        token = cookie_dict.get("access_token", "")
        if token:
            return token, cookie_dict, None
        return "", cookie_dict, "No access_token cookie found for udemy.com in this browser."
    except Exception as exc:
        return "", {}, str(exc)


def load_udemy_auth(browser: str) -> tuple[str, dict[str, str], str | None, str]:
    """Return (access_token, all_cookies_dict, error, source_browser).

    Tries *browser* first, then falls back to all other known browsers.
    All udemy.com cookies are returned so the session can be fully authenticated.
    """
    token, cdict, error = _try_browser(browser)
    if token:
        return token, cdict, None, browser

    for fallback in general.ALLOWED_BROWSERS:
        if fallback == browser:
            continue
        t, cd, _ = _try_browser(fallback)
        if t:
            return t, cd, None, fallback

    return "", {}, error or "No access_token cookie found in any browser.", browser
