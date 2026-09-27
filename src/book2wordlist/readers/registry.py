from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from book2wordlist.readers.base import BookReader
from book2wordlist.readers.epub import EpubReader
from book2wordlist.readers.plaintext import PlainTextReader


@dataclass(frozen=True)
class ReaderRegistry:
    implementations: tuple[type[BookReader], ...]

    def class_for(self, path: str | Path) -> type[BookReader]:
        for reader in self.implementations:
            if reader.supports(path):
                return reader
        raise ValueError(
            f'Unsupported file type {Path(path).suffix or str(path)!r} '
            f'(supported: {", ".join(self.extensions())})'
        )

    def extensions(self) -> list[str]:
        return [
            extension
            for reader in self.implementations
            for extension in reader.extensions
        ]

    def descriptions(self) -> list[str]:
        return [
            f'{reader.format_name} ({", ".join(reader.extensions)})'
            for reader in self.implementations
        ]


READERS = ReaderRegistry((EpubReader, PlainTextReader))
