from __future__ import annotations

from collections import OrderedDict

from .base import (
    AuthResult,
    CourseProvider,
    CourseUnit,
    DownloadResult,
    DownloadTask,
    LectureUnit,
    MediaAsset,
    ParsedTarget,
    PreparedTarget,
    ProviderUiSpec,
    ValidationResult,
)
from .coursera_provider import CourseraProvider
from .udemy_provider import UdemyProvider


_PROVIDER_REGISTRY = OrderedDict(
    (
        (provider.key, provider)
        for provider in (
            CourseraProvider(),
            UdemyProvider(),
        )
    )
)


def get_provider(provider_key: str | None):
    key = (provider_key or "coursera").strip().lower()
    if key not in _PROVIDER_REGISTRY:
        raise KeyError(f"Unknown provider: {provider_key}")
    return _PROVIDER_REGISTRY[key]


def list_providers():
    return list(_PROVIDER_REGISTRY.values())


def provider_choices():
    return [(provider.key, provider.display_name) for provider in _PROVIDER_REGISTRY.values()]


__all__ = [
    "AuthResult",
    "CourseProvider",
    "CourseUnit",
    "CourseraProvider",
    "DownloadResult",
    "DownloadTask",
    "LectureUnit",
    "MediaAsset",
    "ParsedTarget",
    "PreparedTarget",
    "ProviderUiSpec",
    "UdemyProvider",
    "ValidationResult",
    "get_provider",
    "list_providers",
    "provider_choices",
]
