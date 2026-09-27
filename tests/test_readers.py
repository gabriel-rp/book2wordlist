import pytest

from book2wordlist.language import Language
from book2wordlist.readers import (
    epub as readers_epub,
    plaintext as readers_text,
)
from book2wordlist.readers.registry import READERS
from conftest import body, make_epub


def test_epub_reader_reports_language_and_documents(tiny_epub):
    result = readers_epub.EpubReader().read(tiny_epub)

    assert result.language == 'en-US'
    assert len(result.documents) == 2
    assert 'cats' in result.documents[0].lower()
    assert result.char_count == sum(len(d) for d in result.documents)


def test_epub_reader_stamps_the_format_and_its_capability(tiny_epub):
    result = readers_epub.EpubReader().read(tiny_epub)

    assert result.format_name == 'EPUB'
    assert result.declares_language is True


def test_inline_tags_do_not_fuse_adjacent_words(tmp_path):
    path = make_epub(
        tmp_path / 'tags.epub',
        ['<html><body><p>Hello<em>world</em></p></body></html>'],
    )

    text = ' '.join(readers_epub.EpubReader().read(path).documents)

    assert 'helloworld' not in text.lower()
    assert 'Hello world' in text


def test_the_tag_separator_is_configurable(tmp_path):
    path = make_epub(
        tmp_path / 'tags.epub',
        ['<html><body><p>Hello<em>world</em></p></body></html>'],
    )
    reader = readers_epub.EpubReader(
        readers_epub.EpubOptions(tag_separator='|')
    )

    assert 'Hello|world' in reader.read(path).documents[0]


def test_blank_documents_are_skipped(tmp_path):
    path = make_epub(
        tmp_path / 'blank.epub',
        [body('real content'), '<html><body><p>   </p></body></html>'],
    )

    assert len(readers_epub.EpubReader().read(path).documents) == 1


def test_an_epub_without_language_metadata_yields_none(tmp_path):
    path = make_epub(tmp_path / 'nolang.epub', [body('text')], language=None)

    assert readers_epub.EpubReader().read(path).language is None
    assert readers_epub.EpubReader().detect_language(path) is None


def test_epub_detect_language_reads_the_metadata(tmp_path):
    path = make_epub(tmp_path / 'de.epub', [body('Haus')], language='de-DE')

    assert readers_epub.EpubReader().detect_language(path) == 'de-DE'


def test_plain_text_is_read_as_one_document(tiny_txt):
    result = readers_text.PlainTextReader().read(tiny_txt)

    assert len(result.documents) == 1
    assert 'cats' in result.documents[0]
    assert result.format_name == 'plain text'


def test_plain_text_declares_no_language(tiny_txt):
    result = readers_text.PlainTextReader().read(tiny_txt)

    assert result.language is None
    assert result.declares_language is False


def test_plain_text_does_not_implement_detection(tiny_txt):
    with pytest.raises(NotImplementedError, match='no language metadata'):
        readers_text.PlainTextReader().detect_language(tiny_txt)


def test_detection_support_is_derived_from_the_implementation():
    assert readers_epub.EpubReader.supports_language_detection()
    assert not readers_text.PlainTextReader.supports_language_detection()


def test_plain_text_falls_back_to_a_lenient_encoding(tmp_path):
    path = tmp_path / 'latin.txt'
    path.write_bytes('Grüße aus Köln'.encode('cp1252'))

    text = readers_text.PlainTextReader().read(path).documents[0]

    assert text == 'Grüße aus Köln'


def test_the_encoding_order_is_configurable(tmp_path):
    path = tmp_path / 'latin.txt'
    path.write_bytes('Köln'.encode('cp1252'))
    reader = readers_text.PlainTextReader(
        readers_text.PlainTextOptions(encodings=('latin-1',))
    )

    assert reader.read(path).documents[0] == 'Köln'


def test_an_empty_text_file_yields_no_documents(tmp_path):
    path = tmp_path / 'empty.txt'
    path.write_text('   \n')

    assert readers_text.PlainTextReader().read(path).documents == []


@pytest.mark.parametrize(
    'name,expected',
    [
        ('book.epub', readers_epub.EpubReader),
        ('BOOK.EPUB', readers_epub.EpubReader),
        ('book.txt', readers_text.PlainTextReader),
        ('book.text', readers_text.PlainTextReader),
    ],
)
def test_the_registry_dispatches_on_the_extension(name, expected):
    assert READERS.class_for(name) is expected


def test_the_registry_rejects_an_unsupported_extension():
    with pytest.raises(ValueError, match='Unsupported file type'):
        READERS.class_for('book.pdf')


def test_the_unsupported_error_lists_what_is_supported():
    with pytest.raises(ValueError) as excinfo:
        READERS.class_for('book.pdf')

    assert '.epub' in str(excinfo.value)
    assert '.txt' in str(excinfo.value)


def test_the_registry_describes_its_formats():
    descriptions = ' '.join(READERS.descriptions())

    assert 'EPUB (.epub)' in descriptions
    assert 'plain text (.txt, .text)' in descriptions


def test_an_explicit_language_wins_over_the_declared_one(tiny_epub):
    reader = readers_epub.EpubReader()
    book = reader.read(tiny_epub)

    assert reader.resolve_language(Language.GERMAN, book) is Language.GERMAN


def test_detect_reads_the_language_the_epub_declares(tiny_epub):
    reader = readers_epub.EpubReader()
    book = reader.read(tiny_epub)

    assert reader.resolve_language(Language.DETECT, book) is Language.ENGLISH
    assert reader.resolve_language(None, book) is Language.ENGLISH


def test_detecting_a_format_without_metadata_is_an_error(tiny_txt):
    reader = readers_text.PlainTextReader()
    book = reader.read(tiny_txt)

    with pytest.raises(ValueError, match='carry no language metadata'):
        reader.resolve_language(Language.DETECT, book)


def test_an_epub_that_declares_nothing_is_an_error(tmp_path):
    path = make_epub(tmp_path / 'nolang.epub', [body('text')], language=None)
    reader = readers_epub.EpubReader()

    with pytest.raises(ValueError, match='declares no language'):
        reader.resolve_language(Language.DETECT, reader.read(path))


def test_an_epub_declaring_an_unsupported_language_is_an_error(tmp_path):
    path = make_epub(tmp_path / 'pt.epub', [body('texto')], language='pt-BR')
    reader = readers_epub.EpubReader()

    with pytest.raises(ValueError, match="declares the language 'pt-BR'"):
        reader.resolve_language(Language.DETECT, reader.read(path))


def test_an_explicit_language_saves_a_file_that_cannot_be_detected(tiny_txt):
    reader = readers_text.PlainTextReader()

    assert (
        reader.resolve_language(Language.GERMAN, reader.read(tiny_txt))
        is Language.GERMAN
    )
