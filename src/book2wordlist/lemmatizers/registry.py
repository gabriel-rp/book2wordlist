from __future__ import annotations

from dataclasses import dataclass

from book2wordlist.language import Language
from book2wordlist.lemmatizers.base import Lemmatizer, LemmatizerOptions
from book2wordlist.lemmatizers.spacy import SpacyLemmatizer


@dataclass(frozen=True)
class LemmatizerBackend:
    """Swapping NLP library means pointing this at another `Lemmatizer`;
    the languages the CLI offers follow from what that one ships models for.
    """

    implementation: type[Lemmatizer]

    @property
    def name(self) -> str:
        return self.implementation.backend_name

    @property
    def options_type(self) -> type[LemmatizerOptions]:
        return self.implementation.options_type

    def supported_languages(self) -> tuple[Language, ...]:
        return self.implementation.supported_languages()

    def language_choices(self) -> list[Language]:
        return [Language.DETECT, *self.supported_languages()]

    def load(
        self,
        language: Language,
        options: LemmatizerOptions | None = None,
    ) -> Lemmatizer:
        return self.implementation(language, options)


LEMMATIZER = LemmatizerBackend(SpacyLemmatizer)
