import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import Settings, { FoldingSettings, SettingsSummary, SettingsToggle } from './Settings';

const defaults = { amount: 10, categories: [], difficulty: '', type: '', timer: '' };

describe('Settings', () => {
  it('offers a time limit that starts switched off', async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    render(<Settings settings={defaults} onChange={onChange} />);

    const group = screen.getByRole('group', { name: 'Time per question' });
    expect(group).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Off' })).toBeChecked();

    await user.click(screen.getByRole('radio', { name: '20 sec' }));
    expect(onChange).toHaveBeenCalledWith({ ...defaults, timer: '20' });
  });

  it('puts an impossible number of questions back in range when you leave the box', async () => {
    const user = userEvent.setup();
    function Harness() {
      const [settings, setSettings] = useState(defaults);
      return <Settings settings={settings} onChange={setSettings} />;
    }
    render(<Harness />);
    const box = screen.getByLabelText('Number of questions (1–50)');

    await user.clear(box);
    await user.type(box, '999');
    await user.tab();
    expect(box).toHaveValue(50);

    await user.clear(box);
    await user.tab();
    expect(box).toHaveValue(10);
  });
});

describe('Folding the settings away', () => {
  function Harness({ startOpen = true, settings = defaults }) {
    const [open, setOpen] = useState(startOpen);
    return (
      <>
        <SettingsToggle open={open} onToggle={() => setOpen((o) => !o)} controls="panel" />
        <FoldingSettings id="panel" open={open} settings={settings} onChange={() => {}} />
      </>
    );
  }

  it('hides the controls, says what they are set to, and opens again', async () => {
    const user = userEvent.setup();
    const { container } = render(
      <Harness settings={{ amount: 5, categories: ['22'], difficulty: 'easy', type: '', timer: '20' }} />
    );
    const toggle = screen.getByRole('button', { name: /Hide settings/ });
    expect(toggle).toHaveAttribute('aria-expanded', 'true');

    await user.click(toggle);
    expect(screen.getByRole('button', { name: /Show settings/ })).toHaveAttribute('aria-expanded', 'false');
    // folded away: out of reach for keyboard and screen readers, summarised on one line
    expect(container.querySelector('#panel')).toHaveAttribute('inert');
    expect(screen.getByText('5 questions · Geography · Easy · Any type · 20 sec per question')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /Show settings/ }));
    expect(container.querySelector('#panel')).not.toHaveAttribute('inert');
    expect(screen.queryByText(/5 questions ·/)).not.toBeInTheDocument();
  });
});

describe('SettingsSummary', () => {
  it("spells out the host's choices for everyone else", () => {
    render(
      <SettingsSummary settings={{ amount: 15, categories: ['23'], difficulty: 'hard', type: 'boolean', timer: '10' }} />
    );
    const expected = {
      Questions: '15',
      Categories: 'History',
      Difficulty: 'Hard',
      'Question type': 'True / False',
      'Time per question': '10 sec',
    };
    for (const [term, value] of Object.entries(expected)) {
      expect(screen.getByText(term).nextElementSibling).toHaveTextContent(value);
    }
  });

  it('says Off and Any when nothing is chosen', () => {
    render(<SettingsSummary settings={defaults} />);
    expect(screen.getByText('Time per question').nextElementSibling).toHaveTextContent('Off');
    expect(screen.getByText('Categories').nextElementSibling).toHaveTextContent('Any category');
  });
});
