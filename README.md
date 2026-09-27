# book2wordlist

Turn a book into a ranked lemma wordlist that you can use for vocabulary acquisition.

This tool was designed for language learning. The idea is that to read a book in your target language, it's helpful to be familiar with its vocabulary.

You can use book2wordlist alongside [germanki](https://github.com/gabriel-rp/germanki) or another tool of your preference to create flashcards and study the book's vocabulary.

## Disclaimer - Book Files
This tool only processes e-book files. You must provide a DRM-free version of the book in one of the accepted formats.

## Lemmas
Inflected forms collapse onto their lemma (`said`/`saying`/`says` → `say`), and
function words, names and numbers are filtered out. On *Dune* the top of the
list is `say, see, think, man, know, hand, look, come, ask, take` rather than
`the, of, a, to, and`.

## Install

```sh
uv sync
```

That installs the `book2wordlist` command along with the English and German
models, so there is no separate model download step.

## Use it

```sh
book2wordlist Dune.epub --lang en -o dune.csv
```

```csv
rank,lemma,count,word_type
1,say,2499,verb
2,see,984,verb
3,think,831,verb
4,man,814,noun
5,one,706,numeral
```

One row per lemma, most frequent first, ties broken alphabetically so two runs
of the same book give byte-identical files. Without `-o` the rows go to
stdout, so they pipe.

A full novel takes about 15 seconds. Add `-v` to watch the stages on stderr.

### More examples

```sh
# Take the language from the EPUB's own metadata instead of naming it
book2wordlist Dune.epub --lang detect -o dune.csv

# A German plain-text book: .txt carries no metadata, so name the language
book2wordlist Faust.txt --lang de -o faust.csv

# A longer list that keeps character and place names
book2wordlist Dune.epub --lang en --top-lemmas 2000 --no-filter-names

# Semicolons, for a spreadsheet that expects them
book2wordlist Dune.epub --lang en --csv-delimiter ';' -o dune.csv

# Just the lemmas, one per line, ready to pipe
book2wordlist Dune.epub --lang en --output-type simple | sort > words.txt

# JSON instead, on one line
book2wordlist Dune.epub --lang en --format json --json-indent 0 -o dune.json

# Straight to the terminal
book2wordlist Dune.epub --lang en | head -20
```

### Input formats

| Format | Extensions | Language detection |
|---|---|---|
| EPUB | `.epub` | yes, from the book's metadata |
| Plain text | `.txt`, `.text` | no — pass `--lang` |

### Choosing the language

`--lang` is required, and takes `en`, `de`, or `detect`. `detect` reads the
language the file declares, which only works for formats that carry one: a
`.txt` file, or an EPUB whose metadata is empty or names a language with no
model, is an error rather than a silent guess.

### The columns

`rank`, `lemma`, `count`, `word_type` — as CSV rows or, with `--format json`,
an array of objects with those four keys.

`--output-type simple` narrows that to the lemma alone: a bare line per lemma
with no header in CSV, a bare array of strings in JSON.

`word_type` is one of `noun`, `name`, `verb`, `auxiliary`, `adjective`,
`adverb`, `numeral`, `pronoun`, `determiner`, `preposition`, `conjunction`,
`particle`, `interjection`, `symbol`, `punctuation`, `other`. These are this
tool's own names, not the tagset of the NLP library underneath, so the output
stays the same if that library is ever swapped. They are useful for deciding
what kind of flashcard or glossary entry a term deserves.

### Flags

| Flag | Meaning |
|---|---|
| `--lang {detect,en,de}` | **Required.** The book's language, or `detect` |
| `-o, --output PATH` | Write here instead of stdout |
| `--format {csv,json}` | Output format |
| `--output-type {full,simple}` | `simple` writes the lemma alone |
| `--top-lemmas N` | How many lemmas to write (default: 500) |
| `--no-filter-stopwords` | Keep function words (`the`, `and`, `der`, `und`) |
| `--no-filter-names` | Keep names (`Paul`, `Arrakis`) |
| `--no-filter-non-alpha` | Keep numbers and other non-alphabetic tokens |
| `--min-lemma-length N` | Drop shorter lemmas (default: 2) |
| `--max-chunk-chars N` | Split long documents before lemmatizing |
| `-v, --verbose` | Log each stage to stderr |

There are also per-backend flags — `--spacy-batch-size`,
`--epub-tag-separator`, `--text-encodings`, `--csv-delimiter`,
`--json-indent` and friends.
`book2wordlist --help` lists all of them with their defaults.

Exit code is `1`, with a message on stderr, for a missing file, an unsupported
file type, a language that cannot be detected or has no model, or a model that
is not installed.

## Use it from Python

Every parameter of a run lives in one `Options` dataclass — the CLI builds
exactly the same object from argv.

```python
from book2wordlist.language import Language
from book2wordlist.options import Options
from book2wordlist.pipeline import extract_vocabulary

options = Options(lang=Language.ENGLISH, top_lemmas=100)
for entry in extract_vocabulary('Dune.epub', options):
    print(entry.rank, entry.lemma, entry.count, entry.word_type)
```

```python
from book2wordlist.pipeline import analyze_book, analyze_texts, run

analyze_book('Dune.epub', options)        # entries + counts + language
analyze_texts(['some text'], options)     # same pipeline, no file involved
run('Dune.epub', options)                 # what the CLI does; returns 0 or 1
```

## Good to know

- The name filter depends on the tagger, so invented names are sometimes
  mislabelled as common nouns and survive. On *Dune*, `harkonnen` lands at rank
  278 while `Paul`, `Jessica`, `Arrakis` and `Fremen` are removed.
- Front and back matter (blurbs, copyright) is counted with the prose — around
  0.3% of a typical novel.
- A few rows are numerals, prepositions and interjections (`one`, `beneath`,
  `shall`). They are kept on purpose: they are real vocabulary.
- Stopwords are only dropped when they are function words. Stop lists — German
  especially — also flag inflected content verbs, so a naive filter would take
  the lemma `gehen` down with `ging`.
- Counting is case-insensitive but display is not: English `Fear` merges with
  `fear`, while German nouns keep their capital (`Haus`, not `haus`).

## Extending or contributing

Input formats, NLP backends and output formats each sit behind an interface
with its own package (`readers/`, `lemmatizers/`, `writers/`), so a new EPUB
library, a PDF reader, another lemmatizer or a JSON output is a subclass plus
one line in that package's registry. Each backend owns its own options
dataclass, which becomes a section of `Options` and a group of CLI flags.

```sh
uv run pytest                                       # 141 tests
uv run ruff check src tests && uv run ruff format src tests
uv run pre-commit install                           # hooks on commit
```

CI runs lint, format check and tests on every push and pull request; pushing a
new version to `main` tags a release and publishes to PyPI.
