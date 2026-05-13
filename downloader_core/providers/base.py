from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ParsedTarget:
    provider: str
    kind: str
    slug_or_id: str
    raw_value: str
    is_url: bool = False


@dataclass(frozen=True)
class PreparedTarget:
    parsed_target: ParsedTarget
    runtime_value: str
    mode_enabled: bool = False


@dataclass(frozen=True)
class ValidationResult:
    parsed_target: Optional[ParsedTarget] = None
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.parsed_target is not None and not self.error


@dataclass(frozen=True)
class ProviderUiSpec:
    target_label: str
    target_placeholder: str
    target_help: str
    browser_help: str
    mode_toggle_text: str = "Specialization"
    show_mode_toggle: bool = False


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    error: Optional[str] = None
    source: Optional[str] = None


@dataclass(frozen=True)
class CourseUnit:
    id: str
    title: str
    order: int
    parent_title: Optional[str] = None


@dataclass(frozen=True)
class LectureUnit:
    id: str
    title: str
    section_title: Optional[str]
    index: int


@dataclass(frozen=True)
class MediaAsset:
    type: str
    url: str
    quality: Optional[str]
    language: Optional[str]
    filename: str
    size: Optional[int] = None


@dataclass(frozen=True)
class DownloadTask:
    course: CourseUnit
    lecture: LectureUnit
    asset: MediaAsset


@dataclass(frozen=True)
class DownloadResult:
    status: str
    path: Optional[str] = None
    error: Optional[str] = None


class CourseProvider(ABC):
    key = ""
    display_name = ""
    ui_spec = ProviderUiSpec(
        target_label="URL or slug",
        target_placeholder="Target",
        target_help="Enter a supported target.",
        browser_help="Sign in first.",
    )
    blocking_notice = None

    @abstractmethod
    def validate_target(self, target: str, mode_selected: bool = False) -> ValidationResult:
        raise NotImplementedError

    def prepare_target(self, parsed_target: ParsedTarget, mode_selected: bool = False) -> PreparedTarget:
        return PreparedTarget(parsed_target=parsed_target, runtime_value=parsed_target.slug_or_id, mode_enabled=mode_selected)

    def get_blocking_notice(self) -> Optional[str]:
        return self.blocking_notice
