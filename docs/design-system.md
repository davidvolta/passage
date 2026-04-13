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
- Color is used only for semantic mode indicators — nowhere else in the interface.

**Anti-patterns:** gradients, drop shadows on cards, colorful accents outside mode pills, rounded hero images, icon libraries, loading skeletons, modal overlays, book filter chips.

---

## Color Tokens

### Base palette

| Token | Hex | Usage |
|---|---|---|
| `--color-bg` | `#faf9f7` | Page background — warm off-white, slightly cream |
| `--color-surface` | `#ffffff` | Cards, inputs |
| `--color-border` | `#e8e6e3` | Card borders, sidebar border — warm light gray |
| `--color-border-input` | `#cccccc` | Input default border, meta button border |
| `--color-border-focus` | `#666666` | Input focused border |
| `--color-ink` | `#2a2a2a` | Primary text, headings, active/filled buttons |
| `--color-ink-muted` | `#666666` | Secondary text, hover states |
| `--color-ink-subtle` | `#888888` | Meta text, user messages in channel, sidebar labels |
| `--color-ink-faint` | `#aaaaaa` | Empty states, disabled hints |
| `--color-ink-ghost` | `#bbbbbb` | Ghost save button, warming indicator, book counts |
| `--color-separator` | `#cccccc` | Dot separators between passages |
| `--color-hover-surface` | `#f5f5f5` | Sidebar item hover |

### Mode pill colors (the only accent colors in the interface)

| Token | Hex | Mode |
|---|---|---|
| `--color-mode-purple` | `#7c5cbf` | casual / semantic |
| `--color-mode-red` | `#b04040` | teaching / exact |
| `--color-mode-blue` | `#3a6eaa` | story |

---

## Typography

**Font stack:** `Georgia, serif` — used everywhere, no sans-serif.

| Token | Size | Line height | Usage |
|---|---|---|---|
| `--text-body-lg` | `1.05rem` | `1.9` | Channel response in teaching mode |
| `--text-body` | `1rem` | `1.8` | Channel response default |
| `--text-body-sm` | `0.95rem` | `1.7` | Passage previews, inputs, buttons, tab links |
| `--text-meta` | `0.85rem` | default | Book titles, inline action buttons, sidebar items |
| `--text-tag` | `0.8rem` | default | Ghost save button, warming indicator, mode tag label |
| `--text-xs` | `0.75rem` | default | Mode pill label, book count in sidebar |

All interactive elements use `font-family: inherit`.

---

## Spacing

| Token | Value | Usage |
|---|---|---|
| `--space-2` | `8px` | Input row gap, pill inset from edge |
| `--space-3` | `10px` | Mode pill horizontal padding |
| `--space-4` | `12px` | Between passage preview and meta row; sticky input top padding |
| `--space-6` | `16px` | Sidebar item vertical gap, sidebar header margin-bottom |
| `--space-card` | `20px` | Card internal padding |
| `--space-section` | `24px` | Toolbar margin-bottom, search bar margin-bottom |
| `--space-input-x` | `14px` | Input/textarea left padding |
| `--space-input-right` | `95px` | Channel textarea right padding — reserves room for mode pill (Passages search has no pill) |
| `--space-input-y` | `10px` | Input/textarea vertical padding |
| `--space-page-bottom` | `32px` | Content top padding, messages bottom margin |
| `--space-sidebar` | `200px` | Sidebar open width (desktop) |
| `--space-sidebar-mobile` | `240px` | Sidebar open width (mobile overlay) |
| `--space-separator` | `28px` | Vertical padding around dot separators |
| `--space-end-top` | `120px` | End-dot top padding |
| `--space-end-bottom` | `80px` | End-dot bottom padding |
| `--space-page-x` | `20px` | Page horizontal padding |

---

## Border Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-card` | `8px` | Passage cards |
| `--radius-input` | `6px` | Text inputs, textareas, primary buttons |
| `--radius-btn-meta` | `4px` | Save/Remove inline meta buttons, Books toolbar button |
| `--radius-pill` | `20px` | Mode pills (inset in inputs) |
| `--radius-dot` | `50%` | Dot separators |

---

## Layout

- **Max content width:** `720px`, centered with `margin: 0 auto`
- **Page padding:** `0 20px` (tab bar sits flush top, content starts below it)
- **Tab bar:** fixed to top of every page, `border-bottom: 1px solid --color-border`
- **Passages layout:** `display: flex` — sidebar (collapsible) + main column
- **Channel layout:** `min-height: 100vh; display: flex; flex-direction: column` — input row sticks to `bottom: 20px`
- **Mobile breakpoint:** `600px` — sidebar switches from push-layout to fixed overlay

---

## Components

### Tab Bar

Persistent top navigation on every page. No logo or title — tabs speak for themselves.

```
display:       flex
border-bottom: 1px solid --color-border
padding-top:   20px
```

**Tab link:**
```
padding:      12px 20px
font-size:    --text-body-sm
color:        --color-ink-subtle
text-decoration: none
font-family:  inherit
border-bottom: 2px solid transparent
transition:   color 0.15s
```

| State | Change |
|---|---|
| hover | `color: --color-ink` |
| active page | `color: --color-ink; border-bottom-color: --color-ink` |

Pages: `Home`, `Passages`, `Channel`, `Favorites`

---

### Input Bar (shared — Passages search + Channel chat)

Both pages use the same input visual. Passages uses `<input>`, Channel uses `<textarea>` (auto-grow, capped at 160px).

```
width:         100%
padding:       10px 14px              ← no mode pill in Passages; Channel uses 95px right for mode pill
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

**Action button** (Search / Ask) sits outside the wrapper:
```
padding:       10px 20px
font-size:     --text-body-sm
background:    --color-ink
color:         #ffffff
border:        none
border-radius: --radius-input
font-family:   inherit
white-space:   nowrap
```

| State | Change |
|---|---|
| hover | `background: #444444` |
| disabled | `background: --color-border-input; cursor: default` |

---

### Mode Pill (inset in Input Bar)

A colored pill absolutely positioned at the right edge of the Channel input. Clicking it cycles through modes. This is the **only** use of color in the UI. (Passages search does not have a mode pill.)

```
position:      absolute
right:         8px
top:           50%
transform:     translateY(-50%)
padding:       3px 10px
border-radius: --radius-pill
font-size:     --text-xs
font-family:   inherit
cursor:        pointer
user-select:   none
background:    transparent
border:        1px solid currentColor
white-space:   nowrap
transition:    opacity 0.15s
```

hover: `opacity: 0.7`

**Modes and colors:**

| Mode | Context | Color token | Hex |
|---|---|---|---|
| `casual` | Channel | `--color-mode-purple` | `#7c5cbf` |
| `teaching` | Channel | `--color-mode-red` | `#b04040` |
| `story` | Channel | `--color-mode-blue` | `#3a6eaa` |

Channel cycles: `CASUAL → TEACHING → STORY → CASUAL`

---

### Card — Passage

A contained reading unit. No hover effect. No shadow.

```
background:    --color-surface
border:        1px solid --color-border
border-radius: --radius-card
padding:       --space-card
```

**Preview text:** `--text-body-sm`, `line-height: 1.7`, `white-space: pre-wrap`

**Meta row** (`display: flex; justify-content: space-between; align-items: center; font-size: --text-meta; color: --color-ink-subtle`)
- Left: book title — `font-style: italic`
- Right: Save / Saved / Remove button

---

### Button — Meta (card action)

Save, Saved, Remove — sits in card meta row.

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

Appears in message meta row after streaming completes.

```
background:  none
border:      none
font-size:   --text-tag
color:       --color-ink-ghost
font-family: inherit
padding:     0
cursor:      pointer
```

| State | Change |
|---|---|
| hover | `color: --color-ink-muted` |
| saved | `color: --color-ink` |

---

### Sidebar — Book List (Passages page)

Collapsible panel on the left of the Passages page. On mobile it becomes a fixed overlay.

**Collapsed:** `width: 0; overflow: hidden`
**Open:** `width: 200px; padding-right: 20px; border-right: 1px solid --color-border`
Transition: `width 0.2s, padding 0.2s`

**Header row:**
```
display:         flex
justify-content: space-between
align-items:     center
margin-bottom:   16px
```
- Left label: `font-size: --text-meta; color: --color-ink-subtle` — "Books"
- Right close button: `font-size: --text-meta; color: --color-ink-ghost`, hover `--color-ink-muted`

**Book list item:**
```
padding:         6px 0
font-size:       --text-meta
color:           --color-ink-muted
cursor:          pointer
white-space:     nowrap
overflow:        hidden
text-overflow:   ellipsis
transition:      color 0.15s
```

| State | Change |
|---|---|
| hover | `color: --color-ink` |
| active | `color: --color-ink; font-weight: 500` |

Book count badge: `font-size: --text-xs; color: --color-ink-ghost; margin-left: 4px`

**Mobile (≤600px):** sidebar is `position: fixed; top: 0; left: 0; height: 100vh; z-index: 100; width: 240px`. A translucent overlay (`rgba(0,0,0,0.15)`) fills the rest of the screen and dismisses the sidebar on tap.

---

### Toolbar (Passages page)

Sits between the input bar and results. Contains the Books button and result count.

```
display:       flex
align-items:   center
gap:           12px
margin-bottom: 16px
```

**Books button:**
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
| book filter active | `background: --color-ink; color: #fff; border-color: --color-ink; text reflects selected book` |

---

### Separator — Dot

A single 6px dot between passage cards.

```
display:         flex
justify-content: center
padding:         28px 0
```

`::after`: `width: 6px; height: 6px; background: --color-separator; border-radius: 50%`

---

### Blinking Cursor (streaming)

Shown inline while channel response is streaming.

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

### Warming Indicator

Fixed bottom-right status label; disappears once API is ready.

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

| Element | Property | Value |
|---|---|---|
| Inputs | `border-color` | `0.2s ease` on focus |
| Mode pill | `opacity` | `0.15s` on hover |
| Sidebar | `width`, `padding` | `0.2s` open/close |
| Word particles | position, opacity, scale | JS-driven (rAF loop) |
| Streaming cursor | opacity | `1s step-end infinite` |

**Principle:** No entrance animations. No hover lifts. No color flashes. Motion communicates state changes only.

---

## Page Layouts

### Home (`/`)

```
┌────────────────────────────────────────┐
│ Home  Passages  Channel          ♡     │  ← tab bar
├────────────────────────────────────────┤
│                                        │
│                                        │
│         word particle animation        │  ← #home (100vh − tab height)
│      (click word → /passages?q=word)    │
│                                        │
│                                        │
└────────────────────────────────────────┘
```

---

### Passages (`/passages`)

```
┌────────────────────────────────────────┐
│ Home  Passages  Channel          ♡     │  ← tab bar
├──────────┬─────────────────────────────┤
│ Books    │  [ search...           ] [Search] │
│          │                             │
│ ○ All    │  [Books ▾]  142 passages    │  ← toolbar
│ ○ Book A │                             │
│ ○ Book B │  passage card               │
│ ○ Book C │  ·                          │
│          │  passage card               │
│  (close) │  ·                          │
└──────────┴─────────────────────────────┘
```

Sidebar is hidden by default. "Books" button opens it. On mobile: overlay.

---

### Channel (`/channel`)

```
┌────────────────────────────────────────┐
│ Home  Passages  Channel          ♡     │  ← tab bar
├────────────────────────────────────────┤
│                                        │
│  you: [user question]                  │  ← .msg.user
│                                        │
│  [response text...]                    │  ← .msg.osho
│                     CASUAL  ♡          │  ← .meta
│                                        │
│  (repeats)                             │
│                                        │
├────────────────────────────────────────┤
│ [ Ask anything...          CASUAL ] [Ask] │  ← sticky input row
└────────────────────────────────────────┘
                              warming up…  ← fixed bottom-right
```

---

### Favorites (`/favorites`)

```
┌────────────────────────────────────────┐
│ Home  Passages  Channel          ♡     │  ← tab bar
├────────────────────────────────────────┤
│                                        │
│  passage card               [Remove]   │
│  ·                                     │
│  passage card               [Remove]   │
│  ·                                     │
│                    ·                   │  ← end-dot
│                                        │
│  OR: "No saved passages yet"           │  ← empty state
└────────────────────────────────────────┘
```

---

## Accessibility Notes

- All interactive elements use `font-family: inherit`
- **Focus rings:** inputs use `outline: none` — add `:focus-visible { outline: 2px solid --color-border-focus; outline-offset: 2px }` for keyboard navigation
- **Mode pill contrast:** purple `#7c5cbf` and red `#b04040` on white meet WCAG AA at small text; blue `#3a6eaa` is borderline — verify at actual rendered size
- **Color contrast:** `--color-ink-faint` (`#aaa`) on `--color-bg` is ~2.8:1, below WCAG AA — use `--color-ink-subtle` or darker for body text
- **Sidebar:** add `aria-expanded` to the Books button; `role="navigation"` and `aria-label="Book filter"` to the sidebar
- **Mode pill:** add `aria-label="Current mode: casual. Click to change."` updated on each cycle
- **Reduced motion:** word particle animation should respect `prefers-reduced-motion: reduce`
