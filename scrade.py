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


def scramble_word(word, amount):
    indexes = list(range(len(word)))
    to_swap = sample(indexes, k=min(int(amount * len(word)), len(word)))
    swap_lookup = dict(zip(sorted(to_swap), to_swap))
    return ''.join(word[swap_lookup.get(i, i)] for i in indexes)


def scramble(args):
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


def _hamming_dist(word1, word2):
    return sum(1 for (a, b) in zip(word1, word2) if a != b)


def dehamming(args):
    verbose('Original:', args.text)
    words_by_letters = _words_by_letters_index(args.words_file)
    choices = []
    for m in NON_WORD_WORD.finditer(args.text):
        non_word, word = m.groups()
        if non_word:
            choices.append(non_word)
        if word:
            word = word.lower()
            word_choices = words_by_letters.get(_word_letters(word), [word])
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
    verbose('Original:', args.text)
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
            word = word.lower()
            word_choices = words_by_letters.get(_word_letters(word), [word])
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
    ''' https://www.corpusdata.org/iweb_samples.asp '''
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
    bigram_frequencies = Counter()
    for bigram in _load_corpuses(args.corpus_zip):
        bigram_frequencies[':'.join(bigram)] += 1
    print(json.dumps(bigram_frequencies))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action='store_true')

    subparsers = parser.add_subparsers(dest='command', required=True)

    scramble_parser = subparsers.add_parser('scramble')
    scramble_parser.set_defaults(command=scramble)
    scramble_parser.add_argument('--amount', type=float, default=0.5)
    scramble_parser.add_argument('text')

    dehamming_parser = subparsers.add_parser('descramble-hamming')
    dehamming_parser.set_defaults(command=dehamming)
    dehamming_parser.add_argument('--words-file', type=argparse.FileType('r'), default='/usr/share/dict/words')
    dehamming_parser.add_argument('text')

    debigram_parser = subparsers.add_parser('descramble-bigram')
    debigram_parser.set_defaults(command=debigram)
    debigram_parser.add_argument('--model-file', type=argparse.FileType('r'), required=True)
    debigram_parser.add_argument('text')

    make_model_parser = subparsers.add_parser('make-model')
    make_model_parser.add_argument('corpus_zip', nargs='+', type=argparse.FileType('rb'))
    make_model_parser.set_defaults(command=make_model)

    args = parser.parse_args()

    if args.verbose:
        verbose = print
    else:
        def verbose(*arg, **kw):
            pass

    args.command(args)

