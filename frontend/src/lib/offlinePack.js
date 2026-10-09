import { apiUrl } from './api';
import { categoryById } from './categories';
import { shuffle } from './questions';
import { clampAmount } from './settings';
import { KEYS, readStoredJson, writeStored } from './storage';

// A pack of questions saved in this browser, so solo play still works offline.
//
// While online, the app quietly keeps the pack topped up (one request for 50 questions,
// made after the page has settled, and only when the pack is small or a few days old).
// Offline, Generate deals from it: questions that match the settings, never one already
// dealt. Questions are stored in Open Trivia DB's own shape, exactly as the API returns them.

const PACK_SIZE = 50;
const REFILL_BELOW = 20;
const MAX_AGE_MS = 3 * 24 * 60 * 60 * 1000;

export class OfflinePackError extends Error {}

function read() {
  const pack = readStoredJson(KEYS.offlinePack);
  return pack && Array.isArray(pack.questions) ? pack : { savedAt: 0, questions: [] };
}

// false when storage is full or blocked: offline play just won't be available
function write(pack) {
  return writeStored(KEYS.offlinePack, JSON.stringify(pack));
}

export function packSize() {
  return read().questions.length;
}

export function needsRefill(now = Date.now()) {
  const pack = read();
  return pack.questions.length < REFILL_BELOW || now - pack.savedAt > MAX_AGE_MS;
}

// Top the pack up from the API. Quiet on failure: this is a background nicety.
export async function refillPack() {
  if (!navigator.onLine || !needsRefill()) return false;
  try {
    const response = await fetch(apiUrl(`/api/questions?amount=${PACK_SIZE}&refill=true`));
    const data = await response.json();
    if (!Array.isArray(data) || data.length === 0) return false;
    // keep any saved questions that are still unplayed, add the new ones, drop duplicates
    const seen = new Set();
    const questions = [...data, ...read().questions].filter((q) => {
      if (seen.has(q.question)) return false;
      seen.add(q.question);
      return true;
    });
    return write({ savedAt: Date.now(), questions: questions.slice(0, PACK_SIZE * 2) });
  } catch {
    return false;
  }
}

function matches(question, settings) {
  const wanted = settings.categories ?? [];
  if (wanted.length && !wanted.some((id) => question.category === categoryById(id).name)) return false;
  if (settings.difficulty && question.difficulty !== settings.difficulty) return false;
  if (settings.type && question.type !== settings.type) return false;
  return true;
}

// Deal a round from the pack. The dealt questions are taken out, so offline rounds never repeat.
export function dealFromPack(settings) {
  const amount = clampAmount(settings.amount);
  const pack = read();
  const fitting = pack.questions.filter((q) => matches(q, settings));

  if (fitting.length === 0) {
    throw new OfflinePackError(
      pack.questions.length === 0
        ? "You're offline and there are no saved questions yet. Play once while connected and some will be saved for next time."
        : `You're offline, and none of your ${pack.questions.length} saved questions match these settings. Try Any category, difficulty and type.`
    );
  }
  if (fitting.length < amount) {
    throw new OfflinePackError(
      `You're offline, and only ${fitting.length} saved question${fitting.length === 1 ? '' : 's'} match these settings. Ask for ${fitting.length} or fewer, or widen the settings.`
    );
  }

  const dealt = shuffle(fitting).slice(0, amount);
  const used = new Set(dealt.map((q) => q.question));
  write({ ...pack, questions: pack.questions.filter((q) => !used.has(q.question)) });
  return dealt;
}
