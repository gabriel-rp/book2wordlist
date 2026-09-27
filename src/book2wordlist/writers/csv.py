from __future__ import annotations

from collections.abc import Iterable
import csv
from dataclasses import dataclass
from typing import IO, ClassVar

from book2wordlist.outputformats import OutputFormat, OutputType
from book2wordlist.results import VocabEntry
from book2wordlist.writers.base import ResultWriter, WriterOptions


@dataclass(frozen=True)
class CsvOptions(WriterOptions):
    """What can be tuned about the CSV output.

    The line terminator is a field rather than the csv module's default
    because that default is CRLF, which breaks naive shell pipelines.
    """

    cli_prefix: ClassVar[str] = 'csv'
    cli_help: ClassVar[str] = 'The separator and line ending of the rows.'
    delimiter: str = ','
    line_terminator: str = '\n'


class CsvWriter(ResultWriter):
    output_format: ClassVar[OutputFormat] = OutputFormat.CSV
    options_type: ClassVar[type[WriterOptions]] = CsvOptions

    def write_entries(
        self,
        entries: Iterable[VocabEntry],
        out: IO[str],
        output_type: OutputType = OutputType.FULL,
    ) -> None:
        writer = self._writer(out)
        if output_type.header:
            writer.writerow(output_type.fields)
        for row in self.rows(entries, output_type):
            writer.writerow(list(row.values()))

    def _writer(self, out: IO[str]):
        return csv.writer(
            out,
            delimiter=self.options.delimiter,
            lineterminator=self.options.line_terminator,
        )
