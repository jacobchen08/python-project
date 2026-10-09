// Quiz settings shared by solo and multiplayer: how many questions, which categories (a list
// of Open Trivia DB category ids; empty means any), the difficulty and type, and the time per
// question ('' means "any" or "off").

export const DEFAULT_SETTINGS = { amount: 10, categories: [], difficulty: '', type: '', timer: '' };

export const MIN_QUESTIONS = 1;
export const MAX_QUESTIONS = 50; // Open Trivia DB hands out at most 50 at a time

// The number of questions as a whole number from 1 to 50, whatever was typed into the box
// (it can be empty, 0 or 999 while someone is typing)
export function clampAmount(value) {
  if (value === '' || value == null) return DEFAULT_SETTINGS.amount;
  const number = Math.round(Number(value));
  if (!Number.isFinite(number)) return DEFAULT_SETTINGS.amount;
  return Math.min(Math.max(number, MIN_QUESTIONS), MAX_QUESTIONS);
}
