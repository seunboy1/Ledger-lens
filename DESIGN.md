# Ledger Lens: Design System

The visual and interaction language for Ledger Lens. The source of truth is `frontend/src/app/globals.css` (tokens) and `frontend/src/components/` (patterns). When code and this file disagree, fix one of them.

Companion docs: [`docs/PRD.md`](docs/PRD.md) (what and why) and [`docs/architecture.md`](docs/architecture.md) (how).

---

## 1 · Design read

**What it is:** a product tool for credit analysts at lenders, plus a public landing page that explains it.

**What it should feel like:** a precise instrument. Calm, dense where the data is dense, and never decorative around money. The trust comes from showing the work (rows, plan, proof), not from visual flourish.

| Surface | Variance | Motion | Density |
|---|---|---|---|
| App (Overview, Ask, Statements) | 4 | 3 | 7 |
| Landing page | 6 | 4 | 4 |

## 2 · Principles

1. **Show the source.** Every figure offers a path to the rows behind it: the evidence panel, "View rows" links on signals, the balance proof on each statement.
2. **Numbers are typeset, not decorated.** Figures use Geist Mono with tabular numerals. No gradients, glows or oversized hero numbers on financial data.
3. **Unverified data looks unverified.** Statements in review, failed rows and AI-repaired rows each have their own status treatment and are excluded from answers, and the UI says so.
4. **Say how the answer was produced.** Route ("Answered with SQL aggregation"), filters, tenant scope and the row count are visible in plain words.
5. **Plain copy.** Short, concrete sentences. No em-dashes, no filler verbs, no invented precision.

---

## 3 · Colour

Cool neutrals, one cobalt accent, and semantic credit/debit colours. All colours are CSS custom properties on `:root`, exposed to Tailwind v4 via `@theme inline` (`bg-surface`, `text-ink-soft`, `border-line`, `text-credit`…). Raw hex in components is not allowed.

### 3.1 Tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | `#f4f5f7` | `#0c0e11` | Page ground, sidebar |
| `--surface` | `#fcfcfd` | `#13161b` | Panels, tables, composer |
| `--surface-sunken` | `#eef0f3` | `#0f1115` | Hover fills, user bubbles, active tab |
| `--border` / `--border-strong` | `#e1e4e9` / `#c9ced6` | `#232830` / `#353c47` | Hairlines / control borders |
| `--ink` | `#0f1217` | `#e7e9ec` | Primary text, primary button |
| `--ink-soft` | `#454c58` | `#b0b6c0` | Secondary text |
| `--muted` | `#646b77` | `#8a919c` | Labels, captions (≥ 4.5:1 on `--bg`) |
| `--accent` | `#2b45d4` | `#7b8ffa` | Focus, selection, the one call to attention |
| `--accent-ink` / `--accent-soft` | `#2239b8` / `#e9ecfd` | `#a5b2fc` / `#1b2142` | Accent text / accent fill |
| `--credit` / `--credit-soft` | `#0c6e46` / `#e4f3ec` | `#4cc28f` / `#11261c` | Money in (text) |
| `--debit` / `--debit-soft` | `#b4361c` / `#fbebe6` | `#f08a70` / `#2c1712` | Money out (text) |
| `--warn` / `--warn-soft` | `#8a5200` / `#fbf0db` | `#e8b056` / `#2a1f0c` | Needs review |
| `--error` / `--error-soft` | `#9b2c4a` / `#f8e6ec` | `#ec8aa6` / `#2c1219` | Failed, validation errors |
| `--chart-in` / `--chart-out` | `#0c6e46` / `#e0703c` | `#2e9b6a` / `#e0583f` | Chart marks only |
| `--chart-line` / `--chart-grid` | `#454c58` / `#e6e8ec` | `#b0b6c0` / `#222730` | Balance line / gridlines |

### 3.2 Rules

- **Credit and debit are semantic.** Green is money in, red-orange is money out, nothing else. Errors use plum (`--error`), never `--debit`, so an error never reads as a withdrawal.
- **Text colours and chart colours are separate tokens.** The chart pair was run through the dataviz palette validator: light passes with deutan/protan ΔE 10.6, dark is ΔE 7.8 and therefore always ships with secondary encoding (legend, direct label on the peak, 2px gap between bars, table view). The text pair is tuned for WCAG AA instead.
- **Colour is never the only signal.** Badges carry words and icons; signed amounts carry `+`/`−`; evidence rows say "Credit" or "Debit".
- **One accent.** Primary buttons are ink, not accent. Accent is for focus, selection and links.
- **Theme:** follows `prefers-color-scheme`, overridable with `data-theme="light|dark"` from the toggle in the sidebar (persisted, applied before first paint). One theme per page; no section inverts. The sidebar is not dark-in-light.

---

## 4 · Typography

Loaded with `next/font/google` in `app/layout.tsx`.

| Role | Family | Use |
|---|---|---|
| UI and headings | **Geist** | Everything textual |
| Figures | **Geist Mono** + `tabular-nums` (`.num` class) | Amounts, counts, dates in tables, fingerprints, query-plan details |

| Step | Size | Where |
|---|---|---|
| Display | 38 / 52 / 58px, semibold, −0.03em | Landing hero only |
| Section | 30px semibold | Landing section headings |
| Page title | 24px semibold | App page headings |
| Panel title | 14–15px semibold | Section and panel headings |
| Body | 14.5–15px, line-height 1.65 | Answers, descriptions |
| UI | 13–13.5px | Tables, nav, buttons |
| Caption | 12–12.5px | Labels, metadata (minimum size) |
| Figure | 18–22px mono | KPIs |

**Number formatting** (`lib/format.ts`): Naira with a symbol, separators and 2 decimals (`₦1,251,582.94`); signed values use a true minus (`−₦2,010.00`); statement dates are calendar dates formatted in UTC (`05 Aug 2026`), so they never shift a day with the viewer's time zone.

---

## 5 · Shape, space, elevation

- **Radius system (one rule, used everywhere):** controls 8px (`--radius-ctl`: buttons, inputs, nav rows), panels 12px (`--radius-panel`: cards, tables, composer, sheets), status pills fully rounded. Nothing else.
- **Spacing:** Tailwind 4px scale. Page gutters `px-5` (mobile) / `px-8`. App content max width 1080 to 1180px.
- **Elevation:** flat. Depth comes from `--bg` → `--surface` and 1px borders. One shadow token (`--shadow-pop`) for floating things: tooltips, the landing preview, menus.
- **Cards only where elevation means something** (the proof, the review queue, tables). KPIs and signals sit on dividers, not in boxes.

---

## 6 · Layout

### App shell
```
┌───────────┬─────────────────────────────────────────────┐
│ Sidebar   │ Page                                        │
│ 240px     │  Overview: KPI strip, charts + signals      │
│ brand     │  Ask: conversations │ thread │ evidence     │
│ workspace │  Statements: dropzone, list, detail         │
│ nav       │                                             │
│ user      │                                             │
│ theme     │                                             │
└───────────┴─────────────────────────────────────────────┘
```

| Width | Behaviour |
|---|---|
| ≥ 1280 | Ask shows conversations, thread and a docked evidence panel (380px) |
| 1024–1279 | Evidence opens as a right-hand sheet from the answer or header button |
| 768–1023 | Conversation list hidden ("New" in the header); sidebar stays |
| < 768 | Sidebar becomes a drawer behind a 48px top bar; evidence is a bottom sheet; composer respects the safe-area inset; inputs are 16px so iOS does not zoom |

No page scrolls horizontally at any width. Wide tables sit in their own `overflow-x-auto` containers.

### Landing
Hero headline on its own row (max 2 lines on desktop), then subtext and CTAs beside a real component preview: the same `MessageView` the app uses, rendering actual output from the demo data. Then: one comparison table (three layouts → one stored row), a sticky-heading process list, the proof equation with real figures, and an asymmetric bento of engineering facts. No eyebrows, no fake screenshots, no logo wall.

---

## 7 · Components

| Component | File | Notes |
|---|---|---|
| App shell | `components/AppShell.tsx` | Auth guard (redirects with `?next=`), nav with review-count badge, mobile drawer |
| Button | `components/ui/button.tsx` | `primary` (ink), `accent`, `secondary`, `ghost`, `danger`; sizes `sm/md/lg/icon`; press scales to 0.98 |
| Status badge | `components/StatusBadge.tsx` | Reconciled / Needs review / Processing (spinner) / Failed. Icon + word, never colour alone |
| Message | `components/ask/MessageView.tsx` | Fixed order: route line, answer, KPI strip, evidence button, feedback |
| Evidence panel | `components/ask/EvidencePanel.tsx` | Radix Tabs: *Rows* (description, date, bank, signed amount, printed label when it differs from the canonical type) and *Query plan* (timeline). Notes when only part of the matching rows are shown |
| Composer | `components/ask/Composer.tsx` | Auto-growing textarea, Enter sends, Shift+Enter newline, single focus ring |
| Charts | `components/overview/Charts.tsx` | Grouped bars for in/out, a separate line for balance (never dual-axis). Hover tooltips, focusable bars, direct label on the peak, table view toggle |
| Balance proof | `components/statements/StatementDetail.tsx` | `opening + credits − debits = computed` vs printed closing, with a match or the exact difference |
| Review row | same | Extracted amount, printed balance, the amount the balance implies, an input pre-filled with it, "Save and re-check" |
| Theme toggle | `components/ThemeToggle.tsx` | System / Light / Dark radiogroup |
| Error and loading | `components/States.tsx` | Inline error with retry; shimmer skeletons shaped like the content |

---

## 8 · Motion

Motivated only: new messages and drawers rise 4px and fade in (`.rise-in`, 280ms, `--ease-out`); buttons compress on press; skeletons shimmer while loading; the processing badge spins. Nothing loops for decoration. Under `prefers-reduced-motion` all of it is removed.

## 9 · Accessibility

- Visible `:focus-visible` ring everywhere (2px accent outline), one ring per control.
- Real tables with captions and `scope="col"` headers; Radix Tabs and Dialog for roles and focus management.
- `aria-live` on the answer thread and upload list; `aria-current` on nav; `aria-pressed` on toggles; labels on every icon button and input.
- Charts have `role="img"` labels, keyboard-focusable bars with spoken values, and a table view.
- Contrast: text tokens meet AA on their surfaces in both themes.

## 10 · Voice

- Lead with the number, then the scope: "Total debits (July 2026, Kestrel Bank) came to ₦480,800.00 over 18 transactions."
- Admit coverage: "This excludes 1 statement that is still processing or awaiting review."
- Be honest about the build: the sign-in page says it is a demo workspace for a fictional lender; the landing preview says it is live output on fictional statements.

## 11 · Known gaps

- Real SSO is not wired; the sign-in page enters the demo workspace.
- No keyboard shortcut layer (for example `/` to focus the composer) yet.
- Charts are hand-built SVG; if more chart types arrive, move to a charting library that preserves these specs.
