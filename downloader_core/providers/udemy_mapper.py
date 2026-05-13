from __future__ import annotations

import os
import re

_LABEL_RE = re.compile(r"(\d+)")


def _parse_label(label: object) -> int:
    """Parse a quality label such as '720p' → 720, or '2160' → 2160."""
    m = _LABEL_RE.search(str(label))
    return int(m.group(1)) if m else 0


def _url_from_source(source: dict) -> str:
    return (
        source.get("file")
        or source.get("src")
        or source.get("url")
        or ""
    )


def _pick_quality(sources: list[dict], preferred: str) -> str:
    """Select the best URL from a list of quality-labelled source dicts."""
    if not sources:
        return ""

    if preferred == "best":
        best = max(sources, key=lambda s: _parse_label(s.get("label", 0)))
        return _url_from_source(best)

    target_px = _parse_label(preferred)

    for s in sources:
        if _parse_label(s.get("label", 0)) == target_px:
            return _url_from_source(s)

    lower = [s for s in sources if _parse_label(s.get("label", 0)) <= target_px]
    if lower:
        return _url_from_source(max(lower, key=lambda s: _parse_label(s.get("label", 0))))

    return _url_from_source(
        min(sources, key=lambda s: abs(_parse_label(s.get("label", 0)) - target_px))
    )


def _video_sources(asset: dict) -> list[dict]:
    """Extract an ordered list of video source dicts from a lecture asset."""
    stream = (asset.get("stream_urls") or {}).get("Video") or []
    if stream:
        return stream
    dl = (asset.get("download_urls") or {}).get("Video") or []
    if dl:
        return dl
    return asset.get("media_sources") or []


def _ext_from_name(filename: str, default: str = "bin") -> str:
    """Infer extension from a filename or URL path."""
    name = filename.split("?")[0].rstrip("/")  # strip query string
    if "." in os.path.basename(name):
        ext = os.path.splitext(name)[1].lstrip(".")
        if 1 <= len(ext) <= 10:
            return ext.lower()
    return default


def _get_captions(asset: dict) -> list[dict]:
    """Extract all caption/subtitle entries from a video asset.

    Returns a list of dicts: {locale, title, url}.
    """
    result = []
    for cap in asset.get("captions") or []:
        url = cap.get("url") or ""
        if not url:
            continue
        locale = cap.get("locale_id") or cap.get("locale") or "und"
        title = cap.get("title") or locale
        result.append({"locale": locale, "title": title, "url": url})
    return result


def _get_supplementary(assets: list[dict]) -> list[dict]:
    """Convert a list of supplementary asset dicts into download descriptors.

    Returns a list of dicts:
        {title, url, ext, asset_type}

    For ExternalLink, url will be the external URL with ext='url'.
    For Article, ext='html' and the body is in 'body'.
    For downloadable files, url points to the CDN file.
    """
    result = []
    for asset in assets or []:
        asset_type = asset.get("asset_type") or ""
        title = asset.get("title") or asset.get("filename") or "attachment"
        filename = asset.get("filename") or ""

        if asset_type == "ExternalLink":
            ext_url = asset.get("external_url") or ""
            if ext_url:
                result.append({
                    "title": title,
                    "url": ext_url,
                    "ext": "url",
                    "asset_type": asset_type,
                    "body": None,
                })

        elif asset_type == "Article":
            body = asset.get("body") or ""
            if body:
                result.append({
                    "title": title,
                    "url": "",
                    "ext": "html",
                    "asset_type": asset_type,
                    "body": body,
                })

        else:
            # File, Presentation, E-Book, Video, etc. — find download URL
            url = _find_file_url(asset, filename)
            if url:
                ext = _ext_from_name(filename or url, "bin")
                result.append({
                    "title": title,
                    "url": url,
                    "ext": ext,
                    "asset_type": asset_type,
                    "body": None,
                })

    return result


def _find_file_url(asset: dict, filename: str = "") -> str:
    """Extract the best download URL for a non-video asset."""
    # url_set: {"File": [{"file": "...", "label": "..."}], ...}
    url_set = asset.get("url_set") or {}
    for key in ("File", "Presentation", "E-Book", "SourceCode", "Video"):
        sources = url_set.get(key) or []
        for s in sources:
            url = s.get("file") or s.get("url") or ""
            if url:
                return url

    # download_urls: same structure
    dl = asset.get("download_urls") or {}
    for key, sources in dl.items():
        for s in (sources or []):
            url = s.get("file") or s.get("url") or ""
            if url:
                return url

    # media_sources (sometimes used for non-video files)
    for s in asset.get("media_sources") or []:
        url = s.get("file") or s.get("src") or s.get("url") or ""
        if url:
            return url

    return ""


def map_curriculum(results: list[dict], preferred_resolution: str = "best") -> list[dict]:
    """Parse curriculum items into enriched section/lecture dicts.

    Each lecture dict contains:
        title        str   – lecture title
        asset_type   str   – 'Video', 'Article', etc.
        url          str   – video URL (empty for non-video items)
        ext          str   – file extension ('mp4', 'html', etc.)
        captions     list  – [{locale, title, url}, ...]
        article_body str   – HTML body for Article-type lectures (else '')
        supplementary list – [{title, url, ext, asset_type, body}, ...]
    """
    sections: list[dict] = []
    current: dict | None = None

    for item in results:
        cls = item.get("_class", "")

        if cls == "chapter":
            current = {"title": item.get("title", ""), "lectures": []}
            sections.append(current)

        elif cls == "lecture":
            if current is None:
                current = {"title": "Introduction", "lectures": []}
                sections.append(current)

            asset = item.get("asset") or {}
            asset_type = asset.get("asset_type", "")
            supp_assets = item.get("supplementary_assets") or []

            lecture: dict = {
                "title": item.get("title", "Lecture"),
                "asset_type": asset_type,
                "url": "",
                "ext": "",
                "captions": [],
                "article_body": "",
                "supplementary": _get_supplementary(supp_assets),
            }

            if asset_type in ("Video", "Video Mash"):
                sources = _video_sources(asset)
                url = _pick_quality(sources, preferred_resolution)
                if url:
                    lecture["url"] = url
                    lecture["ext"] = "mp4"
                lecture["captions"] = _get_captions(asset)

            elif asset_type == "Article":
                body = asset.get("body") or ""
                lecture["ext"] = "html"
                lecture["article_body"] = body

            elif asset_type in ("File", "Presentation", "E-Book", "SourceCode"):
                filename = asset.get("filename") or ""
                url = _find_file_url(asset, filename)
                if url:
                    lecture["url"] = url
                    lecture["ext"] = _ext_from_name(filename or url, "bin")

            # Only add lectures that have something to download/save
            has_content = (
                lecture["url"]
                or lecture["article_body"]
                or lecture["supplementary"]
            )
            if has_content:
                current["lectures"].append(lecture)

    return sections

