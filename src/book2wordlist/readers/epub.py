from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar
import warnings

from book2wordlist.readers.base import BookReader, BookText, ReaderOptions


@dataclass(frozen=True)
class EpubOptions(ReaderOptions):
    """What can be tuned about reading EPUBs.

    `tag_separator` is inserted where markup is stripped; emptying it fuses
    the words either side of an inline tag, which is why it is a string and
    not a boolean.
    """

    cli_prefix: ClassVar[str] = 'epub'
    cli_help: ClassVar[str] = (
        'html_parser: which BeautifulSoup parser reads the markup. '
        'tag_separator: what replaces stripped tags, which is what keeps '
        'the words either side of an inline tag apart.'
    )
    html_parser: str = 'lxml'
    tag_separator: str = ' '


class EbooklibEpubReader(BookReader):
    """Everything specific to ebooklib -- its spine walk, its metadata
    accessor, its item types -- is confined to this class, so changing
    library means writing another `BookReader` and repointing `EpubReader`.
    """

    extensions: ClassVar[tuple[str, ...]] = ('.epub',)
    format_name: ClassVar[str] = 'EPUB'
    options_type: ClassVar[type[ReaderOptions]] = EpubOptions

    def detect_language(self, path: str | Path) -> str | None:
        from ebooklib import epub

        return self._language_of(epub.read_epub(str(path)))

    @staticmethod
    def _language_of(book) -> str | None:
        metadata = book.get_metadata('DC', 'language')
        return metadata[0][0] if metadata else None

    def read(self, path: str | Path) -> BookText:
        from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
        import ebooklib
        from ebooklib import epub

        book = epub.read_epub(str(path))
        language = self._language_of(book)

        documents: list[str] = []
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', XMLParsedAsHTMLWarning)
            for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
                markup = BeautifulSoup(
                    item.get_content(), self.options.html_parser
                )
                text = markup.get_text(self.options.tag_separator)
                if text.strip():
                    documents.append(text)

        return self.book_text(language, documents)


EpubReader = EbooklibEpubReader
