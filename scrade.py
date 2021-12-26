#!/usr/bin/env python3

import argparse
import re
from random import sample 


NON_WORD_WORD = re.compile(r'(\W*)(\w*)')


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


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    subparsers = parser.add_subparsers(dest='command', required=True)

    scramble_parser = subparsers.add_parser('scramble')
    scramble_parser.set_defaults(command=scramble)
    scramble_parser.add_argument('--amount', type=float, default=0.5)
    scramble_parser.add_argument('text')

    args = parser.parse_args()
   
    args.command(args)

