from __future__ import annotations

from dataclasses import dataclass

from book2wordlist.outputformats import OutputFormat
from book2wordlist.writers.base import ResultWriter
from book2wordlist.writers.csv import CsvWriter
from book2wordlist.writers.json import JsonWriter


@dataclass(frozen=True)
class WriterRegistry:
    """Adding JSON means writing a `ResultWriter`, giving it an
    `OutputFormat` member and listing it here; --format picks it up.
    """

    implementations: tuple[type[ResultWriter], ...]

    def formats(self) -> list[OutputFormat]:
        return [writer.output_format for writer in self.implementations]

    def names(self) -> list[str]:
        return [fmt.name_ for fmt in self.formats()]

    def class_for(
        self, output_format: OutputFormat | str
    ) -> type[ResultWriter]:
        wanted = OutputFormat.from_name(output_format)
        for writer in self.implementations:
            if writer.output_format is wanted:
                return writer
        raise ValueError(
            f'No writer registered for {wanted.name_!r} '
            f'(available: {", ".join(self.names())})'
        )


WRITERS = WriterRegistry((CsvWriter, JsonWriter))
