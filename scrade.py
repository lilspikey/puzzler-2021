#!/usr/bin/env python3

import argparse
import io
import re
import sqlite3 as db
import zipfile
from collections import Counter, defaultdict
from random import sample 


NON_WORD_WORD = re.compile(r'(\W*)(\w*)')
HTML_TAG = re.compile(r'(<.>)')
SINGLE_UPPER_CASE = re.compile(r'[^A-Z]*([A-Z])[^A-Z]*')


def scramble_word(word, amount):
    indexes = list(range(len(word)))
    to_swap = sample(indexes, k=min(int(amount * len(word)), len(word)))
    swap_lookup = dict(zip(sorted(to_swap), to_swap))
    return ''.join(word[swap_lookup.get(i, i)] for i in indexes)


def scramble(args):
    '''Scramble the words in the provided text'''
    amount = args.amount
    scrambled = []
    for m in NON_WORD_WORD.finditer(args.text):
        non_word, word = m.groups()
        if non_word:
            scrambled.append(non_word)
        if word:
            scrambled.append(scramble_word(word, args.amount))
    print(''.join(scrambled))


def _word_letters(word):
    return ''.join(sorted(word))


def _words_by_letters_index(words):
    words_by_letters = defaultdict(list)
    for word in words:
        word = word.strip().lower()
        words_by_letters[_word_letters(word)].append(word)
    return words_by_letters


def _get_words_from_letters(words_by_letters, word):
    letters = _word_letters(word.lower())
    words = words_by_letters.get(letters, [])
    m = SINGLE_UPPER_CASE.match(word)
    if m:
        letter = m.group(1).lower()
        starting = [w for w in words if w.startswith(letter)]
        if starting:
            words = starting
    if not words:
        words = [word.lower()]
    return words


def _hamming_dist(word1, word2):
    return sum(1 for (a, b) in zip(word1, word2) if a != b)


def dehamming(args):
    '''
    Attempt to descramble the words in provided text using a simple
    dictionary lookup, then a comparison based on the hamming distance
    of matching words to the scrambled word.
    '''
    verbose('Original:', args.text)
    words_by_letters = _words_by_letters_index(args.words_file)
    choices = []
    for m in NON_WORD_WORD.finditer(args.text):
        non_word, word = m.groups()
        if non_word:
            choices.append(non_word)
        if word:
            word_choices = _get_words_from_letters(words_by_letters, word)
            chosen = min(word_choices, key=lambda choice: _hamming_dist(word, choice))
            choices.append(chosen)
    print(''.join(choices))



def memoize_matches(fn):
    _cache = {}
    def _decorated(bigram_frequencies, prev, choices):
        key = (prev, choices)
        results = _cache.get(key, None)
        if results is None:
            results = fn(bigram_frequencies, prev, choices)
            _cache[key] = results
        return results
    return _decorated


@memoize_matches
def _match(bigram_frequencies, prev, choices):
    if choices:
        head, tail = choices[0], choices[1:]
        best_score = 0.0
        best_choices = None
        for choice in head:
            bigram = (prev, choice)
            freq = bigram_frequencies.get(bigram, 0.5)
            tail_score, tail_choices = _match(bigram_frequencies, choice, tail)
            score = tail_score * freq
            if score > best_score:
                best_score = score
                best_choices = (choice,) + tail_choices
        return (best_score, best_choices)
    else:
        bigram = (prev, '<END>')
        freq = bigram_frequencies.get(bigram, 0.5)
        return (freq, ())


class Model:
    def __init__(self, db_file):
        self.conn = db.connect(db_file)
        self.cur = self.conn.cursor()
        self.word_ids = {}

    def words_by_letters(self, words):
        words_by_letters = defaultdict(list)
        words = [word.lower() for word in words]
        letters = {_word_letters(word) for word in words + ['<START>', '<END>']}

        # might get hairy for _very_ large numbers of words...
        self.cur.execute('''
                         SELECT w.id, w.word, l.letters
                         FROM words w JOIN letters l ON w.letters_id = l.id
                         WHERE l.letters IN ({})
                         '''.format(','.join(['?'] * len(letters))),
                         list(letters)
                        )
        for word_id, word, letters in self.cur.fetchall():
            words_by_letters[letters].append(word)
            self.word_ids[word] = word_id

        return words_by_letters

    def bigram_frequencies(self, word_choices):
        bigrams = set()

        prev = ['<START>']
        for choice in word_choices + [['<END>']]:
            for p in prev:
                p_id = self.word_ids[p]
                for n in choice:
                    n_id = self.word_ids[n]
                    bigrams.add((p_id, n_id))
            prev = choice

        # this could get big - ideally I'd chunk this into multiple lists, but
        # maybe later
        flattened_ids = []
        for bigram in bigrams:
            flattened_ids.extend(bigram)
        self.cur.execute('''
                         SELECT p.word, n.word, b.frequency FROM bigrams b
                         JOIN words p ON b.prev_id = p.id
                         JOIN words n ON b.next_id = n.id
                         WHERE {}
                         '''.format(' OR '.join(['(b.prev_id = ? AND b.next_id = ?)'] * len(bigrams))),
                         flattened_ids
                        )

        bigram_frequencies = {}
        for prev_word, next_word, frequency in self.cur.fetchall():
            bigram_frequencies[(prev_word, next_word)] = frequency
        return bigram_frequencies


def debigram(args):
    '''
    Attempt to descramble the words in the provided text using a dictionary
    lookup, then find the best match for the combinations of words based on
    bigram frequencies. e.g. so "tbu htat" would tend to match "but that"
    instead of "tub that".
    '''
    verbose('Original:', args.text)
    model = Model(args.model_file)
    tokens = []
    words = []
    for m in NON_WORD_WORD.finditer(args.text):
        non_word, word = m.groups()
        if non_word:
            tokens.append(non_word)
        if word:
            words.append(word)
            tokens.append(None)

    words_by_letters = model.words_by_letters(words)
    verbose('Model loaded')
    choices = [tuple(_get_words_from_letters(words_by_letters, word)) for word in words]
    _visualise_choices(choices)
    bigram_frequencies = model.bigram_frequencies(choices)

    _, chosen_words = _match(bigram_frequencies, '<START>', tuple(choices))
    next_word = 0
    for i, token in enumerate(tokens):
        if token is None:
            tokens[i] = chosen_words[next_word]
            next_word += 1
    print(''.join(tokens))


def _visualise_choices(choices):
    max_len = max(len(choice) for choice in choices)
    for i in range(max_len):
        row = []
        for choice in choices:
            if i < len(choice):
                row.append(choice[i])
            else:
                row.append(' ' * len(choice[0]))
        verbose(' '.join(row))
    verbose()


def _load_sentence(terms, sentence):
    prev_word = terms.term('<START>')
    for m in NON_WORD_WORD.finditer(sentence):
        _, word = m.groups()
        if word:
            word = terms.term(word.lower())
            yield (prev_word, word)
            prev_word = word
    if prev_word:
        yield (prev_word, terms.term('<END>'))


def _load_doc(terms, doc):
    for line in doc:
        line = line.strip()
        if line:
            line = line.replace('@ @ @ @ @ @ @ @ @ @', '')
            sentences = []
            first_para_read = False
            for part in HTML_TAG.split(line):
                if part == '<p>':
                    first_para_read = True
                elif HTML_TAG.match(part):
                    first_para_read = False
                elif first_para_read:
                    sentences.extend(s.strip() for s in part.split('.'))

            for sentence in sentences:
                yield from _load_sentence(terms, sentence)


def _load_corpus(terms, corpus):
    for name in corpus.namelist():
        with corpus.open(name) as doc:
            yield from _load_doc(terms, io.TextIOWrapper(doc))


def _load_corpuses(terms, corpus_zips):
    for corpus_zip in corpus_zips:
        with zipfile.ZipFile(corpus_zip) as corpus:
            yield from _load_corpus(terms, corpus)


class Terms:
    def __init__(self):
        self.terms = {}

    def term(self, word):
        try:
            return self.terms[word]
        except KeyError:
            term = len(self.terms) + 1
            self.terms[word] = term
            return term


def make_model(args):
    '''
    Make SQLite database containing bigram frequencies + anagram lookup from the provided corpuses.
    Corpus data can be downloaded in zip format from https://www.corpusdata.org/iweb_samples.asp
    '''
    terms = Terms()
    terms.term('<START>')
    terms.term('<END>')
    bigram_frequencies = Counter()
    for bigram in _load_corpuses(terms, args.corpus_zip):
        bigram_frequencies[bigram] += 1

    letters = Terms()
    words = []
    for word, word_id in terms.terms.items():
        word_letters = _word_letters(word)
        words.append((word_id, word, letters.term(word_letters)))

    conn = db.connect(args.model_file)
    try:
        cur = conn.cursor()
        cur.execute('''
                    CREATE TABLE letters (id INTEGER PRIMARY KEY, letters TEXT UNIQUE NOT NULL)
                    ''')
        cur.execute('''
                    CREATE TABLE words (
                        id INTEGER PRIMARY KEY,
                        word TEXT UNIQUE NOT NULL,
                        letters_id INTEGER,
                        FOREIGN KEY (letters_id) REFERENCES letters (id)
                    )
                    ''')
        cur.execute('''
                    CREATE TABLE bigrams (
                        prev_id INTEGER,
                        next_id INTEGER,
                        frequency INTEGER,
                        PRIMARY KEY (prev_id, next_id),
                        FOREIGN KEY (prev_id) REFERENCES words (id),
                        FOREIGN KEY (next_id) REFERENCES words (id)
                    )
                    ''')
        cur.executemany('INSERT INTO letters (letters, id) VALUES(? ,?)', letters.terms.items())
        cur.executemany('INSERT INTO words (id, word, letters_id) VALUES(? ,?, ?)', words)
        cur.executemany('INSERT INTO bigrams (prev_id, next_id, frequency) VALUES(?, ?, ?)',
                        [(bigram[0], bigram[1], freq) for (bigram, freq) in bigram_frequencies.items()])
        conn.commit()
    finally:
        conn.close()


def _add_subcommand(subparsers, name, fn):
    parser = subparsers.add_parser(name, description=fn.__doc__)
    parser.set_defaults(command=fn)
    return parser


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')

    subparsers = parser.add_subparsers(dest='command', required=True)

    scramble_parser = _add_subcommand(subparsers, 'scramble', scramble)
    scramble_parser.add_argument('--amount', type=float, default=0.5)
    scramble_parser.add_argument('text')

    dehamming_parser = _add_subcommand(subparsers, 'descramble-hamming', dehamming)
    dehamming_parser.add_argument('--words-file', type=argparse.FileType('r'), default='/usr/share/dict/words')
    dehamming_parser.add_argument('text')

    debigram_parser = _add_subcommand(subparsers, 'descramble-bigram', debigram)
    debigram_parser.add_argument('--model-file', required=True)
    debigram_parser.add_argument('text')

    make_model_parser = _add_subcommand(subparsers, 'make-model', make_model)
    make_model_parser.add_argument('--model-file', required=True)
    make_model_parser.add_argument('corpus_zip', nargs='+', type=argparse.FileType('rb'))

    args = parser.parse_args()

    if args.verbose:
        verbose = print
    else:
        def verbose(*arg, **kw):
            pass

    args.command(args)

