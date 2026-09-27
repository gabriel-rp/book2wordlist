from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from book2wordlist.language import Language
from book2wordlist.wordtypes import WordType


@dataclass
class LemmaCounts:
    """Lemma frequencies, plus the spellings and word types seen per lemma.

    Counting is keyed on the casefolded lemma so English sentence-initial
    'Fear' merges with 'fear'; `displays` remembers the original spellings
    so German noun capitalization ('Haus', not 'haus') survives into the
    output. Both halves are needed: dropping either breaks one language.
    """

    counts: Counter[str] = field(default_factory=Counter)
    displays: dict[str, Counter[str]] = field(
        default_factory=lambda: defaultdict(Counter)
    )
    word_types: dict[str, Counter[WordType]] = field(
        default_factory=lambda: defaultdict(Counter)
    )

    def add(self, lemma: str, word_type: WordType) -> None:
        key = lemma.casefold()
        self.counts[key] += 1
        self.displays[key][lemma] += 1
        self.word_types[key][word_type] += 1


@dataclass(frozen=True)
class VocabEntry:
    rank: int
    lemma: str
    count: int
    word_type: WordType

    def as_dict(self) -> dict[str, object]:
        return {
            'rank': self.rank,
            'lemma': self.lemma,
            'count': self.count,
            'word_type': self.word_type.label,
        }


@dataclass(frozen=True)
class VocabResult:
    language: Language
    entries: list[VocabEntry]
    lemma_counts: LemmaCounts
