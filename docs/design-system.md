# Passage — Design System

## Overview

**App:** Osho Says / Passage
**What it is:** A literary search and conversation interface for exploring passages of wisdom from Osho's talks.

**Tone:** Contemplative, minimal, unhurried. Like a well-worn book left open on a table.
**Voice:** Still, direct, slightly sacred. No urgency. No noise.

**Design principles:**
- Every element earns its place. No decorative chrome.
- Motion is functional only — no entrance animations, no hover lifts.
- Typography does the heavy lifting. One serif family throughout.
- Warmth comes from the off-white background and warm gray borders, not from color accents.

**Anti-patterns:** gradients, drop shadows on cards, colorful accents, rounded hero images, icon libraries, loading skeletons, modal overlays.

---

## Color Tokens

| Token | Hex | Usage |
|---|---|---|
| `--color-bg` | `#faf9f7` | Page background — warm off-white, slightly cream |
| `--color-surface` | `#ffffff` | Cards, inputs, dropdowns |
| `--color-border` | `#e8e6e3` | Card borders — warm light gray |
| `--color-border-input` | `#cccccc` | Input default border |
| `--color-border-focus` | `#666666` | Input focused border |
| `--color-border-muted` | `#dddddd` | Pill and toggle default border |
| `--color-ink` | `#2a2a2a` | Primary text, headings, active/filled buttons |
| `--color-ink-muted` | `#666666` | Secondary text, hover states |
| `--color-ink-subtle` | `#888888` | Meta text, user messages in channel |
| `--color-ink-faint` | `#aaaaaa` | Nav links, empty states, disabled hints |
| `--color-ink-ghost` | `#bbbbbb` | Ghost save button, mode dropdown trigger |
| `--color-separator` | `#cccccc` | Dot separators between passages |
| `--color-hover-surface` | `#f5f5f5` | Dropdown item hover background |

---

## Typography

**Font stack:** `Georgia, serif` — used everywhere, no sans-serif.

| Token | Size | Line height | Usage |
|---|---|---|---|
| `--text-heading` | `1.8rem` | default | Page `h1` title |
| `--text-body-lg` | `1.05rem` | `1.9` | Osho response in teaching mode |
| `--text-body` | `1rem` | `1.8` | Osho response default |
| `--text-body-sm` | `0.95rem` | `1.7` | Passage previews, inputs, buttons, nav links |
| `--text-meta` | `0.85rem` | default | Book titles, inline action buttons, dropdown items |
| `--text-tag` | `0.8rem` | default | Mode tag label, ghost save button, warming indicator |
| `--text-xs` | `0.75rem` | default | Mode pill labels |

All interactive elements use `font-family: inherit` to stay in Georgia.

---

## Spacing

| Token | Value | Usage |
|---|---|---|
| `--space-1` | `4px` | Gap between mode pills |
| `--space-2` | `8px` | Input row gap, nav margin |
| `--space-3` | `10px` | Message bottom margin baseline |
| `--space-4` | `12px` | Between passage preview and meta row; sticky input top padding |
| `--space-5` | `14px` | Pill horizontal padding |
| `--space-6` | `16px` | Nav link gap |
| `--space-card` | `20px` | Card internal padding |
| `--space-section` | `24px` | Header margin-bottom, filter margin |
| `--space-input-x` | `14px` | Input horizontal padding |
| `--space-input-y` | `10px` | Input vertical padding |
| `--space-page-bottom` | `32px` | Messages bottom margin (channel) |
| `--space-channel-header` | `40px` | Channel header margin-bottom |
| `--space-input-gap` | `48px` | Input row to results gap (search page) |
| `--space-separator` | `28px` | Vertical padding around dot separators |
| `--space-end-top` | `120px` | End-dot top padding (search) |
| `--space-end-bottom` | `80px` | End-dot bottom padding (search) |
| `--space-page-x` | `20px` | Page horizontal padding |
| `--space-page-y` | `40px` | Page vertical padding |

---

## Border Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-card` | `8px` | Passage cards, story cards |
| `--radius-input` | `6px` | Text inputs, textareas, primary buttons, dropdown menu |
| `--radius-btn-meta` | `4px` | Save/Remove inline meta buttons |
| `--radius-pill` | `20px` | Mode pills |
| `--radius-chip` | `16px` | Book filter chips |
| `--radius-dot` | `50%` | Dot separators |

---

## Layout

- **Max content width:** `720px`, centered with `margin: 0 auto`
- **Page padding:** `40px 20px`
- **Grid:** single column only — no multi-column layouts
- **Sticky:** channel input row sticks to `bottom: 20px`; background matches `--color-bg` with `padding-top: 12px` to prevent content bleed
- **Body model:** `min-height: 100vh; display: flex; flex-direction: column` on channel page so input row pushes to bottom

---

## Components

### Card — Passage / Story

A contained reading unit. No hover effect. No shadow.

```
background:    --color-surface
border:        1px solid --color-border
border-radius: --radius-card
padding:       --space-card
margin-bottom: 20px (stories); none (search, uses separator)
```

**Preview text**
- Font: `--text-body-sm`, line-height `1.7`
- `white-space: pre-wrap` for story cards

**Meta row** (`display: flex; justify-content: space-between; align-items: center`)
- Left: book title — `font-style: italic`, `--text-meta`, `--color-ink-subtle`
- Right: action button (Save / Remove) or score label

---

### Button — Primary

Used for Search (index) and Ask (channel).

```
background:    --color-ink
color:         #ffffff
border:        none
border-radius: --radius-input
padding:       10px 20px
font-size:     --text-body-sm
font-family:   inherit
cursor:        pointer
white-space:   nowrap
```

| State | Change |
|---|---|
| hover | `background: #444444` |
| disabled | `background: --color-border-input; cursor: default` |

---

### Button — Meta (inline card action)

Save, Remove, Saved — sits in the card meta row.

```
background:    none
border:        1px solid --color-border-input
border-radius: --radius-btn-meta
padding:       4px 12px
font-size:     --text-meta
color:         --color-ink-muted
font-family:   inherit
cursor:        pointer
```

| State | Change |
|---|---|
| hover | `border-color: --color-ink-muted; color: --color-ink` |
| saved | `background: --color-ink; color: #fff; border-color: --color-ink` |

---

### Button — Ghost Save (channel)

Appears in message meta row after a response streams in.

```
background:    none
border:        none
font-size:     --text-tag
color:         --color-ink-ghost
font-family:   inherit
padding:       0
cursor:        pointer
```

| State | Change |
|---|---|
| hover | `color: --color-ink-muted` |
| saved | `color: --color-ink` |

---

### Input — Text

Search query input on index page, keyword filter on stories page.

```
width:         100%
padding:       10px 14px
font-size:     --text-body-sm
border:        1px solid --color-border-input
border-radius: --radius-input
font-family:   inherit
background:    --color-surface
transition:    border-color 0.2s
```

| State | Change |
|---|---|
| focus | `outline: none; border-color: --color-border-focus` |

---

### Textarea — Channel Input

Auto-grows with content; capped at 160px.

```
width:         100%
padding:       10px 36px 10px 14px   /* right: room for mode trigger */
font-size:     --text-body-sm
border:        1px solid --color-border-input
border-radius: --radius-input
font-family:   inherit
resize:        none
height:        48px
line-height:   1.5
overflow:      hidden
background:    --color-surface
transition:    border-color 0.2s
```

| State | Change |
|---|---|
| focus | `outline: none; border-color: --color-border-focus` |
| teaching / story mode active | `border-color: --color-ink` |

---

### Mode Pill

Header-level toggle (channel page).

```
background:    none
border:        1px solid --color-border-muted
border-radius: --radius-pill
padding:       4px 14px
font-size:     --text-xs
color:         --color-ink-faint
cursor:        pointer
font-family:   inherit
transition:    all 0.15s
```

| State | Change |
|---|---|
| hover | `border-color: --color-ink-ghost; color: --color-ink-muted` |
| active | `background: --color-ink; border-color: --color-ink; color: #fff` |

---

### Book Filter Chip

Pill-style filter on stories page. Same visual logic as Mode Pill but slightly larger.

```
background:    none
border:        1px solid --color-border-input
border-radius: --radius-chip
padding:       6px 14px
font-size:     --text-meta
color:         --color-ink-muted
cursor:        pointer
font-family:   inherit
```

| State | Change |
|---|---|
| hover | `border-color: --color-ink-muted; color: --color-ink` |
| active | `background: --color-ink; color: #fff; border-color: --color-ink` |

---

### Nav Link

Top navigation links (Stories, Search).

```
color:           --color-ink-subtle
text-decoration: none
font-size:       --text-body-sm
```

| State | Change |
|---|---|
| hover | `color: --color-ink` |
| active page | `color: --color-ink; border-bottom: 2px solid --color-ink; padding-bottom: 2px` |

---

### Back / Muted Nav Link

Used on channel page: `← search`.

```
font-size:       --text-body-sm
color:           --color-ink-faint
text-decoration: none
```

| State | Change |
|---|---|
| hover | `color: --color-ink-muted` |

---

### Separator — Dot

A single 6px dot between passage cards. No text, no line.

```
display:         flex
justify-content: center
padding:         28px 0
```

`::after` pseudo-element:
```
content:       ''
width:         6px
height:        6px
background:    --color-separator
border-radius: 50%
display:       block
```

---

### Mode Dropdown (channel)

A small `▼` trigger inside the textarea; opens a mini-menu above it.

**Trigger:**
```
position:    absolute
right:       10px
top:         50%
transform:   translateY(-50%)
cursor:      pointer
padding:     4px
color:       --color-ink-ghost
font-size:   0.6rem
user-select: none
transition:  color 0.2s
```

hover: `color: --color-ink-muted`

**Menu:**
```
position:      absolute
bottom:        calc(100% + 4px)
right:         0
background:    --color-surface
border:        1px solid --color-border-muted
border-radius: --radius-input
box-shadow:    0 2px 8px rgba(0,0,0,0.10)
min-width:     120px
z-index:       10
display:       none   /* toggled to block via .open class */
```

**Menu item:**
```
padding:     8px 14px
font-size:   --text-meta
color:       --color-ink-muted
cursor:      pointer
white-space: nowrap
```

| State | Change |
|---|---|
| hover | `background: --color-hover-surface; color: --color-ink` |
| active mode | `color: --color-ink; font-weight: 500` |

Modes: `conversation`, `teaching`, `story`

---

### Blinking Cursor (streaming text)

Shown inline while a response is streaming.

```
display:        inline-block
width:          2px
height:         1em
background:     --color-ink
margin-left:    2px
vertical-align: middle
animation:      blink 1s step-end infinite
```

```css
@keyframes blink { 50% { opacity: 0; } }
```

---

### Star Button (saved toggle)

Icon-only button in the header. Toggles saved-passages view.

```
background:  none
border:      none
cursor:      pointer
padding:     0
line-height: 1
```

SVG: `22×22px; stroke: --color-ink; stroke-width: 1.5; stroke-linejoin: round`

| State | SVG fill |
|---|---|
| no saved passages | `none` |
| has saved passages | `--color-ink` |

---

### Warming / Status Indicator

Fixed bottom-right label that disappears once the API warms up.

```
position:    fixed
bottom:      24px
right:       24px
font-size:   --text-tag
color:       --color-ink-ghost
font-family: Georgia, serif
```

---

## Motion

| Property | Value | Where |
|---|---|---|
| `border-color` transition | `0.2s ease` | All inputs on focus |
| All properties transition | `0.15s ease` | Mode pills |
| Word particle animation | JS-driven | Index page home canvas |
| Blinking cursor | `1s step-end infinite` | Channel streaming response |

**Principle:** Motion is functional. No page-load entrance animations. No hover lifts or scale transforms on cards. No color flashes.

---

## Page Layouts

### Search (index.html)

```
┌────────────────────────────────────────┐
│ h1: Osho Says         stories  channel ★│  ← .header
├────────────────────────────────────────┤
│ [ Type a topic or question... ] [Search]│  ← .input-row
├────────────────────────────────────────┤
│                                        │
│       word particles (canvas)          │  ← #home (100vh − 240px)
│   OR  passage cards + dot separators   │  ← #results
│   OR  saved passage cards              │  ← #saved
│                                        │
│              Searching…                │  ← #spinner
│                    ·                   │  ← end-dot
└────────────────────────────────────────┘
                                           ← #sentinel (1px IntersectionObserver)
```

### Channel (channel.html)

```
┌────────────────────────────────────────┐
│ ← search   Channel                     │  ← .header
├────────────────────────────────────────┤
│                                        │
│  you: [user question]                  │  ← .msg.user
│                                        │
│  [osho response text...]               │  ← .msg.osho
│                    teaching  save      │  ← .meta
│                                        │
│  (repeats)                             │
│                                        │
├────────────────────────────────────────┤
│ [ Ask the channel anything… ▼ ] [Ask]  │  ← .input-row (sticky)
└────────────────────────────────────────┘
                             warming up…   ← .warming (fixed bottom-right)
```

### Stories (stories.html)

```
┌────────────────────────────────────────┐
│ h1: Osho Says           Search  Stories│  ← .header + nav
├────────────────────────────────────────┤
│ Parables, koans, and life lessons…     │  ← .subtitle
│ 142 stories found                      │  ← .count
│ [All] [Book A] [Book B] [Book C]       │  ← .book-filter chips
│ [ Filter stories by keyword...       ] │  ← .filter-box input
├────────────────────────────────────────┤
│                                        │
│  story card                            │
│  · (separator)                         │
│  story card                            │
│  ·                                     │
│                    ·                   │  ← end-dot
└────────────────────────────────────────┘
```

---

## Accessibility Notes

- All interactive elements use `font-family: inherit` — no browser-default fonts bleed in
- **Focus rings:** currently `outline: none` with only border-color change on inputs — add `:focus-visible { outline: 2px solid --color-border-focus; outline-offset: 2px }` for keyboard navigation
- **Color contrast:** `--color-ink-faint` (`#aaa`) on `--color-bg` (`#faf9f7`) is ~2.8:1 — below WCAG AA (4.5:1). Use `--color-ink-subtle` (`#888`) or `--color-ink-muted` (`#666`) for body-level secondary text where possible
- **Aria:** star button and mode dropdown trigger lack `aria-label` — add `aria-label="Saved passages"` and `aria-label="Change mode"` respectively
- **Reduced motion:** word particle animation should respect `prefers-reduced-motion: reduce`
