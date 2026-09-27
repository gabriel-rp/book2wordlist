from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import replace
import logging
from pathlib import Path
import sys
from typing import IO

from book2wordlist.language import Language
from book2wordlist.lemmatizers.base import Lemmatizer, Token
from book2wordlist.lemmatizers.registry import LEMMATIZER
from book2wordlist.options import DEFAULT_OPTIONS, Options
from book2wordlist.readers.base import BookReader, BookText
from book2wordlist.readers.epub import EpubReader
from book2wordlist.readers.registry import READERS
from book2wordlist.results import LemmaCounts, VocabEntry, VocabResult
from book2wordlist.writers.base import ResultWriter
from book2wordlist.writers.registry import WRITERS

logger = logging.getLogger(__name__)


def reader_for(
    path: str | Path, options: Options = DEFAULT_OPTIONS
) -> BookReader:
    reader_class = READERS.class_for(path)
    return reader_class(options.section(reader_class.options_type))


def read_book(
    path: str | Path,
    options: Options = DEFAULT_OPTIONS,
    reader: BookReader | None = None,
) -> BookText:
    return (reader or reader_for(path, options)).read(path)


def read_epub(
    path: str | Path, options: Options = DEFAULT_OPTIONS
) -> BookText:
    return EpubReader(options.epub).read(path)


def detect_language(
    path: str | Path,
    options: Options = DEFAULT_OPTIONS,
    reader: BookReader | None = None,
) -> str | None:
    return (reader or reader_for(path, options)).detect_language(path)


def chunk_texts(
    texts: Iterable[str], options: Options = DEFAULT_OPTIONS
) -> Iterator[str]:
    for text in texts:
        if len(text) <= options.max_chunk_chars:
            yield text
        else:
            yield from split_text(text, options.max_chunk_chars)


def split_text(text: str, max_chars: int) -> Iterator[str]:
    start, end = 0, len(text)
    while start < end:
        if end - start <= max_chars:
            yield text[start:]
            return
        limit = start + max_chars
        split = text.rfind('\n', start, limit)
        if split <= start:
            split = text.rfind(' ', start, limit)
        if split <= start:
            split = limit
        yield text[start:split]
        start = split


def keep_token(token: Token, options: Options = DEFAULT_OPTIONS) -> bool:
    if token.is_space or token.is_punct:
        return False
    if options.filter_non_alpha and not token.is_alpha:
        return False
    if options.filter_names and token.word_type.is_name:
        return False
    return not (
        options.filter_stopwords
        and token.is_stop
        and token.word_type.is_closed_class
    )


def count_lemmas(
    texts: Iterable[str],
    lemmatizer: Lemmatizer,
    options: Options = DEFAULT_OPTIONS,
) -> LemmaCounts:
    counts = LemmaCounts()
    for token in lemmatizer.tokens(texts):
        if not keep_token(token, options):
            continue
        lemma = token.lemma.strip()
        if len(lemma) < options.min_lemma_length:
            continue
        counts.add(lemma, token.word_type)
    return counts


def top_entries(
    counts: LemmaCounts, options: Options = DEFAULT_OPTIONS
) -> list[VocabEntry]:
    ranked = sorted(counts.counts.items(), key=lambda kv: (-kv[1], kv[0]))
    entries = []
    for rank, (key, count) in enumerate(ranked[: options.top_lemmas], start=1):
        entries.append(
            VocabEntry(
                rank=rank,
                lemma=counts.displays[key].most_common(1)[0][0],
                count=count,
                word_type=counts.word_types[key].most_common(1)[0][0],
            )
        )
    return entries


def load_lemmatizer(
    language: Language, options: Options = DEFAULT_OPTIONS
) -> Lemmatizer:
    return LEMMATIZER.load(language, options.section(LEMMATIZER.options_type))


def analyze_texts(
    documents: Iterable[str],
    options: Options = DEFAULT_OPTIONS,
    lemmatizer: Lemmatizer | None = None,
) -> VocabResult:
    language = Language.from_tag(options.lang)
    if language is Language.DETECT:
        raise ValueError(
            'Plain texts carry no language metadata, so the language '
            'cannot be detected: pass it explicitly'
        )
    options = replace(options, lang=language)
    documents = list(documents)

    if lemmatizer is None:
        lemmatizer = load_lemmatizer(language, options)
    logger.info('Lemmatizing with %s', lemmatizer.name)

    counts = count_lemmas(chunk_texts(documents, options), lemmatizer, options)
    logger.info(
        'Kept %d lemma occurrences across %d unique lemmas',
        sum(counts.counts.values()),
        len(counts.counts),
    )

    return VocabResult(
        language=language,
        entries=top_entries(counts, options),
        lemma_counts=counts,
    )


def analyze_book(
    path: str | Path,
    options: Options = DEFAULT_OPTIONS,
    reader: BookReader | None = None,
    lemmatizer: Lemmatizer | None = None,
) -> VocabResult:
    path = Path(path).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f'No such file: {path}')

    reader = reader or reader_for(path, options)
    logger.info('Reading %s as %s', path, reader.format_name)
    book = reader.read(path)
    logger.info(
        'Extracted %d documents, %d characters',
        len(book.documents),
        book.char_count,
    )

    language = reader.resolve_language(options.lang, book)
    return analyze_texts(
        book.documents, replace(options, lang=language), lemmatizer
    )


def analyze_epub(
    path: str | Path,
    options: Options = DEFAULT_OPTIONS,
    lemmatizer: Lemmatizer | None = None,
) -> VocabResult:
    return analyze_book(path, options, EpubReader(options.epub), lemmatizer)


def extract_vocabulary(
    path: str | Path, options: Options = DEFAULT_OPTIONS
) -> list[VocabEntry]:
    return analyze_book(path, options).entries


def writer_for(options: Options = DEFAULT_OPTIONS) -> ResultWriter:
    writer_class = WRITERS.class_for(options.output_format)
    return writer_class(options.section(writer_class.options_type))


def write_result(
    result: VocabResult,
    options: Options = DEFAULT_OPTIONS,
    stdout: IO[str] | None = None,
    writer: ResultWriter | None = None,
) -> None:
    writer = writer or writer_for(options)

    if options.output is None:
        writer.write_entries(
            result.entries,
            stdout if stdout is not None else sys.stdout,
            options.output_type,
        )
        return

    output = Path(options.output)
    with output.open('w', newline='', encoding='utf-8') as handle:
        writer.write_entries(result.entries, handle, options.output_type)
    logger.info(
        'Wrote %d rows to %s as %s',
        len(result.entries),
        output,
        options.output_format,
    )


def run(
    path: str | Path,
    options: Options = DEFAULT_OPTIONS,
    stdout: IO[str] | None = None,
) -> int:
    try:
        result = analyze_book(path, options)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1

    write_result(result, options, stdout=stdout)
    return 0
