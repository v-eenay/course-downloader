from __future__ import annotations

import re

import requests

UDEMY_API_BASE = "https://www.udemy.com/api-2.0"

_CURRICULUM_FIELDS = (
    "fields[lecture]=title,asset,supplementary_assets,object_index"
    "&fields[chapter]=title,description,object_index"
    "&fields[asset]=asset_type,media_sources,stream_urls,download_urls,filename,title"
    ",captions,url_set,external_url,body"
    "&fields[quiz]=title,object_index"
)

# Patterns to extract the course ID from the Udemy course HTML page.
# Ordered from most specific/reliable to least.
_PAGE_ID_PATTERNS = [
    re.compile(r'data-clp-course-id="(\d+)"'),
    re.compile(r'data-course-id="(\d+)"'),
    re.compile(r'"clp_course_id":(\d+)'),
    re.compile(r'"courseId":(\d+)'),
    re.compile(r'"body_data":\{"course_id":(\d+)'),
    re.compile(r'"_class":"course","id":(\d+)'),
    re.compile(r'"id":(\d+),"_class":"course"'),
]


def make_session(
    access_token: str,
    cookies: dict | None = None,
    org_domain: str = "udemy.com",
) -> requests.Session:
    """Build an authenticated requests session.

    *org_domain* should be the host the user is logged in to, e.g.
    ``ingnepal.udemy.com`` for Udemy Business or ``udemy.com`` for personal
    accounts.  Cookies are registered for that domain so the session's cookie
    jar matches what the Udemy API expects.
    """
    session = requests.Session()
    if cookies:
        for name, value in cookies.items():
            session.cookies.set(name, value, domain=org_domain)
            # Also register on the root domain so API calls to www.udemy.com work.
            if org_domain != "udemy.com":
                session.cookies.set(name, value, domain="udemy.com")
    referer_host = org_domain if "." in org_domain else "www.udemy.com"
    session.headers.update(
        {
            "Authorization": f"Bearer {access_token}",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://{referer_host}/",
            "Accept": "application/json, text/plain, */*",
        }
    )
    return session


def _fetch_course_title(session: requests.Session, course_id: int, fallback: str) -> str:
    """Return the course title from the API given a known course ID."""
    try:
        resp = session.get(
            f"{UDEMY_API_BASE}/courses/{course_id}/?fields[course]=title",
            timeout=15,
        )
        if resp.ok:
            return resp.json().get("title", fallback)
    except Exception:
        pass
    return fallback


def _slug_from_url(url: str) -> str:
    """Extract the course slug from a Udemy URL.

    Handles:
      https://www.udemy.com/course/{slug}/
      /course/{slug}/
      /course/{slug}/learn/
    """
    parts = url.rstrip("/").split("/")
    # Find 'course' segment and return the immediately following segment.
    try:
        course_idx = parts.index("course")
        return parts[course_idx + 1]
    except (ValueError, IndexError):
        return parts[-1]


_SCRIPT_JSON_RE = re.compile(
    r'<script[^>]*>\s*window\.ud(?:Config|Data|Cache|FrontendSettings)?\s*=\s*(\{.*?\})',
    re.DOTALL,
)


def _try_html_page(session: requests.Session, slug: str):
    """Lookup by fetching the course landing page and extracting the ID.

    Udemy's current app is client-rendered — the course ID is NOT in the initial
    HTML, so this method tries a few patterns but is expected to fail often.
    It is kept as a last resort in case Udemy embeds the ID in some contexts.
    Udemy's web server rejects Bearer auth on HTML requests, so we suppress it.
    """
    course_url = f"https://www.udemy.com/course/{slug}/"
    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        # Setting to None suppresses the session-level Authorization header.
        "Authorization": None,
    }
    try:
        resp = session.get(course_url, timeout=30, allow_redirects=True, headers=headers)
        if resp.status_code == 403:
            raise ValueError(
                f"Access denied for course {slug!r}. "
                "Make sure you are enrolled and logged in to Udemy in your browser."
            )
        if resp.status_code == 404:
            raise ValueError(
                f"Course not found: {slug!r}. Check that the URL is correct."
            )
        if not resp.ok:
            return None
        html = resp.text
        for pat in _PAGE_ID_PATTERNS:
            m = pat.search(html)
            if m:
                course_id = int(m.group(1))
                title = _fetch_course_title(session, course_id, slug)
                return course_id, title
    except ValueError:
        raise  # propagate auth/404 errors immediately
    except Exception:
        pass
    return None


def _try_subscribed_exact(session: requests.Session, slug: str, api_base: str = UDEMY_API_BASE):
    """Paginate through ALL enrolled courses and match on published_title == slug.

    The Udemy API's url_component filter is fuzzy/unreliable, so we ignore it
    and page through the full enrollment list instead (typically 1-2 requests).
    The `published_title` field holds the exact URL slug.
    """
    page = 1
    page_size = 100
    while True:
        try:
            resp = session.get(
                f"{api_base}/users/me/subscribed-courses/",
                params={
                    "page": page,
                    "page_size": page_size,
                    "fields[course]": "id,title,url,published_title",
                },
                timeout=25,
            )
            if not resp.ok:
                return None
            data = resp.json()
            for course in data.get("results", []):
                # published_title IS the URL slug (most reliable)
                cslug = course.get("published_title") or _slug_from_url(course.get("url", ""))
                if cslug == slug:
                    return int(course["id"]), course.get("title", slug)
            if not data.get("next"):
                break
            page += 1
        except Exception:
            return None
    return None


def _try_courses_api_exact(session: requests.Session, slug: str, api_base: str = UDEMY_API_BASE):
    """Fallback: use the public courses API and verify the URL slug matches exactly."""
    try:
        resp = session.get(
            f"{api_base}/courses/",
            params={"url_component": slug, "fields[course]": "id,title,url", "page_size": 20},
            timeout=20,
        )
        if resp.ok:
            for course in resp.json().get("results", []):
                if _slug_from_url(course.get("url", "")) == slug:
                    return int(course["id"]), course.get("title", slug)
    except Exception:
        pass
    return None


def get_course_by_slug(
    session: requests.Session, slug: str, api_base: str = UDEMY_API_BASE
) -> tuple:
    """Return (course_id, course_title) for the given course slug.

    Tries in order:
      1. Paginate /users/me/subscribed-courses/ on *api_base* — the most
         reliable method; works for both personal and business accounts.
      2. Same as (1) but on www.udemy.com — catches the case where the user
         entered a slug (no org URL) and their business token also works on
         the standard Udemy API, or vice-versa.
      3. Public /courses/ API on *api_base*.
      4. Course HTML page scrape (last resort; often fails on Next.js).

    Raises ValueError with a clear message if all approaches fail.
    """
    api_bases_to_try = [api_base]
    if api_base != UDEMY_API_BASE:
        api_bases_to_try.append(UDEMY_API_BASE)

    for base in api_bases_to_try:
        result = (
            _try_subscribed_exact(session, slug, base)
            or _try_courses_api_exact(session, slug, base)
        )
        if result:
            return result

    result = _try_html_page(session, slug)
    if result:
        return result

    raise ValueError(
        f"Could not resolve course ID for: {slug!r}.\n"
        "Make sure you are enrolled in the course and logged in to Udemy in your browser.\n"
        "For Udemy Business accounts: paste the full business URL "
        "(e.g. https://ingnepal.udemy.com/course/…) or enter your org name "
        "in the 'Udemy Business Org' field."
    )


def get_curriculum(
    session: requests.Session, course_id: int, api_base: str = UDEMY_API_BASE
) -> list:
    """Return all curriculum items for *course_id* (chapters, lectures, quizzes)."""
    url = (
        f"{api_base}/courses/{course_id}/subscriber-curriculum-items/"
        f"?page_size=1400&{_CURRICULUM_FIELDS}"
    )
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json().get("results", [])
