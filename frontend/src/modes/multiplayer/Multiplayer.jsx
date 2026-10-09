import { useEffect, useMemo, useRef, useState } from 'react';
import FlapText from '../../components/FlapText';
import Icon from '../../components/Icon';
import QuestionCard from '../../components/QuestionCard';
import { FoldingSettings, SettingsSummary, SettingsToggle } from '../../components/Settings';
import ShareResult from '../../components/ShareResult';
import useOnline from '../../hooks/useOnline';
import usePersistentFlag from '../../hooks/usePersistentFlag';
import { apiUrl, roomSocketUrl } from '../../lib/api';
import { ordinal, shareText } from '../../lib/results';
import { clearSeat, loadSeat, saveSeat } from '../../lib/seat';
import { copyText } from '../../lib/clipboard';
import { apiFetch, track } from '../../lib/serverStatus';
import { clampAmount } from '../../lib/settings';
import { KEYS } from '../../lib/storage';
import JoinRoom from './JoinRoom';
import RoomLeaderboard, { POINT_DIGITS } from './RoomLeaderboard';

// Multiplayer: one player creates a room and shares the code, everyone answers the
// same questions, and scores update live for everyone.
// The server (backend/multiplayer.py) checks answers so nobody can peek at them.
//
// Everything travels over one WebSocket per player (see openSocket below for the messages).
// Staying in the room: the server gives each player a token when they join, kept for this
// tab (lib/seat.js). If the connection drops, or the page reloads, we join again with that
// token and the server puts us back in our seat with our answers and score.

const initialCode = new URLSearchParams(window.location.search).get('room') || '';

const RETRY_DELAYS = [1000, 2000, 4000, 8000, 8000, 8000]; // about half a minute of tries

function Multiplayer({ settings, onSettingsChange, onProgress }) {
  const [name, setName] = useState(() => loadSeat()?.name ?? '');
  const [codeInput, setCodeInput] = useState(initialCode.toUpperCase());
  const [phase, setPhase] = useState('menu'); // menu | connecting | room | reconnecting
  const [error, setError] = useState('');

  const [myId, setMyId] = useState(null);
  const [room, setRoom] = useState(null); // latest "state" message from the server
  const [questions, setQuestions] = useState([]);
  const [results, setResults] = useState({}); // question index -> { answer, correct, correctAnswer, points, streak }
  const [revealed, setRevealed] = useState({}); // timed games: question index -> answer, once it has closed
  const [clockOffset, setClockOffset] = useState(0); // server clock minus ours, in milliseconds
  const [currentIndex, setCurrentIndex] = useState(0);
  const [copied, setCopied] = useState(null); // null, or whether the last copy worked
  const online = useOnline();
  const [settingsOpen, setSettingsOpen] = usePersistentFlag(KEYS.roomSettingsOpen, true);

  const socketRef = useRef(null);
  const seatRef = useRef(null); // { code, token, name } once the server has welcomed us
  const joinRef = useRef(null); // { code, name } for the connection being opened
  const roundRef = useRef(null);
  const resumeRef = useRef(false); // true until a mid-game join has been moved to its next question
  const questionCountRef = useRef(0);
  const adoptSettingsRef = useRef(false); // take the room's settings on joining, rather than overwrite them
  const retryRef = useRef({ attempt: 0, timer: null });

  // One mark per question for the step row and the answers board
  const marks = useMemo(
    () =>
      questions.map((_, i) => {
        const result = results[i];
        if (!result) return revealed[i] !== undefined ? 'timeout' : undefined;
        if (result.correctAnswer === undefined) return 'pending';
        return result.correct ? 'correct' : 'wrong';
      }),
    [questions, results, revealed]
  );

  const me = room?.players.find((p) => p.id === myId);

  // Timed games move everyone together, so the server decides which question is on screen
  const timer = room?.status === 'playing' ? room.timer : null;
  const shownIndex = timer ? timer.index : currentIndex;

  // Report how my round is going, for the boards beside the quiz on wide screens
  const answeredCount = marks.filter((m) => m === 'correct' || m === 'wrong').length;
  const correctCount = marks.filter((m) => m === 'correct').length;
  const myStreak = me?.streak ?? 0;
  const items = useMemo(
    () => questions.map((q, i) => ({ question: q.question, category: q.category, mark: marks[i] })),
    [questions, marks]
  );
  useEffect(() => {
    onProgress?.({
      answered: answeredCount,
      correct: correctCount,
      total: questions.length,
      streak: myStreak,
      index: shownIndex,
      items,
      jump: timer ? undefined : setCurrentIndex, // no skipping ahead in a timed game
    });
  }, [answeredCount, correctCount, questions.length, myStreak, shownIndex, timer, items, onProgress]);

  // The host's settings go to the server as they change, so everyone in the room sees them
  const amHost = Boolean(room && myId && room.hostId === myId);
  const canConfigure = amHost && (room.status === 'lobby' || room.status === 'finished');
  useEffect(() => {
    if (!canConfigure || adoptSettingsRef.current) return;
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'settings', settings }));
  }, [settings, canConfigure]);

  function resetRoom() {
    setMyId(null);
    setRoom(null);
    setQuestions([]);
    setResults({});
    setRevealed({});
    setCurrentIndex(0);
    roundRef.current = null;
  }

  function stopRetrying() {
    clearTimeout(retryRef.current.timer);
    retryRef.current = { attempt: 0, timer: null };
  }

  // Out of the room for good: back to the menu. `reason` replaces any error on screen;
  // leave it out to keep the message that's already showing.
  function endSession(reason) {
    stopRetrying();
    seatRef.current = null;
    clearSeat();
    resetRoom();
    setPhase('menu');
    if (reason !== undefined) setError(reason);
  }

  function openSocket(code, joinName) {
    joinRef.current = { code, name: joinName };
    const socket = new WebSocket(roomSocketUrl(code));
    socketRef.current = socket;
    let refused = false; // the server said this room can't be joined, so don't retry
    const joined = track(); // a slow join is most likely the server waking up

    socket.onopen = () => {
      const seat = seatRef.current;
      socket.send(
        JSON.stringify({
          type: 'join',
          name: joinName,
          token: seat && seat.code === code ? seat.token : undefined,
        })
      );
    };

    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      switch (message.type) {
        case 'welcome':
          joined();
          stopRetrying();
          seatRef.current = { code, token: message.token, name: joinRef.current.name };
          saveSeat(seatRef.current);
          setMyId(message.playerId);
          adoptSettingsRef.current = true;
          setPhase('room');
          setError('');
          break;
        case 'state':
          // How far our clock is from the server's, so timed countdowns end when the server's do
          setClockOffset(message.serverNow * 1000 - Date.now());
          if (adoptSettingsRef.current && message.settings) {
            adoptSettingsRef.current = false;
            onSettingsChange(message.settings);
          }
          setRoom(message);
          break;
        case 'reveal':
          // A timed question closed: everyone learns the answer, answered or not
          setRevealed((prev) => ({ ...prev, [message.index]: message.correctAnswer }));
          break;
        case 'answer_rejected':
          // Too late for a timed question: drop the answer we'd marked as checking
          setResults((prev) => {
            const next = { ...prev };
            if (next[message.index]?.correctAnswer === undefined) delete next[message.index];
            return next;
          });
          break;
        case 'questions':
          setQuestions(message.questions);
          questionCountRef.current = message.questions.length;
          // A new game starts from the top; the same game resent after a reconnect keeps your place
          if (message.round !== roundRef.current) {
            resumeRef.current = roundRef.current === null; // joining a game already under way
            roundRef.current = message.round;
            setResults({});
            setRevealed({});
            setCurrentIndex(0);
          }
          break;
        case 'answers': {
          // Our own answers as the server has them, after a reconnect
          setResults(Object.fromEntries(message.results.map((r) => [r.index, r])));
          setRevealed(Object.fromEntries((message.revealed ?? []).map((r) => [r.index, r.correctAnswer])));
          // After a reload we start from nothing, so carry on at the first question left to answer
          if (resumeRef.current) {
            resumeRef.current = false;
            const done = new Set(message.results.map((r) => r.index));
            const next = Array.from({ length: questionCountRef.current }, (_, i) => i).find((i) => !done.has(i));
            if (next !== undefined) setCurrentIndex(next);
          }
          break;
        }
        case 'answer_result':
          setResults((prev) => ({ ...prev, [message.index]: message }));
          break;
        case 'error':
          if (message.code === 'room_not_found' || message.code === 'room_full') refused = true;
          setError(message.message);
          break;
      }
    };

    socket.onclose = () => {
      joined();
      if (socketRef.current !== socket) return; // we left on purpose, or a newer socket took over
      socketRef.current = null;
      if (refused) {
        // Rejoining a room that's gone gets a plain explanation; a fresh join keeps the server's message
        endSession(seatRef.current ? 'That room has closed.' : undefined);
        return;
      }
      if (seatRef.current) {
        scheduleReconnect();
      } else {
        endSession('Could not join the room.');
      }
    };
  }

  function scheduleReconnect() {
    const { attempt } = retryRef.current;
    if (attempt >= RETRY_DELAYS.length) {
      endSession('Lost the connection to the room.');
      return;
    }
    setPhase('reconnecting');
    retryRef.current = {
      attempt: attempt + 1,
      timer: setTimeout(() => openSocket(seatRef.current.code, seatRef.current.name), RETRY_DELAYS[attempt]),
    };
  }

  // Back from another app or tab: try straight away instead of waiting out the delay
  useEffect(() => {
    function onVisible() {
      if (document.visibilityState !== 'visible') return;
      if (retryRef.current.timer && seatRef.current && !socketRef.current) {
        clearTimeout(retryRef.current.timer);
        retryRef.current.timer = null;
        openSocket(seatRef.current.code, seatRef.current.name);
      }
    }
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // A reload in the middle of a game: take our seat back
  useEffect(() => {
    const seat = loadSeat();
    if (seat?.code && seat?.token) {
      seatRef.current = seat;
      setPhase('connecting');
      openSocket(seat.code, seat.name);
    }
    return () => {
      // Leaving the page, or React's development double-mount: close without reconnecting
      const socket = socketRef.current;
      socketRef.current = null;
      clearTimeout(retryRef.current.timer);
      socket?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function createRoom() {
    if (!name.trim()) return setError('Enter your name first.');
    setError('');
    setPhase('connecting');
    try {
      const response = await apiFetch(apiUrl('/api/rooms'), { method: 'POST' });
      const data = await response.json();
      seatRef.current = null;
      openSocket(data.code, name.trim());
    } catch (e) {
      setPhase('menu');
      setError(e.message);
    }
  }

  function joinRoom() {
    if (!name.trim()) return setError('Enter your name first.');
    const code = codeInput.trim().toUpperCase();
    if (!code) return setError('Enter a room code.');
    setError('');
    setPhase('connecting');
    seatRef.current = null;
    openSocket(code, name.trim());
  }

  function leaveRoom() {
    const socket = socketRef.current;
    socketRef.current = null;
    try {
      socket?.send(JSON.stringify({ type: 'leave' }));
    } catch {
      // already closed; the server will free the seat when its hold runs out
    }
    socket?.close();
    endSession('');
  }

  function send(message) {
    const socket = socketRef.current;
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
  }

  function startGame() {
    setError('');
    send({ type: 'start', settings: { ...settings, amount: clampAmount(settings.amount) } });
  }

  function answer(option) {
    // Mark as picked right away so it can't be clicked twice; the server fills in the result.
    // If we're offline, the answer waits here and the server's copy replaces it on reconnect.
    setResults((prev) => ({ ...prev, [shownIndex]: { answer: option } }));
    send({ type: 'answer', index: shownIndex, answer: option });
  }

  async function copyInvite() {
    const ok = await copyText(`${window.location.origin}/?room=${room.code}`);
    setCopied(ok);
    setTimeout(() => setCopied(null), ok ? 1500 : 3000);
  }

  // ---------- Join / create screen ----------
  const inRoom = (phase === 'room' || phase === 'reconnecting') && room;
  if (!inRoom) {
    return (
      <JoinRoom
        name={name}
        onNameChange={setName}
        code={codeInput}
        onCodeChange={setCodeInput}
        connecting={phase === 'connecting'}
        rejoining={seatRef.current?.code}
        online={online}
        error={error}
        onCreate={createRoom}
        onJoin={joinRoom}
      />
    );
  }

  // ---------- Inside a room ----------
  const isHost = room.hostId === myId;
  const host = room.players.find((p) => p.id === room.hostId);
  const total = questions.length;
  const iAmDone = total > 0 && answeredCount === total;
  const current = questions[shownIndex];
  const hostControls = isHost && (
    <>
      <FoldingSettings id="room-settings" open={settingsOpen} settings={settings} onChange={onSettingsChange} idPrefix="mp-" />
      <div className="board-actions">
        <p className="load-hint">Questions are drawn from a bank of about 38,000, built from OpenTriviaQA and Wikidata.</p>
        <button className="btn btn-primary" onClick={startGame} disabled={phase === 'reconnecting'}>
          {room.status === 'finished' ? 'Play again' : 'Start game'}
        </button>
      </div>
    </>
  );

  const topScore = room.players[0]?.score ?? 0;
  const winners = room.players.filter((p) => p.score === topScore);
  const myRank = room.players.findIndex((p) => p.id === myId) + 1;

  // What the feedback line adds after an answer: the points, any speed bonus, a streak
  const result = results[shownIndex];
  let note;
  if (result?.correctAnswer !== undefined && result.correct && result.points) {
    const bonus = result.points - 100;
    note = `+${result.points} points${bonus > 0 ? `, including a +${bonus} speed bonus` : ''}.`;
    if (result.streak >= 2) note += ` ${result.streak} in a row.`;
  }

  return (
    <>
      <section className="board room-bar" aria-label="Room">
        <div className="board-body">
          <div className="room-id">
            <span className="readout-label">Room code</span>
            <FlapText text={room.code} label={room.code.split('').join(' ')} size="xl" />
          </div>
          <div className="room-actions">
            <button className="btn" onClick={copyInvite}>
              <Icon name="link" />
              {copied === null ? 'Copy invite link' : copied ? 'Copied!' : "Couldn't copy: share the code"}
            </button>
            <button className="btn btn-ghost" onClick={leaveRoom}>
              <Icon name="exit" />
              Leave
            </button>
          </div>
        </div>
      </section>

      {phase === 'reconnecting' && (
        <p className="banner banner-warn" role="status">
          <Icon name="pending" />
          Connection lost. Reconnecting… your seat and score are being held.
        </p>
      )}

      {error && <p className="error" role="alert"><Icon name="alert" />{error}</p>}

      {room.status === 'lobby' && (
        <section className="board" aria-labelledby="lobby-title">
          <div className="board-head">
            <h2 className="board-title" id="lobby-title">Quiz settings</h2>
            {isHost ? (
              <SettingsToggle open={settingsOpen} onToggle={() => setSettingsOpen((o) => !o)} controls="room-settings" />
            ) : (
              <span className="board-head-note">Chosen by {host?.name ?? 'the host'}</span>
            )}
          </div>
          <div className="board-body">
            {isHost ? (
              <>
                <p className="muted-text lobby-note">
                  Share the room code with friends, pick the settings, and start when everyone has joined.
                  Everyone sees your choices as you make them. Correct answers score 100 points, plus up to
                  50 more for answering quickly. With a time limit, everyone plays each question together
                  and moves on when time runs out or everyone has answered.
                </p>
                {hostControls}
              </>
            ) : (
              <>
                <SettingsSummary settings={room.settings ?? settings} />
                <p className="waiting">Waiting for {host?.name ?? 'the host'} to start the game…</p>
              </>
            )}
          </div>
        </section>
      )}

      {room.status === 'loading' && (
        <section className="board board-idle">
          <div className="board-body">
            <FlapText text="LOADING" label="" size="lg" />
            <p role="status">Getting questions…</p>
          </div>
        </section>
      )}

      {room.status === 'finished' && (
        <section className="board" aria-labelledby="results-title">
          <div className="board-head">
            <h2 className="board-title" id="results-title">Final results</h2>
            {isHost && (
              <SettingsToggle open={settingsOpen} onToggle={() => setSettingsOpen((o) => !o)} controls="room-settings" />
            )}
          </div>
          <div className="board-body">
            <p className="winner">
              <Icon name="trophy" size={28} />
              <span>
                {winners.map((w) => w.name).join(' & ')} {winners.length > 1 ? 'tie' : 'wins'} with {topScore} points!
              </span>
            </p>
            {me && (
              <dl className="results-stats">
                <div>
                  <dt>You finished</dt>
                  <dd>{ordinal(myRank)} of {room.players.length}</dd>
                </div>
                <div>
                  <dt>Points</dt>
                  <dd>{me.score}</dd>
                </div>
                <div>
                  <dt>Correct</dt>
                  <dd>{me.correct}/{room.questionCount}</dd>
                </div>
                <div>
                  <dt>Best streak</dt>
                  <dd>{me.bestStreak}</dd>
                </div>
              </dl>
            )}
            {me && total > 0 && (
              <ShareResult
                text={shareText({
                  title: `Quizzr · Multiplayer · ${ordinal(myRank)} of ${room.players.length}`,
                  marks,
                  lines: [`${me.score} points · ${me.correct}/${room.questionCount} correct`],
                  url: window.location.origin,
                })}
              />
            )}
            {isHost ? hostControls : <p className="muted-text">Waiting for {host?.name ?? 'the host'} to start another round…</p>}
          </div>
        </section>
      )}

      {room.status === 'finished' && <RoomLeaderboard room={room} myId={myId} />}

      {room.status === 'playing' && iAmDone && !timer && (
        <p className="banner" role="status">
          You're done! Waiting for everyone else to finish…
        </p>
      )}

      {(room.status === 'playing' || room.status === 'finished') && current && (
        <QuestionCard
          index={shownIndex}
          total={total}
          category={current.category}
          difficulty={current.difficulty}
          source={current.source}
          question={current.question}
          options={current.options}
          picked={results[shownIndex]?.answer}
          correctAnswer={results[shownIndex]?.correctAnswer ?? revealed[shownIndex]}
          closed={revealed[shownIndex] !== undefined}
          locked={Boolean(timer)}
          countdown={
            timer && {
              deadline: timer.deadline * 1000 - clockOffset, // on our clock
              limit: room.timeLimit,
              phase: timer.phase,
            }
          }
          score={me?.score ?? 0}
          scoreDigits={POINT_DIGITS}
          scoreSuffix="pts"
          scoreLabel={`Score: ${me?.score ?? 0} points`}
          streak={myStreak}
          note={note}
          marks={marks}
          onAnswer={answer}
          onPrevious={() => setCurrentIndex((i) => Math.max(0, i - 1))}
          onNext={() => setCurrentIndex((i) => Math.min(total - 1, i + 1))}
          onJump={setCurrentIndex}
        />
      )}

      {room.status !== 'finished' && <RoomLeaderboard room={room} myId={myId} />}
    </>
  );
}

export default Multiplayer;
