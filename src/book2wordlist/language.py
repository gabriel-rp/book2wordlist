from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class LanguageSpec:
    """How one language is written and spoken about.

    Only naming lives here. Which languages can actually be processed is
    the lemmatizer backend's answer, and whether a language can be read off
    a file is the reader's -- neither is a property of the language.
    """

    code: str
    label: str


class Language(Enum):
    """A language, or the request to take it from the file."""

    DETECT = LanguageSpec('detect', 'read from the file')
    ENGLISH = LanguageSpec('en', 'English')
    GERMAN = LanguageSpec('de', 'German')

    @property
    def code(self) -> str:
        return self.value.code

    @property
    def label(self) -> str:
        return self.value.label

    def __str__(self) -> str:
        return self.code

    @classmethod
    def from_tag(cls, tag: str | Language) -> Language:
        if isinstance(tag, Language):
            return tag
        code = tag.split('-')[0].strip().lower()
        for lang in cls:
            if lang.code == code:
                return lang
        known = ', '.join(lang.code for lang in cls if lang is not cls.DETECT)
        raise ValueError(f'Unsupported language {tag!r} (supported: {known})')
