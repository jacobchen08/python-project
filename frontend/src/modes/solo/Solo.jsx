import { useEffect, useMemo, useRef, useState } from 'react';
import FlapText from '../../components/FlapText';
import Icon from '../../components/Icon';
import QuestionCard from '../../components/QuestionCard';
import ResultsBoard from '../../components/ResultsBoard';
import { FoldingSettings, SettingsToggle } from '../../components/Settings';
import useBringIntoView from '../../hooks/useBringIntoView';
import useOnline from '../../hooks/useOnline';
import usePersistentFlag from '../../hooks/usePersistentFlag';
import { questionsUrl } from '../../lib/api';
import { dealFromPack, OfflinePackError } from '../../lib/offlinePack';
import { toQuestion } from '../../lib/questions';
import { missedQuestions, shareText, streakNote, streaks } from '../../lib/results';
import { apiFetch } from '../../lib/serverStatus';
import { KEYS } from '../../lib/storage';

// Screens too narrow for the side boards (see styles/layout.css), such as phones
const NARROW_SCREEN = '(max-width: 1239px)';

// Solo: pick settings, generate a round of questions, answer them, see your results.
// Everything happens in this browser: the questions come from the API (or, offline, from the
// pack saved in this browser), and answers are checked here, since you only play yourself.
function Solo({ settings, onSettingsChange, onProgress }) {
  const [questions, setQuestions] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({}); // question index -> answer the user submitted
  const [order, setOrder] = useState([]); // question indexes in the order they were answered
  const [showResults, setShowResults] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const settingsRef = useRef(null);
  const [settingsOpen, setSettingsOpen] = usePersistentFlag(KEYS.soloSettingsOpen, true);
  // On a narrow screen the settings fold away while a round is on, so the question isn't pushed
  // down out of sight. This doesn't change the choice remembered in settingsOpen.
  const [foldedForRound, setFoldedForRound] = useState(false);
  const showSettings = settingsOpen && !foldedForRound;
  const stageRef = useRef(null);
  const [round, setRound] = useState(0); // counts generated rounds, to bring each new one into view
  const [playingOffline, setPlayingOffline] = useState(false); // this round came from the saved pack
  const online = useOnline();

  // Time limit for this round (0 = none), fixed when the questions are generated
  const [timeLimit, setTimeLimit] = useState(0);
  const [deadline, setDeadline] = useState(null); // when the question on screen runs out, on our clock
  const [timedOut, setTimedOut] = useState({}); // question index -> true when time ran out unanswered

  const total = questions.length;
  const answeredCount = order.length; // answered or timed out
  const allAnswered = total > 0 && answeredCount === total;
  // A timed round goes one question at a time; once it's over, reviewing is free again
  const timedRound = timeLimit > 0 && !allAnswered;
  const currentDone = answers[currentIndex] !== undefined || Boolean(timedOut[currentIndex]);

  // One mark per question for the step row: correct, wrong, timed out or not answered yet
  const marks = useMemo(
    () =>
      questions.map((q, i) => {
        if (answers[i] !== undefined) return answers[i] === q.correct ? 'correct' : 'wrong';
        return timedOut[i] ? 'timeout' : undefined;
      }),
    [questions, answers, timedOut]
  );

  // Run the clock on the open question: when it runs out, the question counts as missed
  useEffect(() => {
    if (!timedRound || currentDone || deadline === null) return;
    const index = currentIndex;
    const timer = setTimeout(() => {
      setTimedOut((prev) => ({ ...prev, [index]: true }));
      setOrder((prev) => (prev.includes(index) ? prev : [...prev, index]));
    }, Math.max(0, deadline - Date.now()));
    return () => clearTimeout(timer);
  }, [timedRound, currentDone, deadline, currentIndex]);

  function openQuestion(index) {
    setCurrentIndex(index);
    if (timeLimit > 0) setDeadline(Date.now() + timeLimit * 1000);
  }
  const score = marks.filter((m) => m === 'correct').length;
  const streak = useMemo(() => streaks(order.map((i) => marks[i] === 'correct')), [order, marks]);

  // Report how the round is going, for the boards beside the quiz on wide screens
  const items = useMemo(
    () => questions.map((q, i) => ({ question: q.question, category: q.category, mark: marks[i] })),
    [questions, marks]
  );
  useEffect(() => {
    onProgress?.({
      answered: answeredCount,
      correct: score,
      total,
      streak: streak.current,
      index: currentIndex,
      items,
      // no skipping around in a timed round
      jump: timedRound
        ? undefined
        : (i) => {
            setShowResults(false);
            setCurrentIndex(i);
          },
    });
  }, [answeredCount, score, total, streak, currentIndex, items, timedRound, onProgress]);

  function handleAnswer(answer) {
    if (timedRound && (timedOut[currentIndex] || Date.now() > deadline)) return; // too late
    setAnswers((prev) => ({ ...prev, [currentIndex]: answer }));
    setOrder((prev) => [...prev, currentIndex]);
  }

  // Start a round from Open Trivia DB items, whether they came from the API or the saved pack
  function startRound(items, fromPack) {
    const limit = Number(settings.timer) || 0;
    setQuestions(items.map(toQuestion));
    setCurrentIndex(0);
    setAnswers({});
    setOrder([]);
    setTimedOut({});
    setTimeLimit(limit);
    setDeadline(limit > 0 ? Date.now() + limit * 1000 : null);
    setShowResults(false);
    setPlayingOffline(fromPack);
    setRound((r) => r + 1);
    if (window.matchMedia?.(NARROW_SCREEN).matches) setFoldedForRound(true);
  }

  function toggleSettings() {
    setFoldedForRound(false);
    setSettingsOpen(!showSettings);
  }

  // Offline: deal from the questions saved in this browser instead
  function playFromPack() {
    try {
      startRound(dealFromPack(settings), true);
    } catch (e) {
      setError(e instanceof OfflinePackError ? e.message : 'Could not start an offline round.');
    }
  }

  function generate() {
    setError('');
    if (!navigator.onLine) {
      playFromPack();
      return;
    }
    setLoading(true);
    apiFetch(questionsUrl(settings))
      .then((response) => response.json())
      .then((data) => {
        if (!Array.isArray(data)) throw new Error(data.error || 'Failed to fetch questions');
        startRound(data, false);
      })
      .catch((error) => {
        // the connection dropped on the way: the saved questions can still carry a round
        if (!navigator.onLine) {
          playFromPack();
          return;
        }
        setError(error.message === 'Failed to fetch' ? 'Could not reach the server.' : error.message);
      })
      .finally(() => setLoading(false));
  }

  useBringIntoView(stageRef, round);

  function changeSettings() {
    setFoldedForRound(false);
    setSettingsOpen(true);
    settingsRef.current?.scrollIntoView({ block: 'start', behavior: 'smooth' });
    settingsRef.current?.querySelector('input, select, button')?.focus({ preventScroll: true });
  }

  const current = questions[currentIndex];
  const missed = missedQuestions(questions, marks, (i) => ({ answer: answers[i], correctAnswer: questions[i].correct }));

  return (
    <>
      <section className="board" aria-labelledby="solo-settings-title" ref={settingsRef}>
        <div className="board-head">
          <h2 className="board-title" id="solo-settings-title">Quiz settings</h2>
          <SettingsToggle open={showSettings} onToggle={toggleSettings} controls="solo-settings" />
        </div>
        <div className="board-body">
          <FoldingSettings id="solo-settings" open={showSettings} settings={settings} onChange={onSettingsChange} />
          <div className="board-actions">
            <p className="load-hint">
              {online
                ? 'Questions are drawn from a bank of about 38,000, built from OpenTriviaQA and Wikidata.'
                : 'Offline: questions come from the ones saved in this browser.'}
            </p>
            {/* yellow marks the one thing to do now: only before there are questions */}
            <button className={total === 0 ? 'btn btn-primary' : 'btn'} onClick={generate} disabled={loading}>
              {loading ? 'Loading…' : total > 0 ? 'Generate New Questions' : 'Generate Questions'}
            </button>
          </div>
          {error && <p className="error" role="alert"><Icon name="alert" />{error}</p>}
        </div>
      </section>

      {total === 0 && (
        <section className="board board-idle">
          <div className="board-body">
            <FlapText text="READY" label="" size="lg" />
            <p>Pick your settings, then generate a set of questions.</p>
          </div>
        </section>
      )}

      {total > 0 && showResults && (
        <ResultsBoard
          correct={score}
          total={total}
          note={playingOffline ? 'Played offline, from questions saved in this browser.' : undefined}
          stats={[
            { label: 'Accuracy', value: `${Math.round((score / total) * 100)}%` },
            { label: 'Best streak', value: streak.best },
            ...(timeLimit > 0
              ? [{ label: 'Ran out of time', value: Object.keys(timedOut).length }]
              : []),
          ]}
          missed={missed}
          share={shareText({
            title: `Quizzr · Solo · ${score}/${total}`,
            marks,
            lines: streak.best >= 2 ? [`Best streak: ${streak.best}`] : [],
            url: window.location.origin,
          })}
          actions={
            <>
              <button className="btn btn-primary" onClick={generate} disabled={loading}>
                <Icon name="replay" />
                {loading ? 'Loading…' : 'Play again'}
              </button>
              <button className="btn" onClick={() => setShowResults(false)}>
                Review questions
              </button>
              <button className="btn btn-ghost-quiet" onClick={changeSettings}>
                Change settings
              </button>
            </>
          }
        />
      )}

      {total > 0 && !showResults && (
        <div ref={stageRef} className="stage">
          <QuestionCard
            index={currentIndex}
            total={total}
            category={current.category}
            difficulty={current.difficulty}
            source={current.source}
            question={current.question}
            options={current.options}
            picked={answers[currentIndex]}
            correctAnswer={current.correct}
            score={score}
            streak={streak.current}
            note={streakNote(streak.current, marks[currentIndex] === 'correct' && order.at(-1) === currentIndex)}
            marks={marks}
            countdown={
              timedRound && deadline !== null
                ? { deadline, limit: timeLimit, phase: currentDone ? 'reveal' : 'open' }
                : undefined
            }
            closed={Boolean(timedOut[currentIndex])}
            locked={timedRound}
            lockedHint={currentDone ? undefined : 'Answer before the time runs out.'}
            finishAction={
              allAnswered
                ? { label: 'See results', onClick: () => setShowResults(true) }
                : timedRound && currentDone
                  ? { label: 'Next question', onClick: () => openQuestion(currentIndex + 1) }
                  : undefined
            }
            onAnswer={handleAnswer}
            onPrevious={() => setCurrentIndex((i) => Math.max(0, i - 1))}
            onNext={() => setCurrentIndex((i) => Math.min(total - 1, i + 1))}
            onJump={setCurrentIndex}
          />
        </div>
      )}
    </>
  );
}

export default Solo;
