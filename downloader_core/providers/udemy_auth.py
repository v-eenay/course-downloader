from __future__ import annotations

import general

UDEMY_BASE_DOMAIN = "udemy.com"

# Domain variants tried when searching for Udemy cookies.
# browser_cookie3 / rookiepy filter cookies via SQL LIKE '%domain%', so
# "udemy.com" already matches both udemy.com and *.udemy.com subdomains.
# The extra variants below are belt-and-suspenders for edge cases.
_UDEMY_COOKIE_DOMAIN_VARIANTS = ["udemy.com", ".udemy.com", "udemy"]


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


def _try_browser(browser: str, domain: str) -> tuple[str, dict[str, str], str | None]:
    """Return (access_token, all_cookies_dict, error) for a single browser + domain."""
    try:
        raw = general.load_browser_cookies(domain, browser)
        cookie_dict = _cookies_to_dict(raw)
        token = cookie_dict.get("access_token", "")
        if token:
            return token, cookie_dict, None
        return "", cookie_dict, f"No access_token cookie found for {domain} in {browser}."
    except Exception as exc:
        return "", {}, str(exc)


def _try_browser_exhaustive(browser: str, org_domain: str) -> tuple[str, dict[str, str], str | None]:
    """Try every useful domain variant for *browser* to find an access_token.

    Searches in order:
      1. The explicit org_domain (e.g. ``ingnepal.udemy.com`` for business accounts)
      2. Standard ``udemy.com`` – already matches subdomains via LIKE in most backends
      3. ``.udemy.com`` and ``udemy`` – wider nets for edge cases

    Returns (token, cookies_dict, error).
    """
    # Deduplicate while preserving order
    seen: set[str] = set()
    domains: list[str] = []
    for d in [org_domain, *_UDEMY_COOKIE_DOMAIN_VARIANTS]:
        if d not in seen:
            seen.add(d)
            domains.append(d)

    last_error: str | None = None
    for domain in domains:
        token, cdict, error = _try_browser(browser, domain)
        if token:
            return token, cdict, None
        # If we got cookies back (even without a token), the backend is working
        # and the token simply isn't there – no point trying more domains.
        if cdict:
            return "", {}, error
        last_error = error

    return "", {}, last_error or f"Could not load Udemy cookies from {browser}."


def load_udemy_auth(
    browser: str, org_domain: str = UDEMY_BASE_DOMAIN
) -> tuple[str, dict[str, str], str | None, str]:
    """Return (access_token, all_cookies_dict, error, source_browser).

    Only the *browser* specified by the caller is tried.  Cross-browser
    fallback is intentionally removed: silently switching to a different
    browser's account causes confusing "wrong course / not enrolled" errors,
    especially when the user has both a personal and a business Udemy account
    in different browsers.

    If no token is found the error message explains what to do.
    """
    token, cdict, error = _try_browser_exhaustive(browser, org_domain)
    if token:
        return token, cdict, None, browser

    friendly = (
        f"No Udemy access_token found in {browser}.\n"
        "• Make sure you are logged in to Udemy in that browser and the browser is closed "
        "(so the cookie database is not locked).\n"
        "• If you use a Udemy Business account (e.g. yourorg.udemy.com), paste the full "
        "business course URL — the app will detect the org automatically — or enter your "
        "org subdomain in the 'Udemy Business Org' field."
    )
    return "", {}, friendly, browser
