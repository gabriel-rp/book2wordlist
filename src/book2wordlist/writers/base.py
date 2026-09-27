from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from typing import IO, ClassVar

from book2wordlist.optionsbase import SectionOptions
from book2wordlist.outputformats import OutputFormat, OutputType
from book2wordlist.results import VocabEntry


@dataclass(frozen=True)
class WriterOptions(SectionOptions):
    cli_prefix: ClassVar[str] = 'writer'


class ResultWriter(ABC):
    """Writers own the shape of the output: the column names and the values
    in them are this package's vocabulary, never a passthrough of whatever
    the NLP backend called things.
    """

    output_format: ClassVar[OutputFormat]
    options_type: ClassVar[type[WriterOptions]] = WriterOptions

    def __init__(self, options: WriterOptions | None = None) -> None:
        self.options = options or self.options_type()

    @abstractmethod
    def write_entries(
        self,
        entries: Iterable[VocabEntry],
        out: IO[str],
        output_type: OutputType = OutputType.FULL,
    ) -> None: ...

    @staticmethod
    def rows(
        entries: Iterable[VocabEntry], output_type: OutputType
    ) -> Iterable[dict[str, object]]:
        for entry in entries:
            facts = entry.as_dict()
            yield {field: facts[field] for field in output_type.fields}
