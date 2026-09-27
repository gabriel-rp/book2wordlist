from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from book2wordlist.readers.base import BookReader, BookText, ReaderOptions


@dataclass(frozen=True)
class PlainTextOptions(ReaderOptions):
    """What can be tuned about reading plain text.

    Encodings are tried in order; the last one should accept any byte so
    that decoding cannot fail outright.
    """

    cli_prefix: ClassVar[str] = 'text'
    cli_help: ClassVar[str] = 'encodings: tried in order until one decodes.'
    encodings: tuple[str, ...] = ('utf-8', 'cp1252', 'latin-1')


class PlainTextReader(BookReader):
    """`detect_language` is left unimplemented because a .txt file has
    nothing to detect from, so an explicit language is required and
    `--lang detect` is an error rather than a guess.
    """

    extensions: ClassVar[tuple[str, ...]] = ('.txt', '.text')
    format_name: ClassVar[str] = 'plain text'
    options_type: ClassVar[type[ReaderOptions]] = PlainTextOptions

    def read(self, path: str | Path) -> BookText:
        data = Path(path).read_bytes()
        text = ''
        for encoding in self.options.encodings:
            try:
                text = data.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        return self.book_text(None, [text] if text.strip() else [])
