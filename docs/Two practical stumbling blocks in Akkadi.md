Two practical stumbling blocks in Akkadian → English MT (and how to address them)
Based on recent experiments and discussions with several participants, I want to share a set of observations about what appear to be the primary bottlenecks in this competition. These are not model-architecture issues per se, but data- and representation-level issues that strongly affect downstream training, evaluation, and reinforcement learning.
After multiple iterations, debugging sessions, and failed-but-informative experiments, two main stumbling blocks consistently emerge:
(1) Named entities (personal names, place names, divine names) (2) Inconsistent ASCII / transliteration formats across Akkadian datasets
Both issues disproportionately affect tokenization, alignment, and reward stability, and in practice they limit performance more than model size or optimizer choice.
1. Named entities are a dominant source of error
Personal names, geographic names, and divine names behave very differently from ordinary lexical items:
* They are often transliterated inconsistently across editions.
* They frequently preserve older orthographic conventions.
* They are semantically opaque to the model unless explicitly supported.
In experiments, many otherwise reasonable translations fail almost entirely because a name is mangled, dropped, or hallucinated. This affects not only final accuracy but also reward-based methods, where small orthographic deviations can collapse a sentence-level score.
To address this, I have prepared an onomasticon (a curated list of names and attested spellings), which I will share as supplemental data. Participants may find it useful to:
* add it as a lookup or constraint layer,
* bias decoding for known names,
* or use it for post-generation repair.
Even partial normalization of named entities tends to improve both perceived translation quality and metric stability.
2. Transliteration format normalization is not optional
A second, and often underestimated, issue is ASCII-format variation in Akkadian transliteration. Different corpora encode the same underlying text using different conventions, many of which are not interchangeable without loss.
A concrete example that came up in a private discussion illustrates the problem. One approach converted diacritics into ASCII sequences (e.g., š → sz, ú → u2, etc.) before training. This is a reasonable instinct, but in this case it was done in the wrong direction: the evaluation data already contains diacritics, and reducing the alphabet removed distinctions that are semantically meaningful in Akkadian.
For example, the evaluation data expects forms like:
* i-ṣí-ba-at rather than i-Si₂-ba-at
* KÙ-pì-a rather than KU₃-pi₃-a
* KIŠIB rather than KISZIB
The key takeaway is that the competition data uses an extended alphabet by design, and collapsing it into ASCII can degrade both meaning and alignment. While this increases tokenization difficulty, preserving distinctions such as s / ṣ / š and t / ṭ is preferable to losing them.
The recommended strategy is therefore:
* keep diacritics,
* convert ASCII substitutes (e.g., sz) into diacritics,
* and normalize everything toward the format used in the training and evaluation sets.
Gaps, damage markers, and parallel alignment [update: 2/18/26]
Another recurring source of confusion concerns damaged text and gap markers in the data:
* x represents a single broken sign,
* sequences like x x x x or ... represent a larger lacuna.
For modeling purposes we reduced all breaks to a single marker: <gap>
* we removed the tag for <big_gap> from the train and test (and other transliterations). We also deduplicated instances multiple sequential gaps (e.g. <gap> <gap, <gap>-<gap>, <gap> <gap>, <gap>. <gap>, etc.
Ideally, these gap markers would be parallelized between transliteration and translation whenever possible. However, this was not completely accomplished, as the translation we had access to did not pay strict attention to the gaps. This will be an aspect of the challenge in which a significant advantage will remain for those who have controlled for this data. If a large gap appears in one side but not the other, the model is forced to learn misalignment rather than translation.
This also applies to edge cases such as <gap> attached to a word (e.g., <gap>-A-šùr), which should be preserved rather than blindly removed.
Why this matters for training and RL-based methods
Many participants have observed that standard supervised fine-tuning produces reasonable loss curves, while reinforcement or preference-based methods fail to improve or show no reward signal. In nearly all cases examined so far, this traces back to output non-conformance caused by the issues above.
If the model is penalized for:
* orthographic mismatches,
* bracket artifacts,
* inconsistent gap handling,
* or malformed named entities,
then reward functions cannot reliably distinguish “closer” from “farther” outputs. Addressing normalization and alignment first makes rewards smoother and learning signals usable.
Closing note
None of this is meant as criticism of existing approaches; these are difficult problems, and much of the complexity comes from the philological nature of the data itself. The hope in sharing this publicly is to reduce duplicated effort and make preprocessing choices more transparent across submissions.
I will continue to share supplemental resources (including the onomasticon) as they are finalized, and I’m happy to discuss normalization or alignment strategies further if helpful to others.
341add_reaction
16 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Angantyr
Posted 2 days ago
1
more_vert
@deeppast Clarification needed.
I'm going through the glossaries and find that in Summerian the nasal "ŋ" is used somewhat often. This appears, e.g., in the determinative for wood {ŋeš}, which for this competition is written as {geš}. Can we safely assume ŋ -> g substitution as valid?
Another question is about treating Summerian words from the ORACC glossary, e.g., {na₄}za-gin₃-ŋu₁₀. Intuitively I would change that into: NA₄.ZA.GÌN-gu₁₀, i.e.:
1. treat the base as a summerogram -> uppercase, no {}, .-joined
2. treat the rest as a --joined suffix
What would be the approach to best match the data in train.csv and other sources?
Reply
React
Souhardya
Posted 4 days ago
·  60th in this Competition
4
more_vert
@deeppast , while going through your onomasticon and the train labels, i noticed that there are some differences in the naming convention.
Example 1 — Different name entirely:
Akkadian token: šu-{d}EN.LÍL , Onomasticon canonical form: Šu-Enlil , Actual training label: Šu-Illil
Example 2 — Geminate consonant:
Akkadian token: šu-ku-tum , Onomasticon canonical form: Šukatum , Actual training label: Šukkutum
(The onomasticon drops the geminate kk that the training labels preserve.)
Example 3 — Long vowel:
Akkadian token: ṣí-lu-lu , Onomasticon canonical form: Ṣilulu , Actual training label: Ṣilūlu
(The onomasticon omits the macron on the ū that the training labels include.)
these are some examples pointed out by claude. which convention do the test labels follow — the onomasticon's or the training data's?
Reply
React
Bilzard
Posted a month ago
12
more_vert
@deeppast Regarding normalization, could you clarify which of the following is true for the test set?
1. Both transliterations and translations are already normalized (i.e., tokens like and are already present in both columns).
2. Only the translations are normalized. Participants must implement their own logic to convert x or ... into <gap> or <big_gap> for the test transliterations.
If Case 2 is true, the final scores will be highly sensitive to specific preprocessing choices. This could turn the competition into a "preprocessing lottery" and encourage over-fitting to the Public LB rather than improving the actual MT model.
Reply
React
Anil Ozturk
Posted 2 months ago
·  262nd in this Competition
8
more_vert
I want to be sure on these cases:
* <big_gap> <gap> → <big_gap>
* <gap> <big_gap> <gap> → <big_gap>
* <big_gap> <big_gap> → <big_gap>
* <gap> <gap> → <big_gap>
* someword-<gap> <gap>-someword → someword-<gap> <gap>-someword OR someword-<big_gap>-someword ?
* <big_gap> <gap>-A-šùr → <big_gap> <gap>-A-šùr
* xxxx-kam (train.csv line 43) → <big_gap>-kam OR <big_gap> <gap>-kam ?
It would be good to take feedback on these from you.
I think that having to figure out the normalization logic you are using prevents us from focusing on the actual goal of the competition. There is some processing happening in the background that also affects the original “ground truth” translations you have, so instead of focusing on the machine learning part we end up spending our effort on reverse-engineering your normalization logic. Can't you share the transliteration-translation preprocessors you're using?
Reply
2add_reaction
MPWARE
Posted 2 months ago
·  61st in this Competition
1
more_vert
I'm wondering how to interpret this section that is unclear to me about "?", "!", and ":" for translations :
https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/overview/dataset-instructions
Formatting Suggestions for Transliterations and Translations:
Remove (modern scribal notations):
* ! (certain reading)
* ? (questionable reading)
* / (line divider) - Now we now there is none of these according to @deeppast
* : OR . (word divider)
We've a lot of ?!: in training set translations. But do we have the same in test set? 
Should we apply the suggestion above => Remove all !?: from translations in training set. Or only if they are enclosed with parenthesis.
Some make sense to me with ":" usage for a rate and "?" for a question in translation. It does not look questionable reading for the question marks below.
ff9442fd-9e7d-449c-a2d6-0cc35921cd65: Šalim-Aššur answered: "And what if I have tin and from my goods remaining in his possession? Will he pay me at the rate 6:1 for my tin and 15 shekels per in silver?"
Here the ":" make sense too. If I remove ":" then I should remove ";" too here.
00f0d841-eb7a-46f8-86fc-bf9fd7d52cbf: From Šu-Tammuzī, Elaya, Ennam-Aššur and Lamassī to Ennam-Aššur and Ali-ahum: In accordance with your missive we have hired a attorney for you; Abiya son of Bebe is our attorney. 
I would just remove things like:  "(?)", "(!)", "(fem. plur.)", "(fem.)", "(plur.)", "(pl.)", "(sing.)", "(plural)"
Can't you share the transliteration and translation list of characters you're using / allowing?
Reply
React
Adam Anderson
COMPETITION HOST
Posted 2 months ago
5
more_vert
Good questions, here's the character list for transliterations:
Transliterations Characters
* -
* a
* A
* i
* I
* u
* U
* m
* M
* š
* Š
* n
* N
* b
* B
* r
* R
* t
* T
* l
* L
* k
* K
* G
* g
* í
* Í
* D
* d
* Ù
* ù
* á
* Á
* .
* ú
* Ú
* p
* P
* e
* E
* h
* H
* q
* Q
* 1
* ṣ
* Ṣ
* é
* É
* <
* >
* à
* À
* 4
* z
* Z
* s
* S
* ì
* Ì
* 5
* _
* 2
* 0
* ½
* w
* W
* 3
* {
* }
* ṭ
* Ṭ
* 6
* ⅓
* 8
* ⅔
* 7
* è
* È
* ⅚
* 9
* ¼
* !
* +
* ⅙
* ı
* …
* ş
* İ
* :
Translations Characters
* '
* ?
* e
* E
* a
* A
* i
* I
* t
* T
* n
* N
* s
* S
* o
* O
* r
* R
* l
* L
* h
* H
* u
* U
* m
* M
* d
* D
* F
* f
* š
* Š
* -
* p
* P
* w
* W
* b
* B
* g
* G
* y
* Y
* .
* K
* k
* ,
* C
* c
* v
* ā
* 1
* )
* (
* <
* >
* z
* Z
* _
* Q
* q
* 2
* ī
* ṭ
* Ṭ
* 0
* :
* 3
* ½
* 5
* ;
* x
* ē
* 4
* ū
* 6
* ṣ
* Ṣ
* ⅓
* 8
* ’
* !
* 7
* j
* J
* ⅔
* “
* ”
* 9
* –
* ⅚
* ¼
* ⅙
* "
* ‘
* ı
* —
* [
* ]
* ğ
* â
* +
* à
* ş
Reply
React
13 more replies
+5
3 more replies
Lee Drake
Posted 2 months ago
·  1414th in this Competition
4
more_vert
This is my main worry about participating in this contest. I've been working on cuneiform LLMS for the past two years, and a good text pipeline has to standardize the presentation from multiple script types (on my end I'm also working with Elamite, Sumerian, and Hittite). Getting it to align with ASCII helps learnability tremendously if one wants to leverage pre-trained models like T5 or NLLB. But I don't know how we prepare the unknown text - can we write an input pipeline (and prompt structure) to take in the unknown data with a submission? 
Reply
3add_reaction
Yicong XIAO
Posted 2 months ago
2
more_vert
For the subscripts used in the determinatives, do they also need to be transformed to either diacritics or plain numbers?
e.g. should it be {tug₂} or {tug2} ? 
Reply
React
Yicong XIAO
Posted 2 months ago
1
more_vert
On second thought, since the determinatives appear only in the transliteration text, I can pick either scheme. Then, during inference, I can detect the determinatives in the test set input (should be fairly easy) and transform them according to the scheme I pick. 
Reply
React
Adam Anderson
COMPETITION HOST
Posted 2 months ago
6
more_vert
The expected format for {tug₂} or {tug2} is actually {túg}
For background, in ASCII ATF (CDLI) they don't use diacritics for ú = u2, and ù = u3, and so on. Further, in Oracc these numbers become subscripts: ú = u₂, etc. That second comment was intended to indicate that for the readings with 2 or 3 this dataset used diacritics instead of numbers or subscripted numbers (i.e. á à é è í ì ú ù; NOT a2, a3, etc.; NOT a₂, etc.). However, sign values with 4, 5, 6, …, 10, 12, 13, etc. are found in the dataset (e.g., DU10). So aside from sign values with these readings á à é è í ì ú ù, this dataset uses integer numbers, not subscripted numbers.
Reply
3add_reaction
Anil Ozturk
Posted 2 months ago
·  262nd in this Competition
4
more_vert
{túg} or {TÚG}? there is no lowercased {túg} in any guide you've shared. Please just give a reproducible normalization script or a very clear and strict conversion table. Most of your statements contradict each other.
Reply
2add_reaction
5 more replies
Khushi Yadav
Posted 2 months ago
-8
more_vert
Deep Past Challenge - Translate Akkadian to English
Reply
React
Oscar Guarnizo
Posted 15 days ago
·  1100th in this Competition
0
more_vert
@deeppast Hi, I was wondering where I can get the onomasticon (a curated list of names and attested spellings). Could you help me with that please?
Reply
React
ulasdesouza
Posted 2 months ago
·  970th in this Competition
0
more_vert
do not convert diacritics to ASCII (information loss!) do not remove subscripts (semantic meaning!) Evaluation data contains diacritics - be compatible with this
am i right?
Reply
React
Adam Anderson
COMPETITION HOST
Posted 2 months ago
4
more_vert
Close, but let me be clear:
* (1) with the exception of ḫ, the test data has diacritics (š ṣ ṭ ā á à ī í ì ū ú ù - and upper case versions). If you're obtaining data from CDLI or ORACC, you will need to convert their formatted transliterations to this diacritic style (conversions are listed in the overview) — note ā ī ū are in translations, not transliteration text.
* (2) there are no subscripted numbers in the test data, so expect A-šùr-DU10 for example.
* (3) keep diacritics for transliterations, but normalize them for translations of named entities, for example: A-šùr-DU10 (transliteration) --> Aššur-ṭāb (translation)
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
Hello, why is your CHRF metric so high? What's the difference between it and the CHRF from the public notebook? Public notebook link: https://www.kaggle.com/code/takamichitoda/dpc-starter-train
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
My guess is that if the sentences are the same, then you most likely did sentence alignment.
Reply
React
heng
Posted 2 months ago
·  16th in this Competition
0
more_vert
This public notebook does not use competition metrics.
Try: https://www.kaggle.com/code/metric/dpi-bleu-chrf
Reply
React
MPWARE
Posted 2 months ago
·  61st in this Competition
4
more_vert
@deeppast
(2) there are no subscripted numbers in the test data, so expect A-šùr-DU10 for example.
You said something a bit different in another post:
Subscript digits are converted to normal digits, except for 2 and 3, which are represented by diacritic marks over the vowels (see overview for more details)
https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/664518#3382901
Do I miss something?
Reply
2add_reaction
MPWARE
Posted 2 months ago
·  61st in this Competition
1
more_vert
Answer to myself: Now we know that first assertion it True and second is False.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 2 months ago
4
more_vert
Yes, right, the ack of specificity in that second statement is problematic. For background, in ASCII ATF (CDLI) they don't use diacritics for ú = u2, and ù = u3, and so on. Further, in Oracc these numbers become subscripts: ú = u₂, etc. That second comment was intended to indicate that for the readings with 2 or 3 this dataset used diacritics instead of numbers or subscripted numbers (i.e. á à é è í ì ú ù; NOT a2, a3, etc.; NOT a₂, etc.). However, sign values with 4, 5, 6, …, 10, 12, 13, etc. are found in the dataset (e.g., DU10). So aside from sign values with these readings á à é è í ì ú ù, this dataset uses integer numbers, not subscripted numbers.
Reply
React
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
RYAN HOLBROOK ·  POSTED 17 DAYS AGO
· KAGGLE STAFF
24
more_vert
Dataset Update - Mind the Gaps
Hi everyone,
I just posted an update to the dataset that regularizes <gap> conventions. The train.csv, published.csv, the (hidden) test.csv, and the test set labels have all been updated. The competition host will follow up soon with more details.
I will also be initiating a rescore of all current submissions tomorrow. I will keep you updated as this progresses. All new submissions will be scored against the updated labels.
UPDATE 02/20/2026: We are working on another (hopefully final) update that should address some of the issues raised here. I hope to have it out soon, likely Monday. We will delay the rescore until then.
95add_reaction
25 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Pinned comments
This comment has been deleted.
steubk
Posted 16 days ago
·  49th in this Competition
7
more_vert
@deeppast Thanks for clarifying the updates to the train set translations. I have a few questions:
1. Were the same updates applied to the test set?
2. How are fractions represented in the test set—decimals (e.g., 0.5) or Unicode characters (e.g., ½)?
3. What does PN = <gap> mean? Was the literal string “PN” replaced with <gap>, or were all personal names replaced with <gap>?
Reply
1add_reaction
Vishal Kishore
Posted 16 days ago
·  36th in this Competition
1
more_vert
Just checking, is the data section updated? I can still see fem. sing.  pl. in translations
Edit - I noticed the apostrophe was removed, but I think it’s important for translation quality. ref- The current train.csv has "Šāt-Annas representative", but the previous version had "Šāt-Anna's representative".
Reply
React
All other comments
KishoreKashyap
Posted 3 days ago
·  252nd in this Competition
1
more_vert
Dear Ryan Holbrook, can we have BLEU and ChrF scores along with GM? This will greatly help us to see our model's performance in a transparent manner and thereby help us to diagnose our models well. You can keep GM as the final LB scoring mechanism. Thank you.
Reply
React
MPWARE
Posted 16 days ago
·  61st in this Competition
15
more_vert
First, thank you for providing the updated, cleaner dataset - it’s clear that a lot of effort went into improving data quality, and it will ultimately benefit the challenge.
I do have a couple of concerns I’d like to share:
* Mid-competition changes: Updating the data and rules partway through the competition can be challenging for participants who have been working since the start of the Deep Past Challenge. Many of us invested significant time normalizing and adapting to the original data, and these efforts may no longer be applicable. While I understand the intent to improve the dataset, this kind of change can feel discouraging from a fairness standpoint.
* Information consistency across platforms: Some important clarifications appear to be shared on Discord but not reflected in the official Kaggle discussion or data description. For participants who rely solely on the Kaggle platform, this creates an uneven playing field. It would be very helpful if all critical information were consolidated in the official documentation.
That said, I’m still enjoying the challenge and plan to continue participating.
To help avoid further rework, especially for normalizing re-OCR data such as Larsen, could you please provide a detailed list of the normalization changes that were applied? A quick diff of train.csv suggests that, beyond replacing with , there were also changes such as quote removal, number fractions, Hh, subscripts, and possibly other text adjustments. Having a clear summary would help participants align their preprocessing steps with the updated data. Could you provide the updated list of characters allowed in transliteration and translation?
Finally:
* "Dataset instructions" had not been updated and still ask us to use big_gap.
* fem. plur. are still here but you recommended to remove them
Reply
104add_reaction
Yurnero
Posted 16 days ago
·  3rd in this Competition
4
more_vert
The thing is. This is obviously a good change that eliminates 2-token preprocessing gamble and should have been done in the first week. I'm sure Adam is a professional and knows his domain perfectly. Just sometimes people are unfamiliar with how many GPU/human hours could be burnt by solving a problem within a particular setting and that changing this setting could be a bit painful.
Nevertheless, I'm sure that 'transitivity' of a translation quality still holds (in general) for the new test. Let's just hope that it is the last change~~
Reply
React
Jack
Posted 16 days ago
·  19th in this Competition
4
more_vert
Yes, it's a good change, but wowee I spent a lot of time on stuff that is now useless 🫠 
Reply
React
Tarek Ziad
Posted 16 days ago
·  2463rd in this Competition
11
more_vert
Honestly ,am really frustrated. I’ve been working on many patterns (like […-Suffix] and several others). Now with every dataset update, these patterns are gone or changed. My work on them is basically useless ,it feels like all my time was wasted.
This cannot keep happening. If the dataset isn’t stable, the competition should start only when it’s ready. Also, are you planning to update the data one day before the competition ends? We need a stable dataset so our work actually counts.
Reply
React
Jack
Posted 16 days ago
·  19th in this Competition
1
more_vert
Having more complaints than submissions is craaaaaaaazy
Reply
7add_reaction
Hafiz Atif Ali
Posted 3 days ago
0
more_vert
Then how the things flow
Reply
React
MPWARE
Posted 15 days ago
·  61st in this Competition
7
more_vert
While waiting the update of update, I've reviewed the update and I'm getting lost now: 
* What is the final policy for fraction? I see some fractions in translation and also just float numbers (rounded or not rounded): 2 minas 13.5, 1.8333300000000001,  @deeppast You was saying in another post that we should convert all floating number to fraction, right? Why it's not normalized now?
* Some transliteration in english: 9a208f3b-1cbb-43a6-b870-566abe5ea9a1 (noticed by @yaroshevskiy)
* ד still here (009fb838-8038-42bc-ad34-5f795b3840ee)
* Many x that shoud be < gap >: 04dd324f-120e-44fd-9dbd-93a144906902 (Um-x took), 1b89399d-d4f8-4347-b88b-94f5eec0886f (shekels for x shekels; 15 grain), 476e6eef-f0a4-44fd-b3f8-65e6337a9a51 (When Ana-xs son and Ili-pi-usurs)
* Random possessive usage: 054fdba4-0cff-4153-969d-c77e42413e1c (to our own Amur-Ištar's sons)
* What should we do with /: 1252b18d-4b89-4af9-b6b9-199b40c13848 (qí-bi-ma um-ma SIG5-pí-/i-a-/šur-ma). Why it's not normalized now?
* brackets: 19052127-2c2e-479d-b666-f1ea0ed27cb2, their right on a share < by giving them > a house-plot. Is that normal we still have them in the cleaned translation?
* A lot of not allowed chars in translation (according to the previous list that was provided)
* fem. pl. sing. a44f089e-2645-4aa2-b5e4-ba75e70fdf78, 7e525e12-c226-4c00-9c6e-de303e676771 (I shall return your grain to you fem. pl.. Send me), b64a5273-3e7c-4fe9-9824-bc5cd5e67586 (the cannot give in! As soon as youpl. have heard), 26ebe582-a312-4b63-8138-b7a19b12f277 (I have written to you fem. sing. five times)
* Orphans curly bracket: 8c1f39b5-5b71-4171-b0ef-d4db031a5802 (as follows: Of the 57 skekels of silver} that are available)
* Roman numbers: c84fb0b6-45c9-4e6d-8923-51eddf50c2d7 (dated to the IVth month of the eponymy), Do we have to convert them to just number?
* Parenthesis removed: e76705fe-094c-4fa3-8506-2bca4d4e7b7c ==> to your representatives (with) Aluwa, then I shall act in
Reply
React
Yurnero
Posted 15 days ago
·  3rd in this Competition
1
more_vert
@mpware by fractions he meant 1 / 3 or 1 / 6. stuff like this. So these fractions are substituted with floats now. I have already lost a sub thinking about unicode fractions. Policy for fractions is unchanged
Reply
React
MPWARE
Posted 15 days ago
·  61st in this Competition
2
more_vert
Hi @samson8 , so we should not try to convert 0.3333 to ⅓ and but only for 1 / 3 ? Look at the 2 examples below, sometimes we've to convert, sometimes not. It makes no sense to me. The instructions and the examples are not going in the same direction.
Look at this one: 
0b84671a-8753-49d9-859d-b42c3d8944ae
Transliteration: 2 né-pí-šu 15 ma-na.TA ú iš-tí-in né-pí-šu-um 10 ma-na ni-is-ha-sú DIRI ša-du-a-sú ša-bu-ú ŠU.NÍGIN 42.3333 ma-na KÙ.BABBAR ṣa-ru-pá-am ku-nu-ki-a a-na a-lu-wa ù e-ni-ša-ri-im áp-qí-id-ma a-na a-lim{ki} a ma-lá tí-ir-tí-šu a-ṣé-er ša-lim-a-šùr ú-šé-bi-il5-šu-nu a-ha-ma 13.3333 ma-na URUDU SIG5 a-na ga-am-ri-šu-nu ù 5 GÍN KÙ.BABBAR a-na ú-ku-ul-tí-šu-nu a-dí-in IGI ili5-ba-ni DUMU ba-ší-lam IGI a-hu-qar DUMU zu-ur-zu-ur IGI tù-ra-am-ì-lí DUMU e-dí-na-a-šùr a-ha-ma 10.3333 ma-na 3.5 GÍN KÙ.BABBAR ṣa-ru-pá-am tum ni  0.5 GÍN ṣí-ba-tim ša i-na ṣé-ri-a il5-qé-ú-ni a-na hu-bu-li-šu a-na kà-ri-im wa-ah-šu-ša-na áš-qúl ṣí-ba-at KÙ.GI ša ší-ip-kà-at a-šur-bé-el-a-wa-tim i-ší-tù
Translation: "2 packages of 15 minas each plus a single package of 10 minas, its import duty added, its transport tariff paid - in all 42 ⅓ minas of refined silver under my seal, I entrusted to Aluwa and Enišārum, and I sent them to the City to Šalim-Aššur in accordance with his orders. Furthermore, I paid 13 ⅓ minas of good copper for their expenses and 5 shekels of silver for their food. Witnessed by Ilī-bāni son of Baši-ilum, by Ahu-qar son of Zurzur, by Tūram-ilī son of Eddin-Aššur. Furthermore, 10 ⅓ minas 3 ½ shekels of refined silver  ½ shekel interest that they took on my account, I paid for his debt to the Wahšušana colony. The interest on the gold that remained of Aššur-bēl-awātims investment.
And then this one: Some are kept as floating number, some are fraction. 0.3333 ==> 0.3333, 0.16666 ==> ⅙, 0.5 ==> 0.5, 
0faa50f7-b86c-466c-a8ab-3a6f48fcb00a:
Transliteration: 4 GÍN a-na ší-iṭ-ri-im ša pu-ki-im 1.3333 GÍN a-na e-re-qí-im qá-nu-e áš-qúl 1.6666 GÍN a sú-ba-ri-im áš-qúl 0.3333 ma-na KÙ.BABBAR a-na a-bar-ni-im áš-qúl 0.16666 GÍN a-na um-ṣí-im 0.25 GÍN a šu-um-ki na-ru-uq GIG GÍN a-na ha-áš-lá-tim a-wa-ar-nu-a-lim 0.6666 GÍN a-na e-ṣé áš-qúl 0.6666 GÍN a pá-e ú-ša-qí-il5 1 bi-il5-té-en 0.5 GÍN áš-qúl 0.25 GÍN a-na na-pá-hi-im 95 ki-ra-tim a-na 0.25 GÍN.TA ù 7.5 ŠE.TA 0.5 GÍN a-na 0.16666 GÍN a-na a-na 
Translation: "I paid 4 shekels for a scarf of -weave, 1.3333 shekel for a wagonload of reed; I paid 1.6666 shekel for ; I paid 0.3333 mina of silver for an Abarnian textile, ⅙ shekel for a piece of dried meat, ¼ shekel for onions, x shekels for bags of wheat ;I paid shekels for ? , for a ; I paid 0.6666 shekel for firewood; 0.6666 shekels I paid for chaff, for a double load I paid 0.5 shekel; ¼ shekel for the blacksmith. I supplied 95 drinks to at 52.5 grains of silver each, 0.5shekel for ⅙ shekel for for 
Reply
React
5 more replies
+1
tucking_fired
Posted 12 days ago
·  1312th in this Competition
1
more_vert
Have the same question. Does the private test set now have decimals (0.333 for example) versus fractions ? @deeppast
Reply
React
esprit
Posted 17 days ago
·  262nd in this Competition
4
more_vert
It looks like there are still some -x left.
Also, although the translation of c97bb594-a5a1-4674-9496-48496e91c2ee was originally correct, it has now been completely incorrect.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 17 days ago
3
more_vert
Thanks for pointing this out. I'll fix it and share a new update shortly.
Reply
1add_reaction
Oleg Yaroshevskiy
Posted 17 days ago
·  40th in this Competition
4
more_vert
I've spent just a few minutes on this:
1) Why is that you fem. plur. have written me, saying this one is confusing, same that I acquired for myself(?) -> that I acquired for myself? etc
2) (ki) -> {ki}
3) is in Iddin-Aššur's possession -> is in Iddin-Aššurs possession
4) subscripts
5) ḫ
6) some texts were extended (?)
7) quotations dropped 
8) many digits normalized (?)
Reply
React
Oleg Yaroshevskiy
Posted 17 days ago
·  40th in this Competition
3
more_vert
9a208f3b-1cbb-43a6-b870-566abe5ea9a1," <gap> talents of wool, <gap> 5 hides, <gap> 22 sacks, 4 black donkeys, 3 saddle-rugs for each, plus their harness - all this I gave to Ewarimuša.","From Ikūn-pīya to Ali-ahum: Earlier I gave a slave-girl to Buziya son of Asaya and he brought her to you. He did not give you the slave-girl, but returned and here I wrote his tablet about the price of the slave-girl, 0.5 mina 5 shekels of silver. My dear brother, there <gap> "
both english
Reply
React
Adam Anderson
COMPETITION HOST
Posted 17 days ago
0
more_vert
Thanks Oleg, yes your observations are correct. Thanks for catching that, I will make the update for the training data this week and post another update shortly.
Reply
React
3 more replies
FabienDaniel
Posted 16 days ago
·  140th in this Competition
1
more_vert
Concerning the removal of the quotes in translations, (many, all ?) possessive english structures as brother's, father's, Šalim-Aššur's…became brothers, fathers, Šalim-Aššurs … Was it intended and will we have the same in the hiddent test set ?
Reply
React
Wisdom Aduah
Posted 17 days ago
·  1457th in this Competition
1
more_vert
Does this mean <big_gap> will no longer be part of the hidden test.csv? I can see that they are not in the updated train.csv.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 17 days ago
3
more_vert
Yes, exactly, the test set was updated as well, no longer <big_gap>. You can see an updated post about that here: https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/665209
Reply
React
SHREYAS
Posted 17 days ago
·  34th in this Competition
2
more_vert
@ryanholbrook certain questions regarding new data:
1. are <big_gap> eliminated.
2. should we merge multiple <gap> into one <big_gap> just in case they appear
3. are …(epilses) also removed.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 17 days ago
1
more_vert
Yes, that's right. <big_gap> has been replaced with <gap> and then deduplicated, so you should merge multiples. All ellipses should be removed as well and replaced with <gap. I updated the guidance for that here: https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/665209
Reply
React
steubk
Posted 16 days ago
·  49th in this Competition
5
more_vert
@deeppast Perhaps the new guidance would be clearer if presented in a new post rather than updating a month-old thread whose replies are no longer valid.
Reply
React
Hafiz Atif Ali
Posted 13 days ago
-4
more_vert
That remarkable contribution.
Reply
React
Jack
Posted 16 days ago
·  19th in this Competition
0
more_vert
@ryanholbrook any update on rescoring? Also, will this wipe the leaderboard as well?
Reply
React
Ryan Holbrook
KAGGLE STAFF
Posted 16 days ago
5
more_vert
There's another update incoming to address a couple other things pointed out here. I'll start the rescore once it's up. All of the submissions will be rescored, and the new scores will be reflected on the leaderboard. The new scores are posted as they are available, so while the rescore is ongoing the leaderboard will be a mix of old and new -- I don't think it should take more than an hour or two to complete, though.
Reply
React
AK
Posted 16 days ago
·  13th in this Competition
0
more_vert
@ryanholbrook : is there a possiblity for extension or a possiblity of increasing the submssion per day , given the data is updated after 2 months of running .. 
Reply
React
Yurnero
Posted 16 days ago
·  3rd in this Competition
2
more_vert
Data is basically not updated, It's just a clear 2-token related change~~ And still there is one more month left. It's not worth it
Reply
React
AK
Posted 16 days ago
·  13th in this Competition
0
more_vert
Yes, you are right .. :)
Reply
React
Yurnero
Posted 15 days ago
·  3rd in this Competition
1
more_vert
@ryanholbrook I'm pretty sure that another update only adresses train issues and test will be unchanged. May be delay is not a necessity
Reply
React
steubk
Posted 14 days ago
·  49th in this Competition
1
more_vert
I'm not so sure test will be unchanged 😀
if so why @ryanholbrook said 
I'll start the rescore once it's up. ?
I think that at least  's issue must be address on test test.
Hopefully  @deeppast will be clear in the changes that were made to the final test set compared to the initial test set.
Reply
React
Cody_Null
Posted 12 days ago
·  72nd in this Competition
1
more_vert
Yeah still looking forward to this to ensure that all of the work I am doing actually translates. 
Reply
React
Hafiz Atif Ali
Posted 5 days ago
0
more_vert
It depends 
Reply
1add_reaction
Hide replies
This comment has been deleted.
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
JACK ·  19TH IN THIS COMPETITION ·  POSTED 2 MONTHS AGO
89
more_vert
Compiled Discussions To Read (Avoid Bad Advice)
If you feel stuck or have any questions, here are all the discussions you should read over:
* Two practical stumbling blocks in Akkadian → English MT (and how to address them)
* The translation column of the final test predictions into the corresponding and tags
* How To Handle These Examples
* Other Public Data
* Incomplete translations
* Unicode Fractions vs Decimals: LB Score Unchanged?
* How to handle dot h/H?
* Question about OA_Lexicon_eBL.csv - Personal Name Spelling Inconsistency with Ground Truth
You should also review the dataset instructions section of the overview page. 
27add_reaction
11 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Angantyr
Posted a month ago
1
more_vert
Discussion on the Old Assyrian calendar and how to handle month names
Reply
React
Assia Benkedia
Posted 2 months ago
·  24th in this Competition
1
more_vert
Hi @jackvd,
Thank you for compiling and sharing these discussions 🙏. I’ve read through them carefully and they were genuinely helpful, especially in clarifying which approaches tend to hurt performance rather than help.
I wanted to ask a few quick clarification questions, if you don’t mind. I’ve trained several models now and while training loss keeps improving, my leaderboard score seems to have plateaued, so I’m trying to understand where the real leverage is.
Training data: Did you train using only train.csv, or we have to incorporate any external sources (e.g. ORACC / MTM24 / published_texts)?
Sentence alignment: Did you perform sentence-level alignment on all ~1,581 documents, or only on the longer documents that exceed the 512 token limit?
ḫ / h handling: In the training data, did you normalize ḫ -> h (and Ḫ -> H) before training, or keep the original forms and rely on the model?
Model strategy: Did you focus on a single strong model, or did you find ensembling multiple models to be necessary? I can ensemble my best checkpoints, but I’m wondering whether a single well-trained model is already sufficient.
Thanks again for taking the time to share your insights. They’ve helped cut through a lot of confusing or misleading advice, and I really appreciate it.
Reply
1add_reaction
Adam Anderson
COMPETITION HOST
Posted 2 months ago
1
more_vert
Thanks JACK! These are all excellent guides for those wishing to increase their %
If we consider that the document level data needs to be processed in terms of sentences in alignment, that will probably be what separates the top leaders from the rest.
Reply
React
MPWARE
Posted 2 months ago
·  61st in this Competition
0
more_vert
Hi @deeppast ,
Do you have an answer for dot h/H? https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/665949
Or maybe you cannot disclose such information on how you preprocess dot h/H?
Currently I'm dealing with it as augmentation, I keep dot h/H as is and the I replace randomly by regular h/H with an augmentation process. But I'm quite sure it could be better.
Thanks.
Reply
React
Jack
TOPIC AUTHOR
Posted 2 months ago
·  19th in this Competition
3
more_vert
Replace them with h/H.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 2 months ago
1
more_vert
Right, there are no dot h/H or hooked h/H. There's only regular h/H in the test. 
You can see that's the case in the character set I posted: https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/665209#3384200
Reply
React
Angantyr
Posted 2 months ago
3
more_vert
Right, there are no dot h/H or hooked h/H. There's only regular h/H in the test. 
You can see that's the case in the character set I posted: https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/665209#3384200
We should probably get the h/H corrected in the Overview character table. Also, I'm a bit suspicious of the complete lack of subscripted X (ₓ) in the entire test set. Since all numerical subscripts are turned into digits, but X should be retained then either:
* there is not a single subscripted X in the entire test set
* the subscripted X was turned into a regular sized X and transformed into <gap>.
Could we rule out the second possibility by verifying the data transformation pipeline?
Reply
React
MPWARE
Posted 2 months ago
·  61st in this Competition
0
more_vert
Finally I got it working after several attempts, single model +0.4 on LB by training with h/H. 
Reply
React
Hrithik Reddy
Posted a month ago
·  6th in this Competition
0
more_vert
Is there something other than just converting ḫ/Ḫ -> h/H on both transliteration and translation. 
Reply
React
Yurnero
Posted a month ago
·  3rd in this Competition
0
more_vert
@mpware is it encoding related? I simply replaced h/H with underlines to regular h/H in my train data few days ago and got -1.4 LB
Reply
React
MPWARE
Posted a month ago
·  61st in this Competition
6
more_vert
Yes, just replaced:
TRANSLIT_SPECIAL_CHAR_MAP = {     # h-dot does not exist in test set     "ḫ": "h",     "Ḫ": "H",     "ʾ": "",     # Same for these     "mₓ": "m",     "zₓ": "z",     ... }
I'm also using some random augmentations (low probability) to replace some diacritics to simulate noise:
DIACRITIC_COMMON_MAP = {     "š": "s", "Š": "S", ...
I had to test a few checkpoints before getting +0.4.
Reply
5add_reaction
Hrithik Reddy
Posted a month ago
·  6th in this Competition
3
more_vert
Great, I started out replacing ḫ/Ḫ -> h/H and didn't experiment without them, I was just some what confident with the replacement I haven't tried random augmenting till now , will check that helps improve the LB score or not 
Also I can't clearly map out a relation between my CV and LB , model trained on sentences score more than the model trained on docs on my CV (4-5 point difference) , however there is a max to max difference of +/- 0.1 on LB which is mostly variance 
Also my CV is a subset of sentence aligned which I got from splitting from the sen_oare csv file. 
Thank you , I'm learning a lot 
Reply
1add_reaction
Yurnero
Posted a month ago
·  3rd in this Competition
0
more_vert
Oh alr. Thanks for sharing!
Reply
React
Hide replies
This comment has been deleted.
Simo Medamro
Posted a month ago
-2
more_vert
HEY SIR tokenizer("a-na i-tù-ra-ma") Im running this and its taking too much time. what could be the problem?
Reply
React
Rami Ismael
Posted 14 days ago
0
more_vert
Thank you for sharing and curating this information 
Reply
React
Angantyr
Posted 19 days ago
0
more_vert
@deeppast @ryanholbrook This thread is a good source of typical stumbling blocks with answers and insights on their mitigation. Could we get it pinned along with the "Typical stumbling blocks" thread? It could help spreading the base knowledge the Community has come up with.
Reply
React
Navneet
Posted 2 months ago
0
more_vert
Avoid Bad Advice? @jackvd
Reply
React
Jack
TOPIC AUTHOR
Posted 2 months ago
·  19th in this Competition
6
more_vert
I’ve seen some notebooks and discussions giving bad advice to new competitors or people struggling. I’m hoping this helps avoid that problem and get more people on the right path to improving
Reply
1add_reaction
This comment has been deleted.
Leo Withrow
Posted a month ago
·  807th in this Competition
0
more_vert
Should we be using pre-trained models, or should we be fine-tuning models like byT5 ourselves?
Reply
React
Angantyr
Posted 2 months ago
0
more_vert
@jackvd Considering the Incomplete translations topic this discussion gives more potential for data cleaning. It also sheds light on the problem of incomplte transliterations.
Reply
React
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
耶✌ ·  34TH IN THIS COMPETITION ·  POSTED 2 MONTHS AGO
54
more_vert
The translation column of the final test predictions into the corresponding <gap> and <big_gap> tags
Note: The dataset has been updated. The <big_gap> tag and certain symbols are no longer included. For details, please refer to the official update announcement and the latest dataset released by the organizers.
2025.12.29: I trained the model by replacing all instances of … [x], x, etc. in the transliteration column of train.csv with <gap> and <big_gap>, then made predictions on test.csv. Meanwhile, I replaced all … in the prediction results with <big_gap>and all x with <gap>.
My LB score reached 30.3, and I have released the training code, the converted datasets as well as the submission code. :)
I’ll share my scoring progress and implementation details here in the next steps, and hope this helps you all.
LBsizesubmit timeepochTraining LossValidation LossChrfprogress31.3725B-100.2909000.4187885.175934revised the <gap> <big_gap>31.0569B19min100.3046000.4216865.082081revised the <gap> <big_gap>, determinatives, fraction such as ¼, curly braces {} and delete parentheses ().31.5762B21min100.2822000.3895885.320788Shortened and aligned the 14 sentences with length exceeding 512, resulting in a total of 1595 pieces of data; meanwhile, revised the <gap> <big_gap>, determinatives, fraction such as ¼, curly braces {} ,and delete slash /, parentheses ().31.8749B-100.2972000.4002075.364566Shortened and aligned the 14 sentences with length exceeding 512, resulting in a total of 1595 pieces of data; meanwhile, revised the <gap> <big_gap>32.3695B19min100.2966000.3854655.364575Shortened and aligned the 16 sentences with length exceeding 512, resulting in a total of 1604 pieces of data; meanwhile, revised the <gap> <big_gap>,determinatives, fraction such as ¼, curly braces {} ,keep ! ? (),and delete slash / ,fem. plur. sing. pl.
The Second Stage
I'm back—but actually, I never left. 32.8 This result is definitely not up to my expectations, lol, but the task isn’t finished yet, so there should still be room for improvement.
LBsizesubmit timeepochTraining LossValidation LossChrfprogress32.8797B17min100.2771000.3700776.596245MAX_LENGTH=385,revised the <gap> <big_gap>,Ensure that the <gap> on both sides exist simultaneously or are absent simultaneously, All subscript numbers uppercase, keep determinatives(Ḫ,ḫ), delete ! ? () " ; — - – < > ⌈ [ ] + ʾ / ,fem. plur. sing. pl. , total of 1703 pieces of data33.0699B17min100.2762000.3535375.957525MAX_LENGTH=475,revised the <gap> <big_gap>,Ensure that the <gap> on both sides exist simultaneously or are absent simultaneously, All subscript numbers uppercase, keep determinatives(Ḫ,ḫ), delete ! ? () " ; — - – < > ⌈ [ ] + ʾ / ,fem. plur. sing. pl. , total of 1703 pieces of data33.3820B18min100.2844000.3514125.638265MAX_LENGTH=512,revised the <gap> <big_gap>,Ensure that the <gap> on both sides exist simultaneously or are absent simultaneously, All subscript numbers uppercase, keep determinatives(Ḫ,ḫ), delete ! ? () " ; — - – < > ⌈ [ ] + ʾ / ,fem. plur. sing. pl. , total of 1703 pieces of data
At present, I have basically aligned the 94 filtered documents with lengths exceeding 512 characters, and revised nearly 100 documents with abnormal length ratios. As for why MAX_LENGTH is set to 385, the reason is CUDA out of memory.
Note:After the new update, <big_gap> has been permanently removed.
DenoisingExploratory Data AnalysisOptimization
19add_reaction
21 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Gaurav Rawat
Posted 21 days ago
·  263rd in this Competition
1
more_vert
I dunno got me batch size has been funny in lower recording better cv than big .. trying to figure out the reason why :( and smaller models working better so far
Reply
1add_reaction
耶✌
TOPIC AUTHOR
Posted 21 days ago
·  34th in this Competition
1
more_vert
It actually doesn’t have much to do with the batch size. The main issue is that the data has a lot of truncation and inconsistency, which leads to large score fluctuations. So standardizing the data well is the key to this competition.good luck.
Reply
React
Gaurav Rawat
Posted 21 days ago
·  263rd in this Competition
1
more_vert
Thanks ya but run same seed diff batch size also seeing this but ya think you are right .. larger models also on same pipes give different results was stranger 
Reply
React
SHUN_04
Posted 21 days ago
·  1508th in this Competition
1
more_vert
Thank you for sharing. This discussion is very helpful for me. I'm a beginner, so please excuse my question, but why does your training strategy table only show chrF? In my own training, the BLEU score is extremely low, like 0.00… Since the final evaluation metric is the geometric mean of BLEU and chrF, is this really okay?
Reply
1add_reaction
耶✌
TOPIC AUTHOR
Posted 21 days ago
·  34th in this Competition
0
more_vert
It doesn’t really matter much. Although this can’t directly reflect the leaderboard score, it still gives us a general idea of how the model is performing, and I think that’s sufficient for now.
Reply
1add_reaction
SHUN_04
Posted 21 days ago
·  1508th in this Competition
1
more_vert
Thank you for your response. I have another question. Looking at public inference notebooks, I noticed that many people are using almost the same training models. Why is this the case? Also, is it considered a best practice to take these publicly available models and fine-tune them as a starting point (pre-trained model) on a new dataset that has been pre-processed with tags like ?
Reply
React
cswwp
Posted 2 months ago
·  939th in this Competition
-2
more_vert
想问下，连词符号应该去掉吗？例如A-mur-{d}UTU 转换成Amur D UTU 或 Amur DUTU ？ 看到你之前清洗后的数据还是包含连词符的，官方给的描述还是比较含糊的😅
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
不能去掉，完全不可以，需要处理的主要是转换为gap和big_gap,以及浮点数字从0.3333到⅓这样，没有任何/,然后是罗马数字变为阿拉伯数值 X->10,还有就是限定词，transliteration列的()转为{},其他的标点符号就看你自己个人了，目前没有统一的方法，你可以融合几个不同训练数据的模型，来弥补这些差异，至少现在公开的code，就是这样，竟然达到了34.2。所以保留你的A-mur-{d}UTU，现在就是最完美的样子了
Reply
React
Preechanon Chatthai
Posted 2 months ago
·  1342nd in this Competition
1
more_vert
i can ask u? what u use method for solve problems hallucination and repetition word???
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
I haven't reached the stage of solving this problem yet. The maximum token capacity of my current code model is 512, and hallucinations tend to come with repeated words when the text length increases. I think this issue can be addressed through the following two approaches:
1. Increase the token capacity, which however requires greater computing power.
2. Truncate long sentences into smaller ones by semantic meaning for training, but it will take some time to do.
good luck
Reply
React
Jack
Posted 2 months ago
·  19th in this Competition
2
more_vert
How the heck are you aligning sentences to actually improve your score? I’ve spent hours going through the sentence alignment file to create sentences and manually verified everything and all it did was lower my score. 
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
2
more_vert
That's a great question, and I'll break down the answer into three points:
1. First, the sentences I’m currently processing: sentences where both the transliteration and translation columns exceed 512 characters, and their oare_id exists in Sentences_Oare_FirstWord_LinNum.csv (the critical basis for my segmentation). So far, I’ve filtered out only 94 sentences that meet the above criteria.
2. How I process these sentences: I perform truncation using the sentence start words and English translations from Sentences_Oare_FirstWord_LinNum.csv, while striving to preserve semantic integrity and avoiding truncation of single isolated sentences. Minor punctuation adjustments may be made during truncation—for example, removing or reinserting the closing quotation mark if there is no matching " after said:". Additionally, translations in Sentences_Oare_FirstWord_LinNum.csv may have slight discrepancies with those in train.csv, and the two datasets are complementary to each other. Ultimately, the only requirement is that the truncated length does not exceed 512 characters, as I aim to avoid losing semantic information of the entire passage.
3. On score improvement: I remain somewhat skeptical here. Although truncating sentences alone boosted my score by 0.5, my random seed is still set to 42. As the total number of rows in train.csv increases, the split results for the validation and training sets will change. This may cause the model to train on and learn new content, which could be the actual reason for the score increase.
Conclusion: I will continue aligning partial sentences and monitor the LB score. A significant LB score improvement will confirm the effectiveness of this approach. In fact, with the current token limit of 512, a large volume of data is undoubtedly omitted. Sentence alignment should yield certain benefits, but it requires meticulous execution (there is no definitive rule for this task).Hope this helps you.
Reply
2add_reaction
Jack
Posted 2 months ago
·  19th in this Competition
0
more_vert
Want to check my sentence alignment results from my programmatic + manual approach with what you've got? 
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
You can share you data,public
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
Hello, I have a question. Does your statement that the length exceeds 512 refer to the length of the characters themselves, or the length after space splitting (len(xxx.split(" "))))?
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
没有经过任何处理，是原始的长度，包含了" "
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
2
more_vert
Thank you. Could you please explain your understanding of the first_word_number, first_word_obj_in_text, line_number, and side column fields?
Reply
1add_reaction
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
我目前认为比较好理解的是first_word_number和side column。
first_word_number: 就是这个单词是这一段话里的第几个词(不包含数值 很重要！)
side column: 这个你要结合实际，Akkadian 其实有很多载体，最主要的就是泥板(tablet),然后泥板的每个面都可以写东西(最主要有 Obverse Reverse Edge Left Seal A Seal F )等等面
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
Given these split sentences, will you delete the original entire paragraph to merge the split sentences, or will you merge the split sentences directly without deleting them?
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
会删除已经合并的片段，因为512token截断了句子，我们本来就是想通过句子对齐来解决这个问题
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
Thank you for your answer. I look forward to hearing your data processing method.
Reply
React
Hide replies
QianYuu
Posted 2 months ago
·  163rd in this Competition
1
more_vert
"Shortened and aligned the 14 sentences with length exceeding 512, resulting in a total of 1595 pieces of data"
How is this implemented?
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
2
more_vert
I implemented this manually. Although the organizer released the file Sentences_Oare_FirstWord_LinNum.csv, I noticed that the truncation logic does not seem to include numeric characters, which prevented me from truncating sentences accurately. (It is also possible that I misunderstood the usage instructions.) Therefore, I manually truncated the translation and transliterationcolumns with content length exceeding 512 to achieve sentence-level alignment. This process also helped me gain a better understanding of Akkadian. 
The current 0.5-point improvement has boosted my confidence significantly. My next task will likely be to further optimize sentence alignment. Given my lack of computing resources and reliance on Kaggle's GPU, a 512 token limit is currently the optimal choice.:)
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
1
more_vert
Thank you. I'm also studying Sentences_Oare_FirstWord_LinNum.csv and have made some attempts, but the LB has dropped. I need to take another look.
Reply
React
Jack
Posted 2 months ago
·  19th in this Competition
1
more_vert
Same here 😅 it'll be worth it to figure out though
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
Your 33.0 LB is really great. I believe 33.0 is definitely not your limit. Currently, I haven't made any significant breakthroughs in sentence alignment. I'll study it some more.
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
Aligning documents with a length of over 512 characters should only serve to expand vocabulary. For score improvement, it is still necessary to truncate the corresponding erroneous sentences in the transliteration and translation columns. These errors can be easily identified using the ratio metric. Thank you for your response.:)
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
2
more_vert
Yes, I found that many character lengths didn't match. I thought it was because my character segmentation wasn't good enough, haha, turns out that just deleting those characters solved the problem.
Reply
React
Angantyr
Posted 2 months ago
2
more_vert
Some transliterations or translations are truncated and don't match. I made a list of the transliteration OARE IDs along with a short analysis based on the texts covering train.csv and Sentences_Oare_FirstWord_LinNum.csv.
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
Yes, direct deletion is the fastest method. However, attempting truncation allows us to retain a great deal of semantic information.
Reply
React
Preechanon Chatthai
Posted 2 months ago
·  1342nd in this Competition
0
more_vert
i think mayby domain in test very difference train set and format text diff. i trained model by sentence level. i sentence alignment 8000 sentence can more gm in val set so high (train 80% val 20%) but submit get score 30 
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
My situation is similar to yours; my score is 31.6.
Reply
React
Preechanon Chatthai
Posted 2 months ago
·  1342nd in this Competition
0
more_vert
i think preprocess and postprocess more important than model 
Reply
1add_reaction
Preechanon Chatthai
Posted 2 months ago
·  1342nd in this Competition
0
more_vert
i think we should try to be as close to the hidden test set format as possible and denoise it. maybe can get more gm score. but idk what i should do.
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
4
more_vert
Haha, this competition has become a challenge of understanding and processing data, and has little to do with the model.
Reply
1add_reaction
Gaurav Rawat
Posted 21 days ago
·  263rd in this Competition
0
more_vert
Ya 💯 Seems s as of now
Reply
React
Hide replies
einherjer
Posted 2 months ago
·  244th in this Competition
0
more_vert
@qifeihhh666 what is the rationale of replacing all instances of … [x], x, etc. in the transliteration column only and not in the translation column as well? 
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
The translation column needs to be converted into<gap><big_gap>
Reply
React
einherjer
Posted a month ago
·  244th in this Competition
1
more_vert
@qifeihhh666 Yes, I get that the translation needs to be converted to <gap> and <big_gap>. However, if I understood correctly, you are predicting translations with x, [x], .. (i.e. without <gap> and <big_gap>) and then as a post-processing step, you are converting the predictions with x, [x], … to <gap> and <big_gap> (am I right?).
I wonder why one would do this as a post-processing step. Why not just clean the transliteration and translation before training in the first place? Is there some logic behind that?
Reply
React
This comment has been deleted.
耶✌
TOPIC AUTHOR
Posted a month ago
·  34th in this Competition
0
more_vert
That was the case at the very beginning, but it’s totally different now, ever since the score of 31.3.
Reply
2add_reaction
Aaron Bornstein
Posted 2 months ago
·  34th in this Competition
0
more_vert
It's strange i tried this and dropped to from 28.3 to 27.6 I wonder what I did wrong
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
The translation column needs to be converted into <gap><big_gap>
Reply
React
Aaron Bornstein
Posted 2 months ago
·  34th in this Competition
1
more_vert
Strange I did this though I did it for both the translation and transliteration.
Then based on your comment in another notebook i did only the transliteration. 
Neither work for me I really wonder what i'm missing.
def replace_gaps(text):     if pd.isna(text):          return text      text = re.sub(r'\[\.{3}(?:\s+\.{3})+\]\s+\.{3}(?:\s+\.{3})+', '<big_gap>', text)     text = re.sub(r'\[\.{3}(?:\s+\.{3})+\]', '<big_gap>', text)     text = re.sub(r'\.{3}(?:\s+\.{3})+', '<big_gap>', text)      text = re.sub(r'\[x\]', '<gap>', text)     text = re.sub(r' x ', ' <gap> ', text)     text = re.sub(r'\[…\]', '<big_gap>', text)     text = re.sub(r'\[\.\.\.\]', '<big_gap>', text)     text = re.sub(r'…', '<big_gap>', text)     text = re.sub(r'\.\.\.', '<big_gap>', text)      return text   train_expanded = simple_sentence_aligner(train_df)   train_expanded['transliteration'] = train_expanded['transliteration'].apply(lambda x:replace_gaps(x)) #train_expanded['translation'] = train_expanded['translation'].apply(lambda x:replace_gaps(x))   train_expanded.head()
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
You're doing the right thing. When I used this code on Kaggle, I found the results inconsistent with those processed on my local machine. I first completed the processing locally and double-checked all formatting details like x, xx… […], and everything was perfect. So I recommend processing on your local machine as it’s easier to verify. I’ll publish the 31.3 train.csv dataset shortly, and you can compare the differences with your processed version.good luck
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
2
more_vert
This is the dataset I used for training.train data
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
[3510/3510 1:22:44, Epoch 10/10]
EpochTraining LossValidation LossChrf10.7860000.6401404.08202320.6163000.5515974.46881130.5365000.4974104.93282440.4562000.4555755.02743950.3972000.4266595.08014660.3536000.4156685.10313070.3327000.4107995.15016580.3128000.4098235.14011990.2940000.4100925.141407100.2873000.4102675.161873
Reply
React
Aaron Bornstein
Posted 2 months ago
·  34th in this Competition
3
more_vert
I appreciate all the support and advice here i'll give that a try now by the way one thing i noticed in your training notebook. I'm not sure the simple_sentence_aligner is doing anything I get the same number of rows before and after running it after i get this gap trick to work I plan to pivot to alignment.
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
4
more_vert
Yes, because the final test.csv is in a sentence-aligned format, rather than the document-level alignment used in the current train.csv. Meanwhile, the maximum input length of the model being trained is 512, which results in truncation of a large amount of training data. Converting document-level data into sentence-level alignment is a crucial method to boost performance in subsequent experiments.
This is also one of the sources for supplementing data.
Reply
React
Aaron Bornstein
Posted 2 months ago
·  34th in this Competition
2
more_vert
Good news i trained on the set you provided and it worked I'm now at 31.1. I'm transitioning to work on the sentence alignment challenge I have some ideas of how to do this if I am able to make progress I will share with you the segmented sentence pairs.
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
Congratulations! Yes, At the begining I try sentence alignment, but the results were unsatisfactory (probably because the format hasn't been properly adjusted). So I've been following up on the discussion to fix the formatting issues continuously.Through these days' efforts, tomorrow I'll retry the sentence-aligned dataset with the corrected format conversion. Good luck!
Reply
React
QianYuu
Posted 2 months ago
·  163rd in this Competition
1
more_vert
I'm doing the same job as you.
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
Something amazing—I did maybe exactly these things and got an LB score of 31.5.lol
Reply
2add_reaction
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
Congratulations!
Reply
React
Angantyr
Posted 2 months ago
1
more_vert
I digged into the issue @einherjer posted earlier: https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/664177#3383842
There's a portion of texts where (2 broken lines) string is clearly counted as x x x instead of .... I'm guessing that if the problem is present in Sentences_Oare_FirstWord_LinNum.csv and in the hidden testthen taking that into account could boost the score a bit further (at least until the issue is resolved :D).
Reply
React
Carol Wang
Posted 2 months ago
·  553rd in this Competition
0
more_vert
Can I ask you how to deal with the oare_id ?
Reply
React
Angantyr
Posted 2 months ago
0
more_vert
@ilanwang What do you mean by "dealing with the oare_id"?
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
1
more_vert
I convert any broken lines and large break to <big_gap>.
Reply
React
HZM
Posted 2 months ago
·  22nd in this Competition
0
more_vert
Thanks so much for your share, would you like to show how to preprocess this training data especally replace progress
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
我目前还卡在32.3，应该是格式还有很多错的，我一直在修改，你可以先看看别人和主办方给的归一化建议，等我完善我的归一化格式之后再分享代码。🙂
Reply
React
HZM
Posted 2 months ago
·  22nd in this Competition
0
more_vert
感谢 大佬 回复 很硬核的分享
Reply
React
Hide replies
This comment has been deleted.
Angantyr
Posted 2 months ago
4
more_vert
The oare_id from the train.csv matches the text_uuid from the Sentences_Oare_FirstWord_LinNum.csv.
Reply
React
耶✌
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
2
more_vert
The oare_id from the train.csv matches the text_uuid from the Sentences_Oare_FirstWord_LinNum.csv.
Reply
React
Sue the
Posted 2 months ago
·  553rd in this Competition
1
more_vert
I got it! Thank you very much!
Reply
1add_reaction
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
PRAYAG PATEL ·  463RD IN THIS COMPETITION ·  POSTED A MONTH AGO
42
more_vert
Akkadian Translation Competition - Community Knowledge Synthesis
⚠️ Important Context
Transparency: This is a synthesis of community discussions and public notebooks, not original research. I'm currently ranked at 35.1 score and learning from the community myself.
Timing Note: Many insights here are from early-to-mid January discussions. The community's understanding has evolved since then. If you're in the top 50, you probably know more than what's written here.
Target Audience: This consolidation is aimed at competitors who are:
* New to the competition
* Stuck at baseline scores (30-35)
* Looking for a starting point before diving deeper
What I HAVE tested personally: AKK-300m failure, bucket batching, length penalty variations, the 35.1 optimization stack.
What I'm synthesizing from others: Training recipes, data quality insights, overfitting analysis.
Request to Top Competitors: If anything here is outdated or wrong, please comment! I want this to be accurate and helpful, not misleading.
Purpose of This Post
After weeks of testing, collaboration, and learning from the community, I wanted to consolidate what's actually working (and what's not) to help everyone still pushing for improvements. This is a synthesis of public discussions, shared notebooks, and systematic testing.
TL;DR: We're at an interesting inflection point. The public model ceiling is ~35.1, and breaking past it requires either custom training data, novel techniques, or collaboration. Here's what we know.
Current State of the Leaderboard
The 35.1 Plateau:
* 100s of competitors clustered at exactly 35.1
* Why: Everyone using the same model (Assia Benkedia's byt5-akkadian-optimized-34x) with minor variations
* Implication: To break 35.5+, you need something different
Score Distribution:
* Top tier (36.5-38.1): Likely custom training on private Old Assyrian data
* Competitive cluster (35.1-36.4): Public model + optimizations 
* Copy-paste crowd (34.9-35.0): Direct Assia model usage
* Baseline methods (<34.9): Older approaches
Critical Insight from Aaron Bornstein:
"High scores on the visible 33% of the test set are likely to degrade significantly on the hidden 67% if they are out of domain"
Public LB (34% of test) ≠ Private LB (66% of test). Conservative, semantically-accurate approaches may outperform pattern-matching models on final evaluation.
Proven Optimization Stack (34.9 → 35.1)
1. Base "Model": Assia Benkedia's byt5-akkadian-optimized-34x (34.9)
IMPORTANT CORRECTION (Thanks to Musa Peker for catching this):
This is actually an ENSEMBLE of three models, not a single model:
* /kaggle/input/byt5-akk-gap-sentence-v4-cp-final (likely Assia's)
* /kaggle/input/byt5-akkadian-model
* /kaggle/input/byt5-base-big-data2
Implication: The 34.9 baseline is achieved through ensemble combination, not a single checkpoint. This means:
* Single model ceiling is probably ~33-34
* To beat 35.5, you need either a better base model OR different ensemble components
* The 35.1 "plateau" makes sense - everyone using the same 3-model ensemble + minor optimizations
Credit: Assia Benkedia for the ensemble approach, plus the contributors of the three base models Availability: Kaggle dataset final-byt5
2. Bucket Batching (+0.1)
* Credit: Sera Ria Gomes 
* What it does: Groups similar-length samples together in batches
* Why it works: Reduces padding waste by 20-40% → model sees less noise
* Implementation:
class BucketBatchSampler(Sampler):     """Groups samples by similar length to minimize padding"""     def __init__(self, lengths, batch_size, num_buckets=4):         self.lengths = lengths         self.batch_size = batch_size         self.num_buckets = num_buckets          # Sort indices by length         sorted_indices = sorted(range(len(lengths)), key=lambda i: lengths[i])          # Divide into buckets         bucket_size = len(sorted_indices) // num_buckets         self.buckets = []         for i in range(num_buckets):             start = i * bucket_size             end = start + bucket_size if i < num_buckets - 1 else len(sorted_indices)             self.buckets.append(sorted_indices[start:end])      def __iter__(self):         for bucket in self.buckets:             indices = bucket.copy()             for i in range(0, len(indices), self.batch_size):                 yield indices[i:i + self.batch_size]      def __len__(self):         return sum(len(bucket) // self.batch_size for bucket in self.buckets)
3. Length Penalty = 1.3-1.5 (+0.1)
* Credit: manwithacat (discovered optimal range)
* Why it works: Encourages longer, more complete translations
* Testing results:
   * 1.3: 35.1 ✅ (conservative)
   * 1.5: 35.1 ✅ (also works) 
   * 1.7: 35.0 ❌ (too aggressive)
4. Optimal Configuration
CONFIG = {     "model": "byt5-akkadian-optimized-34x",     "num_beams": 8,     "max_new_tokens": 512,     "length_penalty": 1.3,  # or 1.5     "early_stopping": True,     "batch_size": 8,     "use_bucket_batching": True,     "num_buckets": 4 }
Novel Technique: MBR Decoding (Untested Potential)
* Credit: Hikari_30 
* What it does: Minimum Bayes Risk - generates 20 diverse candidates, scores each against all others using chrF++, selects consensus winner
* Why it could help:
   * Reduces hallucination risk (single beam search can hallucinate)
   * Combines diversity (sampling) + quality (beam search)
   * No training required - pure inference technique
   * Validated in NMT research literature
* Cost: ~3-4x slower inference
* Status: Only 1 person testing it publicly - could improve private LB robustness
Implementation outline:
# Generate 15 diverse candidates (temperature=0.7) # Generate 5 beam search candidates # Score each candidate against all others using chrF++ # Select candidate with highest average similarity
❌ Failed Optimizations (Save Your Time!)
1. Onomasticon Name Replacement (0.0 gain)
* 5,973 Akkadian→English name mappings
* Expected: +0.5 to +1.0 (host claimed "biggest single improvement")
* Actual: 34.9 → 34.9 (no change)
* Why: Model already outputs English names correctly
2. Submission Blending (0.0 gain)
* Attempted: Blend Assia's 34.9 with older 34.6 ensemble
* Result: Assia's model dominated 100%
* Conclusion: Need equal-quality models to blend effectively
3. Hyperparameter Tuning via Optuna (Minimal Impact)
* Credit: HARUKI HARADA
* Tested 20 combinations on validation set
* Best found: length_penalty=1.788, beams=6 → validation score 25.97
* Baseline: length_penalty=1.5, beams=8 → validation score 25.58
* BUT: They still used baseline for submission (didn't trust Optuna)
* Conclusion: Limited impact (~0.4 max), not worth compute time
4. AKK-300m Model (Complete Failure - AVOID!)
* Credit: Thalesian/Akkademia Project 
* Tested Feb 8, 2026
* Result: Outputs only <big_gap> tokens (complete garbage)
* Why it failed:
   * Wrong dialect mix (all Akkadian periods, not Old Assyrian specific)
   * Context window only 64 tokens (vs ByT5's 512)
   * Multi-task confusion (7+ different tasks)
   * Cannot submit: Requires internet to download, not in Kaggle datasets
* Downloads: 744 in 2 days, but ZERO public successes >35.1
* Recommendation: Skip this entirely
5. BetterTransformer
* Not accessible in Kaggle environment (deprecated in newer optimum versions)
* Multiple workaround attempts failed
* Stop pursuing
Critical Warnings & Insights
Data Quality Issues
From Angantyr:
* 163/1,561 training samples (~10%) have incomplete translations
* Pattern: Long Akkadian → First item only, then "…"
* Example: 66 tokens → "1 talent … …" (3 words)
Host Confirmation:
"By no means an error-free dataset. Many of these databases are worked on by students with little oversight"
The Overfitting Crisis
From Aaron Bornstein's Systematic Perturbation Testing:
* Top models (34-38 scores) are ~40% pattern matchers, not true translators
* They hallucinate generic trade sentences from corpus templates
* Public LB (34%) ≠ Private LB (67%)
* Implication: Conservative, semantically-accurate models may rank higher on private LB
The Metric Trap
From Musa Peker:
* Compared two models:
   * "The Parrot" (pattern matcher): 34.2 score, complete nonsense
   * "The Domain Expert" (semantic translator): 11.8 score, accurate translations
* Key insight: BLEU/chrF++ rewards n-gram overlap, NOT semantic accuracy
* Quote: "We are optimizing for a metric that measures 'Vibes' rather than 'Translation'"
Domain Mismatch: EvaCun = ORACC Data
CRITICAL FINDING:
* EvaCun corpus IS the ORACC dataset
* Time Period: Neo-Assyrian (~911-539 BCE) 
* Competition: Old Assyrian (~1950-1750 BCE)
* Gap: 1,000 years wrong!
* Host Quote: "Would you include Middle English to train modern English? Probably not."
* Recommendation: ❌ DO NOT USE for training
💻 Working Code: Complete Inference Pipeline
""" ASSIA'S MODEL + BUCKET BATCHING + OPTIMAL LENGTH PENALTY Expected Score: 35.1  NOTEBOOK SETUP: - Accelerator: GPU T4 x2 - Internet: OFF   - Datasets: deep-past-initiative-machine-translation, final-byt5 """  import re import pandas as pd import torch from torch.utils.data import Dataset, DataLoader, Sampler from transformers import AutoTokenizer, AutoModelForSeq2SeqLM  # ============================================================ # CONFIGURATION # ============================================================ CONFIG = {     "test_path": "/kaggle/input/deep-past-initiative-machine-translation/test.csv",     "model_path": "/kaggle/input/final-byt5/byt5-akkadian-optimized-34x",     "device": torch.device("cuda" if torch.cuda.is_available() else "cpu"),     "max_length": 512,     "batch_size": 8,     "num_buckets": 4,      "generation": {         "num_beams": 8,         "max_new_tokens": 512,         "length_penalty": 1.3,  # or 1.5         "early_stopping": True     } }  # ============================================================ # BUCKET BATCH SAMPLER (SERA'S OPTIMIZATION) # ============================================================ class BucketBatchSampler(Sampler):     def __init__(self, lengths, batch_size, num_buckets=4):         self.lengths = lengths         self.batch_size = batch_size         self.num_buckets = num_buckets          sorted_indices = sorted(range(len(lengths)), key=lambda i: lengths[i])          bucket_size = len(sorted_indices) // num_buckets         self.buckets = []         for i in range(num_buckets):             start = i * bucket_size             end = start + bucket_size if i < num_buckets - 1 else len(sorted_indices)             self.buckets.append(sorted_indices[start:end])      def __iter__(self):         for bucket in self.buckets:             indices = bucket.copy()             for i in range(0, len(indices), self.batch_size):                 yield indices[i:i + self.batch_size]      def __len__(self):         return sum(len(bucket) // self.batch_size for bucket in self.buckets)  # ============================================================ # PREPROCESSING & POSTPROCESSING # ============================================================ def preprocess_input(text):     """Minimal preprocessing for test data"""     if pd.isna(text):         return ""     text = str(text)     text = re.sub(r'(\.{3,}|…+)', '<big_gap>', text)     text = re.sub(r'(xx+|\s+x\s+)', '<gap>', text)     return text  def postprocess_output(text):     """Clean model output - proven effective stack"""     if not isinstance(text, str) or not text.strip():         return ""      # 1. Normalize ḫ/Ḫ → h/H (test set uses h)     text = text.replace('ḫ', 'h').replace('Ḫ', 'H')      # 2. Subscript numbers → regular     subscript_map = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")     text = text.translate(subscript_map)      # 3. Normalize gaps in output     text = re.sub(r'(\[x\]|\(x\)|\bx\b)', '<gap>', text, flags=re.I)     text = re.sub(r'(\.{3,}|…)', '<big_gap>', text)      # 4. Remove scribal annotations     text = re.sub(r'\((fem|plur|pl|sing|\?|!)\.?\)', '', text, flags=re.I)      # 5. Protect gap markers, remove forbidden chars     text = text.replace('<gap>', '\x00GAP\x00')     text = text.replace('<big_gap>', '\x00BIG\x00')     forbidden = '!?()"—–<>⌈⌋⌊[]+ʾ/;'     text = text.translate(str.maketrans('', '', forbidden))     text = text.replace('\x00GAP\x00', ' <gap> ')     text = text.replace('\x00BIG\x00', ' <big_gap> ')      # 6. Unicode fractions     text = re.sub(r'(\d+)\.5\b', r'\1 ½', text)     text = re.sub(r'(\d+)\.25\b', r'\1 ¼', text)     text = re.sub(r'(\d+)\.75\b', r'\1 ¾', text)      # 7. Remove word repetitions     text = re.sub(r'\b(\w+)(?:\s+\1\b)+', r'\1', text)      # 8. Final cleanup     text = re.sub(r'\s+', ' ', text).strip()      return text  # ============================================================ # DATASET CLASS # ============================================================ class AkkadianDataset(Dataset):     def __init__(self, df):         self.ids = df['id'].tolist()         self.texts = [             "translate Akkadian to English: " + str(t)              for t in df['transliteration']         ]         self.lengths = [len(t.split()) for t in self.texts]      def __len__(self):         return len(self.ids)      def __getitem__(self, idx):         return self.ids[idx], self.texts[idx]  # ============================================================ # MAIN INFERENCE # ============================================================ print("Loading test data...") test_df = pd.read_csv(CONFIG['test_path']) test_df['transliteration'] = test_df['transliteration'].apply(preprocess_input)  print("Loading model...") model = AutoModelForSeq2SeqLM.from_pretrained(CONFIG['model_path']).to(CONFIG['device']).eval() tokenizer = AutoTokenizer.from_pretrained(CONFIG['model_path'])  print("Creating dataset with bucket sampling...") dataset = AkkadianDataset(test_df) sampler = BucketBatchSampler(dataset.lengths, CONFIG['batch_size'], CONFIG['num_buckets'])  def collate_fn(batch):     ids = [item[0] for item in batch]     texts = [item[1] for item in batch]     encoded = tokenizer(texts, max_length=CONFIG['max_length'],                         padding=True, truncation=True, return_tensors="pt")     return ids, encoded  dataloader = DataLoader(dataset, batch_sampler=sampler, collate_fn=collate_fn, num_workers=2)  print("Running inference...") predictions = [] with torch.inference_mode():     for batch_ids, encoded_inputs in dataloader:         outputs = model.generate(             input_ids=encoded_inputs.input_ids.to(CONFIG['device']),             attention_mask=encoded_inputs.attention_mask.to(CONFIG['device']),             **CONFIG['generation']         )         decoded = tokenizer.batch_decode(outputs, skip_special_tokens=True)         cleaned = [postprocess_output(text) for text in decoded]         predictions.extend(zip(batch_ids, cleaned))  # Create submission submission = pd.DataFrame(predictions, columns=['id', 'translation']) submission.to_csv('submission.csv', index=False) print(f"Done! Saved {len(submission)} translations. Expected score: 35.1")
🎯 Strategic Insights
For Breaking Past 35.1
You need ONE of these:
1. Custom Training Data (3,000-5,000 clean Old Assyrian sentence pairs)
   * Top scorers manually extracted from PDFs (40-100+ hours of work)
   * Could potentially automate with LLM-assisted extraction
2. Novel Inference Techniques
   * MBR decoding (Hikari_30's approach - untested by most)
   * Ensemble of equal-quality models (not just Assia + older models)
3. Collaboration
   * Aaron Bornstein climbed from #48 → #24 (his methods work!)
   * Combine complementary skills: data processing + inference optimization
Training Insights (If You Go That Route)
From Jean-Louis Roy (#5) - Validated Recipe:
EPOCHS = 10-15  # NOT 26+ MAX_LENGTH = 512  # NOT 256 BATCH_SIZE = 4 GRADIENT_ACCUMULATION_STEPS = 4 LEARNING_RATE = 5e-5 FP16 = False  # Critical - prevents NaN errors
From Jack (#2) - CORRECTED (Thanks to hongan for catching this):
What I originally wrote was WRONG. Jack clarified his actual approach:
✅ What Jack actually does:
* "95% is preprocessing/formatting" - BUT this means CAREFUL MANUAL REVIEW
* Manually reviewed EVERY document in train.csv (where he gained most score)
* Follows recommended formatting guidelines
* Tests different approaches on training data
* Ensures meaning alignment in samples
❌ What Jack does NOT do:
* Keep training data "as is" without review
* Avoid cleaning training data
* Only preprocess test data
Key quote (Feb 2026): "I really started to gain in score when I manually reviewed (briefly - still finding things I've missed) each and every document in the train.csv."
About sentence alignment: "Sentence alignment didn't work for me because my sentences sucked 😭" (This was about HIS implementation, not the approach itself)
Critical insight: "If your formatting is off, especially on translations, nothing else you do will matter since your model isn't matching the desired output format."
From 耶✌ :
* Gap preprocessing applied to BOTH columns (transliteration AND translation)
* Sentence alignment from Sentences_Oare_FirstWord_LinNum.csv improved score +0.5
* MAX_LENGTH progression validated: 385 → 475 → 512 (each step +0.2-0.3)
Safe Data Sources
✅ SAFE TO USE
* train.csv (1,561 samples) - Original competition data
* Sentences_Oare_FirstWord_LinNum.csv (9,782 alignments) - If verified against first_word matching
⚠️ USE WITH CAUTION
* published_texts.csv (7,953 samples) - Transliterations only, unknown time period mix
❌ DO NOT USE
* EvaCun Corpus / ORACC Data - Neo-Assyrian (911-539 BCE), 1,000 years wrong!
Medal Zone Strategy
Gold (Top 15): Requires custom data OR collaboration OR breakthrough technique
Silver (Top 50): Achievable with proven optimization stack (35.1-35.3)
(Top 200): Public model baseline (34.9-35.0)
Key Decision: Private LB shake-up probability ~60% (per Aaron Bornstein's analysis). Conservative, semantically-accurate approaches may outperform pattern-matching models on final evaluation.
🙏 Credits & Acknowledgments
Major Contributors (in alphabetical order):
* Aaron Bornstein - Overfitting analysis, perturbation testing
* Angantyr - Incomplete translation analysis 
* Assia Benkedia - byt5-akkadian-optimized-34x model (publicly released)
* HARUKI HARADA - Optuna hyperparameter tuning, chunked beam search
* Hikari_30 - MBR decoding technique
* Jack - Preprocessing insights ("95% is preprocessing")
* Jean-Louis Roy - Validated training recipe
* manwithacat - Length penalty optimization discovery
* MPWARE - ḫ/h issue discovery, determinative inconsistency
* Musa Peker - Metric trap analysis 
* Sera Ria Gomes - Bucket batching optimization
* Thalesian/Akkademia - AKK-300m model (tested and documented as failed)
* 耶✌ - Gap preprocessing methodology, sentence alignment
Host (DeepPast Initiative) - For hosting this fascinating competition and providing clarifications throughout
Apologies
If I missed giving proper credit to anyone or misattributed any techniques, please let me know in the comments and I'll update immediately. This synthesis is based on public discussions and notebooks—if you contributed something I didn't mention, that's my oversight, not intentional!
Good luck to everyone in the final push! 51 days to go.
4add_reaction
8 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Jack
Posted a month ago
·  19th in this Competition
5
more_vert
I made a lot of mistakes in my preprocessing early on.. I’m not totally sure when that quote is from but it was probably early.
I’d still argue 95% of this will be preprocessing/formatting your transliterations/translations.. but, I’d follow the recommended guidelines. Also, sentence alignment didn’t work for me because my sentences sucked 😂 
If your formatting is off, especially on translations, nothing else you do will matter since your model isn’t matching the desired output format. 
I would start off with minimal changes to the train.csv but you should 100% test different things and ensure meaning is aligned in your samples as well. I really started to gain in score when I manually reviewed (briefly - still finding things I’ve missed) each and every document in the train.csv. 
Reply
React
Musa Peker
Posted a month ago
·  38th in this Competition
3
more_vert
Great synthesis! This is a very comprehensive summary of the current state of the competition. Thanks for putting this together.
I just wanted to add a small technical correction regarding the "Base Model" section (Assia Benkedia's byt5-akkadian-optimized-34x). Upon inspecting the model files and configuration, it appears this is actually an ensemble technique rather than a single model.
The code references a list of BASE_MODELS that includes:
/kaggle/input/byt5-akk-gap-sentence-v4-cp-final (Likely Assia's) /kaggle/input/byt5-akkadian-model /kaggle/input/byt5-base-big-data2
So, the 34.9+ baseline is achieved by ensembling these public models. It’s worth acknowledging that the performance comes from combining the work of multiple contributors/models, not just a single checkpoint.
Thanks again for the great overview!
Reply
React
Prayag Patel
TOPIC AUTHOR
Posted a month ago
·  463rd in this Competition
1
more_vert
Thank you for the correction. 
This is a great info! This also explains why submission blending didn't work for me (I was trying to blend an ensemble with another ensemble)
Quick clarifications:
1. Is the ensemble using simple averaging, or weighted voting?
2. Do you know if the 3 base models were trained on different data splits, or different approaches?
3. Does this mean a well-trained single model could potentially reach around 34 on its own?
Updated the post with this info. Really appreciate this technical detail!
Reply
React
Musa Peker
Posted a month ago
·  38th in this Competition
1
more_vert
This is not a classic inference-time ensemble; instead, it merges the model weights. The parameters of three different ByT5 checkpoints were averaged using Weighted Parameter Averaging with predefined ratios, producing a single new model.
Reply
React
Prayag Patel
TOPIC AUTHOR
Posted a month ago
·  463rd in this Competition
0
more_vert
Thanks so much for the technical details about the ensemble! I updated my post to mention it's weighted parameter averaging(without specific weights or code though).
This explains why submission blending didn't work for me(I was trying to ensemble an already-ensembled model with another ensemble). 
One question if you don't mind: do you know if the 3 base models were trained on different data or just different hyperparameters/random seeds? Trying to figure out if I should be aiming for diversity in training data or diversity in model architecture for my own attempts.
Reply
React
Musa Peker
Posted 20 days ago
·  38th in this Competition
0
more_vert
I don’t have definitive information on whether these models were trained on different datasets or whether the differences arise from architectural choices, hyperparameters, or random seeds.
Reply
React
hongan
Posted a month ago
·  35th in this Competition
3
more_vert
respect the effort. However, I believe many of your quotes and suggestions are not entirely accurate, mainly because they are comments made 2 months ago (!) and I believe we, as a community, have gained a better understanding of the data since then… IMO you need to be prepared to spend many more hours on this task in order to beat the public model and understand why you are doing better, but i could be wrong😀 And until you have gone through the train data at least once, i would refrain from giving any advice to other people…
Reply
React
Prayag Patel
TOPIC AUTHOR
Posted a month ago
·  463rd in this Competition
0
more_vert
Really appreciate the feedback! You're absolutely right that:
1. I haven't yet gone through the training data line-by-line myself
2. many of these insights are from early jan discussions (2 months old)
3. im synthesizing community knowledge, not presenting original research My intent was to consolidate scattered information(added additional context to the post) for people entering the competition now, but I should have been clearer about what I've personally tested vs. what I'm reporting from others.
Quick question, what have you learned in the past 2 months that contradicts or updates the insights here? I'm genuinely curious what the top competitors know now that we didn't know in January. Happy to update the post with newer findings!
Reply
React
hongan
Posted a month ago
·  35th in this Competition
0
more_vert
for example, i believe the "insight" you are giving here is very far from being true:
"95% is preprocessing. Every attempt to follow instructions for cleaning data led to worse performance." Keep training data as close to original as possible Heavy preprocessing ONLY for test/inference data Adding sentence-level data from published_texts.csv made his model WORSE
Reply
React
Jack
Posted a month ago
·  19th in this Competition
0
more_vert
Yes, this is off. I was goin through it at the time. 
Reply
React
Prayag Patel
TOPIC AUTHOR
Posted a month ago
·  463rd in this Competition
0
more_vert
Yeah, good catch on that one.
Turns out I completely misread what Jack meant. Pretty much the opposite of what I wrote lol.
Updated the post with the correction. 
Reply
React
Hikari_30
Posted a month ago
·  661st in this Competition
2
more_vert
I unintentionally made one of my notebooks public. While it wasn't my initial intention, I would be happy if it could contribute to the community's learning and discussion.
Currently, I suspect that the top scores on the Public LB might be overfitting. Therefore, I believe the key to success in this competition—beyond just improving raw model performance—is focusing on robustness. In other words, our goal should be to minimize the "shake" and ensure the model generalizes well to the private data.
P.S. We are looking for teammates! If you are passionate about LLMs or interested in translation tasks, let’s team up! Please feel free to reach out.
Happy Kaggling!
Reply
8add_reaction
This comment has been deleted.
Jack
Posted a month ago
·  19th in this Competition
2
more_vert
Currently, I suspect that your scores on the Public LB might be underfitting.
Reply
React
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
AARON BORNSTEIN ·  34TH IN THIS COMPETITION ·  POSTED 2 MONTHS AGO
42
more_vert
Probing the Best Leaderboard Public Models
I’ve been digging into the high-scoring baseline models (34+ LB) with a systematic probing framework I developed to understand the strengths and weaknesses of these models.
I wanted to share some evidence suggesting we might be seriously overfitting to the public leaderboard. After running 104 paired perturbation probes, my analysis shows the best ByT5 models are effectively functioning as a sophisticated pattern matchers (~60% translation, ~40% memorization) rather than a general translator. 
While they handle negation and numbers perfectly, the best public models fail on many isolated vocabulary and often fail to successfully copies novel proper names, hallucinating generic trade sentences around single words like "Disregard that an unclean man…". 
This strongly suggests the model is exploiting corpus-specific templates rather than learning core semantics, it's important to note that high scores on the visible 33% of the test set are likely to degrade significantly on the hidden 67% if they are out of domain.
Sharing the notebook below hope these probes can help identitfy new techniques for generalizing the models beyond data cleaning tricks.
https://www.kaggle.com/code/aaronbornstein/probing-leader-board-overfitting-34-baseline
24add_reaction
6 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Musa Peker
Posted 2 months ago
·  38th in this Competition
13
more_vert
This is a brilliant and devastating analysis. It confirms exactly what I've been experiencing in my latest experiments. I want to share a concrete example that validates your "Pattern Matcher vs. Translator" hypothesis.
I analyzed two distinct models:
Model A (The Parrot):
* Method: Standard ByT5 with aggressive gap-filling regex.
* Behavior: It hallucinates standard phrases like "The City," "Silver," and "Merchant" to fill gaps. It often repeats n-grams.
* Public LB Score: 34.2
Examples: id,translation
* 0,"Thus Kanesh colony, say to the of our messengers, every single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single single day."
* 1,"In the tablet of the City you wrote to me in the tablet of the City. This day whoever receives the silver, Daur or Ewa, will take the colony of my colony."
Model B (The Domain Expert):
* Method: Reference-aligned training with minimal normalization, focused on semantic accuracy.
* Behavior: It correctly translates specific Old Assyrian trade terms.
* - shaddutum --> "Transport tariff" (Instead of just "silver" or "tax"), 
* - emārum ṣalmum --> "Black donkey" (Instead of just "donkey" or "goods")
* - wabartum --> "Affiliated trading station" (Instead of leaving it as "Wabartum")
* Public LB Score: 11.8 (!)
Examples: id,translation
* 0,From the Kanesh colony to a merchant: In accordance with our instructions we have seized us for an expense of black donkey.
* 1,In accordance with our instructions we have received the silver on behalf of a merchant.
The current Public LB metric (BLEU/CHRF) seems to heavily penalize Semantic Fidelity (Model B) while rewarding Structural Conformity (Model A).
When Model B translates shaddutum as "transport tariff," it likely gets a 0 score for that n-gram if the reference translation uses a generic term like "tax" or "silver." meanwhile, Model A gets points for simply outputting the most statistically probable words ("silver", "give", "city"), even if the sentence meaning is hallucinated.
Your probing framework proves that we are optimizing for a metric that measures "Vibes" rather than "Translation." As you suggested, this creates a massive risk for the Private LB (hidden 67%), where out-of-distribution texts will likely break the pattern-matching models (Model A), while the semantically grounded models (Model B) should theoretically perform better.
Thank you for providing the tools to diagnose this "Metric Trap."
Reply
12add_reaction
Aaron Bornstein
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
3
more_vert
I agree I’m starting to think that some of the gains from data cleaning are also misleading they are essentially minimizing the false positive character match rate on the test distribution but not necessarily increasing the quality of the translations.
Reply
React
John Doge
Posted 2 months ago
11
more_vert
BLEU is simply not suitable for this task. Private LB can also be OOD in many ways, there is no guarantee that a semantically grounded model will perform better under metrics like this. The hosts should consider replacing BLEU with BLEURT - there is still enough time.
Reply
1add_reaction
Aaron Bornstein
TOPIC AUTHOR
Posted 2 months ago
·  34th in this Competition
0
more_vert
@deeppast
Reply
React
hongan
Posted 2 months ago
·  35th in this Competition
0
more_vert
Is Model B (the domain expert) a ByT5 model?
Reply
React
Musa Peker
Posted 2 months ago
·  38th in this Competition
2
more_vert
I used a ByT5-based sequence-to-sequence model with a reference-aligned preprocessing strategy. To improve robustness, I applied character-level noise augmentation and lexicon-based augmentation, along with a few additional optimization techniques during training.
EpochTraining LossValidation LossBLEUCHRFGeom Mean14.0398003.0536550.3084486.9565361.46483122.5666002.0465510.39457511.9337422.16996832.0031001.7285523.78840417.9064858.236322………………231.3508001.29217828.18071550.80050837.836420241.3471001.29000128.44143551.08675238.117981251.3457001.28975327.88627450.65861437.585635
Despite promising offline metrics, the model did not generalize well to the leaderboard evaluation, leading to lower-than-expected scores. 
Reply
4add_reaction
This comment has been deleted.
Musa Peker
Posted 2 months ago
·  38th in this Competition
2
more_vert
This approach is not sentence-aligned. Training is done on full transliteration–translation pairs, without explicit sentence or segment boundary alignment. A lexicon-based augmentation step is used to normalize or substitute source-side tokens, but this operates at the token/word level, not at the sentence or segment level. The main focus is reference-format alignment (punctuation, ellipsis, brackets, fractions) and ByT5-safe character handling, rather than semantic or sentence-level alignment.
Reply
React
hongan
Posted 2 months ago
·  35th in this Competition
1
more_vert
Thanks for your reply! Got it now
Reply
React
cswwp
Posted 23 days ago
·  939th in this Competition
0
more_vert
Great analysis on the 'Pattern Matcher' trap. I'm curious about the training stability you observed. Did you encounter significant volatility in your validation scores (e.g., BLEU/ChrF) as the model began to overfit on templates? Specifically, did you notice a correlation between a sudden jump in scores and the emergence of the 'parrot' behavior (repetitive n-grams) in your validation samples?
Reply
React
Hide replies
Soham_Deshpande
Posted 2 months ago
2
more_vert
How can we redesign evaluation metrics to reward semantic fidelity instead of superficial n-gram conformity?
Reply
React
Navneet
Posted 2 months ago
0
more_vert
High scores on the visible 33%?
Reply
React
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
MARÍLIA PRATA ·  POSTED 3 MONTHS AGO
35
more_vert
Akkadian to English: Cuneify tool, Fairseq toolkit, Python Package Akkademia and Gale-Church algorithm.
Akkadian to English with neural machine translation
Article Citation: Gutherz G, Gordin S, Sáenz L, Levy O, Berant J. Translating Akkadian to English with neural machine translation. PNAS Nexus. 2023 May 2;2(5):pgad096. doi: 10.1093/pnasnexus/pgad096. PMID: 37143863; PMCID: PMC10153418.
"Cuneiform is one of the earliest writing systems in recorded human history (ca. 3,400 BCE–75 CE). Hundreds of thousands of such texts were found over the last two centuries, most of which are written in Sumerian and Akkadian. The authors show the high potential in assisting scholars and interested laypeople alike, by using natural language processing (NLP) methods such as convolutional neural networks (CNN), to automatically translate Akkadian from cuneiform Unicode glyphs directly to English (C2E: Cuneiform to English Task) and from transliteration to English (T2E: Transliteration to English Task)."
"The authors showed that high-quality translations can be obtained when translating directly from cuneiform to English, as they got 36.52 and 37.47 Best Bilingual Evaluation Understudy 4 (BLEU4) scores for C2E (Cuneiform to English Task) and T2E (Transliteration to English Task), respectively. For C2E, their model was better than the translation memory baseline in 9.43, and for T2E, the difference was even higher and stands at 13.96. The model achieves best results in short- and medium-length sentences (c. 118 or less characters)."
"For the purposes of C2E, the signs of each text were encoded as strings of Unicode cuneiform glyphs generated by the Cuneify tool."
"For the Cuneiform script (C2E), the authors used character-based tokenization with a small vocabulary of characters. For transliteration (T2E), they used BytePair Encoding (BPE) with the SentencePiece package, where the size of the vocabulary for the transliteration and English was set to 1,000 and 10,000, respectively."
Fairseq toolkit
"The authors used Fairseq. Fairseq is a sequence modeling toolkit that allows researchers and developers to train custom models for translation, summarization, language modeling, and other text generation tasks.'
"The best results overall were to be found in the short- and middle-length sentences. Longer sources produced more hallucinations or missing translations in the NMT results. This is promising for the usage in realistic scenarios, since all cuneiform texts are divided into manageable lines on the clay tablet."
"The number of characters on an inscribed clay tablet can vary from period to period (signs in the **Old Babylonian period **are bigger than in the Neo-Babylonian period) and from genre to genre. Also, the number of columns by which a tablet is divided will determine the number of characters. Even in a single tablet, the number can vary to fill the space in the line."
"The usage of standard sentence aligners such as the Gale–Church algorithm can be considered as a first step of the process to handle the alignment problem of the data set."
Python Package Akkademia (Akkadian)
"The input data for C2E could originate from already existing OCR tools in the Babylonian Engine (CuRe Demo and Decuneify), which would even allow a layperson to produce an NMT with the online notebook accompanying that publication, as well as part of the python package Akkademia (Akkadian)."
https://pmc.ncbi.nlm.nih.gov/articles/PMC10153418/
https://github.com/cdli-gh/Machine-Translation
https://github.com/gaigutherz/Akkademia
6add_reaction
5 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Aaron Bornstein
Posted 2 months ago
·  34th in this Competition
1
more_vert
One thing to note is that Gale–Church algorithm relies on the sentence length ratio of the sequences for alignment this does not transfer well to morphologically rich Semitic languages like Akkadian take a look at the descriptive stats below from the train set if you use Gale–Church you are likely to get very noisy alignments.
| | | |Character-length statistics |Akkadian transliteration |English translation |Mean |~426 chars |~500 chars |Std dev |~270 |~466 |Min | 21 |6 |Max |932 |3,895 | | |
Reply
1add_reaction
Marília Prata
TOPIC AUTHOR
Posted 2 months ago
1
more_vert
Thank you for this additional information Bornstein. I've just reproduced what I read on that article:https://pmc.ncbi.nlm.nih.gov/articles/PMC10153418/
Reply
React
Navneet
Posted 3 months ago
1
more_vert
Thank you for the best Bilingual Evaluation Understudy 4 (BLEU4) scores @mpwolke
Reply
1add_reaction
Adam Anderson
COMPETITION HOST
Posted 3 months ago
1
more_vert
Yes, the Akkademia repo is a benchmark MT study for Neo-Assyrian texts (ca 911–612 BCE). Note that the time period here is about 1000 years later from the Old Assyrian period (ca. 1950-1750 BCE). It would be a mistake to assume these two different textual datasets contain the very same language usage, in terms of genre and register. 
Reply
React
Marília Prata
TOPIC AUTHOR
Posted 3 months ago
0
more_vert
Indeed DeepPast,
I didn't assume that both periods are equal just because the Assyrian word. Languages are dynamic and subject to changes. We see Portugal/portuguese and Brazilian(my country) "only" in 500 years we notice many modifications. Imagine these Assyrian (Old and Neo) during One thousand years how far could their language have evolved.
What I really assume is, that I'm not able to translate any of them Assyrian, Sumerian, Amorite, Babylonian.
Any way, I tried to use python Akkadian on my Kaggle Notebook, unfortunately it resulted in:
!pip install akkadian
"No module named 'allennlp'" after I ran
import akkadian.transliterate as akk
print(akk.transliterate("𒁹𒀭𒌍𒋀𒈨𒌍𒌷𒁀"))
Which was a pity cause it would be a nice experience.
Thank you.
Marília Prata.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 3 months ago
3
more_vert
Good to hear you're considering the time difference, just making sure. I worked on replicating this workflow in a jupyter notebook, perhaps that will be useful, but it still requires some tinkering… https://github.com/ancient-world-citation-analysis/EvaCun-Colab-Notebook
Reply
React
Marília Prata
TOPIC AUTHOR
Posted 3 months ago
0
more_vert
I'll try to run them in a Private Notebook. Due to my poor knowledge, only when I read the outcomes I'd be able to get it. 
Then, I'll try to understand the EvaCun: ORACC Akkadian Parallel Corpus
I've checked some of the FactGrid Cuneiform: e. g. akkadian_train.txt. 
Thank you.
Reply
React
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
MANWITHACAT ·  903RD IN THIS COMPETITION ·  POSTED 3 MONTHS AGO
30
more_vert
Other Public Data
This might be useful:
https://www.kaggle.com/datasets/manwithacat/oracc-akkadian-english-parallel-corpus
I’m sharing ORACC Akkadian–English Parallel Corpus with the community as a clean, ready-to-use set of aligned Akkadian transliteration → English pairs extracted from ORACC. The material here is drawn from major ORACC projects focused on royal inscriptions and state/administrative archives (RIAo, RINAP, RIBo, SAAo), so it is not a purpose-built corpus of Old Assyrian / Old Akkadian merchant records. In other words: this dataset is best treated as a broad, high-quality Akkadian–English parallel resource—particularly relevant to Neo-Assyrian / Neo-Babylonian-style language and genres—useful for pretraining, baseline NMT, alignment experiments, and tooling, rather than a direct proxy for the Kaneš trade letters.
ORACC Akkadian–English Parallel Corpus
This dataset contains parallel pairs of Akkadian transliteration (source) and English translation (target), extracted and aligned from the Open Richly Annotated Cuneiform Corpus (ORACC).
Source Projects
RIAo (Royal Inscriptions of Assyria online): Assyrian royal inscriptions ~2500-609 BCE RINAP (Royal Inscriptions of the Neo-Assyrian Period): Neo-Assyrian royal texts 744-609 BCE RIBo (Royal Inscriptions of Babylonia online): Babylonian royal inscriptions ~2500-539 BCE SAAo (State Archives of Assyria online): Letters and administrative texts 911-612 BCE
React
4 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Adam Anderson
COMPETITION HOST
Posted 5 days ago
2
more_vert
I should mention, there is a very large corpus of Oracc texts which I provided in a zenodo repository here as well (https://zenodo.org/records/10794626). That said, the same warnings apply here. These include many different genres and languages, and almost none of them are Old Assyrian texts. Use at your own risk.
Reply
1add_reaction
Adam Anderson
COMPETITION HOST
Posted 5 days ago
2
more_vert
This website that is much more aligned in terms of time period (Old Babylonian): https://archibab.fr/textes?trloo=false&dmin=2020&dmax=0&o=ref,id&page=1&size=25&count=32625
Reply
1add_reaction
Adam Anderson
COMPETITION HOST
Posted 3 months ago
8
more_vert
How very resourceful you are. As a matter of fact, I am quite familiar with this dataset, and I would urge caution in using it, mainly because these texts from Oracc are very different from the Old Assyrian archives, in terms of time period and genre. First, there are no other Old Assyrian texts in the Oracc data, and only very few texts of a contemporary time period. The vast majority of these texts are from the first millennium, and therefore are about 1000 years later in time, which makes a huge impact on the use of the language. Second, we found in using this dataset that there were a large number of lexical lists, which were used in antiquity to record Akkadian to Sumerian equivalencies. Many of these lexical lists are also quite late (i.e. Late Babylonian), and therefore they will contain words which have no bearing on the Old Assyrian texts or the ways in which they wrote / spoke. 
I understand that it is desirable to find as much data as possible for this challenge, but consider this. If you were building a Machine Translation model for modern English, would you also include Middle English texts, or maybe Old English lexicons? Probably not, but that's just my point of view.
Reply
React
manwithacat
TOPIC AUTHOR
Posted 3 months ago
·  903rd in this Competition
1
more_vert
I felt it was the least worst option available to try and add something to my model that was vaguely Akkadian. I suppose using your analogy if I was trying to build a machine translation model for modern English and all I had was middle English then maybe I could at least extract some nouns or names or guess at some grammar rules from it.
Sumer Is Icumen In…
Reply
React
Adam Anderson
COMPETITION HOST
Posted 3 months ago
2
more_vert
I understand, in fact I tried this myself. I found that the genre is lost / muddled in translation by including all of this royal inscription text. Some words are generic enough that they are used in many different contexts, so when there's a bunch of examples from the first millennium of words with contexts like kings, conquests, priests, sacrifices, and the like, it creates a very different vector for words which in Old Assyrian are used with economic contexts (almost exclusively). To put it in another way, the sentence in Old Assyrian: "he should send the money to me, and I will pay the tax", under the influence of Neo-Assyrian or Neo-Babylonian royal inscriptions might come out as "he shall send me the tithes, and I will make an offering". This is a made up example, but it is very apparent in the AICC translations from 2023 of the CDLI (https://aicuneiform.com/).
Reply
4add_reaction
manwithacat
TOPIC AUTHOR
Posted 3 months ago
·  903rd in this Competition
0
more_vert
Out of interest , I’ve got a plan and I’m wondering if I’m covering territory that’s already been tried before :
I’m proposing to try, very explicitly as an experimental modelling convenience rather than a claim about historical phonology, to introduce a parallel, highly normalised representation of the Akkadian input in which syllabic spellings are partially collapsed toward an abstract consonantal layer—either by stripping vowels entirely or by mapping consonants onto coarse articulatory classes (e.g. labial, dental/alveolar, sibilant, guttural)—and to feed this alongside the original transliteration rather than in place of it. 
I’m not sure if that’s a silly idea or not, but I’m thinking cuneiform writing system might (does?) encode phonemic material in a deliberately lossy, syllabic way which creates extreme “surface variability” over underlying lexical and morphological regularities a model would ideally learn.
Anyway, worst case scenario, I burn a few GPU hours testing it out.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 3 months ago
0
more_vert
That is not a silly idea at all, in fact it makes good sense when you consider how tokenization works. The hyphens certainly pose an issue for subword tokenization, so normalizing the transliteration could be a good work-around for getting a better tokenization, and perhaps better embeddings too, depending on the size of the model.
Reply
React
jofatmofn
Posted 2 months ago
0
more_vert
I’m proposing to try, very explicitly as an experimental modelling convenience rather than a claim about historical phonology, to introduce a parallel, highly normalised representation of the Akkadian input in which syllabic spellings are partially collapsed toward an abstract consonantal layer—either by stripping vowels entirely or by mapping consonants onto coarse articulatory classes (e.g. labial, dental/alveolar, sibilant, guttural)—and to feed this alongside the original transliteration rather than in place of it. 
@manwithacat, is this normalized transliteration idea related to your thought of using ORACC royal inscriptions and state/administrative archives as data?
Reply
React
manwithacat
TOPIC AUTHOR
Posted 2 months ago
·  903rd in this Competition
0
more_vert
It was, but as the competition host noted above there’s a lot that is lost in translation. Also by their nature these types of inscriptions/proclamations are repetitive which is kind of counter-productive for model training.
My best score is currently using the public model trained by @jeanjean111
Reply
React
Hide replies
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
ANIL OZTURK ·  264TH IN THIS COMPETITION ·  POSTED 2 MONTHS AGO
24
more_vert
Formatting of the Hidden Test Set
Does the hidden test follow the suggested formattings you provided? (like < gap > for ground truth translations, transforming subscript to normal digits for transliterations etc.)
122add_reaction
5 Comments
1 appreciation comment
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Adam Anderson
COMPETITION HOST
Posted 2 months ago
5
more_vert
yes, the hidden test follows these formats < gap > for one signs missing (e.g., x or [x]) and < big_gap > for multiple signs missing (e.g. [x x] […] x x x … …) — Note that I added spaces around the pointy brackets and the words 'gap' and 'big_gap' here, because otherwise they are not displayed in this viewer.
Reply
React
Jack
Posted 2 months ago
·  19th in this Competition
0
more_vert
This knowledge might bump my score a bit since I trained a model that outputs … time to find out! 
Edit: nope!?
Reply
1add_reaction
Anil Ozturk
TOPIC AUTHOR
Posted 2 months ago
·  264th in this Competition
4
more_vert
Thanks! Another one:
Should we expect {tug₂} or (TÚG) in the given test set? The train has it as (TÚG) like a third form, which transformation should I do? Some parts of the legend has the raw text on the left side and the transformed states on the right, but the last part of the legend seems the opposite. I'm really confused.
Reply
React
MPWARE
Posted 2 months ago
·  61st in this Competition
2
more_vert
Same for (d) and {d}
See: https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/664177#3381788
We can normalize it what ever the enclosing characters if we don't get an answer.
I'm surprised to learn that gap / big_gap is already available in test set (I don't see it in the data description).
Reply
React
Anil Ozturk
TOPIC AUTHOR
Posted 2 months ago
·  264th in this Competition
5
more_vert
gap, big gap conversion just give me a big jump (~+6) today… We need way more clearer definitions about the test set. A bunch of example translations formatted like the test set would be a good reference.
Reply
11add_reaction
Jack
Posted 2 months ago
·  19th in this Competition
2
more_vert
Anil, are you formatting just the transliteration? I trained and predicted with the replacement and got worse performance.. My ideas are clearly right but the implementation is definitely wrong 😭 This is my first text-based competition so it is what it is… Also, if you join train.csv with published_texts.csv you can get transliterations with brackets, < big gap >, etc. @mpware
Reply
React
Anil Ozturk
TOPIC AUTHOR
Posted 2 months ago
·  264th in this Competition
1
more_vert
yep, just transliteration
Reply
11add_reaction
耶✌
Posted 2 months ago
·  34th in this Competition
0
more_vert
lol，I've been through the same thing.
Reply
React
Jack
Posted 2 months ago
·  19th in this Competition
0
more_vert
You must not be using byt5, right? I’m going to try some other stuff once I’m on my home pc… no gpu hours on kaggle and I’m traveling for the holidays. 
Reply
React
This comment has been deleted.
This comment has been deleted.
QianYuu
Posted 2 months ago
·  163rd in this Competition
0
more_vert
@jackvd Did you use the published_texts data after merging? Did the training process show any improvement?
Reply
React
This comment has been deleted.
Jack
Posted 2 months ago
·  19th in this Competition
0
more_vert
@qianyuu No, I'm working on my preprocessing while going through all the training pairs. There's a lot of weirdness that I'm planning on making a discussion post about if Anil or someone else doesn't beat me to it.. it's important to know if it exists in the hidden test and without any clarification on that we're just throwing darts a bit
Reply
React
Adam Anderson
COMPETITION HOST
Posted 2 months ago
2
more_vert
Expect TÚG, it is rarely in brackets in the Old Assyrian texts. It is usually written by itself TÚG or in plural form TÚG.HI.A
Reply
1add_reaction
Hide replies
Navneet
Posted 2 months ago
0
more_vert
Subscript to normal digits for transliterations? @jackvd
Reply
React
Appreciation (1)
Irakoze Ntawigenga Kelly
Posted 2 months ago
0
more_vert
learnt from this question, thanks!
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
DAYLIGHTH ·  30TH IN THIS COMPETITION ·  POSTED 11 DAYS AGO
23
more_vert
Is this competition becoming a 'Regex Guessing Game'?
I recently noticed this discussion about the dataset update. While I am genuinely grateful to the Kaggle staff and the host for their continuous efforts to improve the data quality, I must admit I am starting to lose motivation and feel a bit exhausted by this process… Even after the recent updates, the dataset still lacks a fully unified and consistent standard.
I joined this competition to focus my energy on trying new LLM/Seq2Seq strategies, experimenting with advanced NMT training methods, and learning meaningful domain knowledge from both the host and other competitors. Instead, I find myself spending massive amounts of time reading discussion threads just to bridge the information gap, and writing endless Regex pipelines to guess the correct data format. 
21add_reaction
4 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
tucking_fired
Posted 11 days ago
·  1312th in this Competition
4
more_vert
I agree, and there is too much confusion on how the data in the actual dataset is. Its just a guessing game right now
Reply
11add_reaction
epikt
Posted 10 days ago
·  28th in this Competition
2
more_vert
The latest post makes the formatting very clear for everyone, so that's good. But there is a lot to learn from this competition about data cleaning and dataset building, so I'm not sure why it would make you lose motivation. In real life situations, you are often handled a bunch of terrible files to work with, it's just how it is. The organizer does the best they can with what they have, and there is a lot to learn from working with this data. Making it all work is part of the challenge. Just keep at it.
Edit - re: 'The latest post makes the formatting very clear for everyone', after having re-read it I might have been too quick.
Reply
React
DaylightH
TOPIC AUTHOR
Posted 10 days ago
·  30th in this Competition
6
more_vert
Hi @epikt,
Thank you for reading my post and sharing a rational perspective!
In real life situations, you are often handled a bunch of terrible files to work with, it's just how it is.
You are right. Real-world data is often terribly formatted. However, in reality, you can agree on a unified target output with your boss. This gives you a clear direction when cleaning the data. For example, you know to filter out samples with inappropriate lengths, remove outliers, or prepend specific prompts to the model input.
The problem here is that the "direction" of this competition has been entirely uncertain. It was only "finalized" a few hours ago, and we still might need to wait for further clarifications from the host. For instance, whether a fraction should be formatted as 0.3333 or 1/3 has absolutely nothing to do with a model's actual translation ability. What can we learn from this specific formatting toggle? To be more precise, at this point, it feels less like data cleaning and more like reverse engineering.
the organizer does the best they can with what they have,
I completely understand that, but I feel it would have been much better to explicitly define the expected target data format at the very beginning of the competition. I am sure many participants have already invested significant GPU resources and time into this. If the Ground Truth keeps shifting, that money and time are essentially wasted.
Regardless, I really appreciate your encouragement. Best of luck to you in the competition!😀
Reply
React
epikt
Posted 10 days ago
·  28th in this Competition
0
more_vert
The changes in the ground truth data do force us to readjust, but I think that on the opposite, it has the accidental benefit of limiting the usefulness of leaderboard probing, which has been an issue with some past competitions. Probing is its own skill, but it's no fun trying to compete when the top n scores are all there just because they found a way to exploit the metric by probing constantly since day 1. If these are the two choices, as long as they remain reasonable and not too last minute, I'll take the small changes along the way.
Reply
React
Oleg Yaroshevskiy
Posted 10 days ago
·  40th in this Competition
4
more_vert
The latest post makes the formatting very clear for everyone
IMHO quite the opposite, we've seen 3 different train.csv with different formatting and now it's more confusing than before
Reply
1add_reaction
epikt
Posted 10 days ago
·  28th in this Competition
1
more_vert
You're right, after having read through the post more carefully carefully, it does bring as many new questions as it answers. In any case, I've been enjoying this competition, so I just hope this it stays fun. It's true though that with just about 20 days to go it should be the time for the instructions to be clear.
Reply
React
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
ADAM ANDERSON ·  POSTED 11 DAYS AGO
· COMPETITION HOST
30
more_vert
A Stitch in Time Saves Nine
If only the ancients who wrote these texts could imagine how difficult it would be to train computers to translate their work! Working with data from 1950-1750 BCE is not for the faint of heart. From 1927 CE until today, modern scholars have been working with the editing and publication of these ca. 8,000 documents in many different languages, and despite (or because of) almost 100 years of scholarly scrutiny, the datasets are more complicated and in a more convoluted format, than what the ancients originally wrote. These editions were migrated into a database, which became the foundation of the data we used for the training and supplemental data for this challenge. Unbeknownst to them, we are now re-purposing their editions for training ML models, and the messiness of the data is palpable for all to see. That said, this is the first benchmark for a significant ML application with the Old Assyrian data, so with great struggle comes greater pioneering outcomes.
The purpose of this final update is to level the number of markers for gaps from two to one. The hope is that by making some small, but significant adjustments, this will improve the scores for everyone. What we refrained from doing was making any additional changes which could introduce new inconsistencies if not done uniformly. So for the final month of the competition, we will include a clear and concise list of recommendations for the training dataset for alignment with the test data.
Gap Change: Replaced all the following with a single <gap>
* x —> <gap>
* [x] —> <gap>
* … —> <gap>
* (break) —> <gap>
* (large break) —> <gap>
* (n broken lines) —> <gap>
* <gap> <gap> —> <gap>
Results of these changes: no more <big_gap> and no more duplicates for <gap> Before the change took place, these types of gaps were found in the test and training data. This recent change reduced all these duplicates to a single <gap>.
GapCount<gap> <gap>30-<gap> <gap>9-<gap>-<gap>1<gap> <gap>-15<gap> <big_gap>6<gap> <gap> <gap>2<gap> <big_gap> <gap>1-<big_gap> <gap>-4-<big_gap> <big_gap>13<big_gap> <big_gap>15<big_gap> <big_gap>-12<big_gap> <gap> <big_gap>2<big_gap> <big_gap> <big_gap> <big_gap>-3<big_gap> <big_gap> <big_gap> <gap> <gap>1-<big_gap> <big_gap> <gap> <big_gap> <big_gap>-1
Alignment of Determinatives to match test data:
* (d) —> {d}
* (ki) —> {ki}
* (TÚG) —> TÚG
Shortening of long floats to four places after the decimal
* 1.3333300000000001 —> 1.3333
* 2.6666600000000003 —> 2.6666
The rest is up to you. Here are some recommendations, but there's no guarantee that these will improve your score on the leader board:
Some of the transliteration text in the training data is missing, which is unfortunate, but fixable. You can find what is missing from the training data by matching the unique OARE_Text_ID with the equivalent OARE IDs in the published_texts.csv dataset. Do this by matching the unique IDs in the training data to the OARE IDs and find the publication (e.g. AKT 8, 130 = AKT volume 8, text number 130). The PDFs have also been provided, if you find there are missing elements in the translations (https://www.kaggle.com/datasets/deeppast/old-assyrian-kltepe-tablets-in-pdf/data).
Here are some recommended options for changes to the training data:
Remove from translations:
* fem.
* sing.
* pl.
* plural
* (?)
* any stray marks you find (e.g., .., ?, x, xx, << >>, < > except around <gap> of course)
* some of the translations equivocate two optional translations using /, it might be better to choose one or the other options provided, rather than including both with a / (e.g. "you / she brought" —> "you brought" ).
Do not remove from translations (as these are in the test too):
* quotation marks " "
* apostrophes '
* meaningful question marks ? or exclamation marks !
Replace in translations:
* PN —> <gap>
* -gold —> pašallum gold
* -tax —> šadduātum tax
* -textiles —> kutānum textiles
* 1 / 12 (shekel) —> 15 grains
* 5 / 12 shekel —> ⅓ shekel 15 grains
* 5 11 / 12 shekels —> 6 shekels less 15 grains
* 7 / 12 shekel —> ½ shekel 15 grains
Decimals to Fractions:
* 0.5 —> ½
* 0.25 —> ¼
* 0.3333 —> ⅓
* 0.8333 —> ⅚
* 0.625 —> ⅝
* 0.6666 —> ⅔
* 0.75 —>  ¾
* 0.1666 —> ⅙
Change Roman numerals to integer numbers for months: e.g., month V —> month 5
MonthRomanMNformsAKAMonth 1IBēlat ekallembe-el-tí-É.GAL-lim; be-el-té-kà-limBēlat-ekallimMonth 2IIša-sarratimša sá-ra-timMonth 3IIIKenātimke-na-timša kēnātimMonth 4IVMahur-ilīMa-hu-ur-DINGIR; ma-ḫu-ur-ì-líMonth 5VAbšarraniáb-ša-ra-ni; áb ša-ra-ni; áb-ša-ra-nuab šarrāni; abšarraniMonth 6VIHuburHu-bu-urMonth 7VIIṢip'umṣí-ip-imṣipumMonth 8VIIIQarrātumqá-ra-a-tí; qá-ra-a-timMonth 9IXKanwartakán-bar-ta; Kà-an-ma-ar-taKanmartaMonth 10XTe’inātumté-i-na-timMonth 11XIKuzallumku-zal-li; ku-zal-luMonth 12XIIAllanātuma-lá-na-tum; a-lá-na-tim
Optional changes in transliterations:
* Ḫ → H
* ḫ → h
* KÙ.B. —> KÙ.BABBAR
Change unicode subscript numbers to normal integers in transliterations:
* ₀ → 0
* ₁ → 1
* ₂ → 2
* ₃ → 3
* ₄ → 4
* ₅ → 5
* ₆ → 6
* ₇ → 7
* ₈ → 8
* ₉ → 9
Decimals to Fractions for transliterations:
* 0.5 —> ½
* 0.25 —> ¼
* 0.3333 —> ⅓
* 0.8333 —> ⅚
* 0.625 —> ⅝
* 0.6666 —> ⅔
* 0.75 —>  ¾
* 0.1666 —> ⅙
Examples of the Outcomes for Test
TransliterationTranslation1 e-ma-ar-šu <gap>1 donkey of his <gap><gap> a-na Ú-<gap> a-dí-in<gap> I gave it to U-<gap>.<gap> ⅓ ma-na a-na En-na-nim DUMU Am-ri-a áš-qúlI paid <gap> ⅓ mina (silver) to Ennānum, son of Amriya.
Examples of the Optimal Outcomes for Train
TransliterationTranslation<gap> ma-na KÙ.BABBAR ṣa-ru-pá-am <gap> GÍN KÙ.GI pá-ša-lam<gap> minas of refined silver, <gap> shekels of pašallum gold<gap> GÚ SÍG.HI.A <gap> 5 maš-ku <gap> 22 na-ru-qá-tum 4 ANŠE ṣa-la-mu<gap> talents of wool, <gap> 5 hides, <gap> 22 sacks, 4 black donkeys⅓ ma-na 2 ½ GÍN KÙ.BABBAR 20 NINDA i-ṣé-er tù-wa-ra-a-ah-šu a-lá-hu-um i-šuTuwar-ahšu owes ⅓ mina 2 ½ shekels of silver (and) 20 loaves of bread to Ali-ahum.
11add_reaction
42 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Pinned comments
Ryan Holbrook
KAGGLE STAFF
Posted 10 days ago
2
more_vert
The updated data is now live on the site. I will commence the rescore of existing submissions shortly.
UPDATE 02/26/2026: The rescore is now complete. Please let us know if you have any questions or concerns.
Reply
React
Jack
Posted 10 days ago
·  19th in this Competition
2
more_vert
rip scores
Reply
9add_reaction
Anil Ozturk
Posted 10 days ago
·  264th in this Competition
1
more_vert
Our score on LB is 34.1 but the best scoring sub in our sub history seems to be 33.5. I don't understand. 😅
Reply
React
Ryan Holbrook
KAGGLE STAFF
Posted 10 days ago
4
more_vert
Hi @nlztrk,
Something seems to have gone wrong with the LB update. We are investigating.
Reply
React
Mattia Angeli
Posted 9 days ago
·  35th in this Competition
0
more_vert
Also the scores of some  public NBs have not been updated
Reply
React
guoqin gu
Posted 9 days ago
·  5th in this Competition
0
more_vert
Hi, my LB rank changed again (40+->30+) after rerun, is there new update?
Reply
React
This comment has been deleted.
Jack
Posted 8 days ago
·  19th in this Competition
1
more_vert
Any update on this?
Reply
React
Ryan Holbrook
KAGGLE STAFF
Posted 6 days ago
0
more_vert
I recalculated the leaderboard based on the rescore. It should be up to date now. Are you still seeing out of date scores?
Reply
React
Hide replies
chenwenqiang_001
Posted 9 days ago
·  37th in this Competition
0
more_vert
transliteration:2- translation: 2+ or 2- translation of test is 2- or 2+ or 2(+gap) ??? please let me know.thank you 
Reply
React
All other comments
Kh0a
Posted 5 days ago
·  34th in this Competition
1
more_vert
question about (n broken lines), do the lines between "Nimar-Istar." and "When he returns from Mamma he will bring it to me" counts as n broken lines?
If I understand correctly, the translation should be:
I furthermore gave 1 mina of good, native copper for an allu’āru-container of sweet wine from Mamma to Puzur-Amurrum son of Nimar-Ištar. <gap> When he returns from Mamma he will bring it to me. (This was) apart from the 4 allu’āru-containers, the proceeds from the silver and washed copper that they have received (previously). Witnessed by Šu-Bēlum son of Kuzizia.

Reply
React
Ricardo Pérez
Posted 6 days ago
6
more_vert
Thanks for the comprehensive update and all the clarifications in the comments. After applying the v3 changes, a few things that helped on my end:
Recovering truncated transliterations: Confirmed that ~10% are affected. Matching oare_id against published_texts.csv and cross-referencing with the AKT PDFs recovered most of them. Be careful, though, some entries aren't just truncated; the translation doesn't match the transliteration at all (as MPWARE pointed out for AKT 8, 55), so it's worth doing a length-ratio sanity check before blindly patching.
The -textiles / -gold / -tax replacements: Based on the host's clarification, these only apply when preceded by a space (i.e., -textiles to kutānum textiles), not in the middle of a word, like import-tax or kutānu-textiles. A naive str.replace will break things, regex with word boundaries or explicit space matching is safer here.
Straight quotes: Curly quotes to straight quotes for both " and '. Small thing, but easy to miss if your text editor or PDF extraction reintroduces curly ones.
Still working through the fraction conversions and subscript normalization. Good luck to everyone in the final stretch!
Reply
React
FX-6300
Posted 8 days ago
·  282nd in this Competition
3
more_vert
It looks like the “Change Roman numerals to integer numbers for months” table is misaligned/broken: Month 2 is labeled as Roman III, and III appears twice. 
According to Kouwenberg (Introduction to Old Assyrian, p. 182), the Old Assyrian calendar starts with Month 1 = I (Bēlat ekallem/Bēltekallem), followed by Month 2 = II (ša sarrātim) and Month 3 = III (ša kēnātim). Could you add Month 1 and shift/correct the Roman numerals accordingly?
Reply
2add_reaction
MPWARE
Posted 10 days ago
·  61st in this Competition
12
more_vert
@deeppast Thanks for the update. Some clarification to be 101% sure:
About double quotes:
Do not remove from translations (as these are in the test too):
quotation marks " "
In the previous update:
quotations " “= removed
The final rule is keep all quotation marks, correct? And for curly double quotes, we have to convert them to plain double quotes or not?
About parentheses:
In the previous update:
parentheses ( )= removed
Now, we need to keep parenthesis as for the examples outcomes you've provided, right?
For instance: 0faa50f7-b86c-466c-a8ab-3a6f48fcb00a
"at 52.5 grains (of silver) each, 0.5 shekel" we must keep the parenthesis around of silver, right?
We must not do: "at 52.5 grains of silver each, 0.5 shekel"
About replacements:
-tax —> šadduātum tax
-gold —> pašallum gold
textiles —> kutānum textiles (are you sure it's not -textiles —> kutānum textiles )?
And it's textiles and -tax and -gold surrounded by spaces? If not then in 198e428d-f51b-40d1-96d8-aee4bfa60d8d:
"of Ennam-Suen, 8 textiles as import-tax, 10 textiles are pre-emption" 
would become: 
"of Ennam-Suen, 8 kutānum textiles as importšadduātum tax, 10 kutānum textiles are pre-emption". 
and it 229be03b-c772-4a6c-8792-c3f80948a97d:
"received 28 kutānu-textiles and 1 black donkey"
would become: 
"received 28 kutānu-kutānum textiles and 1 black donkey"
Which would look weird, please confirm.
About <gap>:
In previous update:
added space around gap in translations (not transliterations)
Is it still true? Do we need to add space around <gap> except if glued with a dash?
Reply
React
Oleg Yaroshevskiy
Posted 9 days ago
·  40th in this Competition
3
more_vert
the questions about quotes and parentheses are extremely important
Reply
React
Adam Anderson
COMPETITION HOST
Posted 8 days ago
4
more_vert
Yes, keep parentheses and quotations should be dead quotes, no curl, same for apostrophes / scare quotes.
Do not remove from translations (as these are in the test too): quotation marks " " apostrophes ' meaningful question marks ? or exclamation marks !
As for the words which begin with -: words which appear with an initial hyphen have a space before them, rather than those words which are joined to another word with a hyphen. These suggestions are meant to provide some context for the missing words, but the only way to know for sure is to check in the PDFs, which is why they were not replaced in v3. These missing parts were removed in the OARE database, and should be replaced in an ideal situation by checking the PDFs.
* -gold —> pašallum gold
* -tax —> šadduātum tax
* -textiles —> kutānum textiles
Reply
React
MPWARE
Posted 8 days ago
·  61st in this Competition
1
more_vert
I'm trying to identify the mapping between oare_id in train.csv and the AKT PDF in order to complete broken sections, I've found 1561 matches:
* AKT 5 = 77 oare_id 
* AKT 6a = 304 oare_id
* AKT 6b = 222 oare_id
* AKT 6c = 201 oare_id
* AKT 6d = 139 oare_id
* AKT 6e = 255 oare_id
* AKT 8 = 363 oare_id (e.g. 0123a9b9-e81e-4d7a-a79b-10e7c0aacbb9 Kt 91/k 471, page 213)
Someone with similar results? @jackvd You was saying around 400 items was broken?
Reply
React
Angantyr
Posted 8 days ago
4
more_vert
I have similar results with regard to AKT 5 and AKT 6a. I still have to verify a few ids to be sure but when I do I can post it in the updated train.csv dataset to make everyone lives a bit easier.
Edit: The dataset with sources included should be up and running.
PublicationpageAKT 576AKT 6a295AKT 6b218AKT 6c196AKT 6d137AKT 6e233AKT 8355
Reply
React
MPWARE
Posted 7 days ago
·  61st in this Competition
5
more_vert
I've updated my list:
pub_pd = pd.read_csv("data/published_texts.csv")  train_df = pd.read_csv("data/train.csv")  akt_pd = pub_pd[(pub_pd['oare_id'].isin(train_df["oare_id"].unique()))][["oare_id", "label", "excavation_no", "transliteration"]] akt_pd["pdf"] = akt_pd["label"].str.extract(     r"\bAKT\s+(\d+[a-zA-Z]?)",     expand=False )
pdf 5      77 6a    304 6b    222 6c    201 6d    139 6e    255 8     363
Some rows in train.csv are more than broken, the translation just does not match the transliteration at all. For instance: AKT8, 55. Kt 91/k 304 (1-161-91) oare_id: 5f088d12-ed99-434a-a113-65deab7e1426
In the PDF:
In train.csv: whatever v1,v2 or v3
After RE-OCR:
oare_ids from AKT 6e are one of the most broken.
This competition is about normalization and cleaning.
Reply
6add_reaction
Angantyr
Posted 6 days ago
0
more_vert
I wonder for how many of such cases we could employ a set match filtering, e.g., 'a-na'/'from', 'ku.babbar'/'silver', etc.
It would not be a guarantee but a first stage flag to have a manual check and there are many words that have a 1:1 equivalent with English.
Reply
React
chenwenqiang_001
Posted 10 days ago
·  37th in this Competition
7
more_vert
I think you should update these data from the beginning.Some samples from train.csv were aligned by hand. To revise these one more is really a challenging work.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 8 days ago
2
more_vert
There will be no further updates, I'm sorry.
Reply
React
Yicong XIAO
Posted 10 days ago
6
more_vert
@deeppast hihi, 
Regarding the unit conversions that you mentioned below, I suspect that the right-hand-side of the first two rows should be interchanged
1 / 12 (shekel) —> ⅔ shekel 15 grains 5 / 12 shekel —> 15 grains 5 11 / 12 shekels —> 6 shekels less 15 grains 7 / 12 shekel —> ½ shekel 15 grains
Is it that 1/12 shekel == 15 grains ?
if so, then the conversions should instead be 
1 / 12 (shekel) —> 15 grains 5 / 12 shekel —> ⅔ shekel 15 grains 5 11 / 12 shekels —> 6 shekels less 15 grains 7 / 12 shekel —> ½ shekel 15 grains
is it?
Reply
React
Adam Anderson
COMPETITION HOST
Posted 8 days ago
2
more_vert
close, 5 / 12 --> ⅓ shekel 15 grains
Reply
React
esprit
Posted 8 days ago
·  262nd in this Competition
0
more_vert
Isn't it 5 / 12 shekel —> ⅓ shekel 15 grains instead of 5 / 12 shekel —> ⅔ shekel 15 grains?
There are probably many similar mistakes in the test data.
Reply
React
Yicong XIAO
Posted 8 days ago
0
more_vert
oops nice catch you are right
Reply
React
tennogh
Posted 8 days ago
·  1649th in this Competition
1
more_vert
Regarding the terms "pašallum gold", "šadduātum tax", "kutānum textiles", those appear in different forms in the texts. Are those the forms that are expected from the test data (e.g. "kutanum-textile", "kutanu textile" -> "kutānum textiles")?
Reply
React
耶✌
Posted 8 days ago
·  34th in this Competition
3
more_vert
I don’t think that’s the case. 
First, words like pašallum, šadduātum, and kutānum do not exist in train.csv at all. 
Second, submissions that do not include words such as pašallum, šadduātum, and kutānum have achieved higher scores.
The host only seemed to suggest that we do this. :)
Reply
2add_reaction
chenwenqiang_001
Posted 8 days ago
·  37th in this Competition
1
more_vert
when i drop the '[', ['] in the train, my scores would drop. Normally, if dropping the "[" and "]" , the scores would have been improved. I don't know why it is like this.
Reply
3add_reaction
Jack
Posted 8 days ago
·  19th in this Competition
0
more_vert
In your transliterations or translations? 
Reply
React
Steve Roberts
Posted 9 days ago
·  192nd in this Competition
3
more_vert
The new update seems to have truncated the longer transliteration strings. The previous training data had the following long training entries:
indexoare_idtransliteration_lengthtranslation_length1771c428f5b-15b5-463a-8e27-f9b2f0d858fc59274664764f3382c-cb81-41af-99c9-36854585b747338588927937e71fb-57c8-46c0-afbc-48f9429886e4343537968991eef40-f139-4206-90ed-7fb45648b1974085931090adb0573b-20fb-469d-8343-0ace8e2489e03576261260c97bb594-a5a1-4674-9496-48496e91c2ee296021378dff850c8-ccd4-44a9-9994-2834ca832a6d379603
The new data has truncated these to be:
indexoare_idtransliteration_lengthtranslation_length1771c428f5b-15b5-463a-8e27-f9b2f0d858fc13873964764f3382c-cb81-41af-99c9-36854585b747107587927937e71fb-57c8-46c0-afbc-48f9429886e4114537968991eef40-f139-4206-90ed-7fb45648b1971085931090adb0573b-20fb-469d-8343-0ace8e2489e01076251377dff850c8-ccd4-44a9-9994-2834ca832a6d120585
I'm not sure if this applies to the other rows too, but it certainly seems to have lost a lot of data.
Reply
React
MPWARE
Posted 9 days ago
·  61st in this Competition
1
more_vert
Around 10% of transliterations are truncated. We've to fix that ourself according to the instructions.
Reply
React
steubk
Posted 9 days ago
·  49th in this Competition
1
more_vert
which instructions?
Reply
React
MPWARE
Posted 9 days ago
·  61st in this Competition
1
more_vert
Some of the transliteration text in the training data is missing, which is unfortunate, but fixable. You can find what is missing from the training data by matching the unique OARE_Text_ID with the equivalent OARE IDs in the published_texts.csv dataset. Do this by matching the unique IDs in the training data to the OARE IDs and find the publication (e.g. AKT 8, 130 = AKT volume 8, text number 130). The PDFs have also been provided, if you find there are missing elements in the translations (https://www.kaggle.com/datasets/deeppast/old-assyrian-kltepe-tablets-in-pdf/data).
Reply
3add_reaction
Steve Roberts
Posted 9 days ago
·  192nd in this Competition
4
more_vert
It's a bit bad though that data that was there, and which I spent a large amount of time working out how to split, has now suddenly disappeared from the data set. 
Reply
React
Yicong XIAO
Posted 8 days ago
0
more_vert
A large number of data where the ratio between the lengths of transliteration and translation seem weird have wrong/truncated transliteration/translation, e.g. 8376cbda-b423-42d4-abb5-188d04896392. Can follow the instruction to find the raw pdf and amend these data case by case.
Reply
React
epikt
Posted 10 days ago
·  28th in this Competition
6
more_vert
I am a bit confused about the table that follows 'Results of these changes: no more <big_gap>'. That table still says <gap> <gap>: 30, <gap> <big_gap>: 6, etc. Does this mean that there's till 30 occurrences of <gap> <gap>, 6 occurrences of <gap> <big_gap>, etc. in the test set?
I thought I had understood that all of the <big_gap> had been replaced by <gap> and neighboring gaps had been merged together, but I'm less certain I understand right now.
Edit: it seems that some time since this post Results of these changes: no more <big_gap> was changed to Results of these changes: no more <big_gap> and no more duplicates for <gap> Before the change took place, these types of gaps were found in the test and training data. This recent change reduced all these duplicates to a single <gap>. so it's now clearer. Thank you for the clarification!
Reply
React
hongan
Posted 10 days ago
·  35th in this Competition
0
more_vert
In this very post, i can't find any info about merging gap…
Reply
React
epikt
Posted 10 days ago
·  28th in this Competition
0
more_vert
That's what had been mentioned in last week's update:
Gaps, damage markers, and parallel alignment [update: 2/18/26]  Another recurring source of confusion concerns damaged text and gap markers in the data:      x represents a single broken sign,     sequences like x x x x or ... represent a larger lacuna.  For modeling purposes we reduced all breaks to a single marker: <gap>   we removed the tag for <big_gap> from the train and test (and other transliterations). We also deduplicated instances multiple sequential gaps (e.g. <gap> <gap, <gap>-<gap>, <gap> <gap>, <gap>. <gap>, etc.
Source: https://www.kaggle.com/competitions/deep-past-initiative-machine-translation/discussion/665209
Reply
React
hongan
Posted 10 days ago
·  35th in this Competition
2
more_vert
thanks, i'm aware, just thought this post is a comprehensive summary of all the changes, which apparently is not…
Reply
React
steubk
Posted 10 days ago
·  49th in this Competition
1
more_vert
just for the record, this update does not include all the changes made in the previous update For example unicode subscript numbers are now present in the train transliteration: 0064939c-59b9-4448-a63d-34612af0a1b5 -> 1 TÚG ša qá-tim i-tur₄-DINGIR il₅-qé ...
Reply
React
Oleg Yaroshevskiy
Posted 10 days ago
·  40th in this Competition
2
more_vert
Can't describe an amount of confusion when comparing a new train dropped last week and a new train from yesterday and now I'm trying do understand how to merge those two
upd: sorry, my humble verdict is that these updates last week made things worse…
Reply
React
Oleg Yaroshevskiy
Posted 10 days ago
·  40th in this Competition
0
more_vert
how to understand this:
before: 31 kutānu-textiles of Iddin-Suen, 30 kutānu-textiles of Ah-šalim, 46 kutānu-textiles of hinnāya and Uṣurānum, 21 kutānu-textiles of Aššur-rēī, 36 kutānu-textiles of Šu-Ištar, 28 kutānu-textiles of Ennam-Suen, 24 kutānu-textiles of Lā-qēp, 18 kutānu-textiles of the merchant, 7 kutānu-textiles without seals, 14 textiles import-tax, 17 textiles as pre-emption. after:  31 -textiles of Iddin-Suen, 30 -textiles of Ah-šalim, 46 -textiles of hinnāya and Uṣurānum, 21 -textiles of Aššur-rē'ī, 36 -textiles of Šu-Ištar, 28 -textiles of Ennam-Suen, 24 -textiles of Lā-qēp, 18 -textiles of the merchant, 7 -textiles without seals, 14 textiles import-tax, 17 textiles as pre-emption.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 9 days ago
-1
more_vert
Yes, you can see in the post above, I recommend making some small changes, egg. -textiles --> kutānum textiles, but this should be checked with the AKT volumes in PDF to be certain. The interum data (v2) update did this, but it introduced new errors because of a simple search / replace. Those changes were rolled back in the lates update (v3), and instructions were provided how to deal with those (above).
Reply
React
4 more replies
annd
Posted 10 days ago
·  861st in this Competition
2
more_vert
Remove from translations:      fem.     sing.     pl.     plural     (?)     any stray marks you find (e.g., .., ?, x, xx, << >>, < > except around <gap> of course)
You recommend removing these words but would these words be included in the test set?
Reply
React
Adam Anderson
COMPETITION HOST
Posted 5 days ago
0
more_vert
no, they are not included in the test set
Reply
React
Anil Ozturk
Posted 11 days ago
·  264th in this Competition
1
more_vert
Thanks, these are some new changes. Do we expect another test set update?
Reply
React
Adam Anderson
COMPETITION HOST
Posted 11 days ago
0
more_vert
Yes, both test and train were updated (final update 2/26/26).
Reply
2add_reaction
MengYe
Posted 7 days ago
·  72nd in this Competition
0
more_vert
1 / 12 (shekel) —> 15 grains
what should we do with 1/4, 1/6, and 1/8
Reply
React
Adam Anderson
COMPETITION HOST
Posted 5 days ago
1
more_vert
Those fractions are counted in terms of shekels: ¼ (shekel) ⅙ (shekel)
Reply
React
Yicong XIAO
Posted 8 days ago
0
more_vert
@deeppast hi, just to be 100% clarified, is ḫ gonna be a valid character in the test set? 
Asking this because in the "Examples of the Optimal Outcomes for Train" you mentioned, the proper noun "Tuwar-aḫšu" is displayed as "Tuwar-ahšu" 
thanks!
Reply
React
Adam Anderson
COMPETITION HOST
Posted 5 days ago
0
more_vert
yes, neither Ḫ nor ḫ appear in the test set.
Reply
React
Sasha Turutin
Posted 10 days ago
·  255th in this Competition
0
more_vert
Hi! Can you clarify these examples in translation:
I paid <gap> ⅓ mina (silver) to Ennānum, son of Amriya. Tuwar-ahšu owes ⅓ mina 2 ½ shekels of silver (and) 20 loaves of bread to Ali-ahum.
Why are we using curved parenthesis? I looked at train.csv on datasets page and there are no examples of "(silver)". Or examples of parenthesis usage.
Reply
React
Adam Anderson
COMPETITION HOST
Posted 9 days ago
2
more_vert
The parentheses are used by translators to fill in words that are missing in the Akkadian transliteration, but which provides sometimes necessary context.
Reply
React
Yicong XIAO
Posted 10 days ago
0
more_vert
Thanks for the update! 
May I ask about a specific case: 33773ec0-e74f-41bf-b985-f3e35b0f26c9
From what Amur-Aššur (owes?)
will such case of (some word?) appear in the test set? 
Reply
React
Adam Anderson
COMPETITION HOST
Posted 9 days ago
0
more_vert
yes, unfortunately, that does exist.
Reply
React
moth
Posted 11 days ago
·  1062nd in this Competition
0
more_vert
Thanks @deeppast for your ongoing efforts. What does this exactly mean?
PN —> < gap >
Does this mean that every personal name to be found must be replaced by a gap tag? Or just the literal PN?
Also, 
Shortening of long floats to four places after the decimal
I am a bit confused by this since later you suggest converting them to unicode fractions. Does the hidden test set (both translations and transliterations) contain floating point numbers or only unicode fractions?
Thanks in advance 
Reply
React
Adam Anderson
COMPETITION HOST
Posted 11 days ago
3
more_vert
That's a literal PN token, there are some of these in Veenhof's translations from AKT 8.
I already shortened the floats, so that the conversion to fractions will be easier for you, if you choose to do so. As seen in the example at the end, the test contains only unicode fractions (no decimals at all).
Reply
React
moth
Posted 11 days ago
·  1062nd in this Competition
0
more_vert
Perfect, thanks a lot!
Reply
React
This comment has been deleted.
menu
Skip to content
Create
* Home
* Competitions
* Datasets
* Models
* Benchmarks
* Game Arena
* Code
* Discussions
* Learn
* More
* Your Work
* VIEWED
   * 
* EDITED
   * 
* BOOKMARKS
   * Home Credit Default Risk
   * Vesuvius Challenge - Surface Detection [TFRecord]
   * UNet3DA100
   * byt5-small_akkadian_model
   * Amazon ML Challenge 2025
View Active Events
DEEP PAST INITIATIVE · FEATURED CODE COMPETITION · 16 DAYS TO GO
Deep Past Challenge - Translate Akkadian to English
Bringing Bronze Age Voices Back to Life – Machine Translation of Old Assyrian Cuneiform
Deep Past Challenge - Translate Akkadian to English
Submit Prediction
more_horiz
MPWARE ·  61ST IN THIS COMPETITION ·  POSTED A MONTH AGO
18
more_vert
Any luck with letters from Larsen PDF?
Discussions are so quiet since Kaggle removed the Discussions rewards, that's sad … Anyway, I'm trying to use Larsen 2002 - The Assur-nada Archive. PIHANS 96 2002.pdf provided as additional data to train with more transliterations / translations.
I faced some issues: First, it's difficult to use a PDF library to read content safely as we cannot capture unicode characters. If you inspect some sections, for instance:
page 51 - CCT 5, 6a, Line 3:
From text extracted from PDF:
* Transliteration: Pu-su-ki-in ù A-sùr-ta-ak-/la-ku
* Translation: Pnsu-kén and Aššur-taldâku:
Almost real text extracted by a multi-modal model:
* Transliteration: Pu-šu-ki-in ù A-šùr-ta-ak-/la-ku
* Translation: Pušu-kēn and Aššur-taklāku:
Look at the translation differences: Pnsu vs Pušu
Another example, page 54 line 12:
From text extracted from PDF:
* Transliteration: :"TOI"a-ni-a-tim ù 15 TÙI0JI01A
* Translation: These 8 textiles plus 15 textiles
Almost real text extracted by a multi-modal model:
* Transliteration: 8 TÚG a-ni-ú-tim ù 15 TÚG.HI.A
* Translation: These 8 textiles plus 15 textiles
Look at the garbage transliteration :"TOI"a-ni-a-tim ù 15 TÙI0JI01A vs 8 TÚG a-ni-ú-tim ù 15 TÚG.HI.A
Even parsing with a multi-modal model is far from being 100% correct. Second, the sentences alignment in some letter looks weird such as:
page 58: TC 3,95 line 16:
ha-am-ša-tim šu-ma => If
{"transliteration": "lu-up-ta a-na 25", "translation": "to run for 25 weeks."}, # 15 {"transliteration": "ha-am-ša-tim šu-ma", "translation": "If"}, {"transliteration": "lá i-ma-ga-ar-ku-nu", "translation": "he does not agree with you,"}, {"transliteration": "a-na 30 lu 35 ha-am-ša-/tim", "translation": "then draw it up for 30 or 35 weeks."}, {"transliteration": "lu-up-ta tup-pu-šu", "translation": "Certify his tablet"}, {"transliteration": "hi-ir-ma-ma a-na A-šur-na-/da", "translation": "and entrust it to Aššur-nāda."},
I'm sharing some of my parsed letters. 
5add_reaction
10 Comments
undoredo
format_sizeformat_boldformat_italicformat_strikethrough
insert_linkformat_quotecode
format_list_numberedformat_list_bulleted
table_chartinsert_photo
smart_displayinsert_emoticon
help
This comment will be made public once posted.
attach_filePost Comment
Adam Anderson
COMPETITION HOST
Posted a month ago
3
more_vert
Great work, and thanks for keeping things rolling! Note that all the PDFs that have been provided so far already have transliterations in the publications.csv - what is missing are the translations for these texts. So you don't need to redo all the transliteration text, you just need to get the corresponding translations.
You're right to identify that the alignment is an issue, which is why looking at the line numbers as they correspond to the translations are somewhat helpful, but also not exactly in alignment. For example the last word of the previous sentence was "ha-am-ša-tim" and the first word of the next sentence began "šu-ma". 
* šu-ma = šumma = if (https://www.ebl.lmu.de/dictionary/%C5%A1umma%20I)
* ha-am-ša-tim = hamuštum = group of 5 (https://www.ebl.lmu.de/dictionary?origin=CDA&word=hamu%C5%A1tum)
Using the dictionary for lemmatizing should be helpful if you're matching on the sense of the Akkadian with the English translations, although this type of lemmatization is very advanced work.
Reply
2add_reaction
MPWARE
TOPIC AUTHOR
Posted a month ago
·  61st in this Competition
1
more_vert
@deeppast Do you think transliteration in published.csv are safe? IMO it's difficult to be used due to what I've explained in my post, parsed PDF does not reflect the printed transliteration by design. PDF parser cannot be used safely for "Larsen 2002 - The Assur-nada Archive. PIHANS 96 2002.pdf":
Page 54, line 12:
Look at the garbage transliteration :"TOI"a-ni-a-tim ù 15 TÙI0JI01A instead of 8 TÚG a-ni-ú-tim ù 15 TÚG.HI.A
published.csv:


Printed text:

This is what I get by another method:
Any thoughts?
If the hidden set contains such garbage then just let us know because I should not spend more time to capture real transliteration/english but just garbage transliteration/english pairs.
Reply
React
MPWARE
TOPIC AUTHOR
Posted a month ago
·  61st in this Competition
1
more_vert
Re-OCR sounds a good way to get clean transliteration. I've tried a few OCR models, DeepSeek-OCR-2 is not bad but far from the majors.
Reply
React
6 more replies
FML
Posted a month ago
·  850th in this Competition
1
more_vert
I am trying to work with the:
Larsen 2010 - The Archive of the Šalim-Aššur Family, Vol. 1. 
However, it is extremely difficult unless I review each translation manually. The transliteration is ok because I can find in the published_texts.csv.
We could make a team, I could clean the translation manually and you (anyone) do the model😀!
Reply
React
MPWARE
TOPIC AUTHOR
Posted a month ago
·  61st in this Competition
0
more_vert
Where is this one? Any link?
Reply
React
FML
Posted a month ago
·  850th in this Competition
1
more_vert
https://www.kaggle.com/datasets/deeppast/old-assyrian-kltepe-tablets-in-pdf/data?select=AKT+6a.pdf
Reply
React
Aneesh
Posted a month ago
·  373rd in this Competition
-1
more_vert
Hi @mpware Can you drop in the url or file of the pdf? I can't find a way to open it.
Reply
React
MPWARE
TOPIC AUTHOR
Posted a month ago
·  61st in this Competition
0
more_vert
https://www.kaggle.com/datasets/deeppast/old-assyrian-grammars-and-other-resources/data?select=Larsen+2002+-+The+Assur-nada+Archive.+PIHANS+96+2002.pdf
Reply
React
This comment has been deleted.
FML
Posted a month ago
·  850th in this Competition
0
more_vert
I just published the notebook
https://www.kaggle.com/code/seraquevence/dpc-increase-the-train-data-v02
I hope it helps in yours strategies. Regards.
Reply
React
Jack
Posted a month ago
·  19th in this Competition
0
more_vert
Extraction is difficult but feasible. Diacritics and ˹ ˺ are my main pain points.. the extractions will definitely require some cleaning but should be pretty helpful once usable. 
Reply
React
9Hash
Posted 22 days ago
0
more_vert
those were supposed to be removed before training if I'm not wrong, so whats causing the pain?
Reply
React
Angantyr
Posted a month ago
0
more_vert
I was convinced that people just lost interest.
I'm yet to start the fine-tuning -- still patching the parser for the transliterations, mainly from train.csv. 
Reply
React
these are some important discussion and add some other dataset in data folder , check them out 
about these dataset talk about in these discussion