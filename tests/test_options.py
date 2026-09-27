import argparse
from pathlib import Path

from book2wordlist.language import Language
from book2wordlist.lemmatizers.spacy import SpacyOptions
from book2wordlist.options import Options
from book2wordlist.writers.csv import CsvOptions


def test_a_section_is_found_by_its_type():
    options = Options(spacy=SpacyOptions(batch_size=2))

    assert options.section(SpacyOptions).batch_size == 2
    assert options.section(CsvOptions) is options.csv


def test_from_namespace_splits_flat_flags_into_sections():
    args = argparse.Namespace(
        book=Path('x.epub'),
        lang=Language.GERMAN,
        top_lemmas=5,
        spacy_batch_size=16,
        spacy_exclude=('ner',),
        epub_html_parser='html.parser',
        epub_tag_separator=' ',
        text_encodings=('utf-8',),
        csv_delimiter=';',
        csv_line_terminator='\n',
    )

    options = Options.from_namespace(args)

    assert options.lang is Language.GERMAN
    assert options.top_lemmas == 5
    assert options.spacy == SpacyOptions(batch_size=16, exclude=('ner',))
    assert options.epub.html_parser == 'html.parser'
    assert options.text.encodings == ('utf-8',)
    assert options.csv.delimiter == ';'


def test_from_namespace_ignores_what_is_not_an_option():
    args = argparse.Namespace(book=Path('x.epub'), nonsense=1)

    assert Options.from_namespace(args) == Options()
