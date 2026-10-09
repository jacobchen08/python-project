import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import CategoryPicker from './CategoryPicker';
import { categoriesSummary } from '../lib/categories';

function Harness({ start = [] }) {
  const [value, setValue] = useState(start);
  return (
    <>
      <CategoryPicker value={value} onChange={setValue} />
      <output data-testid="value">{value.join(',')}</output>
    </>
  );
}

describe('CategoryPicker', () => {
  it('starts on any category, and opens a panel of categories grouped by line', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const key = screen.getByRole('button', { name: 'Categories: Any category' });
    expect(key).toHaveAttribute('aria-expanded', 'false');

    await user.click(key);
    expect(key).toHaveAttribute('aria-expanded', 'true');
    const panel = screen.getByRole('group', { name: 'Categories' });
    expect(within(panel).getAllByRole('checkbox')).toHaveLength(24);
    expect(within(panel).getByText('History, Geography & Politics')).toBeInTheDocument();
  });

  it('chooses several categories, and a whole line at once', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    await user.click(screen.getByRole('button', { name: /Categories/ }));

    await user.click(screen.getByRole('checkbox', { name: 'Geography' }));
    await user.click(screen.getByRole('checkbox', { name: 'History' }));
    expect(screen.getByTestId('value')).toHaveTextContent('22,23');
    expect(screen.getByRole('button', { name: 'Categories: Geography & History' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Choose all of Art & Mythology' }));
    expect(screen.getByTestId('value')).toHaveTextContent('20,22,23,25');
    expect(screen.getByRole('button', { name: 'Categories: 4 categories' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Clear' }));
    expect(screen.getByTestId('value')).toBeEmptyDOMElement();
  });

  it('closes with Done or Escape and puts focus back on the field', async () => {
    const user = userEvent.setup();
    render(<Harness start={['22']} />);
    const key = screen.getByRole('button', { name: 'Categories: Geography' });
    await user.click(key);
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('group', { name: 'Categories' })).not.toBeInTheDocument();
    expect(key).toHaveFocus();

    await user.click(key);
    await user.click(screen.getByRole('button', { name: 'Done' }));
    expect(key).toHaveAttribute('aria-expanded', 'false');
  });
});

describe('categoriesSummary', () => {
  it('reads naturally for none, one, two and many', () => {
    expect(categoriesSummary([])).toBe('Any category');
    expect(categoriesSummary(['15'])).toBe('Video Games');
    expect(categoriesSummary(['22', '23'])).toBe('Geography & History');
    expect(categoriesSummary(['9', '22', '23'])).toBe('3 categories');
  });
});
