import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import QuestionCard from './QuestionCard';

function renderCard(props = {}) {
  const onAnswer = vi.fn();
  const utils = render(
    <QuestionCard
      index={0}
      total={3}
      category="History"
      difficulty="medium"
      question="In what year did the Berlin Wall fall?"
      options={['1987', '1989', '1991', '1993']}
      picked={undefined}
      correctAnswer="1989"
      score={0}
      marks={[undefined, undefined, undefined]}
      onAnswer={onAnswer}
      onPrevious={() => {}}
      onNext={() => {}}
      onJump={() => {}}
      {...props}
    />
  );
  return { onAnswer, ...utils };
}

describe('QuestionCard', () => {
  it('only counts an answer once it is submitted', async () => {
    const user = userEvent.setup();
    const { onAnswer } = renderCard();
    const submit = screen.getByRole('button', { name: 'Submit answer' });

    expect(submit).toBeDisabled();
    await user.click(screen.getByRole('button', { name: /1987/ }));
    await user.click(screen.getByRole('button', { name: /1989/ })); // changed their mind
    expect(onAnswer).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /1989/ })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: /1987/ })).toHaveAttribute('aria-pressed', 'false');

    await user.click(submit);
    expect(onAnswer).toHaveBeenCalledOnce();
    expect(onAnswer).toHaveBeenCalledWith('1989');
  });

  it('shows the result in words, not only colour, once answered', () => {
    renderCard({ picked: '1987', marks: ['wrong', undefined, undefined], note: '3 in a row.' });
    expect(screen.getByRole('status')).toHaveTextContent('Not quite. The answer is 1989.');
    expect(screen.getByText('Your answer')).toBeInTheDocument();
    expect(screen.getByText('Correct')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Submit answer' })).not.toBeInTheDocument();
    for (const option of ['1987', '1989', '1991', '1993']) {
      expect(screen.getByRole('button', { name: new RegExp(option) })).toBeDisabled();
    }
  });

  it('shows the category, difficulty and streak', () => {
    renderCard({ streak: 3 });
    expect(screen.getByText('History')).toBeInTheDocument();
    expect(screen.getByText('Medium')).toBeInTheDocument();
    expect(screen.getByText('Streak: 3 in a row')).toBeInTheDocument();
  });

  it('marks questions from the question bank, and only those', () => {
    const { rerender } = renderCard({ source: 'bank' });
    expect(screen.getByText('Bank')).toBeInTheDocument();
    rerender(
      <QuestionCard index={0} total={3} category="History" difficulty="medium" question="Q" options={['A', 'B']}
        score={0} marks={[]} source="opentdb" onAnswer={() => {}} onPrevious={() => {}} onNext={() => {}} onJump={() => {}} />
    );
    expect(screen.queryByText('Bank')).not.toBeInTheDocument();
  });

  it('offers the finish action in place of Next when the round is done', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    renderCard({ index: 2, picked: '1989', finishAction: { label: 'See results', onClick } });
    expect(screen.queryByRole('button', { name: /^Next/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /See results/ }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('counts down a timed question and locks the navigation', () => {
    renderCard({
      locked: true,
      countdown: { deadline: Date.now() + 8000, limit: 10, phase: 'open' },
    });
    expect(screen.getByText('8 seconds left')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Previous/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /^Next/ })).not.toBeInTheDocument();
    expect(screen.getByText('Everyone is on this question together.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Question 2' })).toBeDisabled();
  });

  it("shows the answer when time runs out before you answer", () => {
    renderCard({
      locked: true,
      closed: true,
      marks: ['timeout', undefined, undefined],
      countdown: { deadline: Date.now() - 500, limit: 10, phase: 'reveal' },
    });
    expect(screen.getByRole('status')).toHaveTextContent("Time's up. The answer is 1989.");
    expect(screen.getByText('Correct')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Submit answer' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /1987/ })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Question 1, ran out of time' })).toBeInTheDocument();
    expect(screen.getByText('Next question coming up…')).toBeInTheDocument();
  });

  it('lets a solo player move on themselves once a timed question is done', async () => {
    const user = userEvent.setup();
    const onClick = vi.fn();
    renderCard({
      locked: true,
      picked: '1989',
      marks: ['correct', undefined, undefined],
      countdown: { deadline: Date.now() + 4000, limit: 10, phase: 'reveal' },
      finishAction: { label: 'Next question', onClick },
    });
    expect(screen.queryByRole('button', { name: /Previous/ })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /Next question/ }));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('plays from the keyboard: a letter chooses, Enter submits', async () => {
    const user = userEvent.setup();
    const { onAnswer } = renderCard();
    await user.keyboard('c');
    expect(screen.getByRole('button', { name: /1991/ })).toHaveAttribute('aria-pressed', 'true');
    await user.keyboard('2');
    expect(screen.getByRole('button', { name: /1989/ })).toHaveAttribute('aria-pressed', 'true');
    await user.keyboard('{Enter}');
    expect(onAnswer).toHaveBeenCalledWith('1989');
  });

  it('moves between questions with the arrow keys, but not while locked', async () => {
    const user = userEvent.setup();
    const onNext = vi.fn();
    const onPrevious = vi.fn();
    const { rerender } = renderCard({ index: 1, onNext, onPrevious });
    await user.keyboard('{ArrowRight}{ArrowLeft}');
    expect(onNext).toHaveBeenCalledOnce();
    expect(onPrevious).toHaveBeenCalledOnce();

    rerender(
      <QuestionCard
        index={1}
        total={3}
        question="Locked"
        options={['x', 'y']}
        marks={[]}
        score={0}
        locked
        onAnswer={() => {}}
        onNext={onNext}
        onPrevious={onPrevious}
      />
    );
    await user.keyboard('{ArrowRight}{ArrowLeft}');
    expect(onNext).toHaveBeenCalledOnce();
    expect(onPrevious).toHaveBeenCalledOnce();
  });

  it('ignores shortcuts on a board whose tab is hidden', async () => {
    const user = userEvent.setup();
    const onAnswer = vi.fn();
    render(
      <div hidden>
        <QuestionCard
          index={0}
          total={1}
          question="Hidden"
          options={['x', 'y']}
          marks={[]}
          score={0}
          onAnswer={onAnswer}
        />
      </div>
    );
    await user.keyboard('a{Enter}');
    expect(onAnswer).not.toHaveBeenCalled();
  });

  it('jumps to a question from the step row', async () => {
    const user = userEvent.setup();
    const onJump = vi.fn();
    renderCard({ onJump, marks: ['correct', undefined, undefined] });
    await user.click(screen.getByRole('button', { name: 'Question 3' }));
    expect(onJump).toHaveBeenCalledWith(2);
    expect(screen.getByRole('button', { name: 'Question 1, correct' })).toHaveAttribute('aria-current', 'step');
  });
});
