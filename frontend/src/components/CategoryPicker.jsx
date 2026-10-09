import { useId, useRef, useState } from 'react';
import Icon from './Icon';
import RouteBadge from './RouteBadge';
import { categories, categoriesSummary, categoryById, categoryLabel, lineNames } from '../lib/categories';

// Choosing any number of categories. Picking none means any category.
//
// The field shows what's chosen (route badges and a short summary); pressing it opens a
// panel below the settings with every category as a toggle, grouped by line like a route
// map. The panel is part of the board, not a pop-up, so nothing covers the other settings.

// The lines in the order the line map shows them, each with its categories A–Z
const groups = Object.entries(lineNames).map(([line, name]) => ({
  line,
  name,
  members: categories
    .filter((c) => c.line === line)
    .sort((a, b) => categoryLabel(a.name).localeCompare(categoryLabel(b.name))),
}));

function CategoryPicker({ value = [], onChange, idPrefix = '' }) {
  const [open, setOpen] = useState(false);
  const keyRef = useRef(null);
  const panelId = `${idPrefix}category-panel${useId()}`;
  const chosen = new Set(value.map(String));
  const badges = value.slice(0, 4).map((id) => categoryById(id));

  // Keep the ids in the order categories are listed, so the same choice always reads the same
  function choose(next) {
    onChange(categories.map((c) => String(c.id)).filter((id) => next.has(id)));
  }

  function toggle(id) {
    const next = new Set(chosen);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    choose(next);
  }

  function toggleGroup(members, allOn) {
    const next = new Set(chosen);
    for (const c of members) {
      if (allOn) next.delete(String(c.id));
      else next.add(String(c.id));
    }
    choose(next);
  }

  function close() {
    setOpen(false);
    keyRef.current?.focus();
  }

  return (
    <>
      <div className="field">
        <span className="field-label" aria-hidden="true">Categories</span>
        <button
          type="button"
          ref={keyRef}
          className="picker-key"
          aria-label={`Categories: ${categoriesSummary(value)}`}
          aria-expanded={open}
          aria-controls={panelId}
          onClick={() => setOpen((o) => !o)}
          onKeyDown={(e) => {
            if (e.key === 'Escape' && open) {
              e.preventDefault();
              setOpen(false);
            }
          }}
        >
          <span className="picker-badges" aria-hidden="true">
            {badges.length === 0 ? (
              <RouteBadge code="ALL" line="any" />
            ) : (
              badges.map((c) => <RouteBadge key={c.id} code={c.code} line={c.line} />)
            )}
            {value.length > 4 && <span className="picker-more">+{value.length - 4}</span>}
          </span>
          <span className="picker-text">{categoriesSummary(value)}</span>
          <Icon name="chevron-down" className={`picker-chevron${open ? ' is-open' : ''}`} />
        </button>
      </div>

      {open && (
        <fieldset
          id={panelId}
          className="category-panel"
          onKeyDown={(e) => {
            if (e.key === 'Escape') {
              e.stopPropagation();
              close();
            }
          }}
        >
          <legend className="sr-only">Categories</legend>
          <div className="category-panel-head">
            <p className="category-panel-hint">Pick as many as you like. None picked means any category.</p>
            <button type="button" className="board-toggle" onClick={() => choose(new Set())} disabled={value.length === 0}>
              Clear
            </button>
          </div>

          {groups.map(({ line, name, members }) => {
            const allOn = members.every((c) => chosen.has(String(c.id)));
            return (
              <div key={line} className={`category-group route-${line}`}>
                <div className="category-group-head">
                  <span className="line-swatch" aria-hidden="true" />
                  <span className="category-group-name">{name}</span>
                  <button
                    type="button"
                    className="category-group-all"
                    aria-label={`${allOn ? 'Clear' : 'Choose all of'} ${name}`}
                    onClick={() => toggleGroup(members, allOn)}
                  >
                    {allOn ? 'Clear' : 'All'}
                  </button>
                </div>
                <div className="category-chips">
                  {members.map((c) => {
                    const id = String(c.id);
                    const on = chosen.has(id);
                    return (
                      <label key={id} className={`category-chip route-${c.line}${on ? ' is-on' : ''}`}>
                        <input type="checkbox" checked={on} onChange={() => toggle(id)} />
                        <RouteBadge code={c.code} line={c.line} size="sm" />
                        <span>{categoryLabel(c.name)}</span>
                        {on && <Icon name="check" size={14} className="category-check" />}
                      </label>
                    );
                  })}
                </div>
              </div>
            );
          })}

          <div className="category-panel-foot">
            <button type="button" className="btn" onClick={close}>
              Done
            </button>
          </div>
        </fieldset>
      )}
    </>
  );
}

export default CategoryPicker;
