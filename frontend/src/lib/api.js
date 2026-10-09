import { apiFetch } from './serverStatus';
import { clampAmount } from './settings';

// Where the API lives.
// - Development, and the single-service deploy: the same origin as the page. In development
//   vite.config.js proxies /api to the FastAPI server on port 8000.
// - Frontend hosted as its own static site: set VITE_API_HOST (e.g. quizzr-api.onrender.com)
//   at build time, and every request goes there instead.
const API_HOST = (import.meta.env.VITE_API_HOST ?? '').trim();
const API_ORIGIN = API_HOST ? (API_HOST.includes('://') ? API_HOST : `https://${API_HOST}`).replace(/\/$/, '') : '';

export function apiUrl(path) {
  return `${API_ORIGIN}${path}`;
}

export function questionsUrl(settings) {
  const params = new URLSearchParams({
    amount: clampAmount(settings.amount),
    category: settings.categories?.length ? settings.categories.join(',') : 'all', // e.g. "22,23"
    difficulty: settings.difficulty || 'all',
    type: settings.type || 'all',
  });
  return apiUrl(`/api/questions?${params}`);
}

// Daily challenge. Errors come back as { detail } from FastAPI; turn them into thrown Errors.
async function dailyRequest(path, options) {
  const response = await apiFetch(apiUrl(`/api/daily${path}`), options); // throws a readable Error when it can't connect
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof data.detail === 'string' ? data.detail : 'Something went wrong. Try again.';
    throw new Error(detail);
  }
  return data;
}

function post(body) {
  return { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) };
}

export const daily = {
  // the token goes in a header, never the URL, so it stays out of logs and history
  load: (token) => dailyRequest('', { headers: { 'X-Quizzr-Token': token } }),
  start: (token, name) => dailyRequest('/start', post({ token, name })),
  // `date` is the day the run started, so a run that crosses midnight (UTC) still counts
  answer: (token, index, answer, date) => dailyRequest('/answer', post({ token, index, answer, date })),
  leaderboard: (token, date) =>
    dailyRequest(date ? `/leaderboard?date=${date}` : '/leaderboard', { headers: { 'X-Quizzr-Token': token } }),
};

export function roomSocketUrl(code) {
  const origin = API_ORIGIN || window.location.origin;
  return `${origin.replace(/^http/, 'ws')}/api/ws/${code}`;
}
