// Open Trivia DB categories. Like train lines on a departure board, each category gets a
// short line code, and related categories share a line colour.
export const categories = [
  { id: 9, name: 'General Knowledge', code: 'GEN', line: 'blue' },
  { id: 10, name: 'Entertainment: Books', code: 'BKS', line: 'magenta' },
  { id: 11, name: 'Entertainment: Film', code: 'FLM', line: 'magenta' },
  { id: 12, name: 'Entertainment: Music', code: 'MUS', line: 'magenta' },
  { id: 13, name: 'Entertainment: Musicals & Theatres', code: 'THR', line: 'magenta' },
  { id: 14, name: 'Entertainment: Television', code: 'TV', line: 'magenta' },
  { id: 15, name: 'Entertainment: Video Games', code: 'VG', line: 'magenta' },
  { id: 16, name: 'Entertainment: Board Games', code: 'BRD', line: 'magenta' },
  { id: 17, name: 'Science & Nature', code: 'SCI', line: 'teal' },
  { id: 18, name: 'Science: Computers', code: 'CMP', line: 'teal' },
  { id: 19, name: 'Science: Mathematics', code: 'MTH', line: 'teal' },
  { id: 20, name: 'Mythology', code: 'MYT', line: 'violet' },
  { id: 21, name: 'Sports', code: 'SPT', line: 'blue' },
  { id: 22, name: 'Geography', code: 'GEO', line: 'orange' },
  { id: 23, name: 'History', code: 'HIS', line: 'orange' },
  { id: 24, name: 'Politics', code: 'POL', line: 'orange' },
  { id: 25, name: 'Art', code: 'ART', line: 'violet' },
  { id: 26, name: 'Celebrities', code: 'CEL', line: 'magenta' },
  { id: 27, name: 'Animals', code: 'ANI', line: 'teal' },
  { id: 28, name: 'Vehicles', code: 'VEH', line: 'blue' },
  { id: 29, name: 'Entertainment: Comics', code: 'CMX', line: 'magenta' },
  { id: 30, name: 'Science: Gadgets', code: 'GDG', line: 'teal' },
  { id: 31, name: 'Entertainment: Japanese Anime & Manga', code: 'ANM', line: 'magenta' },
  { id: 32, name: 'Entertainment: Cartoon & Animations', code: 'CTN', line: 'magenta' },
];

export const anyCategory = { id: '', name: 'Any Category', code: 'ALL', line: 'any' };

export function categoryById(id) {
  return categories.find((c) => String(c.id) === String(id)) ?? anyCategory;
}

export function categoryByName(name) {
  return categories.find((c) => c.name === name);
}

// A category's name as players see it: "Entertainment: Video Games" reads as "Video Games" and
// "Science: Computers" as "Computers". The line badge beside it already shows the family.
// (The full name stays in the data, because Open Trivia DB uses it to identify the category.)
export function categoryLabel(name) {
  return String(name ?? '').replace(/^(Entertainment|Science): /, '');
}

// A choice of categories in a few words: "Any category", one name, two names, or a count
export function categoriesSummary(ids) {
  if (!ids?.length) return 'Any category';
  const labels = ids.map((id) => categoryLabel(categoryById(id).name));
  return labels.length <= 2 ? labels.join(' & ') : `${labels.length} categories`;
}

// Difficulty levels: a line colour plus a count of pips, so it never relies on colour alone
export const difficulties = [
  { value: 'easy', label: 'Easy', accent: 'teal', pips: 1 },
  { value: 'medium', label: 'Medium', accent: 'orange', pips: 2 },
  { value: 'hard', label: 'Hard', accent: 'magenta', pips: 3 },
];

export function difficultyByValue(value) {
  return difficulties.find((d) => d.value === value);
}

// The line colours, also used to tell players apart on the leaderboard
export const lines = ['blue', 'magenta', 'teal', 'orange', 'violet'];

// What each line carries, for the line map beside the quiz
export const lineNames = {
  magenta: 'Entertainment & Celebrities',
  teal: 'Science & Animals',
  orange: 'History, Geography & Politics',
  violet: 'Art & Mythology',
  blue: 'General, Sports & Vehicles',
};
