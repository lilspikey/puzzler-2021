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
aliens is a 1986 science fiction action film written and directed by james cameron.
```

Which is pretty decent really.

If you run this with the `--verbose` flag you can see the possible word anagrams too:

```
$ ./scrade.py --verbose descramble-bigram --model-file english.db 'ilAesn si a 1896 sincece itoicnf aicont lmfi ttinrew and ceredtdi by smJae Cearnmo.'
Original: ilAesn si a 1896 sincece itoicnf aicont lmfi ttinrew and ceredtdi by smJae Cearnmo.
Model loaded
aliens is a 1968 science fiction action film written and directed by james cameron
alines si   1896         ficiton cation flim         dan credited yb jemas canmore
            1986                 canito milf         dna                          
            1869                 actoin fiml         nad                          
            1689                 antico              nda                          
            9618                 catino              adn                          
            1698                 ticona                                           
            6891                                                                  
            9816                                                                  
            6198                                                                  
            6189                                                                  
            9681                                                                  

aliens is a 1986 science fiction action film written and directed by james cameron.
````

which does confirm there are relatively few options to select from.

~~I think for larger text I'd need to add in some memoisation, as it's basically doing a dynamic programming style search, but the possible
anagrams for a given word are normally fairly small, which means the combinations we need to search aren't so bad~~ Adding memoisation sped
up the matching nicely.

Also both of these don't work if they don't have a word in their dictionary/bigrams and will simply leave it untouched.


## Longer examples
Scrambling:

```
$ ./scrade.py scramble --amount 1 "$(cat <<TEXT
The turkey vulture (Cathartes aura) is the most widespread of the New World vultures,
with a range extending from southern Canada to the southernmost tip of South America.
It feeds primarily on a wide variety of carrion, from small mammals to large herbivores,
preferring those recently dead to putrefying carcasses; it rarely kills prey itself.
Populations appear to be stable, and it is listed as a least-concern species by the
International Union for Conservation of Nature. This photograph shows a turkey vulture
in flight in Cuba. It employs static soaring flight, in which it flaps its wings
infrequently, and takes advantage of rising thermals to stay aloft.
TEXT)"
heT teykru lrevtuu (ahrCttaes auar) is teh msto edprdewias fo teh ewN dlWor rulsvteu,
iwht a rgnea dinxegnte rfmo rusoenht Cdanaa ot het nmtuoehsrost ipt of ohStu cimArae.
It dsefe lpyrrmiia on a dewi atyrvie fo caorrni, fmro lsmla mmalsma to egarl rvbehrsieo,
eegrrinfrp hoset eyrlcent edda ot rtyuipefng acsscraes; it erlrya slkli ryep siltef.
nasloPitoup peraap ot eb lstbae, nda ti is lsidet sa a ltase-cnocenr espseic by het
ittaonInrlena inoUn fro nneooriaCsvt fo auteNr. sThi hrphogoatp shosw a keutyr eltuvru
in fhgtil in bauC. It emspoly cittas aoirgsn fhgilt, ni chiwh it sfpal tsi ignws
lfnyrtenqeui, nda estak eagvnatda of rnisig hmtsaerl to atys taolf.
```

De-scrambling:
```
$ ./scrade.py descramble-bigram --model-file english.db  "$(cat <<TEXT
heT teykru lrevtuu (ahrCttaes auar) is teh msto edprdewias fo teh ewN dlWor rulsvteu,
iwht a rgnea dinxegnte rfmo rusoenht Cdanaa ot het nmtuoehsrost ipt of ohStu cimArae.
It dsefe lpyrrmiia on a dewi atyrvie fo caorrni, fmro lsmla mmalsma to egarl rvbehrsieo,
eegrrinfrp hoset eyrlcent edda ot rtyuipefng acsscraes; it erlrya slkli ryep siltef.
nasloPitoup peraap ot eb lstbae, nda ti is lsidet sa a ltase-cnocenr espseic by het
ittaonInrlena inoUn fro nneooriaCsvt fo auteNr. sThi hrphogoatp shosw a keutyr eltuvru
in fhgtil in bauC. It emspoly cittas aoirgsn fhgilt, ni chiwh it sfpal tsi ignws
lfnyrtenqeui, nda estak eagvnatda of rnisig hmtsaerl to atys taolf.
TEXT)"
the turkey vulture (attachers aura) is the most widespread of the new world vultures,
with a range extending from southern canada to the southernmost tip of south america.
it feeds primarily on a wide variety of carrion, from small mammals to large herbivores,
preferring those recently dead to putrefying carcasses; it rarely skill prey itself.
populations appear to be stable, and it is listed as a least-concern species by the
international union for conservation of nature. this photograph shows a turkey vulture
in flight in cuba. it employs static soaring flight, in which it flaps its wings
infrequently, and takes advantage of rising thermals to stay float.
```

You can see a few of words have not be unscrambled correctly here - `attachers` instead
of `Cathartes`, `skill` instead of `kills` and `float` instead of `aloft`.

Here's the same descramble, but with the `--verbose` option so the full word choices are visible:
```
Original: heT teykru lrevtuu (ahrCttaes auar) is teh msto edprdewias fo teh ewN dlWor rulsvteu,
iwht a rgnea dinxegnte rfmo rusoenht Cdanaa ot het nmtuoehsrost ipt of ohStu cimArae.
It dsefe lpyrrmiia on a dewi atyrvie fo caorrni, fmro lsmla mmalsma to egarl rvbehrsieo,
eegrrinfrp hoset eyrlcent edda ot rtyuipefng acsscraes; it erlrya slkli ryep siltef.
nasloPitoup peraap ot eb lstbae, nda ti is lsidet sa a ltase-cnocenr espseic by het
ittaonInrlena inoUn fro nneooriaCsvt fo auteNr. sThi hrphogoatp shosw a keutyr eltuvru
in fhgtil in bauC. It emspoly cittas aoirgsn fhgilt, ni chiwh it sfpal tsi ignws
lfnyrtenqeui, nda estak eagvnatda of rnisig hmtsaerl to atys taolf.
Model loaded
the turkey vulture attachers aura is the most widespread of the new world vultures with a anger extending from southern canada to the southernmost tip of south america it feeds primarily on a wide variety of carrino from small mammals to large herbivores preferring those recently dead to putrefying carcasses it rarely skill prey itself populations appear to be tables and it is listed as a least concern species by the international union for conversation of nature this photograph shows a turkey vulture in flight in cuba it employs static soaring flight in which it flaps its wings infrequently and takes advantage of rising thermals to stay float
teh                               si hte toms            fo hte     wolrd          whit   range           form sutheron        ot hte              pit fo shout amercia          primarliy no   dewi         fo carrion form malls         ot regal                       theos recenlty dade ot                      ti yarrel kills pyre stifle             papera ot eb stable dan ti si stiled sa   slate                 yb hte interntaional       fro conservation fo neutra tish photogrpah                        ni        ni                 tastic sironga        ni whcih ti       sit swing              dan stake           fo snigir          ot saty aloft
                                     teh tmos               teh                    wtih   regan           morf                    teh              itp                                                          corrina morf msall            glare                       ethos          aedd                                         repy filets             appaer       ablest dna       steidl      tesla                    teh                     ofr                 nauert tihs                                                                ticats                                  ist                    dna steak                                 asty      
                                     het mots               het                    wiht   grean           frmo                    het              pti                                                                  frmo                  lager                       tesho          deda                                         pyer tfiles                          satble nad       stiedl      steal                    het                     orf                 natrue thsi                                                                attics                                  tsi                    nad keats                                 stya      
                                     eth msot               eth                           negra                                   eth              ipt                                                                                        elgar                       thoes          adde                                         yerp stifel                          bleats nda       detils      tales                    eth                     rfo                                                                                                                                    sti                    nda skate                                           
                                                                                          ragen                                                    tpi                                                                                        argel                       hoste                                                            feltis                          baltes adn       detsil      stale                                                                                                                                                                                   tis                    adn kates                                           
                                                                                          renga                                                                                                                                               alger                       sothe                                                            eltifs                                           distel      leats                                                                                                                                                                                                              asket                                           
                                                                                                                                                                                                                                              alegr                                                                                        flites                                           itseld      teals                                                                                                                                                                                                              taeks                                           
                                                                                                                                                                                                                                              ragel                                                                                        istlef                                           delist      letsa                                                                                                                                                                                                              keast                                           
                                                                                                                                                                                                                                              geral                                                                                                                                         silted      altes                                                                                                                                                                                                              kesat                                           
                                                                                                                                                                                                                                                                                                                                                                                                        atles                                                                                                                                                                                                              saket                                           
                                                                                                                                                                                                                                                                                                                                                                                                        lates                                                                                                                                                                                                                                                              
                                                                                                                                                                                                                                                                                                                                                                                                        telsa                                                                                                                                                                                                                                                              
                                                                                                                                                                                                                                                                                                                                                                                                        stela                                                                                                                                                                                                                                                              
                                                                                                                                                                                                                                                                                                                                                                                                        aelst                                                                                                                                                                                                                                                              
                                                                                                                                                                                                                                                                                                                                                                                                        eastl                                                                                                                                                                                                                                                              

the turkey vulture (attachers aura) is the most widespread of the new world vultures,
with a range extending from southern canada to the southernmost tip of south america.
it feeds primarily on a wide variety of carrion, from small mammals to large herbivores,
preferring those recently dead to putrefying carcasses; it rarely skill prey itself.
populations appear to be stable, and it is listed as a least-concern species by the
international union for conservation of nature. this photograph shows a turkey vulture
in flight in cuba. it employs static soaring flight, in which it flaps its wings
infrequently, and takes advantage of rising thermals to stay float.
```
