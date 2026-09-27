from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import ClassVar

from book2wordlist.language import Language
from book2wordlist.optionsbase import SectionOptions
from book2wordlist.wordtypes import WordType


@dataclass(frozen=True)
class LemmatizerOptions(SectionOptions):
    cli_prefix: ClassVar[str] = 'lemmatizer'


@dataclass(frozen=True)
class Token:
    """One analyzed token, in backend-neutral terms.

    These attributes are exactly what `keep_token` needs; a backend that
    cannot supply one of the flags should give the value that keeps the
    token rather than inventing one.
    """

    text: str
    lemma: str
    word_type: WordType
    is_alpha: bool = True
    is_punct: bool = False
    is_space: bool = False
    is_stop: bool = False


class Lemmatizer(ABC):
    """A backend declares for itself which languages it can handle: that
    set is a property of the models it ships with, not of this package, so
    the CLI asks the backend rather than keeping its own list.
    """

    backend_name: ClassVar[str] = 'lemmatizer'
    options_type: ClassVar[type[LemmatizerOptions]] = LemmatizerOptions

    def __init__(
        self,
        language: Language,
        options: LemmatizerOptions | None = None,
    ) -> None:
        self.language = Language.from_tag(language)
        self.options = options or self.options_type()

    @classmethod
    @abstractmethod
    def supported_languages(cls) -> tuple[Language, ...]: ...

    @classmethod
    def supports(cls, language: Language) -> bool:
        return language in cls.supported_languages()

    @classmethod
    def require_supported(cls, language: Language) -> Language:
        if not cls.supports(language):
            supported = ', '.join(
                f'{lang.code} ({lang.label})'
                for lang in cls.supported_languages()
            )
            raise ValueError(
                f'The {cls.backend_name} backend does not support '
                f'{language.code!r} (supported: {supported})'
            )
        return language

    @abstractmethod
    def analyze(self, texts: Iterable[str]) -> Iterator[list[Token]]: ...

    @property
    def name(self) -> str:
        return self.backend_name

    def tokens(self, texts: Iterable[str]) -> Iterator[Token]:
        for batch in self.analyze(texts):
            yield from batch
