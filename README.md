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

This descrambler does the same trick with looking up all word anagrams, but also loads a file containing "bigram" frequencies
(word pairs) from a file and uses that to pick the best combination of words to select.

To create the model file you need to download some corpus data from:

[https://www.corpusdata.org/iweb_samples.asp](https://www.corpusdata.org/iweb_samples.asp)

Then generate a JSON file with the frequencies (this can take a while and the file is usually quite large):

```
$ ./scrade.py make-model corpus/text*.zip > english.json
```

Then this file can be used with the `descramble-bigram` command:

```
$ ./scrade.py descramble-bigram --model-file english.json 'ilAesn si a 1896 sincece itoicnf aicont lmfi ttinrew and ceredtdi by smJae Cearnmo.' 
aliens is a 1986 science fiction action film written and directed by james cameron.
```

It works reasonably well, though it's very slow to load the bigram frequencies.  The actual matching of the words seems to be pretty quick.
I think for larger text I'd need to add in some memoisation, as it's basically doing a dynamic programming style search, but the possible
anagrams for a given word are normally fairly small.

Also both of these don't work if they don't have a word in their dictionary/bigrams and will simply leave it untouched.

