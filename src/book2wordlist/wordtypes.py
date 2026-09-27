from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class WordTypeSpec:
    """What this package knows about one kind of word.

    `label` is what reaches the output, so it is ours to choose rather than
    whatever tagset a backend happens to use. `closed_class` marks the
    function-word classes: a stopword is only safe to drop when its type is
    one of these, since stop lists also flag inflected content verbs.
    """

    label: str
    closed_class: bool = False


class WordType(Enum):
    NOUN = WordTypeSpec('noun')
    NAME = WordTypeSpec('name')
    VERB = WordTypeSpec('verb')
    ADJECTIVE = WordTypeSpec('adjective')
    ADVERB = WordTypeSpec('adverb')
    NUMERAL = WordTypeSpec('numeral')
    SYMBOL = WordTypeSpec('symbol')
    PUNCTUATION = WordTypeSpec('punctuation')
    OTHER = WordTypeSpec('other')
    AUXILIARY = WordTypeSpec('auxiliary', closed_class=True)
    PRONOUN = WordTypeSpec('pronoun', closed_class=True)
    DETERMINER = WordTypeSpec('determiner', closed_class=True)
    PREPOSITION = WordTypeSpec('preposition', closed_class=True)
    CONJUNCTION = WordTypeSpec('conjunction', closed_class=True)
    PARTICLE = WordTypeSpec('particle', closed_class=True)
    INTERJECTION = WordTypeSpec('interjection', closed_class=True)

    @property
    def label(self) -> str:
        return self.value.label

    @property
    def is_closed_class(self) -> bool:
        return self.value.closed_class

    @property
    def is_name(self) -> bool:
        return self is WordType.NAME

    def __str__(self) -> str:
        return self.label

    @classmethod
    def labels(cls) -> list[str]:
        return [word_type.label for word_type in cls]
