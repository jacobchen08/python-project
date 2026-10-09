import { useRef } from 'react';
import Icon from './Icon';
import CategoryPicker from './CategoryPicker';
import useIndicator from '../hooks/useIndicator';
import { categoriesSummary, difficulties } from '../lib/categories';
import { clampAmount, MAX_QUESTIONS, MIN_QUESTIONS } from '../lib/settings';
import Pips from './Pips';

const difficultyOptions = [{ value: '', label: 'Any' }, ...difficulties];

// Seconds per question. Off (the default) means take as long as you like.
const timers = [
  { value: '', label: 'Off' },
  { value: '10', label: '10 sec' },
  { value: '20', label: '20 sec' },
  { value: '30', label: '30 sec' },
];

const types = [
  { value: '', label: 'Any' },
  { value: 'multiple', label: 'Multiple choice' },
  { value: 'boolean', label: 'True / False' },
];

// A row of labeled switch positions with one thumb that slides to the chosen one
// (radio buttons underneath)
function Switch({ legend, name, options, value, onChange }) {
  const trackRef = useRef(null);
  const thumb = useIndicator(trackRef, '.switch-pos:has(input:checked)', [value]);
  const current = options.find((o) => o.value === value);

  return (
    <fieldset className="field switch">
      <legend>{legend}</legend>
      <div className="switch-track" ref={trackRef} style={thumb ?? undefined}>
        {thumb && <span className={`switch-thumb${current?.accent ? ` accent-${current.accent}` : ''}`} aria-hidden="true" />}
        {options.map((option) => (
          <label key={option.value} className={`switch-pos${thumb ? '' : ' no-thumb'}`}>
            <input
              type="radio"
              name={name}
              value={option.value}
              checked={value === option.value}
              onChange={() => onChange(option.value)}
            />
            {option.pips && <Pips count={option.pips} accent={option.accent} />}
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}

// Number of questions, categories, difficulty, question type and time per question
function Settings({ settings, onChange, idPrefix = '' }) {
  function update(key, value) {
    onChange({ ...settings, [key]: value });
  }

  function step(delta) {
    update('amount', clampAmount(clampAmount(settings.amount) + delta));
  }

  return (
    <div className="settings-grid">
      <div className="field">
        <label htmlFor={`${idPrefix}num-questions`}>Number of questions (1–50)</label>
        <div className="counter">
          <button type="button" className="counter-key" onClick={() => step(-1)} aria-label="One fewer question">
            <Icon name="minus" />
          </button>
          <input
            id={`${idPrefix}num-questions`}
            type="number"
            value={settings.amount}
            min={MIN_QUESTIONS}
            max={MAX_QUESTIONS}
            onChange={(e) => update('amount', e.target.value)}
            onBlur={() => update('amount', clampAmount(settings.amount))}
          />
          <button type="button" className="counter-key" onClick={() => step(1)} aria-label="One more question">
            <Icon name="plus" />
          </button>
        </div>
      </div>

      <CategoryPicker value={settings.categories} onChange={(value) => update('categories', value)} idPrefix={idPrefix} />

      <Switch
        legend="Difficulty"
        name={`${idPrefix}difficulty`}
        options={difficultyOptions}
        value={settings.difficulty}
        onChange={(value) => update('difficulty', value)}
      />

      <Switch
        legend="Question type"
        name={`${idPrefix}type`}
        options={types}
        value={settings.type}
        onChange={(value) => update('type', value)}
      />

      <Switch
        legend="Time per question"
        name={`${idPrefix}timer`}
        options={timers}
        value={settings.timer ?? ''}
        onChange={(value) => update('timer', value)}
      />
    </div>
  );
}

// The label of the chosen option in one of the lists above
const optionLabel = (list, value) => list.find((o) => o.value === (value ?? ''))?.label ?? 'Any';

// The settings on one line, for when the settings board is folded away
export function SettingsLine({ settings }) {
  const amount = Number(settings.amount) || 10;
  const difficulty = settings.difficulty ? optionLabel(difficultyOptions, settings.difficulty) : 'Any difficulty';
  const type = settings.type ? optionLabel(types, settings.type) : 'Any type';
  const timer = settings.timer ? `${settings.timer} sec per question` : 'No time limit';
  return (
    <p className="settings-line">
      {[`${amount} question${amount === 1 ? '' : 's'}`, categoriesSummary(settings.categories), difficulty, type, timer].join(' · ')}
    </p>
  );
}

// The button that folds the settings away and back
export function SettingsToggle({ open, onToggle, controls }) {
  return (
    <button type="button" className="board-toggle" aria-expanded={open} aria-controls={controls} onClick={onToggle}>
      <Icon name="chevron-down" className={open ? 'is-open' : ''} />
      {open ? 'Hide settings' : 'Show settings'}
    </button>
  );
}

// The settings themselves, folding shut when hidden. While shut they're also inert, so
// keyboard and screen reader users don't land in controls they can't see.
export function FoldingSettings({ id, open, settings, onChange, idPrefix }) {
  return (
    <>
      <div id={id} className="folding" data-open={open} inert={!open}>
        <div className="folding-inner">
          <Settings settings={settings} onChange={onChange} idPrefix={idPrefix} />
        </div>
      </div>
      {!open && <SettingsLine settings={settings} />}
    </>
  );
}

// The same choices, read-only: what guests in a room see while the host decides
export function SettingsSummary({ settings }) {
  const rows = [
    ['Questions', settings.amount],
    ['Categories', categoriesSummary(settings.categories)],
    ['Difficulty', optionLabel(difficultyOptions, settings.difficulty)],
    ['Question type', optionLabel(types, settings.type)],
    ['Time per question', optionLabel(timers, settings.timer)],
  ];
  return (
    <dl className="settings-summary">
      {rows.map(([term, value]) => (
        <div key={term}>
          <dt>{term}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

export default Settings;
