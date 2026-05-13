from __future__ import annotations

import re

from .base import ParsedTarget, ValidationResult


_UDEMY_URL_PATTERN = re.compile(
    r"udemy\.com/(?:[^/?#]+/)*course/([^/?#]+)",
    re.IGNORECASE,
)
_SLUG_PATTERN = re.compile(r"^[a-zA-Z0-9-]+$")


def parse_udemy_target(target: str) -> ValidationResult:
    if target is None:
        return ValidationResult(error="Enter a Udemy course URL.")

    normalized_target = target.strip()
    if not normalized_target:
        return ValidationResult(error="Enter a Udemy course URL.")

    lowered_target = normalized_target.lower()
    url_match = _UDEMY_URL_PATTERN.search(lowered_target)
    if url_match:
        return ValidationResult(
            parsed_target=ParsedTarget(
                provider="udemy",
                kind="course",
                slug_or_id=url_match.group(1),
                raw_value=normalized_target,
                is_url=True,
            )
        )

    if _SLUG_PATTERN.fullmatch(normalized_target):
        return ValidationResult(
            parsed_target=ParsedTarget(
                provider="udemy",
                kind="course",
                slug_or_id=normalized_target.lower(),
                raw_value=normalized_target,
                is_url=False,
            )
        )

    return ValidationResult(
        error="Invalid Udemy course URL/slug. Use a standard Udemy course URL such as https://www.udemy.com/course/example/."
    )
