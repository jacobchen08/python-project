# Question bank

`questions.json.gz` holds the questions the app draws from (about 38,000). Rebuild it with:

```bash
python backend/scripts/question_bank/build.py
```

The build downloads its sources into `sources/` (not committed) and reuses them on later runs.

## Where the questions come from

| Source | Licence | What's used |
| --- | --- | --- |
| [OpenTriviaQA](https://github.com/uberspot/OpenTriviaQA) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Hand-written multiple-choice questions, filtered and lightly repaired (lost apostrophes, stray spaces) |
| [Wikidata](https://www.wikidata.org) | [CC0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain) | Facts about books, games, places, art, people and more, turned into questions by `backend/scripts/question_bank/` |
| Worked out by the build | — | Number trivia for Mathematics (Roman numerals, primes, polygons…) |

Because it includes OpenTriviaQA's questions, the bank as a whole is shared under **CC BY-SA 4.0**: you can reuse it, with credit, under the same licence.

Open Trivia DB's questions are not stored here. The app still asks Open Trivia DB's API live for the daily challenge, and whenever the bank can't meet a quiz's settings.
