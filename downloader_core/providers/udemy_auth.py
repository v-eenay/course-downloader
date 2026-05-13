from __future__ import annotations

import general

UDEMY_BASE_DOMAIN = "udemy.com"


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
        return "", cookie_dict, f"No access_token cookie found for {domain} in this browser."
    except Exception as exc:
        return "", {}, str(exc)


def load_udemy_auth(
    browser: str, org_domain: str = UDEMY_BASE_DOMAIN
) -> tuple[str, dict[str, str], str | None, str]:
    """Return (access_token, all_cookies_dict, error, source_browser).

    For Udemy Business accounts the org_domain should be the full host, e.g.
    ``ingnepal.udemy.com``.  Cookies are loaded for that domain first, then
    ``udemy.com`` as a fallback (access_token is often set on the root domain).
    Tries all supported browsers if the given browser has no token.
    """
    # Domains to search: org-specific first, then root udemy.com (covers most
    # personal accounts and also business accounts whose cookies land on the
    # root domain).
    domains = [org_domain] if org_domain != UDEMY_BASE_DOMAIN else [UDEMY_BASE_DOMAIN]
    if UDEMY_BASE_DOMAIN not in domains:
        domains.append(UDEMY_BASE_DOMAIN)

    for browser_to_try in [browser] + [
        b for b in general.ALLOWED_BROWSERS if b != browser
    ]:
        for domain in domains:
            token, cdict, error = _try_browser(browser_to_try, domain)
            if token:
                return token, cdict, None, browser_to_try

    return "", {}, "No access_token cookie found in any browser.", browser
