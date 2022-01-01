#!/usr/bin/env python3

import argparse
import io
import json
import re
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


def _match(bigram_frequencies, prev, choices):
    if choices:
        head, tail = choices[0], choices[1:]
        best_score = 0.0
        best_choices = None
        for choice in head:
            bigram = '{}:{}'.format(prev, choice)
            freq = bigram_frequencies.get(bigram, 0.5)
            tail_score, tail_choices = _match(bigram_frequencies, choice, tail)
            score = tail_score * freq
            if score > best_score:
                best_score = score
                best_choices = (choice,) + tail_choices
        return (best_score, best_choices)
    else:
        bigram = '{}:<END>'.format(prev)
        freq = bigram_frequencies.get(bigram, 0.5)
        return (freq, ())


def debigram(args):
    '''
    Attempt to descramble the words in the provided text using a dictionary
    lookup, then find the best match for the combinations of words based on
    bigram frequencies. e.g. so "tbu htat" would tend to match "but that"
    instead of "tub that".
    '''
    verbose('Original:', args.text)
    # this data file is quite large and takes a few seconds to load
    # potentially we could use a sqlite db and just pull in what we
    # need to, but that adds more complication than what I can be
    # bothered with
    bigram_frequencies = json.load(args.model_file)
    words = set()
    for bigram in bigram_frequencies:
        start, end = bigram.split(':')
        words.add(start)
        words.add(end)
    words_by_letters = _words_by_letters_index(words)
    choices = []
    tokens = []
    for m in NON_WORD_WORD.finditer(args.text):
        non_word, word = m.groups()
        if non_word:
            tokens.append(non_word)
        if word:
            word_choices = _get_words_from_letters(words_by_letters, word)
            choices.append(tuple(word_choices))
            tokens.append(None)
    _, chosen_words = _match(bigram_frequencies, '<START>', tuple(choices))
    next_word = 0
    for i, token in enumerate(tokens):
        if token is None:
            tokens[i] = chosen_words[next_word]
            next_word += 1
    print(''.join(tokens))


def _load_sentence(sentence):
    prev_word = '<START>'
    for m in NON_WORD_WORD.finditer(sentence):
        _, word = m.groups()
        if word:
            word = word.lower()
            yield (prev_word, word)
            prev_word = word
    if prev_word:
        yield (prev_word, '<END>')


def _load_doc(doc):
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
                yield from _load_sentence(sentence)


def _load_corpus(corpus):
    for name in corpus.namelist():
        with corpus.open(name) as doc:
            yield from _load_doc(io.TextIOWrapper(doc))


def _load_corpuses(corpus_zips):
    for corpus_zip in corpus_zips:
        with zipfile.ZipFile(corpus_zip) as corpus:
            yield from _load_corpus(corpus)


def make_model(args):
    '''
    Make JSON containing bigram frequencies from the provided corpuses.
    Corpus data can be downloaded in zip format from https://www.corpusdata.org/iweb_samples.asp
    '''
    bigram_frequencies = Counter()
    for bigram in _load_corpuses(args.corpus_zip):
        bigram_frequencies[':'.join(bigram)] += 1
    print(json.dumps(bigram_frequencies))


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
    debigram_parser.add_argument('--model-file', type=argparse.FileType('r'), required=True)
    debigram_parser.add_argument('text')

    make_model_parser = _add_subcommand(subparsers, 'make-model', make_model)
    make_model_parser.add_argument('corpus_zip', nargs='+', type=argparse.FileType('rb'))

    args = parser.parse_args()

    if args.verbose:
        verbose = print
    else:
        def verbose(*arg, **kw):
            pass

    args.command(args)

