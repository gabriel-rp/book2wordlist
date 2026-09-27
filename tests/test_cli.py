from pathlib import Path
from unittest.mock import patch

import pytest

from book2wordlist import cli
from book2wordlist.language import Language
from book2wordlist.options import Options
from book2wordlist.outputformats import OutputFormat


def parse(argv):
    return Options.from_namespace(cli.build_parser().parse_args(argv))


def test_the_parser_produces_the_options_dataclass():
    options = parse(
        ['book.epub', '--lang', 'detect', '-o', 'out.csv', '--top-lemmas', '7']
    )

    assert isinstance(options, Options)
    assert options.output == Path('out.csv')
    assert options.top_lemmas == 7
    assert options.lang is Language.DETECT


def test_the_language_is_required():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(['book.epub'])


def test_the_language_flag_is_parsed_into_the_enum():
    assert parse(['book.epub', '--lang', 'de']).lang is Language.GERMAN


def test_an_unknown_language_is_rejected_by_the_parser():
    with pytest.raises(SystemExit):
        cli.build_parser().parse_args(['book.epub', '--lang', 'fr'])


def test_the_language_choices_come_from_the_backend():
    help_text = cli.build_parser().format_help()

    assert '{detect,en,de}' in help_text
    assert 'spaCy backend ships models for' in help_text


def test_backend_options_reach_their_sections():
    options = parse(
        [
            'book.epub',
            '--lang',
            'en',
            '--spacy-batch-size',
            '32',
            '--spacy-exclude',
            'ner,parser,tagger',
            '--epub-html-parser',
            'html.parser',
            '--text-encodings',
            'utf-8',
            '--csv-delimiter',
            ';',
            '--no-json-ensure-ascii',
        ]
    )

    assert options.spacy.batch_size == 32
    assert options.spacy.exclude == ('ner', 'parser', 'tagger')
    assert options.epub.html_parser == 'html.parser'
    assert options.text.encodings == ('utf-8',)
    assert options.csv.delimiter == ';'
    assert options.json.ensure_ascii is False


def test_a_boolean_backend_option_can_be_turned_on_and_off():
    assert (
        parse(
            ['b.epub', '--lang', 'en', '--json-ensure-ascii']
        ).json.ensure_ascii
        is True
    )
    assert (
        parse(
            ['b.epub', '--lang', 'en', '--no-json-ensure-ascii']
        ).json.ensure_ascii
        is False
    )


@pytest.mark.parametrize(
    'flag,attribute',
    [
        ('--no-filter-names', 'filter_names'),
        ('--no-filter-stopwords', 'filter_stopwords'),
        ('--no-filter-non-alpha', 'filter_non_alpha'),
    ],
)
def test_each_filter_is_switchable_on_its_own(flag, attribute):
    default = parse(['b.epub', '--lang', 'en'])
    switched = parse(['b.epub', '--lang', 'en', flag])

    assert getattr(default, attribute) is True
    assert getattr(switched, attribute) is False


def test_the_format_flag_is_parsed_into_the_enum():
    assert parse(
        ['b.epub', '--lang', 'en', '--format', 'csv']
    ).output_format is (OutputFormat.CSV)


def test_the_help_documents_inputs_outputs_and_backends():
    help_text = cli.build_parser().format_help()

    assert 'EPUB (.epub)' in help_text
    assert 'plain text' in help_text and '.text' in help_text
    assert 'examples:' in help_text
    assert 'rank, lemma, count, word_type' in help_text
    assert 'spacy options:' in help_text
    assert 'csv options:' in help_text


def test_main_parses_and_delegates_to_the_pipeline():
    with patch('book2wordlist.cli.run', return_value=0) as run:
        code = cli.main(['book.epub', '--lang', 'en', '--top-lemmas', '3'])

    assert code == 0
    path, options = run.call_args.args
    assert path == Path('book.epub')
    assert options.top_lemmas == 3


def test_main_writes_the_wordlist(tiny_epub, tmp_path, en_lemmatizer):
    out = tmp_path / 'vocab.csv'

    with patch(
        'book2wordlist.pipeline.load_lemmatizer', return_value=en_lemmatizer
    ):
        code = cli.main([str(tiny_epub), '--lang', 'en', '-o', str(out)])

    assert code == 0
    assert out.read_text().startswith('rank,lemma,count,word_type\n')


def test_main_writes_to_stdout_by_default(tiny_epub, capsys, en_lemmatizer):
    with patch(
        'book2wordlist.pipeline.load_lemmatizer', return_value=en_lemmatizer
    ):
        code = cli.main([str(tiny_epub), '--lang', 'detect'])

    assert code == 0
    assert capsys.readouterr().out.startswith('rank,lemma,count,word_type\n')


def test_main_reports_a_missing_file(tmp_path, capsys):
    code = cli.main([str(tmp_path / 'absent.epub'), '--lang', 'en'])

    assert code == 1
    assert 'No such file' in capsys.readouterr().err
