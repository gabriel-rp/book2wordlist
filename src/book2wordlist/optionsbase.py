from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any, ClassVar


@dataclass(frozen=True)
class SectionOptions:
    """Base for the options one backend defines for itself.

    Each reader, lemmatizer and writer owns a subclass holding only the
    parameters that make sense for it, and `cli_prefix` is how those reach
    argparse: the flag `--spacy-batch-size` lands in the dest
    `spacy_batch_size`, which `from_namespace` maps back onto the field
    `batch_size` of the section whose prefix is 'spacy'.
    """

    cli_prefix: ClassVar[str] = ''
    cli_help: ClassVar[str] = ''

    @classmethod
    def field_names(cls) -> list[str]:
        return [field.name for field in fields(cls)]

    @classmethod
    def dest(cls, field_name: str) -> str:
        return f'{cls.cli_prefix}_{field_name}'

    @classmethod
    def flag(cls, field_name: str) -> str:
        return '--' + cls.dest(field_name).replace('_', '-')

    @classmethod
    def from_namespace(cls, args: Any) -> SectionOptions:
        values = vars(args)
        given = {
            name: values[cls.dest(name)]
            for name in cls.field_names()
            if cls.dest(name) in values
        }
        return cls(**given)
