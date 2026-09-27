from unittest.mock import patch

import pytest

from book2wordlist.language import Language
from book2wordlist.lemmatizers.base import Lemmatizer, Token
from book2wordlist.lemmatizers.registry import LEMMATIZER
from book2wordlist.lemmatizers.spacy import SpacyLemmatizer, SpacyOptions
from book2wordlist.wordtypes import WordType


def test_a_backend_declares_its_own_languages():
    assert SpacyLemmatizer.supported_languages() == (
        Language.ENGLISH,
        Language.GERMAN,
    )
    assert SpacyLemmatizer.supports(Language.ENGLISH)
    assert not SpacyLemmatizer.supports(Language.DETECT)


def test_an_unsupported_language_names_the_backend_and_its_models():
    with pytest.raises(ValueError) as excinfo:
        SpacyLemmatizer.require_supported(Language.DETECT)

    message = str(excinfo.value)
    assert 'spaCy' in message
    assert 'en (English)' in message and 'de (German)' in message


def test_the_model_package_is_the_backends_business():
    assert SpacyLemmatizer.package_for(Language.ENGLISH) == 'en_core_web_sm'
    assert SpacyLemmatizer.package_for(Language.GERMAN) == 'de_core_news_sm'


def test_a_missing_model_explains_how_to_install_it():
    with (
        patch('spacy.load', side_effect=OSError('not found')),
        pytest.raises(RuntimeError, match='spacy download'),
    ):
        SpacyLemmatizer.load_nlp(Language.ENGLISH)


def test_the_excluded_components_come_from_the_backend_options(en_lemmatizer):
    names = en_lemmatizer.nlp.pipe_names

    assert 'parser' not in names
    assert 'ner' not in names
    assert 'lemmatizer' in names
    assert 'tagger' in names


def test_analyze_yields_one_token_list_per_text(en_lemmatizer):
    batches = list(en_lemmatizer.analyze(['A cat.', 'Two dogs.']))

    assert len(batches) == 2
    assert all(isinstance(t, Token) for t in batches[0])


def test_tokens_carry_our_word_types_not_the_backend_tagset(en_lemmatizer):
    by_text = {
        t.text: t for t in en_lemmatizer.tokens(['Paul quickly ate two figs.'])
    }

    assert by_text['Paul'].word_type is WordType.NAME
    assert by_text['ate'].word_type is WordType.VERB
    assert by_text['quickly'].word_type is WordType.ADVERB
    assert by_text['two'].word_type is WordType.NUMERAL
    assert by_text['figs'].word_type is WordType.NOUN


def test_token_flags_survive_the_translation(en_lemmatizer):
    tokens = {t.text: t for t in en_lemmatizer.tokens(['The cat , 42 .'])}

    assert tokens['The'].is_stop
    assert tokens[','].is_punct
    assert not tokens['42'].is_alpha


def test_the_batch_size_comes_from_the_backend_options(en_lemmatizer):
    lemmatizer = SpacyLemmatizer(
        Language.ENGLISH, SpacyOptions(batch_size=3), nlp=en_lemmatizer.nlp
    )

    with patch.object(
        lemmatizer.nlp, 'pipe', wraps=lemmatizer.nlp.pipe
    ) as pipe:
        list(lemmatizer.analyze(['A cat.']))

    assert pipe.call_args.kwargs['batch_size'] == 3


def test_a_lemmatizer_is_built_through_the_registry(en_lemmatizer):
    with patch.object(
        SpacyLemmatizer, 'load_nlp', return_value=en_lemmatizer.nlp
    ):
        lemmatizer = LEMMATIZER.load(Language.ENGLISH)

    assert isinstance(lemmatizer, Lemmatizer)
    assert lemmatizer.language is Language.ENGLISH
