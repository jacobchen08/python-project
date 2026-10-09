import { useEffect, useRef, useState } from 'react';
import FlapText from './FlapText';
import Icon from './Icon';
import RouteBadge from './RouteBadge';
import Pips from './Pips';
import { categoryByName, categoryLabel, difficultyByValue } from '../lib/categories';
import { markLabels } from '../lib/results';

// Shows one question with its answer buttons. Used by solo, daily and multiplayer.
// `picked` is the answer the player chose (undefined until they answer) and
// `correctAnswer` is only needed once they have answered, or once the question has closed.
// `marks` has one entry per question: 'correct', 'wrong', 'pending', 'timeout' or undefined.
//
// Timed multiplayer adds three props: `countdown` ({ deadline, limit, phase }, the deadline
// already on this browser's clock), `closed` (time's up, answered or not) and `locked`
// (everyone moves on together, so there's no going back or skipping ahead).

function StepRow({ total, index, marks, onJump, locked }) {
  return (
    <ol className="steps" aria-label="Questions">
      {Array.from({ length: total }, (_, i) => {
        const mark = marks[i];
        return (
          <li key={i}>
            <button
              type="button"
              className={`step ${mark ?? ''}`}
              aria-current={i === index ? 'step' : undefined}
              aria-label={`Question ${i + 1}${mark ? `, ${markLabels[mark]}` : ''}`}
              disabled={locked}
              onClick={() => onJump?.(i)}
            >
              {mark === 'correct' && <Icon name="check" size={14} />}
              {(mark === 'wrong' || mark === 'timeout') && <Icon name="cross" size={14} />}
            </button>
          </li>
        );
      })}
    </ol>
  );
}

// Time left on a timed question, from a clock that ticks five times a second
function useCountdown(countdown) {
  const [now, setNow] = useState(() => Date.now());
  const running = countdown?.phase === 'open';
  useEffect(() => {
    if (!running) return;
    const tick = setInterval(() => setNow(Date.now()), 200);
    return () => clearInterval(tick);
  }, [running, countdown?.deadline]);
  if (!countdown) return { secondsLeft: null, fraction: 0 };
  if (!running) return { secondsLeft: 0, fraction: 0 };
  const left = Math.max(0, countdown.deadline - now);
  return {
    secondsLeft: Math.ceil(left / 1000),
    fraction: Math.min(1, left / (countdown.limit * 1000)),
  };
}

// A draining bar under the head: the same time as the digits, readable at a glance
function CountdownBar({ fraction, urgent }) {
  return (
    <div className={`countdown${urgent ? ' is-urgent' : ''}`} aria-hidden="true">
      <span className="countdown-fill" style={{ transform: `scaleX(${fraction})` }} />
    </div>
  );
}

function QuestionCard({
  index,
  total,
  category,
  difficulty,
  source,
  question,
  options,
  picked,
  correctAnswer,
  score,
  scoreSuffix = `/ ${total}`,
  scoreDigits,
  scoreLabel = `Score: ${score} / ${total}`,
  streak = 0,
  note,
  finishAction,
  countdown,
  closed = false,
  locked = false,
  lockedHint,
  marks,
  onAnswer,
  onPrevious,
  onNext,
  onJump,
}) {
  const isAnswered = picked !== undefined;
  const timedOut = closed && !isAnswered;
  const line = categoryByName(category);
  const level = difficultyByValue(difficulty);
  const { secondsLeft, fraction } = useCountdown(countdown);
  const urgent = countdown?.phase === 'open' && secondsLeft <= 5;

  // Clicking an answer only selects it; nothing counts until the player submits.
  // The selection belongs to one question, so moving to another starts fresh.
  const [selection, setSelection] = useState({ index, option: null });
  const selected = !isAnswered && !closed && selection.index === index ? selection.option : null;

  function submit() {
    if (selected !== null) onAnswer(selected);
  }

  // Which way the player moved, so the next question slides in from that side
  const [move, setMove] = useState({ index, direction: 'right' });
  if (move.index !== index) {
    setMove({ index, direction: index < move.index ? 'left' : 'right' });
  }
  const direction = move.direction;

  // as many digits as the total has: "1 / 9" for a short round, "01 / 10" for a long one
  const digits = String(total).length;

  function answerState(option) {
    if (timedOut) return option === correctAnswer ? 'correct' : 'dimmed';
    if (!isAnswered) return option === selected ? 'selected' : '';
    if (correctAnswer === undefined) return option === picked ? 'pending' : 'dimmed'; // waiting on the server
    if (option === correctAnswer) return 'correct';
    if (option === picked) return 'wrong';
    return 'dimmed';
  }

  const isLast = index >= total - 1;
  const canAnswer = !isAnswered && !closed;
  const canGoBack = !locked && index > 0;
  const forward = finishAction?.onClick ?? (!locked && !isLast ? onNext : null);

  // Keyboard play: A–D or 1–4 choose, Enter submits, arrows (or N / P) move between questions.
  // Every mode keeps its board mounted, so only the one on screen listens.
  const boardRef = useRef(null);
  const keys = useRef(null);
  useEffect(() => {
    keys.current = { canAnswer, options, selected, canGoBack, forward, onAnswer, onPrevious, index };
  });
  useEffect(() => {
    function onKeyDown(event) {
      const board = boardRef.current;
      if (!board || board.closest('[hidden]')) return; // a board on a tab that isn't showing
      if (event.altKey || event.ctrlKey || event.metaKey) return;
      const target = event.target;
      if (target.closest?.('input, select, textarea, [contenteditable="true"]')) return;
      const k = keys.current;
      const key = event.key.toLowerCase();
      const choice = 'abcd'.indexOf(key) !== -1 ? 'abcd'.indexOf(key) : '1234'.indexOf(key);

      if (choice !== -1 && k.canAnswer && choice < k.options.length) {
        event.preventDefault();
        setSelection({ index: k.index, option: k.options[choice] });
      } else if (key === 'enter' && k.canAnswer && k.selected !== null && !target.closest?.('button, a')) {
        event.preventDefault(); // a focused button's own Enter still just presses that button
        k.onAnswer(k.selected);
      } else if ((key === 'arrowright' || key === 'n') && k.forward) {
        event.preventDefault();
        k.forward();
      } else if ((key === 'arrowleft' || key === 'p') && k.canGoBack) {
        event.preventDefault();
        k.onPrevious();
      }
    }
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  return (
    <section className="board question-board" ref={boardRef} tabIndex={-1} aria-label={`Question ${index + 1} of ${total}`}>
      <div className="board-head quiz-head">
        <div className="readout">
          <span className="readout-label">Question</span>
          <span className="readout-value">
            <FlapText text={String(index + 1).padStart(digits, '0')} label={`Question ${index + 1}`} size="lg" />
            <span className="readout-slash" aria-hidden="true">/</span>
            <FlapText text={String(total).padStart(digits, '0')} label={'of ' + total} size="lg" />
          </span>
        </div>
        <div className="readout-group">
          {countdown && (
            <div className={`readout readout-end readout-time${urgent ? ' is-urgent' : ''}`}>
              <span className="readout-label">Time</span>
              <span className="readout-value">
                <FlapText text={String(secondsLeft).padStart(2, '0')} label={`${secondsLeft} seconds left`} size="lg" />
              </span>
            </div>
          )}
          <div className={`readout readout-end readout-streak${streak >= 2 ? ' is-hot' : ''}`}>
            <span className="readout-label">Streak</span>
            <span className="readout-value">
              <FlapText text={String(streak).padStart(digits, '0')} label={`Streak: ${streak} in a row`} size="lg" />
            </span>
          </div>
          <div className="readout readout-end">
            <span className="readout-label">Score</span>
            <span className="readout-value">
              <FlapText
                text={String(score).padStart(scoreDigits ?? digits, '0')}
                label={scoreLabel}
                size="lg"
              />
              <span className="readout-of">{scoreSuffix}</span>
            </span>
          </div>
        </div>
      </div>

      {countdown && <CountdownBar fraction={fraction} urgent={urgent} />}

      <div className="board-body">
        <StepRow total={total} index={index} marks={marks} onJump={onJump} locked={locked} />

        {/* Keyed on the question so each new one slides in from the side you moved towards */}
        <div key={index} className={`question-stage from-${direction}`}>
        {(category || level) && (
          <div className="question-meta">
            {category && (
              <p className="category-tag">
                {line && <RouteBadge code={line.code} line={line.line} size="sm" />}
                {categoryLabel(category)}
              </p>
            )}
            {(level || source === 'bank') && (
              <div className="question-meta-end">
                {source === 'bank' && (
                  <p className="source-tag" title="From Quizzr's own question bank">
                    <span className="sr-only">Source: </span>Bank
                  </p>
                )}
                {level && (
                  <p className="difficulty-tag">
                    <Pips count={level.pips} accent={level.accent} />
                    <span className="sr-only">Difficulty: </span>
                    {level.label}
                  </p>
                )}
              </div>
            )}
          </div>
        )}
        <p className="question">{question}</p>

        <div className="answers" role="group" aria-label="Answers">
          {options.map((option, i) => {
            const state = answerState(option);
            return (
              <button
                key={option}
                style={{ '--i': i }}
                className={`answer ${state}`}
                aria-pressed={isAnswered || closed ? undefined : option === selected}
                onClick={() => setSelection({ index, option })}
                disabled={isAnswered || closed}
              >
                <span className="answer-letter" aria-hidden="true">{String.fromCharCode(65 + i)}</span>
                <span className="answer-text">{option}</span>
                {state === 'correct' && (
                  <span className="answer-status"><Icon name="check" />Correct</span>
                )}
                {state === 'wrong' && (
                  <span className="answer-status"><Icon name="cross" />Your answer</span>
                )}
                {state === 'pending' && (
                  <span className="answer-status"><Icon name="pending" />Checking</span>
                )}
              </button>
            );
          })}
        </div>
        </div>

        {!isAnswered && !closed && (
          <div className="submit-row">
            <p className="submit-hint" aria-live="polite">
              {selected === null ? 'Pick an answer, then submit it.' : `Your answer: ${selected}`}
            </p>
            <button className="btn btn-primary" onClick={submit} disabled={selected === null}>
              Submit answer
            </button>
          </div>
        )}

        <p className="key-hint" aria-hidden="true">
          <kbd>A</kbd>–<kbd>D</kbd> choose · <kbd>Enter</kbd> submit · <kbd>←</kbd> <kbd>→</kbd> move
        </p>

        <div className="feedback-slot" role="status">
          {timedOut && correctAnswer !== undefined && (
            <p className="feedback wrong">
              <Icon name="pending" size={20} />
              <span>Time's up. The answer is {correctAnswer}.</span>
            </p>
          )}
          {isAnswered && correctAnswer !== undefined && (
            <p className={`feedback ${picked === correctAnswer ? 'correct' : 'wrong'}`}>
              <Icon name={picked === correctAnswer ? 'check' : 'cross'} size={20} />
              <span>
                {picked === correctAnswer ? 'Correct!' : `Not quite. The answer is ${correctAnswer}.`}
                {note && <span className="feedback-note"> {note}</span>}
              </span>
            </p>
          )}
          {/* At five seconds, say so once for people who can't see the countdown */}
          {countdown?.phase === 'open' && !isAnswered && urgent && secondsLeft > 0 && (
            <span className="sr-only">Five seconds left.</span>
          )}
        </div>

        {locked ? (
          <div className="nav nav-locked-row">
            <p className="nav-locked" aria-live="polite">
              {lockedHint ??
                (finishAction
                  ? ''
                  : countdown?.phase === 'reveal'
                    ? isLast
                      ? 'Final results coming up…'
                      : 'Next question coming up…'
                    : isAnswered
                      ? 'Answer in. Waiting for everyone else or the clock…'
                      : 'Everyone is on this question together.')}
            </p>
            {finishAction && (
              <button className="btn btn-primary btn-finish" onClick={finishAction.onClick}>
                {finishAction.label}
                <Icon name="arrow-right" />
              </button>
            )}
          </div>
        ) : (
          <div className="nav">
            <button className="btn" onClick={onPrevious} disabled={index === 0}>
              <Icon name="arrow-left" />
              Previous
            </button>
            {finishAction ? (
              <button className="btn btn-primary btn-finish" onClick={finishAction.onClick}>
                {finishAction.label}
                <Icon name="arrow-right" />
              </button>
            ) : (
              <button className="btn" onClick={onNext} disabled={isLast}>
                Next
                <Icon name="arrow-right" />
              </button>
            )}
          </div>
        )}
      </div>
    </section>
  );
}

export default QuestionCard;
