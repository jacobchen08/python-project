import asyncio
import json
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

import logs
from ratelimit import RateLimiter, limited
from trivia import TriviaError, fetch_questions, parse_categories, prepare_question, public_question

# Multiplayer flow:
# 1. POST /api/rooms creates a room and returns its code.
# 2. Each player opens a WebSocket to /api/ws/{code} and sends {"type": "join", "name": ...}.
#    The server answers with {"type": "welcome", "playerId", "token"}. The first player is the host.
# 3. The host sends {"type": "start", "settings": {...}}; everyone receives the same questions.
# 4. Players send {"type": "answer", "index": i, "answer": "..."}; the server checks it
#    (correct answers are never sent to the browser before answering) and broadcasts the scores.
# 5. {"type": "leave"} gives up your seat straight away.
#
# Reconnecting: if a socket drops without "leave" (a phone switching apps, a flaky network),
# the player's seat is held for RECONNECT_GRACE seconds. Joining again with
# {"type": "join", "token": ...} puts them back in their seat with their answers and score.
#
# Scoring: a correct answer is worth BASE_POINTS plus a speed bonus of up to SPEED_BONUS,
# measured from the start of the game or the player's previous answer. Streaks count
# correct answers in a row.
#
# Timed games (settings.timer = 10, 20 or 30 seconds) run in lockstep on the server's clock:
# one question is open at a time, for everyone. It closes when its time is up or when every
# connected player has answered, then the answer is revealed to all ({"type": "reveal"}),
# and REVEAL_SECONDS later the next one opens. Answers that arrive after the deadline are
# refused. The state message carries the open question and its deadline, plus the server's
# clock so browsers can count down accurately.
#
# Rooms live in memory, so they disappear if the server restarts.

router = APIRouter(prefix="/api")

ROOM_CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I to avoid confusion
ROOM_CODE_LENGTH = 5
MAX_PLAYERS = 20
EMPTY_ROOM_TTL = 10 * 60  # seconds a created room can sit with nobody in it
RECONNECT_GRACE = 90  # seconds a disconnected player's seat is held for them

BASE_POINTS = 100
SPEED_BONUS = 50
BONUS_FULL_SECONDS = 5  # answer within this long for the whole bonus
BONUS_ZERO_SECONDS = 20  # after this long there's no bonus left

TIMER_CHOICES = {10, 20, 30}  # seconds per question in a timed game
REVEAL_SECONDS = 3  # pause on the revealed answer before the next question opens
ANSWER_GRACE = 0.75  # seconds of network delay forgiven after a deadline

# Abuse limits: every legitimate message is tiny, and nobody needs more than a few a second
MAX_MESSAGE_CHARS = 2000
MESSAGES_PER_WINDOW = 40
MESSAGE_WINDOW = 10  # seconds
room_limit = RateLimiter(limit=10, window=60)  # rooms one address can create per minute

rooms = {}
_seat_timers = set()  # keeps pending seat-expiry tasks alive until they run


# ---------- Scoring ----------

def speed_bonus(elapsed):
    """Bonus points for a correct answer given `elapsed` seconds after the previous one."""
    if elapsed <= BONUS_FULL_SECONDS:
        return SPEED_BONUS
    if elapsed >= BONUS_ZERO_SECONDS:
        return 0
    remaining = (BONUS_ZERO_SECONDS - elapsed) / (BONUS_ZERO_SECONDS - BONUS_FULL_SECONDS)
    return round(SPEED_BONUS * remaining)


# ---------- Settings the host chooses ----------

DEFAULT_SETTINGS = {"amount": 10, "categories": [], "difficulty": "", "type": "", "timer": ""}


def timer_setting(settings):
    try:
        seconds = int(settings.get("timer") or 0)
    except (TypeError, ValueError):
        return 0
    return seconds if seconds in TIMER_CHOICES else 0


def clean_settings(settings):
    """The host's quiz settings, kept to values the game understands, to share with the room."""
    if not isinstance(settings, dict):
        return dict(DEFAULT_SETTINGS)
    try:
        amount = max(1, min(int(settings.get("amount")), 50))
    except (TypeError, ValueError):
        amount = DEFAULT_SETTINGS["amount"]
    # a list of category ids; older browsers send one "category" instead
    categories = parse_categories(settings.get("categories") if "categories" in settings else settings.get("category"))
    difficulty = settings.get("difficulty") or ""
    qtype = settings.get("type") or ""
    timer = timer_setting(settings)
    return {
        "amount": amount,
        "categories": categories,
        "difficulty": difficulty if difficulty in ("easy", "medium", "hard") else "",
        "type": qtype if qtype in ("multiple", "boolean") else "",
        "timer": str(timer) if timer else "",
    }


# ---------- Players and rooms ----------

class Player:
    def __init__(self, name, ws):
        self.id = secrets.token_hex(4)
        self.token = secrets.token_urlsafe(16)  # proves who you are when you reconnect
        self.name = name
        self.ws = ws
        self.connected = True
        self.left_at = None
        self.reset()

    def reset(self):
        self.score = 0  # points
        self.correct = 0
        self.streak = 0
        self.best_streak = 0
        self.answers = {}  # question index -> {"answer", "correct", "points"}
        self.last_answer_at = time.time()

    def record(self, index, answer, correct, now):
        """Store an answer and return the points it earned."""
        elapsed = now - self.last_answer_at
        self.last_answer_at = now
        points = BASE_POINTS + speed_bonus(elapsed) if correct else 0
        self.answers[index] = {"answer": answer, "correct": correct, "points": points}
        if correct:
            self.score += points
            self.correct += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.streak = 0
        return points


class Room:
    def __init__(self, code):
        self.code = code
        self.players = {}
        self.host_id = None
        self.status = "lobby"  # lobby -> loading -> playing -> finished
        self.questions = []
        self.round = 0  # goes up with every game, so clients can tell a new game from a resend
        self.created_at = time.time()
        # timed games only
        self.time_limit = 0  # seconds per question; 0 means untimed
        self.current = None  # index of the question everyone is on
        self.question_phase = None  # "open" while answers count, then "reveal"
        self.opened_at = None
        self.deadline = None
        self.revealed = {}  # question index -> correct answer, once that question has closed
        self.clock_task = None
        self.settings = dict(DEFAULT_SETTINGS)  # the host's current choices, shown to everyone

    def connected_players(self):
        return [p for p in self.players.values() if p.connected]

    def find_by_token(self, token):
        if not token:
            return None
        given = str(token).encode()  # as bytes: compare_digest refuses non-ASCII strings
        return next((p for p in self.players.values() if secrets.compare_digest(p.token.encode(), given)), None)

    def pass_host_if_needed(self):
        """Keep a connected host whenever anyone is connected."""
        host = self.players.get(self.host_id)
        if host is not None and host.connected:
            return
        active = self.connected_players()
        if active:
            self.host_id = active[0].id
        elif host is None:
            self.host_id = next(iter(self.players), None)

    def state_message(self):
        players = sorted(self.players.values(), key=lambda p: (-p.score, -p.correct, p.name.lower()))
        return {
            "type": "state",
            "code": self.code,
            "status": self.status,
            "hostId": self.host_id,
            "questionCount": len(self.questions),
            "timeLimit": self.time_limit,
            "settings": self.settings,
            "timer": (
                {"index": self.current, "phase": self.question_phase, "deadline": self.deadline}
                if self.time_limit and self.status == "playing"
                else None
            ),
            "serverNow": time.time(),  # lets browsers line their countdown up with our clock
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "score": p.score,
                    "correct": p.correct,
                    "streak": p.streak,
                    "bestStreak": p.best_streak,
                    "answered": len(p.answers),
                    "connected": p.connected,
                }
                for p in players
            ],
        }

    def questions_message(self):
        # Everything except the correct answers
        return {
            "type": "questions",
            "round": self.round,
            "questions": [public_question(q) for q in self.questions],
        }

    def answers_message(self, player):
        """A returning player's own answers, so their screen can pick up where it was."""
        return {
            "type": "answers",
            "round": self.round,
            "results": [
                {
                    "index": index,
                    "answer": a["answer"],
                    "correct": a["correct"],
                    "correctAnswer": self.questions[index]["correct"],
                    "points": a["points"],
                }
                for index, a in sorted(player.answers.items())
            ],
            # timed games: closed questions this player didn't answer still show the answer
            "revealed": [{"index": i, "correctAnswer": c} for i, c in sorted(self.revealed.items())],
        }

    def everyone_finished(self):
        # Only players who are here right now: nobody waits on a seat that's being held
        total = len(self.questions)
        active = self.connected_players()
        return total > 0 and bool(active) and all(len(p.answers) == total for p in active)

    async def broadcast(self, message):
        for player in self.connected_players():
            try:
                await player.ws.send_json(message)
            except Exception:
                pass  # that player's disconnect is handled by their own socket loop


# ---------- Opening rooms, holding seats and giving them up ----------

def new_room_code():
    while True:
        code = "".join(secrets.choice(ROOM_CODE_CHARS) for _ in range(ROOM_CODE_LENGTH))
        if code not in rooms:
            return code


def prune_empty_rooms():
    now = time.time()
    for code, room in list(rooms.items()):
        if not room.players and now - room.created_at > EMPTY_ROOM_TTL:
            del rooms[code]


def remove_player(room, player):
    room.players.pop(player.id, None)
    if not room.players:
        rooms.pop(room.code, None)
        stop_clock(room)
    else:
        room.pass_host_if_needed()


def expire_seat(room, player, now=None):
    """Give up a disconnected player's seat once the grace period is over. True if removed."""
    now = time.time() if now is None else now
    if player.connected or room.players.get(player.id) is not player or player.left_at is None:
        return False
    if now - player.left_at < RECONNECT_GRACE:
        return False
    remove_player(room, player)
    return True


async def expire_seat_later(room, player):
    await asyncio.sleep(RECONNECT_GRACE)
    if expire_seat(room, player) and room.code in rooms:
        await settle(room)


async def hold_seat(room, player):
    """The player's socket closed without "leave": keep their seat for a while."""
    player.connected = False
    player.left_at = time.time()
    player.ws = None
    room.pass_host_if_needed()
    await settle(room)
    task = asyncio.create_task(expire_seat_later(room, player))
    _seat_timers.add(task)
    task.add_done_callback(_seat_timers.discard)


async def settle(room):
    """Move the game on if everyone here is done, then tell everyone the new state."""
    if room.status == "playing":
        if room.time_limit:
            # Timed: close the open question as soon as everyone connected has answered it
            active = room.connected_players()
            if room.question_phase == "open" and active and all(room.current in p.answers for p in active):
                await close_question(room, room.current)
                return  # close_question sends the new state
        elif room.everyone_finished():
            room.status = "finished"
            logs.log_event("game_finished", code=room.code, players=len(room.players))
    await room.broadcast(room.state_message())


# ---------- The clock for timed games ----------

def stop_clock(room):
    task = room.clock_task
    room.clock_task = None
    if task is not None and task is not asyncio.current_task():
        task.cancel()


def start_clock(room, step):
    """Run the next timed step, replacing whatever the clock was waiting on."""
    stop_clock(room)
    room.clock_task = asyncio.create_task(step)


def room_is_live(room):
    return rooms.get(room.code) is room and room.status == "playing"


async def open_question(room, index):
    now = time.time()
    room.current = index
    room.question_phase = "open"
    room.opened_at = now
    room.deadline = now + room.time_limit
    for player in room.players.values():
        player.last_answer_at = now  # the speed bonus counts from the moment it opens
    start_clock(room, close_after(room, index, room.time_limit))
    await room.broadcast(room.state_message())


async def close_after(room, index, delay):
    await asyncio.sleep(delay)
    await close_question(room, index)


async def close_question(room, index):
    if not room_is_live(room) or room.current != index or room.question_phase != "open":
        return
    room.question_phase = "reveal"
    correct = room.questions[index]["correct"]
    room.revealed[index] = correct
    for player in room.players.values():
        if index not in player.answers:
            player.streak = 0  # running out of time breaks a streak
    await room.broadcast({"type": "reveal", "index": index, "correctAnswer": correct})
    await room.broadcast(room.state_message())
    start_clock(room, advance_after(room, index))


async def advance_after(room, index):
    await asyncio.sleep(REVEAL_SECONDS)
    if not room_is_live(room) or room.current != index:
        return
    if index + 1 < len(room.questions):
        await open_question(room, index + 1)
    else:
        room.status = "finished"
        logs.log_event("game_finished", code=room.code, players=len(room.players), timed=True)
        room.current = room.question_phase = room.deadline = None
        room.clock_task = None
        await room.broadcast(room.state_message())


# ---------- Playing a game ----------

async def start_game(room, settings):
    room.status = "loading"
    await room.broadcast(room.state_message())
    try:
        raw = await asyncio.to_thread(
            fetch_questions,
            settings.get("amount", 10),
            ",".join(settings.get("categories") or []) or "all",
            settings.get("difficulty") or "all",
            settings.get("type") or "all",
        )
    except TriviaError as e:
        room.status = "lobby" if not room.questions else "finished"
        await room.broadcast({"type": "error", "message": str(e)})
        await room.broadcast(room.state_message())
        return

    room.questions = [prepare_question(q) for q in raw]
    room.round += 1
    room.time_limit = timer_setting(settings)
    room.revealed = {}
    room.current = room.question_phase = room.deadline = None
    stop_clock(room)
    for player in room.players.values():
        player.reset()
    room.status = "playing"
    logs.log_event(
        "game_started",
        code=room.code,
        players=len(room.players),
        questions=len(room.questions),
        timer=room.time_limit,
        categories=settings.get("categories") or ["any"],
    )
    await room.broadcast(room.questions_message())
    if room.time_limit:
        await open_question(room, 0)  # sends the state with the first deadline
    else:
        await room.broadcast(room.state_message())


async def submit_answer(room, player, index, answer):
    if room.status != "playing":
        return
    if not isinstance(index, int) or not 0 <= index < len(room.questions):
        return
    if index in player.answers:
        return
    if room.time_limit:
        # Timed: only the open question counts, and only until its deadline
        on_time = room.question_phase == "open" and time.time() <= room.deadline + ANSWER_GRACE
        if index != room.current or not on_time:
            await player.ws.send_json({"type": "answer_rejected", "index": index, "message": "Time's up for that question."})
            return

    answer = str(answer)  # whatever the message held, store and echo it as text
    question = room.questions[index]
    correct = answer == question["correct"]
    points = player.record(index, answer, correct, time.time())

    await player.ws.send_json({
        "type": "answer_result",
        "index": index,
        "answer": answer,
        "correct": correct,
        "correctAnswer": question["correct"],
        "points": points,
        "streak": player.streak,
    })
    await settle(room)


async def handle_message(room, player, message):
    kind = message.get("type")
    if kind == "start":
        if player.id == room.host_id and room.status in ("lobby", "finished"):
            room.settings = clean_settings(message.get("settings"))
            await start_game(room, room.settings)
    elif kind == "settings":
        # The host changing settings in the lobby: everyone sees the new choices straight away
        if player.id == room.host_id and room.status in ("lobby", "finished"):
            room.settings = clean_settings(message.get("settings"))
            await room.broadcast(room.state_message())
    elif kind == "answer":
        await submit_answer(room, player, message.get("index"), message.get("answer"))


# ---------- HTTP routes ----------

@router.post("/rooms", dependencies=[Depends(limited(room_limit, "You're creating rooms too quickly. Wait a minute and try again."))])
def create_room():
    prune_empty_rooms()
    room = Room(new_room_code())
    rooms[room.code] = room
    logs.log_event("room_created", code=room.code, open_rooms=len(rooms))
    return {"code": room.code}


@router.get("/rooms/{code}")
def get_room(code: str):
    room = rooms.get(code.upper())
    if room is None:
        raise HTTPException(status_code=404, detail="Room not found")
    return {"code": room.code, "status": room.status, "playerCount": len(room.players)}


# ---------- The WebSocket each player keeps open ----------

async def receive_message(ws):
    text = await ws.receive_text()
    if len(text) > MAX_MESSAGE_CHARS:
        return {}  # far bigger than any real message: ignore it
    try:
        message = json.loads(text)
    except ValueError:
        return {}
    return message if isinstance(message, dict) else {}


async def refuse(ws, code, message):
    await ws.send_json({"type": "error", "code": code, "message": message})
    await ws.close()


@router.websocket("/ws/{code}")
async def room_socket(ws: WebSocket, code: str):
    await ws.accept()

    room = rooms.get(code.upper())
    if room is None:
        await refuse(ws, "room_not_found", "Room not found. Check the code and try again.")
        return

    # First message must be the join message: a name, plus a token when reconnecting
    try:
        join = await receive_message(ws)
    except WebSocketDisconnect:
        return
    if rooms.get(room.code) is not room:  # the room closed while we waited
        await refuse(ws, "room_not_found", "That room has closed.")
        return

    player = room.find_by_token(join.get("token"))
    if player is not None:
        # Back in their held seat; a newer connection replaces an older one
        old_ws = player.ws
        player.ws = ws
        player.connected = True
        player.left_at = None
        if old_ws is not None:
            try:
                await old_ws.close()
            except Exception:
                pass
    else:
        if len(room.players) >= MAX_PLAYERS:
            await refuse(ws, "room_full", "That room is full.")
            return
        name = str(join.get("name", "")).strip()[:20] or "Player"
        player = Player(name, ws)
        room.players[player.id] = player
    room.pass_host_if_needed()

    leaving = False
    try:
        await ws.send_json({"type": "welcome", "playerId": player.id, "token": player.token})
        if room.status in ("playing", "finished"):
            await ws.send_json(room.questions_message())
            await ws.send_json(room.answers_message(player))
        await room.broadcast(room.state_message())

        flood = RateLimiter(limit=MESSAGES_PER_WINDOW, window=MESSAGE_WINDOW)
        while True:
            message = await receive_message(ws)
            if message.get("type") == "leave":
                leaving = True
                break
            if not flood.allow(player.id):
                continue  # a flood of messages: drop the extras rather than let one socket hog the room
            await handle_message(room, player, message)
    except WebSocketDisconnect:
        pass
    finally:
        if player.ws is ws:  # skip if a newer connection has taken over this seat
            if leaving:
                remove_player(room, player)
                if room.code in rooms:
                    await settle(room)
            else:
                await hold_seat(room, player)
