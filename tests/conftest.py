from ebooklib import epub
import pytest

from book2wordlist.language import Language
from book2wordlist.lemmatizers.base import Token
from book2wordlist.lemmatizers.spacy import SpacyLemmatizer
from book2wordlist.wordtypes import WordType


def make_epub(path, documents, language='en-US'):
    book = epub.EpubBook()
    book.set_identifier('test-id')
    book.set_title('Test Book')
    if language is not None:
        book.set_language(language)

    items = []
    for index, html in enumerate(documents):
        chapter = epub.EpubHtml(title=f'C{index}', file_name=f'c{index}.xhtml')
        chapter.set_content(html)
        book.add_item(chapter)
        items.append(chapter)

    book.add_item(epub.EpubNcx())
    book.spine = items
    epub.write_epub(str(path), book)
    return path


def body(text):
    return f'<html><body><p>{text}</p></body></html>'


def make_token(
    text='word',
    word_type=WordType.NOUN,
    *,
    is_stop=False,
    is_alpha=True,
    is_punct=False,
    is_space=False,
    lemma=None,
):
    return Token(
        text=text,
        lemma=lemma if lemma is not None else text,
        word_type=word_type,
        is_alpha=is_alpha,
        is_punct=is_punct,
        is_space=is_space,
        is_stop=is_stop,
    )


@pytest.fixture(scope='session')
def en_lemmatizer():
    return SpacyLemmatizer(Language.ENGLISH)


@pytest.fixture(scope='session')
def de_lemmatizer():
    return SpacyLemmatizer(Language.GERMAN)


@pytest.fixture
def tiny_epub(tmp_path):
    return make_epub(
        tmp_path / 'tiny.epub',
        [body('The cats ran quickly.'), body('Cats drank the water.')],
    )


@pytest.fixture
def tiny_txt(tmp_path):
    path = tmp_path / 'tiny.txt'
    path.write_text('The cats ran quickly. Cats drank the water.\n')
    return path
