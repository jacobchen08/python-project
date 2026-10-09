---
name: Quizzr
description: Trivia on a split-flap departure board, hung on a station-hall wall.
colors:
  wall: "#d8d5cd"
  wall-ink: "#161614"
  wall-muted: "#4c4943"
  enamel: "#f1ede4"
  board: "#141413"
  board-head: "#1b1a18"
  board-edge: "#33312c"
  row: "#1a1917"
  row-hover: "#221f1c"
  tile-top: "#2c2b27"
  tile-bottom: "#232220"
  key: "#2a2925"
  key-hover: "#34322d"
  key-edge: "#3d3b35"
  well: "#0c0c0b"
  ink: "#f1ede4"
  ink-dim: "#aaa59a"
  ink-faint: "#8d887e"
  signal: "#f7c21a"
  signal-hover: "#ffd23d"
  signal-edge: "#c69800"
  signal-ink: "#141413"
  line-blue: "#6fa8ff"
  line-magenta: "#f472b6"
  line-teal: "#2fc6c6"
  line-orange: "#ff9d47"
  line-violet: "#b69cff"
  notice: "#8d887e"
  seam: "rgba(0, 0, 0, 0.7)"
  ok: "#4fd98a"
  bad: "#ff7a6b"
typography:
  display:
    fontFamily: "Sofia Sans Condensed Variable, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "clamp(40px, 6vw, 60px)"
    fontWeight: 800
    lineHeight: 0.95
    letterSpacing: "0.01em"
  flap:
    fontFamily: "Sofia Sans Condensed Variable, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "clamp(38px, 8vw, 56px)"
    fontWeight: 700
    lineHeight: 1
  headline:
    fontFamily: "Sofia Sans Condensed Variable, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "clamp(24px, 3.2vw, 30px)"
    fontWeight: 700
    lineHeight: 1.15
  question:
    fontFamily: "Sofia Sans Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "clamp(22px, 3.6vw, 30px)"
    fontWeight: 650
    lineHeight: 1.32
    letterSpacing: "-0.005em"
  body:
    fontFamily: "Sofia Sans Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
    fontFeature: "tnum"
  answer:
    fontFamily: "Sofia Sans Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 500
    lineHeight: 1.35
  key:
    fontFamily: "Sofia Sans Condensed Variable, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 700
    letterSpacing: "0.07em"
  board-title:
    fontFamily: "Sofia Sans Condensed Variable, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "15px"
    fontWeight: 700
    letterSpacing: "0.14em"
  label:
    fontFamily: "Sofia Sans Condensed Variable, Arial Narrow, Segoe UI, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    letterSpacing: "0.12em"
rounded:
  badge: "2px"
  tile: "3px"
  key: "4px"
  track: "5px"
  board: "6px"
spacing:
  tile-gap: "4px"
  row-gap: "6px"
  field-gap: "8px"
  row-pad: "12px"
  board-pad-sm: "18px"
  board-pad: "24px"
  stack: "28px"
components:
  board:
    backgroundColor: "{colors.board}"
    textColor: "{colors.ink}"
    rounded: "{rounded.board}"
    padding: "24px"
  board-head:
    backgroundColor: "{colors.board-head}"
    textColor: "{colors.ink}"
    typography: "{typography.board-title}"
    padding: "14px 24px"
  sign-plate:
    backgroundColor: "{colors.enamel}"
    textColor: "{colors.board}"
    typography: "{typography.display}"
    rounded: "{rounded.board}"
    padding: "16px 16px 16px 28px"
  mode-tab:
    backgroundColor: "transparent"
    textColor: "{colors.board}"
    typography: "{typography.key}"
    rounded: "{rounded.key}"
    height: "44px"
    padding: "0 20px"
  mode-tab-selected:
    backgroundColor: "{colors.board}"
    textColor: "{colors.ink}"
  button-key:
    backgroundColor: "{colors.key}"
    textColor: "{colors.ink}"
    typography: "{typography.key}"
    rounded: "{rounded.key}"
    height: "46px"
    padding: "0 18px"
  button-key-hover:
    backgroundColor: "{colors.key-hover}"
  button-primary:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.signal-ink}"
    typography: "{typography.key}"
    rounded: "{rounded.key}"
    height: "52px"
    padding: "0 26px"
  button-primary-hover:
    backgroundColor: "{colors.signal-hover}"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.key}"
    height: "46px"
    padding: "0 18px"
  button-ghost-hover:
    textColor: "{colors.bad}"
  field:
    backgroundColor: "{colors.tile-bottom}"
    textColor: "{colors.ink}"
    rounded: "{rounded.key}"
    height: "48px"
    padding: "0 14px"
  switch-track:
    backgroundColor: "{colors.well}"
    textColor: "{colors.ink-dim}"
    rounded: "{rounded.track}"
    padding: "4px"
  flap-tile:
    backgroundColor: "{colors.tile-top}"
    textColor: "{colors.ink}"
    typography: "{typography.flap}"
    rounded: "{rounded.tile}"
  answer-row:
    backgroundColor: "{colors.row}"
    textColor: "{colors.ink}"
    typography: "{typography.answer}"
    rounded: "{rounded.key}"
    height: "58px"
    padding: "6px 18px 6px 6px"
  answer-row-hover:
    backgroundColor: "{colors.row-hover}"
  answer-row-selected:
    backgroundColor: "{colors.row-hover}"
  answer-letter:
    backgroundColor: "{colors.tile-top}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tile}"
    size: "44px"
  answer-letter-selected:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.signal-ink}"
  answer-letter-correct:
    backgroundColor: "{colors.ok}"
    textColor: "{colors.board}"
  answer-letter-wrong:
    backgroundColor: "{colors.bad}"
    textColor: "{colors.board}"
  step-cell:
    backgroundColor: "{colors.tile-bottom}"
    textColor: "{colors.ink}"
    rounded: "{rounded.tile}"
    height: "30px"
  step-cell-now:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.signal-ink}"
  route-badge:
    textColor: "{colors.signal-ink}"
    rounded: "{rounded.tile}"
    height: "24px"
    padding: "0 6px"
  rank-tile-you:
    backgroundColor: "{colors.signal}"
    textColor: "{colors.signal-ink}"
    rounded: "{rounded.tile}"
    size: "34px"
  share-ticket:
    backgroundColor: "{colors.row}"
    textColor: "{colors.ink}"
    rounded: "{rounded.key}"
    padding: "18px 20px"
---

# Design System: Quizzr

## Overview

**Creative North Star: "The Departure Board"**

Every quiz is a timetable. Questions, room codes and scores arrive on matte black split-flap boards hung on a station-hall wall. The wall is the page and follows the viewer's light or dark preference. The boards are always black, and the enamel station sign above them is the same painted off-white by day and by night. Each board is a separate module with a gap of wall between it and the next, and each hangs from its top edge and swings into place when its mode is shown.

The system is dense and mechanical without being noisy. Codes, numbers and short labels sit on flap tiles: two halves split by a hairline seam, each character flipping forward through a drum until it lands. Everything written to be read, like question text, answers and explanations, is set in a readable grotesk and never flips. One colour, signal yellow, marks what is happening now. Five line colours tell categories, difficulty levels and players apart, like route bullets on a real board. Correct and wrong always pair a drawn glyph with a word.

This world rejects the trivia-app default: a gradient card with coloured answer tiles. It has no blended gradients, no glows and no soft, heavily rounded SaaS cards.

**Key Characteristics:**
- Black boards on a wall that follows the colour scheme; boards and sign plate do not change between schemes.
- Split-flap tiles (a hard 50% split and a 1px seam) for codes, numbers, ranks and answer letters.
- Signal yellow is rationed to "now".
- Five line colours, each always paired with a code, a pip count or a name.
- Condensed caps for signage, readable sentence case for reading.
- Controls read as physical keys, with a darker lip underneath that sinks 1px when pressed.
- One settle curve for all motion; with reduced motion, things land in place instead of travelling.

**In the code:** every token below is defined once in `frontend/src/styles/tokens.css`. Each part of the screen has its own stylesheet beside it in `frontend/src/styles/` (for example `flaps.css` for split-flap tiles and `question.css` for the question board), loaded in cascade order by `styles/index.css`.

## Colors

A warm off-black board family with off-white ink, one rationed signal yellow, five route-line colours and a status pair, all set on a pale enamel-grey wall.

### Primary
- **Signal Yellow** (signal): the colour of "now". It appears on the selected mode's sign bar, the lit step cell, the current Answers-log row number, your leaderboard rank tile and name, the one primary key per screen, and the focused next room-code tile. Its hover is a brighter **Lamp Yellow** (signal-hover), its edge a darker **Brass Edge** (signal-edge), and text on it is always **Board Black** (signal-ink).

### Secondary
- **Route Lines** (line-blue, line-magenta, line-teal, line-orange, line-violet): each category family, difficulty level and multiplayer player gets one of these, the way a line bullet does on a departure board. They appear as route badges with a 2–3 letter code, difficulty pips (one, two or three bars), the lamp strip under a selected switch position, the player line before a name, and the line map swatches.

### Tertiary
- **Arrival Green** (ok) and **Signal Red** (bad): status on the board. They always come with a check or cross glyph and a word (CORRECT, WRONG, TIME). Red also drains the countdown strip in its last five seconds and outlines error messages.

### Neutral
- **Enamel Grey Wall** (wall): the page in light mode. In dark mode it becomes a night concourse (#21201d), with wall ink #eeeae1 and wall muted #aba699.
- **Wall Ink / Wall Muted** (wall-ink, wall-muted): text written directly on the wall, such as the header tagline.
- **Enamel** (enamel): the station sign plate. It stays the same in both schemes because it is a painted object.
- **Board Black** (board): every board and the selected mode tab. In dark mode it steps down to #121211, and board-head to #181715.
- **Board Head / Board Edge** (board-head, board-edge): the header strip of a board, and the 1px edges and row dividers inside it.
- **Row / Row Hover** (row, row-hover): answer rows, share tickets and settings summaries; row-hover also marks the current row.
- **Tile Top / Tile Bottom** (tile-top, tile-bottom): the two halves of a flap tile. Tile-bottom also fills fields and step cells.
- **Key / Key Hover / Key Edge** (key, key-hover, key-edge): board keys and their 1px outline. Key-edge is also the outline for fields, answer rows and step cells.
- **Well** (well): the recessed trough behind switch tracks and the countdown strip.
- **Ink / Ink Dim / Ink Faint** (ink, ink-dim, ink-faint): board text for reading, for labels and secondary copy, and for disabled or placeholder text.

### Named Rules
**The Now Rule.** Signal yellow only marks "now": the selected mode's sign bar, the lit step cell, the current answer-log row, your leaderboard row, the one primary key per screen, and the focused next room-code tile. The yellow keyboard focus ring follows the same logic, because it marks where you are. Anything that is not "now", such as the share ticket's top edge, uses board-edge ink instead.

**The Line Rule.** A line colour is never the only signal. It always comes with a code (a route badge), a count (pips), or a name (the player or the line map entry).

**The Glyph-and-Word Rule.** Correct and wrong are always a drawn glyph plus a word, never colour alone.

**The Black Board Rule.** Only the wall follows `prefers-color-scheme`. Boards stay black and the sign plate stays enamel in both schemes.

## Typography

**Display Font:** Sofia Sans Condensed Variable (with Arial Narrow, Segoe UI, sans-serif)
**Body Font:** Sofia Sans Variable (with Segoe UI, system-ui, sans-serif)

**Character:** A signage condensed grotesk in caps for everything a board would paint or flip, paired with its regular-width sibling for anything a person has to read. Every number is set with tabular figures (`font-variant-numeric: tabular-nums` on the root).

### Hierarchy
- **Display** (800, clamp 40–60px, 0.95, uppercase): the name on the sign plate only.
- **Flap** (700, clamp 38–56px at xl; 28–36px at lg; 20px at md): split-flap readouts such as the question number, score, timer and room code (34px code tiles).
- **Headline** (700 condensed, clamp 24–30px, 1.15): results verdict and multiplayer winner line.
- **Question** (650 sans, clamp 22–30px, 1.32, max 34em): the question text. It is sentence case and never flips.
- **Answer** (500 sans, 17px, 1.35): answer rows and field values.
- **Body** (400 sans, 16px, 1.5): running copy, with notes and hints at 14–15px in ink-dim.
- **Key** (700 condensed, 16px, 0.07em, uppercase): every key and mode tab; the primary key is 18px.
- **Board Title** (700 condensed, 15px, 0.14em, uppercase): the heading in each board head.
- **Label** (600 condensed, 12–13px, 0.12–0.14em, uppercase, ink-dim): field labels, readout labels, board column heads and stat terms. These label data the way a timetable column head does, directly above the value they name.

### Named Rules
**The Two Voices Rule.** Condensed caps are for signage, flaps, keys and labels. Sentence-case grotesk is for questions, answers and explanations. The two never swap roles.

**The Question Never Flips Rule.** Only codes, numbers and short labels use the flap cascade. Question and answer text arrives by sliding in, never character by character.

## Layout

A single quiz column of up to 880px, centred on the wall (padding 44px 24px 72px, dropping to 24px 16px 48px at 640px and below). Boards stack with 24px between them inside a mode panel, and 28px separates the header from the main column. At 1240px and wider the page becomes a grid: an 880px quiz column plus a 290px rail of side boards (round board first, then the Answers log and line map), with a 36px column gap. At 1520px and wider there is one 250–300px rail on each side, and the rails are sticky 24px from the top so a column of boards stays in view while the quiz scrolls. Side boards are hidden below 1240px.

Inside a board the body padding is 24px (18px at 640px and below) and the head is 14px 24px. Rows sit on 1px board-edge dividers, and answer rows are 6px apart. The settings grid has two columns with 22px by 24px gaps and collapses to one column at 640px. Answer rows move their status column under the text at 520px, and the streak readout hides at 560px.

## Elevation & Depth

This is a hybrid system. Each board casts one soft shadow onto the wall, and depth inside a board is tactile rather than lifted: keys have a darker inset lip, tiles have a split face and seam, and switch tracks and the countdown sit in a recessed well. There are no glows.

### Shadow Vocabulary
- **Board on the wall** (`box-shadow: 0 2px 3px rgba(0,0,0,0.18), 0 18px 32px -18px rgba(0,0,0,0.55)`; dark scheme `0 2px 3px rgba(0,0,0,0.35), 0 20px 36px -18px rgba(0,0,0,0.8)`): every board, banner, the sign plate and the open category picker.
- **Key lip** (`box-shadow: inset 0 -2px 0 rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.05)`): board keys, counter keys and kbd hints. The primary key uses `inset 0 -3px 0 rgba(0,0,0,0.22)`. Pressing removes the lip and moves the key down 1px.
- **Raised tile** (`box-shadow: inset 0 1px 0 rgba(255,255,255,0.07), 0 1px 2px rgba(0,0,0,0.6)`): the switch thumb sitting in its well.
- **Flap tile** (`box-shadow: inset 0 -1px 0 rgba(0,0,0,0.55), 0 1px 1px rgba(0,0,0,0.4)`): split-flap characters.
- **Painted rule** (`box-shadow: inset 0 0 0 5px enamel, inset 0 0 0 7px board`): the 2px black line painted 5px inside the sign plate's edge.

### Named Rules
**The Hung Board Rule.** Only whole boards cast a shadow on the wall. Nothing inside a board floats. Depth there comes from lips, seams and wells.

## Shapes

Corners are small and mechanical. Boards and the sign plate use 6px, keys, fields and answer rows 4px, the switch track 5px, tiles 3px, and badges 2px. Flap tiles are drawn as two halves with a hard 50% colour stop between tile-top and tile-bottom, plus a 1px seam (the seam token) across the middle. Every number tile carries the same seam: flaps, answer letters, step-list numbers, the Answers board, missed-question numbers and ranks. A tile that lights up with a result (correct, wrong, or selected) becomes one solid plate and drops its seam, so the seam never reads as a strikethrough. Route badges are small 24px plates (20px in the compact size). Difficulty pips are 4 by 11px bars, and player lines are 5 by 18px bars. The icon set is drawn on a 24px grid with 2px round strokes in currentColor.

## Components

### Buttons (Keys)
Physical keys on the board.
- **Shape:** gently squared (4px), 46px tall, 1px key-edge outline, key lip underneath.
- **Board key:** key fill with ink text, in condensed caps. Hover moves to key-hover; pressing sinks it 1px and removes the lip. Disabled keys go transparent with board-edge outline and ink-faint text.
- **Primary:** one per screen. Signal fill, brass edge, board-black text, 52px tall, 240px minimum width (full width at 640px and below), 18px type. Hover uses Lamp Yellow. When busy it is disabled at a 55% signal/board mix with a progress cursor.
- **Ghost:** transparent and without a lip; hover turns the outline and text Signal Red (used for leave or exit actions). There is also a quiet ghost variant.
- **Focus:** 2px signal outline at 2px offset. On the primary key the outline is ink.

### Mode Tabs on the Sign Plate (Navigation)
- The sign plate is an enamel plate with a painted inner rule, holding the name in Display type and the mode tabs (SOLO / DAILY / MULTIPLAYER).
- Tabs are 44px condensed-caps keys outlined at 30% board ink on enamel. A single black plate with a 4px signal bar at its foot slides between tabs (420ms settle) to mark the selected mode. At 640px and below the tabs share the full row.

### Switches (Chips)
- **Style:** labelled switch positions in a 4px-padded well. A raised split tile slides to the chosen position (360ms settle), and its foot carries a 3px lamp strip in the option's line colour.
- **State:** unselected positions are ink-dim; the chosen position is ink at 700 weight. Difficulty positions carry pips that brighten from a 45% mix to full line colour when chosen or hovered.

### Boards (Cards / Containers)
- **Corner Style:** 6px.
- **Background:** board black, with a board-head strip over a 1px board-edge divider.
- **Shadow Strategy:** board on the wall (see Elevation & Depth).
- **Border:** 1px board-edge. Notice boards (server waking, reconnecting) take a 1px dashed notice edge with board-ink icons, so they never borrow a line colour, the signal or a status colour.
- **Internal Padding:** 24px (18px on phones), with an optional board foot in 14px ink-dim.

### Inputs / Fields
- **Style:** 48px tile-bottom well with a 1px key-edge outline and 4px corners, 17px text at 500 weight, and a signal caret. Placeholder text is ink-faint.
- **Focus:** hover lifts the edge to ink-faint; focus adds a 2px signal outline at 2px offset.
- **Category picker:** a key that shows the chosen categories' route badges and a short summary ("Any category", "Geography & History", "3 categories"), with a drawn chevron. Pressing it opens a panel set into the board like a well, never a pop-up: the categories as toggle chips grouped by line, each line with an All/Clear key. A chosen chip becomes a raised split tile with its line colour as a 3px lamp strip along its foot and a tick, so the choice never rests on colour alone. Two chips to a row on phones.
- **Counter:** a condensed 24px number between two 48px keys.
- **Room code:** a hidden real input laid over five flap tiles at 34px. The tile you type into next gets the signal outline.

### Answer Rows (Signature)
Departure rows: a 44px split letter tile, the answer text, and a status column.
- **Default:** row fill with a 1px key-edge outline and 4px corners, at least 58px tall. Hover lifts the edge to ink-dim, fills row-hover, and turns the letter tile ink-on-board.
- **Selected (now):** signal edge and a solid signal letter tile.
- **Correct / Wrong:** green or red edge, a solid status-colour letter tile that flips over to its result (440ms), and a status column with a glyph and word sliding in from the right. Other rows dim to ink-faint.
- Rows stagger in 60ms apart after the question slides in from the direction of travel.

### Step Row and Readouts
- **Step row:** a grid of 30px cells (at least 28px wide, 4px gaps), one per question. Each cell shows a check, cross or pending mark, and the current cell is solid signal.
- **Readouts:** label-type captions above flap values ("01 / 10", time, streak, score). In the last five seconds of a timed question the time label turns red and the tiles pulse once a second.
- **Countdown:** a 6px well strip under the board head that drains a signal fill, switching to red when urgent.

### Route Badges and Pips
- **Route badge:** a line-coloured 3px plate carrying the category's 2–3 letter code in 800 condensed board-black type. It flips in (380ms). "Any category" is an outlined ink-faint plate reading ALL.
- **Pips:** three bars with one, two or three lit (easy is teal, medium orange, hard magenta).

### Leaderboard and Results
- **Leaderboard:** departure rows with a 34 by 38px split rank tile, a player line, the name, badges and progress. Your row has a signal rank tile, a signal name and a YOU badge.
- **Results:** a condensed verdict headline, stats as label/value departure rows on board-edge dividers, and missed questions as numbered rows with side-by-side YOUR ANSWER / CORRECT cells, each with a glyph, word and a status edge at a 55% mix.
- **Share ticket:** a row-fill slip with a 4px board-edge top edge, a condensed title, a row of 26px mark tiles (glyphs in status colour), and dim 14px lines.

### Motion
One settle curve (`cubic-bezier(0.16, 1, 0.3, 1)`) for everything that travels. The boards hang onto the wall with a 9° tilt (520ms, staggered 70ms) once, as the page opens; boards that appear after that (another mode, a question, the results) drop in over 280ms instead of swinging every time. Each flap flip takes about 110ms (the top leaf falls, then the bottom leaf lands), neighbouring tiles start 18ms apart, and a tile runs at most 9 steps. Digits more than two steps away flip straight to the new value, so a countdown never spins the whole wheel. With `prefers-reduced-motion`, leaves, hangs, slides and pulses are removed and every state change lands immediately.

## Do's and Don'ts

### Do:
- **Do** put every new screen on black boards hung on the wall, with separate modules, gaps of wall between them, and a 6px corner with the board-on-wall shadow.
- **Do** keep signal yellow to the "now" list: the selected mode's sign bar, the lit step cell, the current answer-log row, your leaderboard row, the one primary key per screen, and the focused next room-code tile.
- **Do** pair every line colour with a code, a pip count or a name.
- **Do** show correct and wrong as a drawn glyph plus a word, in ok or bad.
- **Do** set codes, numbers, ranks and letters on split-flap tiles (hard 50% split and 1px seam), and drop the seam when a tile lights up solid.
- **Do** use condensed caps for signage, keys and labels, and the sentence-case grotesk for questions and answers.
- **Do** move with the settle curve and give every animation a reduced-motion path that lands in place.
- **Do** use the drawn 24px icon set (2px round strokes, currentColor).

### Don't:
- **Don't** use blended gradients or glows. The only gradient in the system is the hard 50% stop that draws a flap tile's two halves.
- **Don't** use soft, heavily rounded SaaS cards; board corners stop at 6px.
- **Don't** use signal yellow for decoration, celebration or share tickets.
- **Don't** make boards or the sign plate follow the colour scheme; only the wall changes.
- **Don't** flip question or answer text through the flap cascade.
- **Don't** use a line colour on its own, or colour alone for correct and wrong.
