import csv
import io
import json

import pytest

from book2wordlist.outputformats import OutputFormat, OutputType
from book2wordlist.results import VocabEntry
from book2wordlist.wordtypes import WordType
from book2wordlist.writers.csv import CsvOptions, CsvWriter
from book2wordlist.writers.json import JsonOptions, JsonWriter
from book2wordlist.writers.registry import WRITERS


def entries():
    return [
        VocabEntry(rank=1, lemma='say', count=9, word_type=WordType.VERB),
        VocabEntry(rank=2, lemma='Haus', count=4, word_type=WordType.NOUN),
    ]


def written(writer, output_type=OutputType.FULL):
    out = io.StringIO()
    writer.write_entries(entries(), out, output_type)
    return out.getvalue()


def test_csv_header_and_rows_use_our_own_column_names():
    rows = list(csv.reader(io.StringIO(written(CsvWriter()))))

    assert rows[0] == ['rank', 'lemma', 'count', 'word_type']
    assert rows[1] == ['1', 'say', '9', 'verb']
    assert rows[2] == ['2', 'Haus', '4', 'noun']


def test_csv_uses_unix_line_endings():
    text = written(CsvWriter())

    assert '\r' not in text
    assert text.endswith('2,Haus,4,noun\n')


def test_the_csv_delimiter_comes_from_the_writer_options():
    text = written(CsvWriter(CsvOptions(delimiter=';')))

    assert text.splitlines()[1] == '1;say;9;verb'


def test_json_writes_one_object_per_lemma():
    rows = json.loads(written(JsonWriter()))

    assert rows[0] == {
        'rank': 1,
        'lemma': 'say',
        'count': 9,
        'word_type': 'verb',
    }
    assert [row['rank'] for row in rows] == [1, 2]


def test_json_indentation_is_configurable():
    assert '\n  ' in written(JsonWriter())
    assert written(JsonWriter(JsonOptions(indent=0))).count('\n') == 1


def test_json_keeps_non_ascii_readable_unless_told_otherwise():
    entry = [
        VocabEntry(rank=1, lemma='Grüße', count=1, word_type=WordType.NOUN)
    ]
    out, escaped = io.StringIO(), io.StringIO()

    JsonWriter().write_entries(entry, out)
    JsonWriter(JsonOptions(ensure_ascii=True)).write_entries(entry, escaped)

    assert 'Grüße' in out.getvalue()
    assert '\\u' in escaped.getvalue()


@pytest.mark.parametrize('output_format', list(OutputFormat))
def test_every_format_reports_the_same_four_facts(output_format):
    writer = WRITERS.class_for(output_format)()

    text = written(writer)

    for fact in ('rank', 'lemma', 'count', 'word_type', 'say', 'verb'):
        assert fact in text
    assert 'VERB' not in text


@pytest.mark.parametrize(
    'name,expected',
    [('csv', CsvWriter), ('json', JsonWriter)],
)
def test_the_registry_resolves_a_format_to_its_writer(name, expected):
    assert WRITERS.class_for(name) is expected
    assert WRITERS.class_for(OutputFormat.from_name(name)) is expected


def test_the_registry_rejects_an_unknown_format():
    with pytest.raises(ValueError, match='Unsupported output format'):
        WRITERS.class_for('yaml')


def test_the_registry_names_what_it_has():
    assert WRITERS.names() == ['csv', 'json']


def test_simple_csv_is_a_bare_list_of_lemmas():
    text = written(CsvWriter(), OutputType.SIMPLE)

    assert text == 'say\nHaus\n'


def test_simple_json_is_a_bare_array_of_lemmas():
    assert json.loads(written(JsonWriter(), OutputType.SIMPLE)) == [
        'say',
        'Haus',
    ]


@pytest.mark.parametrize('output_format', list(OutputFormat))
def test_simple_drops_every_fact_but_the_lemma(output_format):
    text = written(WRITERS.class_for(output_format)(), OutputType.SIMPLE)

    assert 'say' in text
    for dropped in ('rank', 'count', 'word_type', 'verb', '9'):
        assert dropped not in text


def test_an_unknown_output_type_is_rejected():
    with pytest.raises(ValueError, match='Unsupported output type'):
        OutputType.from_name('terse')
