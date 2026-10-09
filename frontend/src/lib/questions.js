// Turning Open Trivia DB questions into ones solo play can show.
//
// Open Trivia DB sends text with HTML entities (&quot;, &#039;) and keeps the correct answer
// apart from the wrong ones. Solo play decodes the text and shuffles the options once, so
// going back to a question shows them where they were. (Daily and multiplayer questions
// arrive ready to show: the server does this in backend/trivia.py.)

function decodeHtml(html) {
  const txt = document.createElement('textarea');
  txt.innerHTML = html;
  return txt.value;
}

export function shuffle(list) {
  const copy = [...list];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

// One question in Open Trivia DB's shape, ready to play: { question, category, difficulty, source, correct, options }
export function toQuestion(item) {
  const correct = decodeHtml(item.correct_answer);
  return {
    question: decodeHtml(item.question),
    category: decodeHtml(item.category),
    difficulty: item.difficulty,
    source: item.source,
    correct,
    options:
      item.type === 'multiple'
        ? shuffle([correct, ...item.incorrect_answers.map((a) => decodeHtml(a))])
        : ['True', 'False'],
  };
}
