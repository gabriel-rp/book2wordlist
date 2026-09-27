from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import ClassVar

from book2wordlist.language import Language
from book2wordlist.lemmatizers.base import (
    Lemmatizer,
    LemmatizerOptions,
    Token,
)
from book2wordlist.wordtypes import WordType


@dataclass(frozen=True)
class SpacyOptions(LemmatizerOptions):
    cli_prefix: ClassVar[str] = 'spacy'
    cli_help: ClassVar[str] = (
        'batch_size: documents handed to the model at once. '
        'exclude: pipeline components left unloaded.'
    )
    batch_size: int = 8
    exclude: tuple[str, ...] = ('parser', 'ner')


@dataclass(frozen=True)
class SpacyModel:
    language: Language
    package: str


class SpacyLemmatizer(Lemmatizer):
    backend_name: ClassVar[str] = 'spaCy'
    options_type: ClassVar[type[LemmatizerOptions]] = SpacyOptions
    models: ClassVar[tuple[SpacyModel, ...]] = (
        SpacyModel(Language.ENGLISH, 'en_core_web_sm'),
        SpacyModel(Language.GERMAN, 'de_core_news_sm'),
    )
    word_types: ClassVar[dict[str, WordType]] = {
        'NOUN': WordType.NOUN,
        'PROPN': WordType.NAME,
        'VERB': WordType.VERB,
        'AUX': WordType.AUXILIARY,
        'ADJ': WordType.ADJECTIVE,
        'ADV': WordType.ADVERB,
        'NUM': WordType.NUMERAL,
        'PRON': WordType.PRONOUN,
        'DET': WordType.DETERMINER,
        'ADP': WordType.PREPOSITION,
        'CCONJ': WordType.CONJUNCTION,
        'SCONJ': WordType.CONJUNCTION,
        'PART': WordType.PARTICLE,
        'INTJ': WordType.INTERJECTION,
        'SYM': WordType.SYMBOL,
        'PUNCT': WordType.PUNCTUATION,
        'X': WordType.OTHER,
        'SPACE': WordType.OTHER,
    }

    def __init__(
        self,
        language: Language,
        options: LemmatizerOptions | None = None,
        nlp=None,
    ) -> None:
        super().__init__(language, options)
        self.require_supported(self.language)
        self.nlp = (
            nlp
            if nlp is not None
            else self.load_nlp(self.language, self.options)
        )

    @classmethod
    def supported_languages(cls) -> tuple[Language, ...]:
        return tuple(model.language for model in cls.models)

    @classmethod
    def package_for(cls, language: Language) -> str:
        cls.require_supported(language)
        return next(
            model.package for model in cls.models if model.language is language
        )

    @classmethod
    def load_nlp(
        cls, language: Language | str, options: SpacyOptions | None = None
    ):
        import spacy

        options = options or SpacyOptions()
        language = Language.from_tag(language)
        package = cls.package_for(language)
        try:
            return spacy.load(package, exclude=list(options.exclude))
        except OSError as exc:
            raise RuntimeError(
                f'The spaCy model {package!r} is not installed. Install it '
                f'with:\n    uv run python -m spacy download {package}'
            ) from exc

    @property
    def name(self) -> str:
        return (
            f'spaCy {self.nlp.meta["name"]} ({", ".join(self.nlp.pipe_names)})'
        )

    def analyze(self, texts: Iterable[str]) -> Iterator[list[Token]]:
        pipe = self.nlp.pipe(texts, batch_size=self.options.batch_size)
        for doc in pipe:
            yield [
                Token(
                    text=token.text,
                    lemma=token.lemma_,
                    word_type=self.word_types.get(token.pos_, WordType.OTHER),
                    is_alpha=token.is_alpha,
                    is_punct=token.is_punct,
                    is_space=token.is_space,
                    is_stop=token.is_stop,
                )
                for token in doc
            ]
