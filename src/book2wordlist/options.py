from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

from book2wordlist.language import Language
from book2wordlist.lemmatizers.spacy import SpacyOptions
from book2wordlist.outputformats import OutputFormat, OutputType
from book2wordlist.readers.epub import EpubOptions
from book2wordlist.readers.plaintext import PlainTextOptions
from book2wordlist.writers.csv import CsvOptions
from book2wordlist.writers.json import JsonOptions


@dataclass(frozen=True)
class Options:
    """Every parameter of one run, in one place.

    Nothing down the pipeline takes loose keyword arguments: the CLI builds
    one of these from argv, a module integration builds the same object
    directly, and both then call the same functions. What to read stays an
    explicit argument, since that is what differs between an EPUB path, a
    text file and an in-memory list of documents.

    The fields here are the ones that mean the same thing whatever backend
    runs; anything specific to one reader, lemmatizer or writer lives in
    that backend's own section below, which the backend itself defines.
    """

    lang: Language = Language.DETECT

    filter_stopwords: bool = True
    filter_names: bool = True
    filter_non_alpha: bool = True
    min_lemma_length: int = 2

    top_lemmas: int = 500

    max_chunk_chars: int = 100_000

    output: Path | None = None
    output_format: OutputFormat = OutputFormat.CSV
    output_type: OutputType = OutputType.FULL
    verbose: bool = False

    spacy: SpacyOptions = field(default_factory=SpacyOptions)
    epub: EpubOptions = field(default_factory=EpubOptions)
    text: PlainTextOptions = field(default_factory=PlainTextOptions)
    csv: CsvOptions = field(default_factory=CsvOptions)
    json: JsonOptions = field(default_factory=JsonOptions)

    @classmethod
    def sections(cls) -> dict[str, type]:
        return {
            'spacy': SpacyOptions,
            'epub': EpubOptions,
            'text': PlainTextOptions,
            'csv': CsvOptions,
            'json': JsonOptions,
        }

    @classmethod
    def from_namespace(cls, args: Any) -> Options:
        sections = cls.sections()
        names = {f.name for f in fields(cls) if f.name not in sections}
        values = {k: v for k, v in vars(args).items() if k in names}
        for name, section in sections.items():
            values[name] = section.from_namespace(args)
        return cls(**values)

    def section(self, options_type: type) -> Any:
        for name in self.sections():
            value = getattr(self, name)
            if isinstance(value, options_type):
                return value
        return options_type()


DEFAULT_OPTIONS = Options()
