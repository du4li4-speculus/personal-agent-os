"""Input adapters for the TOEFL Writing Grader evidence boundary."""

from .base_adapter import AdapterError, InputAdapter, build_source_bundle, normalize_sources
from .image_adapter import ImageAdapter
from .pages_adapter import PagesAdapter
from .text_adapter import TextAdapter

__all__ = [
    "AdapterError",
    "InputAdapter",
    "TextAdapter",
    "ImageAdapter",
    "PagesAdapter",
    "build_source_bundle",
    "normalize_sources",
]
