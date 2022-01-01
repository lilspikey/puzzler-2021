# Puzzler 2021

## Scrambling
```
$ ./scrade.py scramble --amount 1 'Aliens is a 1986 science fiction action film written and directed by James Cameron.'
ilAesn si a 1896 sincece itoicnf aicont lmfi ttinrew and ceredtdi by smJae Cearnmo.
```

## Descrambling

### Simple hamming distance descrambler.

This descrambler takes the letters from the scrambled words and finds all the words (from a dictionary) that use those
exact same letters (e.g. are anagrams).  When there are multiple matches, the hamming distance between the words and the
original scrambled text is used to decided which word to pick.

This works ok-ish when text is only slightly scrambled:

```
$ ./scrade.py descramble-hamming 'lelHo world how are you tdoay?'
hello world how are you today?
```

but not so great when text is heavily scrambled (though it's great for finding amusing anagrams):

```
$ ./scrade.py descramble-hamming 'ilAesn si a 1896 sincece itoicnf aicont lmfi ttinrew and ceredtdi by smJae Cearnmo.'
alsine si a 1896 science fiction action film twinter and directed by james romance.
```

### Bigram frequency descrambler

This descrambler does the same trick with looking up all word anagrams, but also looks at "bigram" frequencies
(word pairs) and uses them to pick the best combination of words to select.

To create the model file you need to download some corpus data from:

[https://www.corpusdata.org/iweb_samples.asp](https://www.corpusdata.org/iweb_samples.asp)

Then generate an SQLite database with the bigram frequencies + anagram lookup (this can take a while and the file is usually quite large):

```
$ ./scrade.py make-model --model-file english.db corpus/text*.zip
```

Originally a JSON file was used for this data, but loading that data when descrambling took quite a few seconds.  Using a SQLite database
lets us target which data we need to read much more efficiently.


Then this database can be used with the `descramble-bigram` command:

```
$ ./scrade.py descramble-bigram --model-file english.db 'ilAesn si a 1896 sincece itoicnf aicont lmfi ttinrew and ceredtdi by smJae Cearnmo.'
aliens is a 1968 science fiction action film written and directed by james cameron.
```

It works reasonably well - though Aliens was released in 1986 not 1968.

~~I think for larger text I'd need to add in some memoisation, as it's basically doing a dynamic programming style search, but the possible
anagrams for a given word are normally fairly small, which means the combinations we need to search aren't so bad~~ Adding memoisation sped
up the matching nicely.

Also both of these don't work if they don't have a word in their dictionary/bigrams and will simply leave it untouched.

