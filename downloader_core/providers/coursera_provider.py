from __future__ import annotations

import general

from .base import CourseProvider, ParsedTarget, ProviderUiSpec, ValidationResult


class CourseraProvider(CourseProvider):
    key = "coursera"
    display_name = "Coursera"
    ui_spec = ProviderUiSpec(
        target_label="URL or slug",
        target_placeholder="Course, specialization, or certificate",
        target_help=(
            "Use a course, specialization, professional certificate, or supported program specialization URL. "
            "Slug inputs are also supported."
        ),
        browser_help=(
            "Sign in first. Supported browsers: {browsers}."
        ),
        mode_toggle_text="Specialization",
        show_mode_toggle=True,
    )

    def validate_target(self, target: str, mode_selected: bool = False) -> ValidationResult:
        default_kind = "specialization" if mode_selected else "course"
        parsed = general.parse_coursera_target(target, default_kind=default_kind)
        if parsed is None:
            return ValidationResult(
                error="Invalid course, specialization, or professional certificate URL/slug.",
            )

        return ValidationResult(
            parsed_target=ParsedTarget(
                provider=self.key,
                kind=parsed.kind,
                slug_or_id=parsed.slug,
                raw_value=target.strip(),
                is_url=parsed.is_url,
            )
        )
