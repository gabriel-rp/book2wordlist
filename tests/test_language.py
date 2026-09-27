import pytest

from book2wordlist.language import Language


@pytest.mark.parametrize(
    'tag,expected',
    [
        ('en-US', Language.ENGLISH),
        ('de-DE', Language.GERMAN),
        ('EN', Language.ENGLISH),
        (' de ', Language.GERMAN),
        ('detect', Language.DETECT),
        (Language.GERMAN, Language.GERMAN),
    ],
)
def test_from_tag_normalizes(tag, expected):
    assert Language.from_tag(tag) is expected


def test_from_tag_rejects_an_unknown_language():
    with pytest.raises(ValueError, match='Unsupported language'):
        Language.from_tag('pt-BR')


def test_the_unknown_language_error_names_the_known_ones():
    with pytest.raises(ValueError) as excinfo:
        Language.from_tag('pt')

    assert 'en' in str(excinfo.value) and 'de' in str(excinfo.value)
