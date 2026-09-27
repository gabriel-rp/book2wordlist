from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from book2wordlist.language import Language
from book2wordlist.optionsbase import SectionOptions


@dataclass(frozen=True)
class ReaderOptions(SectionOptions):
    cli_prefix: ClassVar[str] = 'reader'


@dataclass(frozen=True)
class BookText:
    """What every reader returns: a book's text and what it could declare.

    One string per document (an EPUB's spine items, a PDF's pages) rather
    than one big string, because the lemmatizer is fed document by document.
    `declares_language` records whether the reader implements detection at
    all, separating "this format has language metadata and the file left it
    empty" from "this format has no such metadata".
    """

    language: str | None
    documents: list[str]
    format_name: str = 'book'
    declares_language: bool = False

    @property
    def char_count(self) -> int:
        return sum(len(doc) for doc in self.documents)


class BookReader(ABC):
    """Metadata is optional: `detect_language` is only implemented by
    formats that have a language to report, which is why settling the
    language of a run is the reader's job -- only the format knows whether
    there is anything to read it from.
    """

    extensions: ClassVar[tuple[str, ...]] = ()
    format_name: ClassVar[str] = 'book'
    options_type: ClassVar[type[ReaderOptions]] = ReaderOptions

    def __init__(self, options: ReaderOptions | None = None) -> None:
        self.options = options or self.options_type()

    @abstractmethod
    def read(self, path: str | Path) -> BookText: ...

    def detect_language(self, path: str | Path) -> str | None:
        raise NotImplementedError(
            f'{self.format_name} files carry no language metadata'
        )

    @classmethod
    def supports_language_detection(cls) -> bool:
        return cls.detect_language is not BookReader.detect_language

    def resolve_language(
        self, requested: Language | str | None, book: BookText
    ) -> Language:
        if requested is not None:
            requested = Language.from_tag(requested)
        if requested is not None and requested is not Language.DETECT:
            return requested

        if not self.supports_language_detection():
            raise ValueError(
                f'{self.format_name} files carry no language metadata, so '
                'the language cannot be detected: pass it explicitly'
            )
        if book.language is None:
            raise ValueError(
                f'This {self.format_name} declares no language: pass it '
                'explicitly'
            )
        try:
            return Language.from_tag(book.language)
        except ValueError as exc:
            raise ValueError(
                f'This {self.format_name} declares the language '
                f'{book.language!r}, which is not supported: pass a '
                'supported one explicitly'
            ) from exc

    @classmethod
    def supports(cls, path: str | Path) -> bool:
        return Path(path).suffix.lower() in cls.extensions

    def book_text(
        self, language: str | None, documents: list[str]
    ) -> BookText:
        return BookText(
            language=language,
            documents=documents,
            format_name=self.format_name,
            declares_language=self.supports_language_detection(),
        )
