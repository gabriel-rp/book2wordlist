from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class OutputFormatSpec:
    name: str


class OutputFormat(Enum):
    CSV = OutputFormatSpec('csv')
    JSON = OutputFormatSpec('json')

    @property
    def name_(self) -> str:
        return self.value.name

    def __str__(self) -> str:
        return self.value.name

    @classmethod
    def names(cls) -> list[str]:
        return [fmt.value.name for fmt in cls]

    @classmethod
    def from_name(cls, name: str | OutputFormat) -> OutputFormat:
        if isinstance(name, OutputFormat):
            return name
        for fmt in cls:
            if fmt.value.name == name:
                return fmt
        raise ValueError(
            f'Unsupported output format {name!r} '
            f'(supported: {", ".join(cls.names())})'
        )


@dataclass(frozen=True)
class OutputTypeSpec:
    """Which facts about a lemma reach the output, and whether to head them.

    `simple` exists so the list can be piped into other tools: one lemma per
    line with no header, or a bare JSON array of strings.
    """

    name: str
    fields: tuple[str, ...]
    header: bool = True


class OutputType(Enum):
    FULL = OutputTypeSpec('full', ('rank', 'lemma', 'count', 'word_type'))
    SIMPLE = OutputTypeSpec('simple', ('lemma',), header=False)

    @property
    def fields(self) -> tuple[str, ...]:
        return self.value.fields

    @property
    def header(self) -> bool:
        return self.value.header

    def __str__(self) -> str:
        return self.value.name

    @classmethod
    def names(cls) -> list[str]:
        return [output_type.value.name for output_type in cls]

    @classmethod
    def from_name(cls, name: str | OutputType) -> OutputType:
        if isinstance(name, OutputType):
            return name
        for output_type in cls:
            if output_type.value.name == name:
                return output_type
        raise ValueError(
            f'Unsupported output type {name!r} '
            f'(supported: {", ".join(cls.names())})'
        )
