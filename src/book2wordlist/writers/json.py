from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from typing import IO, ClassVar

from book2wordlist.outputformats import OutputFormat, OutputType
from book2wordlist.results import VocabEntry
from book2wordlist.writers.base import ResultWriter, WriterOptions


@dataclass(frozen=True)
class JsonOptions(WriterOptions):
    """What can be tuned about the JSON output.

    `indent` of 0 writes the array on one line; anything higher pretty-prints
    it. `ensure_ascii` off keeps umlauts and accents readable as themselves
    rather than as \\uXXXX escapes, which matters for the German lists.
    """

    cli_prefix: ClassVar[str] = 'json'
    cli_help: ClassVar[str] = 'Indentation, and whether to escape non-ASCII.'
    indent: int = 2
    ensure_ascii: bool = False


class JsonWriter(ResultWriter):
    output_format: ClassVar[OutputFormat] = OutputFormat.JSON
    options_type: ClassVar[type[WriterOptions]] = JsonOptions

    def write_entries(
        self,
        entries: Iterable[VocabEntry],
        out: IO[str],
        output_type: OutputType = OutputType.FULL,
    ) -> None:
        rows = list(self.rows(entries, output_type))
        if len(output_type.fields) == 1:
            rows = [next(iter(row.values())) for row in rows]
        json.dump(
            rows,
            out,
            indent=self.options.indent or None,
            ensure_ascii=self.options.ensure_ascii,
        )
        out.write('\n')
