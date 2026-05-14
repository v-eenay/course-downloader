from __future__ import annotations

import logging

import general

UDEMY_BASE_DOMAIN = "udemy.com"

# Domain strings passed to the cookie backends.
# browser_cookie3 builds SQL: WHERE host LIKE '%<domain>%'
# so "udemy.com" already matches ingnepal.udemy.com, www.udemy.com, etc.
# We still try several variants because rookiepy may filter more strictly.
_UDEMY_COOKIE_SEARCH_DOMAINS = [
    "udemy.com",    # catches all *.udemy.com via LIKE in browser_cookie3
    ".udemy.com",   # explicit suffix for rookiepy-style matching
    "udemy",        # broadest catch-all – anything with "udemy" in the host
]


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


def _load_all_udemy_cookies(
    browser: str, org_domain: str = UDEMY_BASE_DOMAIN
) -> tuple[dict[str, str], list[str]]:
    """Load and merge cookies from every relevant Udemy domain for *browser*.

    We search multiple domain strings and merge the results so that cookies
    stored under any Udemy subdomain (e.g. ingnepal.udemy.com) are captured.
    We do NOT stop early when one domain returns cookies but no access_token —
    that was a previous bug that caused Udemy Business logins to fail because
    www.udemy.com tracking cookies satisfied the "got cookies" check.

    Returns (merged_cookie_dict, list_of_backend_errors).
    """
    # Build deduplicated domain list: org-specific variants first (if known),
    # then standard catch-all patterns.
    domains: list[str] = []
    seen: set[str] = set()

    def _add(d: str) -> None:
        if d and d not in seen:
            seen.add(d)
            domains.append(d)

    # Explicit org subdomain (e.g. "ingnepal.udemy.com")
    if org_domain and org_domain not in ("udemy.com", "www.udemy.com"):
        _add(org_domain)
        # Also add with leading dot for rookiepy suffix matching
        _add(org_domain if org_domain.startswith(".") else "." + org_domain)

    for d in _UDEMY_COOKIE_SEARCH_DOMAINS:
        _add(d)

    merged: dict[str, str] = {}
    errors: list[str] = []

    for domain in domains:
        try:
            raw = general.load_browser_cookies(domain, browser)
            batch = _cookies_to_dict(raw)
            if batch:
                merged.update(batch)
                logging.debug(
                    "Udemy cookies from %s via %s: %d cookie(s) (has access_token=%s)",
                    domain, browser, len(batch), "access_token" in batch,
                )
        except Exception as exc:
            errors.append(f"{domain}: {exc}")

    return merged, errors


def load_udemy_auth(
    browser: str, org_domain: str = UDEMY_BASE_DOMAIN
) -> tuple[str, dict[str, str], str | None, str]:
    """Return (access_token, all_cookies_dict, error, source_browser).

    Searches the specified *browser* across all Udemy domain variants and
    returns as soon as an access_token is found.  No cross-browser fallback —
    that previously caused wrong-account errors for users with both personal
    and business Udemy accounts in different browsers.
    """
    logging.info("Loading Udemy cookies from %s (org domain: %s)…", browser, org_domain)
    merged, errors = _load_all_udemy_cookies(browser, org_domain)

    token = merged.get("access_token", "")
    if token:
        return token, merged, None, browser

    # Build a helpful diagnostic message
    error_lines: list[str] = [f"No Udemy access_token found in {browser}."]
    if errors:
        error_lines.append("Backend errors:")
        error_lines.extend(f"  • {e}" for e in errors)

    error_lines += [
        "",
        "Troubleshooting:",
        "• Close Edge completely — the cookie DB is locked while the browser is open.",
        "• Make sure you are logged in to Udemy in Edge.",
        "• For Udemy Business (yourorg.udemy.com): paste the full course URL",
        "  (https://ingnepal.udemy.com/course/…) OR enter your org name",
        "  (e.g.  ingnepal) in the 'Udemy Business Org' field.",
    ]

    return "", {}, "\n".join(error_lines), browser
