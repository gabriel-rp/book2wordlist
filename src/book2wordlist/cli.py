from __future__ import annotations

import argparse
from dataclasses import fields
import logging
from pathlib import Path
import sys
import textwrap

from book2wordlist.language import Language
from book2wordlist.lemmatizers.registry import LEMMATIZER
from book2wordlist.options import DEFAULT_OPTIONS, Options
from book2wordlist.outputformats import OutputFormat, OutputType
from book2wordlist.pipeline import run
from book2wordlist.readers.registry import READERS
from book2wordlist.wordtypes import WordType
from book2wordlist.writers.registry import WRITERS

DESCRIPTION = """\
Extract the most frequent lemmatized terms from a book -- the vocabulary
actually worth learning from it.

Inflected forms collapse onto their lemma (said/saying/says -> say), and
function words, names and numbers are filtered out, so the top of the list
is say, see, think, man, know rather than the, of, a, to, and.
"""

EPILOG = """\
examples:
  book2wordlist Dune.epub --lang en -o dune.csv
      500 English lemmas.

  book2wordlist Dune.epub --lang detect -o dune.csv
      The same, taking the language from the EPUB metadata instead.

  book2wordlist Faust.txt --lang de -o faust.csv
      Plain text carries no metadata, so 'detect' would be an error here;
      name the language instead.

  book2wordlist Dune.epub --lang en --top-lemmas 2000 --no-filter-names
      A longer list that keeps character and place names.

  book2wordlist Dune.epub --lang en --format csv --csv-delimiter ';'
      The same rows, written for a spreadsheet that expects semicolons.

  book2wordlist Dune.epub --lang en --output-type simple
      Just the lemmas, one per line, ready to pipe.

output:
  One row per lemma, most frequent first, ties broken alphabetically so
  runs are byte-identical: rank, lemma, count, word_type. --format changes
  the syntax, --output-type simple narrows it to the lemma alone.

  word_type is this package's own vocabulary, not the tagset of whichever
  NLP library is underneath:
{word_types}

notes:
  A full novel takes roughly 15 seconds, nearly all of it lemmatization.
  Exit code is 1, with a message on stderr, for a missing file, an
  unsupported file type, a language that cannot be detected or that the
  backend has no model for, or a model that is not installed.
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='book2wordlist',
        description=DESCRIPTION,
        epilog=EPILOG.format(word_types=word_type_help()),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        'book',
        type=Path,
        metavar='BOOK',
        help='the book to read. Supported: '
        + '; '.join(READERS.descriptions()),
    )

    out = parser.add_argument_group('output')
    out.add_argument(
        '-o',
        '--output',
        type=Path,
        metavar='PATH',
        default=None,
        help='write the wordlist here (default: stdout)',
    )
    out.add_argument(
        '--format',
        dest='output_format',
        type=OutputFormat.from_name,
        choices=list(OutputFormat),
        default=DEFAULT_OPTIONS.output_format,
        metavar='{' + ','.join(WRITERS.names()) + '}',
        help=f'output format (default: {DEFAULT_OPTIONS.output_format})',
    )
    out.add_argument(
        '--output-type',
        type=OutputType.from_name,
        choices=list(OutputType),
        default=DEFAULT_OPTIONS.output_type,
        metavar='{' + ','.join(OutputType.names()) + '}',
        help=(
            "which facts to write. 'simple' writes the lemma alone, with no "
            'header and no rank, count or word type, for piping into other '
            f'tools (default: {DEFAULT_OPTIONS.output_type})'
        ),
    )
    out.add_argument(
        '--top-lemmas',
        type=int,
        metavar='N',
        default=DEFAULT_OPTIONS.top_lemmas,
        help=(
            'how many lemmas to write. A novel yields around 8000 distinct '
            f'ones (default: {DEFAULT_OPTIONS.top_lemmas})'
        ),
    )

    language = parser.add_argument_group(
        'language',
        wrap(
            f'The {LEMMATIZER.name} backend ships models for: '
            + ', '.join(
                f'{lang.code} ({lang.label})'
                for lang in LEMMATIZER.supported_languages()
            )
            + '. Another backend would offer another set.'
        ),
    )
    language.add_argument(
        '--lang',
        required=True,
        type=Language.from_tag,
        choices=LEMMATIZER.language_choices(),
        metavar='{'
        + ','.join(lang.code for lang in LEMMATIZER.language_choices())
        + '}',
        help=(
            'required. The language of the book, or '
            f'{Language.DETECT.code!r} to read it from the file metadata. '
            'Only formats that carry a language can be detected (EPUB can, '
            'plain text cannot); anything else is an error rather than a '
            'guess'
        ),
    )
    filters = parser.add_argument_group(
        'filters',
        'What is dropped before counting. Each can be turned off on its own.',
    )
    filters.add_argument(
        '--no-filter-stopwords',
        action='store_false',
        dest='filter_stopwords',
        help=(
            'keep function words (the, and, der, und). Only closed-class '
            'stopwords are dropped, so content verbs survive'
        ),
    )
    filters.add_argument(
        '--no-filter-names',
        action='store_false',
        dest='filter_names',
        help='keep names (Paul, Arrakis, and other proper nouns)',
    )
    filters.add_argument(
        '--no-filter-non-alpha',
        action='store_false',
        dest='filter_non_alpha',
        help='keep numbers and other non-alphabetic tokens',
    )
    filters.add_argument(
        '--min-lemma-length',
        type=int,
        metavar='N',
        default=DEFAULT_OPTIONS.min_lemma_length,
        help=(
            'drop lemmas shorter than this, which are mostly tokenizer '
            f'debris (default: {DEFAULT_OPTIONS.min_lemma_length})'
        ),
    )

    processing = parser.add_argument_group('processing')
    processing.add_argument(
        '--max-chunk-chars',
        type=int,
        metavar='N',
        default=DEFAULT_OPTIONS.max_chunk_chars,
        help=(
            'split documents longer than this before lemmatizing, keeping '
            "them under the backend's length limit; the split is lossless "
            f'(default: {DEFAULT_OPTIONS.max_chunk_chars})'
        ),
    )
    processing.add_argument(
        '-v',
        '--verbose',
        action='store_true',
        help='log each stage and its counts to stderr',
    )

    add_backend_options(parser)
    return parser


def wrap(text: str, indent: str = '  ') -> str:
    return textwrap.fill(
        text, width=78, initial_indent=indent, subsequent_indent=indent
    )


def word_type_help() -> str:
    return textwrap.fill(
        ', '.join(WordType.labels()),
        width=72,
        initial_indent='    ',
        subsequent_indent='    ',
    )


def add_backend_options(parser: argparse.ArgumentParser) -> None:
    for name, section in Options.sections().items():
        group = parser.add_argument_group(
            f'{name} options', wrap(section.cli_help)
        )
        defaults = section()
        for field in fields(section):
            value = getattr(defaults, field.name)
            if isinstance(value, bool):
                group.add_argument(
                    section.flag(field.name),
                    dest=section.dest(field.name),
                    action=argparse.BooleanOptionalAction,
                    default=value,
                    help=f'(default: {value!r})',
                )
            elif isinstance(value, tuple):
                group.add_argument(
                    section.flag(field.name),
                    dest=section.dest(field.name),
                    type=comma_separated,
                    metavar='A,B',
                    default=value,
                    help=f'(default: {",".join(value)})',
                )
            else:
                group.add_argument(
                    section.flag(field.name),
                    dest=section.dest(field.name),
                    type=type(value),
                    metavar=field.name.upper(),
                    default=value,
                    help=f'(default: {value!r})',
                )


def comma_separated(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(',') if part.strip())


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    options = Options.from_namespace(args)
    logging.basicConfig(
        level=logging.INFO if options.verbose else logging.WARNING,
        format='%(asctime)s %(levelname)s %(message)s',
    )
    return run(args.book, options)


if __name__ == '__main__':
    sys.exit(main())
