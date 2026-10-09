import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { dealFromPack, needsRefill, OfflinePackError, packSize, refillPack } from './offlinePack';

const question = (n, extra = {}) => ({
  type: 'multiple',
  difficulty: 'easy',
  category: 'General Knowledge',
  question: `Question ${n}`,
  correct_answer: `Right ${n}`,
  incorrect_answers: ['a', 'b', 'c'],
  ...extra,
});

function savePack(questions, savedAt = Date.now()) {
  localStorage.setItem('quizzr-offline-pack', JSON.stringify({ savedAt, questions }));
}

const settings = (extra = {}) => ({ amount: 3, categories: [], difficulty: '', type: '', timer: '', ...extra });

describe('the offline question pack', () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => vi.unstubAllGlobals());

  it('deals a round and never deals the same question twice', () => {
    savePack([1, 2, 3, 4, 5, 6].map((n) => question(n)));
    const first = dealFromPack(settings());
    const second = dealFromPack(settings());
    expect(first).toHaveLength(3);
    expect(second).toHaveLength(3);
    const all = [...first, ...second].map((q) => q.question);
    expect(new Set(all).size).toBe(6);
    expect(packSize()).toBe(0);
  });

  it('only deals questions that match the settings', () => {
    savePack([
      question(1, { category: 'Geography', difficulty: 'hard' }),
      question(2, { category: 'Geography', difficulty: 'easy' }),
      question(3, { category: 'History', difficulty: 'hard' }),
    ]);
    const dealt = dealFromPack(settings({ amount: 1, categories: ['22'], difficulty: 'hard' })); // 22 = Geography
    expect(dealt.map((q) => q.question)).toEqual(['Question 1']);
  });

  it('deals from any of several chosen categories', () => {
    savePack([
      question(1, { category: 'Geography' }),
      question(2, { category: 'History' }),
      question(3, { category: 'Art' }),
    ]);
    const dealt = dealFromPack(settings({ amount: 2, categories: ['22', '23'] })); // Geography, History
    expect(dealt.map((q) => q.category).sort()).toEqual(['Geography', 'History']);
  });

  it('explains when there are too few matching questions, and keeps the pack intact', () => {
    savePack([question(1), question(2)]);
    expect(() => dealFromPack(settings({ amount: 5 }))).toThrow(OfflinePackError);
    expect(() => dealFromPack(settings({ amount: 5 }))).toThrow(/only 2 saved questions match/);
    expect(packSize()).toBe(2);
  });

  it('explains when nothing has been saved yet', () => {
    expect(() => dealFromPack(settings())).toThrow(/no saved questions yet/);
  });

  it('asks for a refill when the pack is small or old', () => {
    savePack(Array.from({ length: 30 }, (_, i) => question(i)));
    expect(needsRefill()).toBe(false);
    savePack(Array.from({ length: 30 }, (_, i) => question(i)), Date.now() - 4 * 24 * 3600 * 1000);
    expect(needsRefill()).toBe(true);
    savePack([question(1)]);
    expect(needsRefill()).toBe(true);
  });

  it('refills from the API, keeping unplayed questions and dropping duplicates', async () => {
    savePack([question(1), question(2)]);
    vi.stubGlobal('fetch', vi.fn(async () => ({ json: async () => [question(2), question(3), question(4)] })));
    expect(await refillPack()).toBe(true);
    expect(packSize()).toBe(4);
  });

  it("doesn't try to refill while offline", async () => {
    vi.stubGlobal('fetch', vi.fn());
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false);
    expect(await refillPack()).toBe(false);
    expect(fetch).not.toHaveBeenCalled();
  });
});
