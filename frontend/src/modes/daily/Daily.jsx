import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import FlapText from '../../components/FlapText';
import Icon from '../../components/Icon';
import QuestionCard from '../../components/QuestionCard';
import ResultsBoard from '../../components/ResultsBoard';
import useBringIntoView from '../../hooks/useBringIntoView';
import useOnline from '../../hooks/useOnline';
import { daily } from '../../lib/api';
import { formatSeconds, missedQuestions, ordinal, shareText, streakNote, streaks } from '../../lib/results';
import { KEYS, readStored, writeStored } from '../../lib/storage';
import DailyLeaderboard from './DailyLeaderboard';

// Daily challenge: the same 10 questions for everyone today, one go each.
// The server (backend/daily.py) checks every answer and keeps the leaderboard.
// A random token in localStorage stands in for an account, so a returning visitor
// picks up where they left off.

function makeToken() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return Array.from(crypto.getRandomValues(new Uint8Array(16)), (b) => b.toString(16).padStart(2, '0')).join('');
}

// This browser's daily token, made up and saved the first time it's needed
function dailyToken() {
  let token = readStored(KEYS.dailyToken);
  if (token === null) {
    token = makeToken();
    writeStored(KEYS.dailyToken, token);
  }
  return token;
}

// "Tue 29 Sep" in the visitor's own language
function dayLabel(date) {
  return new Date(`${date}T12:00:00Z`).toLocaleDateString(undefined, {
    weekday: 'short',
    day: 'numeric',
    month: 'short',
    timeZone: 'UTC',
  });
}

// When the next challenge appears, in the visitor's local time
function nextChallengeLabel(date) {
  const next = new Date(`${date}T00:00:00Z`);
  next.setUTCDate(next.getUTCDate() + 1);
  return next.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
}

function Daily({ onProgress }) {
  const [token] = useState(dailyToken);
  const [name, setName] = useState(() => readStored(KEYS.name) ?? '');
  const [status, setStatus] = useState('loading'); // loading | failed | intro | playing
  const [error, setError] = useState('');
  const [date, setDate] = useState(null);
  const [total, setTotal] = useState(10);
  const [questions, setQuestions] = useState([]);
  const [player, setPlayer] = useState(null);
  const [results, setResults] = useState({}); // question index -> { answer, correct, correctAnswer }
  const [currentIndex, setCurrentIndex] = useState(0);
  const [showResults, setShowResults] = useState(false);
  const [board, setBoard] = useState(null);
  const [starting, setStarting] = useState(false);
  const online = useOnline();
  const [justStarted, setJustStarted] = useState(0); // bumps on Start, to bring question 1 into view
  const stageRef = useRef(null);

  useBringIntoView(stageRef, justStarted);

  // `day` is the run's date once known; without it the server shows today's board
  const refreshBoard = useCallback((day) => {
    daily.leaderboard(token, day).then(setBoard).catch(() => {});
  }, [token]);

  // Take in the server's view of this player: their answers, and where to carry on
  const applyPlayer = useCallback((view, list) => {
    setPlayer(view);
    setResults(Object.fromEntries(view.answers.map((a) => [a.index, a])));
    const answered = new Set(view.answers.map((a) => a.index));
    const next = list.findIndex((_, i) => !answered.has(i));
    setCurrentIndex(next === -1 ? 0 : next);
    setShowResults(view.finished);
  }, []);

  const load = useCallback(() => {
    daily
      .load(token)
      .then((data) => {
        setDate(data.date);
        setTotal(data.total);
        if (data.player) {
          setQuestions(data.questions);
          applyPlayer(data.player, data.questions);
          setStatus('playing');
        } else {
          setStatus('intro');
        }
      })
      .catch((e) => {
        setError(e.message);
        setStatus('failed');
      });
    refreshBoard();
  }, [token, refreshBoard, applyPlayer]);

  useEffect(load, [load]);

  async function start() {
    const trimmed = name.trim();
    if (!trimmed) return setError('Enter your name first. It goes on the leaderboard.');
    setStarting(true);
    setError('');
    try {
      const data = await daily.start(token, trimmed);
      writeStored(KEYS.name, trimmed); // if it isn't saved, the name just won't be filled in next time
      setDate(data.date);
      setQuestions(data.questions);
      applyPlayer(data.player, data.questions);
      setStatus('playing');
      setJustStarted((n) => n + 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setStarting(false);
    }
  }

  async function answer(option) {
    const index = currentIndex;
    setResults((prev) => ({ ...prev, [index]: { answer: option } })); // shows as "checking"
    setError('');
    try {
      const data = await daily.answer(token, index, option, date);
      setResults((prev) => ({ ...prev, [index]: data }));
      setPlayer(data.player);
      if (data.player.finished) refreshBoard(date);
    } catch (e) {
      setResults((prev) => {
        const copy = { ...prev };
        delete copy[index];
        return copy;
      });
      setError(e.message);
    }
  }

  // Marks and streaks, with answers in the order they were given
  const marks = useMemo(
    () =>
      questions.map((_, i) => {
        const r = results[i];
        if (!r) return undefined;
        if (r.correctAnswer === undefined) return 'pending';
        return r.correct ? 'correct' : 'wrong';
      }),
    [questions, results]
  );
  const ordered = useMemo(() => player?.answers ?? [], [player]);
  const streak = useMemo(() => streaks(ordered.map((a) => a.correct)), [ordered]);
  const correct = marks.filter((m) => m === 'correct').length;
  const answered = marks.filter((m) => m === 'correct' || m === 'wrong').length;

  // Report how the round is going, for the boards beside the quiz on wide screens
  const items = useMemo(
    () => questions.map((q, i) => ({ question: q.question, category: q.category, mark: marks[i] })),
    [questions, marks]
  );
  useEffect(() => {
    onProgress?.({
      answered,
      correct,
      total: questions.length,
      streak: streak.current,
      index: currentIndex,
      items,
      jump: (i) => {
        setShowResults(false);
        setCurrentIndex(i);
      },
    });
  }, [answered, correct, questions.length, streak, currentIndex, items, onProgress]);

  const head = (
    <section className="board daily-head" aria-labelledby="daily-title">
      <div className="board-head">
        <h2 className="board-title" id="daily-title">Daily challenge</h2>
        {date && <span className="daily-date">{dayLabel(date)}</span>}
      </div>
      <div className="board-body">
        <p className="daily-lede">
          The same {total} questions for everyone today, and one go each. Every answer counts,
          and ties go to whoever finished faster.
        </p>
        {status === 'intro' && (
          <div className="daily-start">
            <div className="field name-field">
              <label htmlFor="daily-name">Your name for the leaderboard</label>
              <input
                id="daily-name"
                type="text"
                maxLength={20}
                placeholder="e.g. Alex"
                value={name}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && start()}
              />
            </div>
            <button className="btn btn-primary" onClick={start} disabled={starting || !online}>
              {starting ? 'Starting…' : "Start today's challenge"}
            </button>
          </div>
        )}
        {status === 'intro' && (
          <p className="muted-text daily-clock-note">The clock starts when you press start.</p>
        )}
        {status === 'playing' && player && !player.finished && (
          <p className="muted-text">Playing as {player.name}. The clock is running.</p>
        )}
        {status === 'loading' && <p className="muted-text" role="status">Loading today's challenge…</p>}
        {status === 'failed' && (
          <div className="daily-start">
            <button
              className="btn"
              onClick={() => {
                setStatus('loading');
                setError('');
                load();
              }}
            >
              <Icon name="replay" />
              Try again
            </button>
          </div>
        )}
        {error && <p className="error" role="alert"><Icon name="alert" />{error}</p>}
      </div>
    </section>
  );

  const current = questions[currentIndex];
  const finished = player?.finished;

  return (
    <>
      {head}

      {status === 'playing' && finished && showResults && (
        <ResultsBoard
          title="Today's results"
          correct={player.correct}
          total={questions.length}
          stats={[
            { label: 'Time', value: formatSeconds(player.seconds) },
            { label: 'Rank', value: `${ordinal(player.rank)} of ${player.finishers}` },
            { label: 'Best streak', value: streak.best },
          ]}
          missed={missedQuestions(questions, marks, (i) => ({
            answer: results[i]?.answer,
            correctAnswer: results[i]?.correctAnswer,
          }))}
          share={shareText({
            title: `Quizzr Daily · ${dayLabel(date)} · ${player.correct}/${questions.length}`,
            marks,
            lines: [`${formatSeconds(player.seconds)} · ${ordinal(player.rank)} of ${player.finishers}`],
            url: window.location.origin,
          })}
          note={`A new challenge appears at ${nextChallengeLabel(date)} your time.`}
          actions={
            <button className="btn" onClick={() => setShowResults(false)}>
              Review questions
            </button>
          }
        />
      )}

      {status === 'playing' && current && !(finished && showResults) && (
        <div ref={stageRef} className="stage">
          <QuestionCard
            index={currentIndex}
            total={questions.length}
            category={current.category}
            difficulty={current.difficulty}
            source={current.source}
            question={current.question}
            options={current.options}
            picked={results[currentIndex]?.answer}
            correctAnswer={results[currentIndex]?.correctAnswer}
            score={correct}
            streak={streak.current}
            note={streakNote(streak.current, marks[currentIndex] === 'correct' && ordered.at(-1)?.index === currentIndex)}
            marks={marks}
            finishAction={finished ? { label: 'See results', onClick: () => setShowResults(true) } : undefined}
            onAnswer={answer}
            onPrevious={() => setCurrentIndex((i) => Math.max(0, i - 1))}
            onNext={() => setCurrentIndex((i) => Math.min(questions.length - 1, i + 1))}
            onJump={setCurrentIndex}
          />
        </div>
      )}

      {status === 'intro' && (
        <section className="board board-idle">
          <div className="board-body">
            <FlapText text="DAILY" label="" size="lg" />
            <p>Today's questions stay hidden until you start.</p>
          </div>
        </section>
      )}

      <DailyLeaderboard board={board} total={total} />
    </>
  );
}

export default Daily;
