# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Primarily a portfolio and learning project. The main audience is recruiters, reviewers, and peers who open the deployed link to try it, usually for a few minutes and often alone, sometimes pulling in a friend to test multiplayer. The same person may be judging both how it feels to play and how well it is built. Everyday trivia players are a secondary audience, not the design target.

## Product Purpose
A trivia quiz in the browser. Players choose how many questions (1–50), a category, a difficulty, and a question type, then play either solo or in a live multiplayer room. Success means a first-time visitor starts playing within seconds, finishes a round without confusion, and comes away seeing a polished, well-engineered product.

In solo mode you pick settings and play. In multiplayer, one person creates a room and shares a 5-letter code or an invite link (`/?room=CODE`), and everyone is playing right away. Positioning beyond that is still undecided.

## Operating Context
- Three modes as tabs: Solo, Daily and Multiplayer. All stay mounted, so switching tabs doesn't lose progress.
- Multiplayer flow: enter a name, then create or join a room. The room creator is the host and picks the settings. Everyone gets the same questions and answers at their own pace, and a live leaderboard shows scores and progress. The final results name the winner or winners, and the host can start another round.
- Questions come from a bank of about 38,000 stored with the server (`backend/data/`), built from OpenTriviaQA and Wikidata by `backend/scripts/question_bank/`. Each category holds more or fewer questions according to how popular it's likely to be (2,000 for broad topics such as Film or History, down to 800 for Board Games). Open Trivia DB's live API supplies the daily challenge and fills in when the bank can't meet a quiz's settings; its questions are never stored.

## Capabilities and Constraints
- Stack: React 19 + Vite frontend (`frontend/`) and a FastAPI backend (`backend/`) with WebSockets for rooms. On Render's free plan (`render.yaml`) the frontend is a static site and the API a separate Docker service.
- Must stay free to run and account-free. Rooms live in memory and are lost when the server restarts. Rooms hold at most 20 players, and names are capped at 20 characters.
- The server checks multiplayer answers and never sends correct answers to the browser before a player answers. This is an existing behavior, not a headline claim.
- Room codes use a 5-character alphabet that leaves out 0/O and 1/I.
- Three modes: Solo, Daily (the same 10 questions for everyone each UTC day, one go per browser, leaderboard ranked by correct answers then time), and Multiplayer.
- The daily challenge is the only persisted data (`backend/daily.py`): Postgres when `DATABASE_URL` is set, otherwise a SQLite file (path set by `QUIZZR_DB`). On Render's free plan the disk is temporary, so without Postgres daily results reset whenever the server restarts.
- Multiplayer seats are held for 90 seconds after a dropped connection, and players rejoin with a per-tab token. Scoring is 100 points per correct answer plus up to 50 for speed.
- Timed multiplayer (10, 20 or 30 seconds per question, chosen by the host) runs in lockstep on the server's clock: one question open for everyone, late answers refused, the answer revealed to all when it closes.
- Every mode ends with a results screen and a copyable share text.
- Requests slower than 2.5 seconds show a "still working / waking the server up" notice, and requests give up after 90 seconds. Because the frontend is hosted separately, the page loads at once and can show the notice while the API wakes up.
- Tests: pytest (`backend/tests`) and Vitest (`frontend/src/**/*.test.*`), run by GitHub Actions (`.github/workflows/ci.yml`).
- Name: "Quizzr" is now shown in the app header, but it's still unconfirmed as a brand. Positioning beyond zero friction is undecided.

