import io
from unittest.mock import patch

import pytest

from book2wordlist import pipeline
from book2wordlist.language import Language
from book2wordlist.lemmatizers.spacy import SpacyLemmatizer, SpacyOptions
from book2wordlist.options import Options
from book2wordlist.readers.epub import EpubOptions, EpubReader
from book2wordlist.results import LemmaCounts, VocabEntry
from book2wordlist.wordtypes import WordType
from conftest import body, make_epub, make_token


def test_the_reader_is_chosen_and_configured_from_options(tiny_epub):
    options = Options(epub=EpubOptions(tag_separator='|'))

    reader = pipeline.reader_for(tiny_epub, options)

    assert isinstance(reader, EpubReader)
    assert reader.options.tag_separator == '|'


def test_read_book_dispatches_on_the_file(tiny_epub, tiny_txt):
    assert pipeline.read_book(tiny_epub).format_name == 'EPUB'
    assert pipeline.read_book(tiny_txt).format_name == 'plain text'


def test_detect_language_uses_the_readers_capability(tiny_epub, tiny_txt):
    assert pipeline.detect_language(tiny_epub) == 'en-US'

    with pytest.raises(NotImplementedError):
        pipeline.detect_language(tiny_txt)


def test_short_texts_pass_through_chunking_untouched():
    texts = ['one', 'two']

    assert list(pipeline.chunk_texts(texts, Options())) == texts


def test_chunking_respects_the_cap_and_loses_nothing():
    text = 'wort ' * 5000

    chunks = list(pipeline.chunk_texts([text], Options(max_chunk_chars=1000)))

    assert len(chunks) > 1
    assert max(len(c) for c in chunks) <= 1000
    assert ''.join(chunks) == text


def test_chunking_prefers_paragraph_then_space_boundaries():
    options = Options(max_chunk_chars=10)

    assert list(pipeline.chunk_texts(['aaaa\nbbbb bbbb'], options))[0] == (
        'aaaa'
    )
    assert list(pipeline.chunk_texts(['aaaa bbbb cccc'], options))[0] == (
        'aaaa bbbb'
    )


def test_chunking_hard_cuts_when_no_boundary_exists():
    text = 'x' * 25

    chunks = list(pipeline.chunk_texts([text], Options(max_chunk_chars=10)))

    assert [len(c) for c in chunks] == [10, 10, 5]
    assert ''.join(chunks) == text


def test_chunking_handles_several_documents():
    options = Options(max_chunk_chars=10)

    chunks = list(pipeline.chunk_texts(['a' * 15, 'b' * 5], options))

    assert ''.join(chunks) == 'a' * 15 + 'b' * 5


@pytest.mark.parametrize(
    'token,options,kept',
    [
        (make_token(is_space=True), Options(), False),
        (make_token(is_punct=True), Options(), False),
        (make_token('3', WordType.NUMERAL, is_alpha=False), Options(), False),
        (
            make_token('3', WordType.NUMERAL, is_alpha=False),
            Options(filter_non_alpha=False),
            True,
        ),
        (make_token('Paul', WordType.NAME), Options(), False),
        (
            make_token('Paul', WordType.NAME),
            Options(filter_names=False),
            True,
        ),
        (
            make_token('the', WordType.DETERMINER, is_stop=True),
            Options(),
            False,
        ),
        (
            make_token('the', WordType.DETERMINER, is_stop=True),
            Options(filter_stopwords=False),
            True,
        ),
        (make_token('ging', WordType.VERB, is_stop=True), Options(), True),
        (make_token('Haus', WordType.NOUN, is_stop=True), Options(), True),
        (
            make_token('beneath', WordType.PREPOSITION, is_stop=False),
            Options(),
            True,
        ),
    ],
)
def test_which_tokens_reach_the_count(token, options, kept):
    assert pipeline.keep_token(token, options) is kept


@pytest.mark.parametrize(
    'word_type', [wt for wt in WordType if wt.is_closed_class]
)
def test_every_closed_class_stopword_is_dropped(word_type):
    assert not pipeline.keep_token(make_token('the', word_type, is_stop=True))


def test_english_inflections_collapse_onto_one_lemma(en_lemmatizer):
    counts = pipeline.count_lemmas(
        ['The cat ran. Cats run. A cat runs.'], en_lemmatizer
    )

    assert counts.counts['cat'] == 3
    assert counts.counts['run'] == 3


def test_casefolded_keys_merge_sentence_initial_capitals(en_lemmatizer):
    counts = pipeline.count_lemmas(
        ['Fear is real. I fear nothing.'], en_lemmatizer
    )

    assert counts.counts['fear'] == 2


def test_german_lemmas_and_the_open_class_stopword_rule(de_lemmatizer):
    text = (
        'Die Häuser waren größer als die Autos, und er ging schnell nach '
        'Hause. Paul lief 3 Kilometer und kaufte zwei Bücher.'
    )

    counts = pipeline.count_lemmas([text], de_lemmatizer)
    lemmas = set(counts.counts)

    assert {'haus', 'auto', 'buch', 'kilometer'} <= lemmas
    assert {'gehen', 'laufen', 'kaufen'} <= lemmas
    assert not {'der', 'und', 'als', 'nach', 'sein', 'paul', '3'} & lemmas


def test_german_noun_capitalization_is_preserved(de_lemmatizer):
    counts = pipeline.count_lemmas(['Die Häuser sind schön.'], de_lemmatizer)

    lemmas = {e.lemma for e in pipeline.top_entries(counts, Options())}

    assert 'Haus' in lemmas
    assert 'haus' not in lemmas


def test_short_lemmas_are_dropped(en_lemmatizer):
    counts = pipeline.count_lemmas(
        ['a e i o u cat'], en_lemmatizer, Options(min_lemma_length=2)
    )

    assert all(len(lemma) >= 2 for lemma in counts.counts)


def test_names_can_be_kept(en_lemmatizer):
    text = 'Arrakis is harsh. Arrakis is dry.'

    kept = pipeline.count_lemmas(
        [text], en_lemmatizer, Options(filter_names=False)
    )
    dropped = pipeline.count_lemmas([text], en_lemmatizer, Options())

    assert 'arrakis' in kept.counts
    assert 'arrakis' not in dropped.counts


def test_count_lemmas_records_the_word_type(en_lemmatizer):
    counts = pipeline.count_lemmas(['The cat ran fast.'], en_lemmatizer)

    assert counts.word_types['cat'].most_common(1)[0][0] is WordType.NOUN


def build_counts(pairs):
    counts = LemmaCounts()
    for lemma, count in pairs:
        for _ in range(count):
            counts.add(lemma, WordType.NOUN)
    return counts


def test_entries_are_ranked_by_descending_count():
    counts = build_counts([('rare', 1), ('common', 10), ('mid', 5)])

    entries = pipeline.top_entries(counts, Options())

    assert [e.lemma for e in entries] == ['common', 'mid', 'rare']
    assert [e.rank for e in entries] == [1, 2, 3]


def test_ties_break_alphabetically_for_determinism():
    counts = build_counts([('zebra', 4), ('apple', 4), ('mango', 4)])

    entries = pipeline.top_entries(counts, Options())

    assert [e.lemma for e in entries] == ['apple', 'mango', 'zebra']


def test_top_entries_respects_the_limit():
    counts = build_counts([(f'w{i}', i) for i in range(1, 21)])

    assert len(pipeline.top_entries(counts, Options(top_lemmas=5))) == 5


def test_the_most_frequent_spelling_is_displayed():
    counts = LemmaCounts()
    for _ in range(3):
        counts.add('Haus', WordType.NOUN)
    counts.add('haus', WordType.NOUN)

    entries = pipeline.top_entries(counts, Options(top_lemmas=1))

    assert entries[0].lemma == 'Haus'
    assert entries[0].count == 4


def test_the_most_frequent_word_type_is_reported():
    counts = LemmaCounts()
    counts.add('run', WordType.VERB)
    counts.add('run', WordType.VERB)
    counts.add('run', WordType.NOUN)

    assert pipeline.top_entries(counts, Options(top_lemmas=1))[
        0
    ].word_type is (WordType.VERB)


def test_analyze_texts_runs_without_any_file(en_lemmatizer):
    result = pipeline.analyze_texts(
        ['The cat drank the water.'],
        Options(lang=Language.ENGLISH, top_lemmas=10),
        en_lemmatizer,
    )

    assert result.language is Language.ENGLISH
    assert 'cat' in {e.lemma for e in result.entries}
    assert 'the' not in {e.lemma for e in result.entries}


def test_analyze_texts_requires_a_language(en_lemmatizer):
    with pytest.raises(ValueError, match='cannot be detected'):
        pipeline.analyze_texts(['A cat.'], Options(), en_lemmatizer)


def test_analyze_book_reads_an_epub(tiny_epub, en_lemmatizer):
    result = pipeline.analyze_book(
        tiny_epub,
        Options(lang=Language.DETECT, top_lemmas=10),
        lemmatizer=en_lemmatizer,
    )

    assert result.language is Language.ENGLISH
    assert 'cat' in {e.lemma for e in result.entries}


def test_analyze_book_reads_plain_text(tiny_txt, en_lemmatizer):
    result = pipeline.analyze_book(
        tiny_txt,
        Options(lang=Language.ENGLISH, top_lemmas=10),
        lemmatizer=en_lemmatizer,
    )

    assert 'cat' in {e.lemma for e in result.entries}


def test_analyze_book_rejects_an_unsupported_file_type(tmp_path):
    path = tmp_path / 'book.pdf'
    path.write_text('x')

    with pytest.raises(ValueError, match='Unsupported file type'):
        pipeline.analyze_book(path)


def test_analyze_book_rejects_a_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError, match='No such file'):
        pipeline.analyze_book(tmp_path / 'absent.epub')


def test_an_epub_without_a_language_is_an_error(tmp_path, en_lemmatizer):
    path = make_epub(tmp_path / 'nolang.epub', [body('text')], language=None)

    with pytest.raises(ValueError, match='declares no language'):
        pipeline.analyze_book(path, Options(), lemmatizer=en_lemmatizer)


def test_an_explicit_language_overrides_the_epub_metadata(
    tmp_path, de_lemmatizer
):
    path = make_epub(
        tmp_path / 'mislabelled.epub', [body('Die Häuser')], language='en-US'
    )

    result = pipeline.analyze_book(
        path, Options(lang=Language.GERMAN), lemmatizer=de_lemmatizer
    )

    assert result.language is Language.GERMAN


def test_analyze_epub_reads_an_epub_whatever_it_is_called(
    tmp_path, en_lemmatizer
):
    path = make_epub(tmp_path / 'book.bin', [body('The cat drank.')])

    result = pipeline.analyze_epub(
        path,
        Options(lang=Language.DETECT, top_lemmas=5),
        lemmatizer=en_lemmatizer,
    )

    assert 'cat' in {e.lemma for e in result.entries}


def test_the_lemmatizer_is_built_from_the_backend_section(en_lemmatizer):
    options = Options(lang=Language.ENGLISH, spacy=SpacyOptions(batch_size=4))

    with patch.object(
        SpacyLemmatizer, 'load_nlp', return_value=en_lemmatizer.nlp
    ):
        lemmatizer = pipeline.load_lemmatizer(Language.ENGLISH, options)

    assert lemmatizer.options == SpacyOptions(batch_size=4)


def test_extract_vocabulary_returns_entries(tiny_epub, en_lemmatizer):
    with patch(
        'book2wordlist.pipeline.load_lemmatizer', return_value=en_lemmatizer
    ):
        entries = pipeline.extract_vocabulary(
            tiny_epub, Options(lang=Language.ENGLISH, top_lemmas=3)
        )

    assert all(isinstance(e, VocabEntry) for e in entries)
    assert [e.rank for e in entries] == [1, 2, 3]


def test_write_result_writes_to_stdout_by_default(tiny_epub, en_lemmatizer):
    result = pipeline.analyze_book(
        tiny_epub,
        Options(lang=Language.ENGLISH, top_lemmas=2),
        lemmatizer=en_lemmatizer,
    )
    out = io.StringIO()

    pipeline.write_result(result, Options(top_lemmas=2), stdout=out)

    assert out.getvalue().startswith('rank,lemma,count,word_type\n')


def test_write_result_writes_the_output_file(
    tiny_epub, tmp_path, en_lemmatizer
):
    result = pipeline.analyze_book(
        tiny_epub,
        Options(lang=Language.ENGLISH, top_lemmas=2),
        lemmatizer=en_lemmatizer,
    )
    options = Options(
        lang=Language.ENGLISH, output=tmp_path / 'vocab.csv', top_lemmas=2
    )

    pipeline.write_result(result, options)

    assert options.output.read_text().startswith('rank,lemma')


def test_run_returns_zero_and_writes(tiny_epub, tmp_path, en_lemmatizer):
    out = tmp_path / 'vocab.csv'

    with patch(
        'book2wordlist.pipeline.load_lemmatizer', return_value=en_lemmatizer
    ):
        code = pipeline.run(
            tiny_epub, Options(lang=Language.ENGLISH, output=out)
        )

    assert code == 0
    assert 'cat' in out.read_text()


def missing_file(tmp_path):
    return tmp_path / 'absent.epub'


def unsupported_type(tmp_path):
    path = tmp_path / 'book.pdf'
    path.write_text('x')
    return path


def undetectable_language(tmp_path):
    return make_epub(tmp_path / 'nolang.epub', [body('text')], language=None)


@pytest.mark.parametrize(
    'make_input,message',
    [
        (missing_file, 'No such file'),
        (unsupported_type, 'Unsupported file type'),
        (undetectable_language, 'declares no language'),
    ],
)
def test_run_reports_the_problem_and_exits_nonzero(
    tmp_path, capsys, make_input, message
):
    code = pipeline.run(make_input(tmp_path), Options())

    assert code == 1
    assert message in capsys.readouterr().err


def test_run_reports_a_missing_model(tiny_epub, capsys):
    with patch(
        'book2wordlist.pipeline.load_lemmatizer',
        side_effect=RuntimeError('model missing'),
    ):
        code = pipeline.run(tiny_epub)

    assert code == 1
    assert 'model missing' in capsys.readouterr().err
