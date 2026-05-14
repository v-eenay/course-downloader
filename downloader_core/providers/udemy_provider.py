from __future__ import annotations

import logging
import os
import re
from urllib.parse import urlparse

import requests

from .base import CourseProvider, ProviderUiSpec, ValidationResult
from .udemy_parser import parse_udemy_target


def _org_host_from_url(raw_url: str | None) -> str:
    """Return the Udemy host for the given URL.

    For personal accounts this is ``www.udemy.com``.
    For Udemy Business accounts it will be something like ``yourorg.udemy.com``.
    Falls back to ``www.udemy.com`` if the URL cannot be parsed.
    """
    if not raw_url:
        return "www.udemy.com"
    try:
        host = urlparse(raw_url).netloc.lower().lstrip("www.")
        # Accept any *.udemy.com host
        if host == "udemy.com" or host.endswith(".udemy.com"):
            parsed_host = urlparse(raw_url).netloc.lower()
            return parsed_host
    except Exception:
        pass
    return "www.udemy.com"

_UNSAFE_RE = re.compile(r'[\\/:*?"<>|]')


def _safe_name(name: str, max_len: int = 120) -> str:
    """Strip characters that are invalid in Windows file/dir names."""
    return _UNSAFE_RE.sub("_", name).strip(". ")[:max_len]


def _download_file(session: requests.Session, url: str, dest: str) -> None:
    """Stream-download *url* to *dest*, using a .part file for atomicity."""
    tmp = dest + ".part"
    try:
        with session.get(url, stream=True, timeout=120) as resp:
            resp.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=1 << 20):
                    if chunk:
                        fh.write(chunk)
        os.replace(tmp, dest)
    except Exception:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _write_url_shortcut(url: str, dest: str) -> None:
    """Write a Windows .url Internet Shortcut file."""
    with open(dest, "w", encoding="utf-8") as f:
        f.write(f"[InternetShortcut]\nURL={url}\n")


def _write_html(body: str, title: str, dest: str) -> None:
    """Write an HTML file with a minimal wrapper so it opens cleanly."""
    html = (
        "<!DOCTYPE html><html><head>"
        f'<meta charset="utf-8"><title>{title}</title>'
        "<style>body{font-family:sans-serif;max-width:900px;margin:2em auto;padding:0 1em}</style>"
        f"</head><body>{body}</body></html>"
    )
    with open(dest, "w", encoding="utf-8") as f:
        f.write(html)


class UdemyProvider(CourseProvider):
    key = "udemy"
    display_name = "Udemy"
    ui_spec = ProviderUiSpec(
        target_label="Course URL",
        target_placeholder="https://www.udemy.com/course/example/  or  https://org.udemy.com/course/example/",
        target_help=(
            "Paste a Udemy course URL. Works with personal and Udemy Business accounts "
            "(e.g. yourorg.udemy.com). You must be enrolled and logged in to a supported browser."
        ),
        browser_help="Sign in to Udemy first. Supported browsers: {browsers}.",
        mode_toggle_text="Course",
        show_mode_toggle=False,
    )

    def validate_target(self, target: str, mode_selected: bool = False) -> ValidationResult:
        return parse_udemy_target(target)

    def run(self, parsed_target, args_dict: dict) -> None:
        from .udemy_auth import load_udemy_auth
        from .udemy_api import make_session, get_course_by_slug, get_curriculum
        from .udemy_mapper import map_curriculum

        browser = args_dict.get("browser") or "edge"
        base_path = args_dict.get("path") or os.getcwd()
        resolution = args_dict.get("video_resolution") or "best"
        slug = parsed_target.slug_or_id

        # ── Org / Business domain detection ──────────────────────────────
        # Priority: 1) explicit --udemy-org arg, 2) org host extracted from URL,
        # 3) default udemy.com
        explicit_org = (args_dict.get("udemy_org") or "").strip().lower()
        if explicit_org:
            # Normalise: allow "yourorg" or "yourorg.udemy.com"
            if not explicit_org.endswith(".udemy.com") and explicit_org != "udemy.com":
                explicit_org = f"{explicit_org}.udemy.com"
            org_host = explicit_org
        else:
            raw_url = parsed_target.raw_value if parsed_target.is_url else None
            org_host = _org_host_from_url(raw_url)   # e.g. "yourorg.udemy.com"

        org_domain = org_host.lstrip("www.")          # e.g. "yourorg.udemy.com"
        api_base = f"https://{org_host}/api-2.0"

        # ── Authentication ────────────────────────────────────────────────
        logging.info("Authenticating with Udemy via %s cookies…", browser)
        token, cookies, error, source_browser = load_udemy_auth(browser, org_domain=org_domain)
        if not token:
            raise RuntimeError(
                f"Udemy authentication failed: {error}\n"
                "Make sure you are logged in to Udemy in a supported browser."
            )
        if source_browser != browser:
            logging.info(
                "access_token found in %s (fallback from %s).",
                source_browser,
                browser,
            )

        session = make_session(token, cookies, org_domain=org_domain)

        # ── Course metadata ───────────────────────────────────────────────
        logging.info("Looking up course: %s", slug)
        course_id, course_title = get_course_by_slug(session, slug, api_base=api_base)
        logging.info("Downloading class: %s", course_title)

        # ── Curriculum ────────────────────────────────────────────────────
        logging.info("Fetching curriculum…")
        results = get_curriculum(session, course_id, api_base=api_base)
        sections = map_curriculum(results, resolution)

        total_items = sum(len(s["lectures"]) for s in sections)
        if total_items == 0:
            raise RuntimeError(
                "No downloadable content found in the curriculum. "
                "Check that you are enrolled in this course and that the URL is correct."
            )
        logging.info(
            "Found %d item(s) across %d section(s).",
            total_items,
            len(sections),
        )

        # ── Download loop ─────────────────────────────────────────────────
        course_dir = os.path.join(base_path, "Udemy", _safe_name(course_title))

        item_idx = 0
        for sec_idx, section in enumerate(sections, start=1):
            sec_dir = os.path.join(
                course_dir,
                f"Section {sec_idx:02d} - {_safe_name(section['title'])}",
            )
            os.makedirs(sec_dir, exist_ok=True)

            for lec in section["lectures"]:
                item_idx += 1
                num = f"{item_idx:03d}"
                safe_title = _safe_name(lec["title"])

                pct = int((item_idx - 1) / total_items * 100)
                print(f"[download] {pct}%", flush=True)
                logging.info(
                    "Item %d/%d: %s (%s)",
                    item_idx,
                    total_items,
                    lec["title"],
                    lec["asset_type"],
                )

                # ── Main asset ────────────────────────────────────────────
                if lec["url"]:
                    # Video or downloadable file
                    filepath = os.path.join(sec_dir, f"{num}. {safe_title}.{lec['ext']}")
                    if not os.path.exists(filepath):
                        try:
                            _download_file(session, lec["url"], filepath)
                        except Exception as e:
                            logging.warning("Failed to download %s: %s", lec["title"], e)

                elif lec["article_body"]:
                    # Article / reading material
                    filepath = os.path.join(sec_dir, f"{num}. {safe_title}.html")
                    if not os.path.exists(filepath):
                        _write_html(lec["article_body"], lec["title"], filepath)

                # ── Captions / subtitles ──────────────────────────────────
                for cap in lec.get("captions") or []:
                    cap_url = cap.get("url") or ""
                    if not cap_url:
                        continue
                    lang = (cap.get("locale") or "und").replace("_", "-")
                    cap_path = os.path.join(sec_dir, f"{num}. {safe_title}.{lang}.vtt")
                    if not os.path.exists(cap_path):
                        try:
                            _download_file(session, cap_url, cap_path)
                            logging.info("  Subtitle: %s", cap.get("title", lang))
                        except Exception as e:
                            logging.warning("  Subtitle %s failed: %s", lang, e)

                # ── Supplementary assets ──────────────────────────────────
                for supp in lec.get("supplementary") or []:
                    supp_title = _safe_name(supp.get("title") or "attachment")
                    supp_ext = supp.get("ext") or "bin"
                    supp_name = f"{num}. {safe_title} - {supp_title}.{supp_ext}"
                    supp_path = os.path.join(sec_dir, supp_name)

                    if os.path.exists(supp_path):
                        continue

                    supp_url = supp.get("url") or ""
                    body = supp.get("body") or ""

                    if supp_ext == "url" and supp_url:
                        _write_url_shortcut(supp_url, supp_path)
                        logging.info("  External link: %s", supp.get("title"))
                    elif supp_ext == "html" and body:
                        _write_html(body, supp.get("title", ""), supp_path)
                        logging.info("  Article: %s", supp.get("title"))
                    elif supp_url:
                        try:
                            _download_file(session, supp_url, supp_path)
                            logging.info("  Attachment: %s", supp.get("title"))
                        except Exception as e:
                            logging.warning("  Attachment %s failed: %s", supp.get("title"), e)

        print("[download] 100%", flush=True)
        logging.info("Done. Course saved to: %s", course_dir)
