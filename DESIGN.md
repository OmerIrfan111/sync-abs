---
name: ABS Sync
description: Confident, colorful operations console for multi-marketplace dropshipping — modern SaaS visual language over the same plain-English, glanceable data.
colors:
  primary-violet: "#6C5DD3"
  primary-violet-deep: "#5B4BD1"
  primary-violet-tint: "#F3F1FD"
  accent-teal: "#14B8A6"
  accent-amber: "#F59E0B"
  accent-pink: "#EC4899"
  ink: "#1B1B2F"
  ink-soft: "#1a1a1a"
  graphite: "#767676"
  hairline: "#f1f0f5"
  paper: "#F6F6FB"
  surface: "#ffffff"
  signal-healthy: "#059669"
  signal-warning: "#d97706"
  signal-critical: "#e11d48"
  signal-info: "#4f46e5"
typography:
  title:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 700
    lineHeight: 1.2
  heading:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "IBM Plex Sans, system-ui, sans-serif"
    fontSize: "0.6875rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.02em"
  wordmark:
    fontFamily: "Special Elite, cursive"
    fontSize: "1.25rem"
    fontWeight: 400
    lineHeight: 1
rounded:
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "20px"
components:
  button-primary:
    backgroundColor: "{colors.primary-violet}"
    textColor: "#ffffff"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-violet-deep}"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.lg}"
---

# Design System: ABS Sync

## 1. Overview

**Creative North Star: "Modern Control Room"**

Phase 6 moved ABS Sync from a muted, hairline-only "quiet ops tool" look to a confident, colorful modern SaaS console (explicitly requested to match reference dashboards with soft-shadow rounded cards, a violet primary, and varied semantic accent colors per metric). The underlying product principles are unchanged — plain-English labels, honest data, status that's never color-only, glanceable-first hierarchy — but the visual expression is richer and more energetic than the original "Control Room" spec.

This still rejects the crypto-trading-terminal mood (dark backgrounds, neon green/red tickers, gauge dials) — that aesthetic signals speculation, not operational trust. It also still avoids gradient text and decorative glassmorphism. What changed is the willingness to use color: multiple accent hues per KPI row, soft card shadows instead of hairline-only borders, and larger corner radii.

**Key Characteristics:**
- Light lavender-tinted canvas (`#F6F6FB`) — never dark mode by default.
- Status is never color-only: every health/error state pairs a color with an icon and a plain-English word.
- One **primary** accent (violet, `#6C5DD3`) for actions, active nav, and links; a rotating set of semantic/chart accents (teal, amber, pink, emerald, rose) for KPI icon chips and data visualizations — this is a "Committed" color strategy, not "Restrained."
- Cards float above the page with a soft shadow (`shadow-sm`, hover `shadow-md`) and generous rounded corners (16-24px), not just a hairline border.
- Plain-English labels over technical jargon everywhere a non-technical operator will read it.

## 2. Colors

### Primary
- **Violet** (#6C5DD3): primary actions, links, active nav item, primary KPI icon chip. The one color that means "this is the app's identity," used generously on interactive elements (buttons, active states) but never as a full-bleed background fill.

### Chart / KPI accent rotation
Used for icon chips and data visualizations to give each metric its own visual identity (a "Committed/Full palette" strategy, replacing the old single-accent rule):
- Teal (#14B8A6), Amber (#F59E0B), Pink (#EC4899), plus the semantic colors below when the metric is itself a health signal.

### Neutral
- **Ink** (#1B1B2F): primary text, headings.
- **Ink Soft** (#1a1a1a): body copy needing more weight than graphite.
- **Graphite** (#767676): secondary/supporting text, placeholder copy, inactive icons.
- **Hairline** (#f1f0f5): subtle dividers inside cards (table rows, list separators) — cards themselves are separated from the page by shadow, not border.
- **Paper** (#F6F6FB): page background (cool lavender-gray, not warm cream).
- **Surface** (#ffffff): card and input backgrounds.

### Semantic status
- **Signal Healthy** (#059669, emerald): connected suppliers/marketplaces, successful syncs, positive profit.
- **Signal Warning** (#d97706, amber): needs attention soon but not broken (credentials expiring, pending routing).
- **Signal Critical** (#e11d48, rose): broken now (auth failures, expired credentials, cancelled orders, negative margin).
- **Signal Info** (#4f46e5, indigo): neutral in-progress states (routed, awaiting shipment) that are neither good nor bad yet.

### Named Rules
**The Status-Never-Alone Rule (unchanged).** A health/error state is never conveyed by color alone. Every status pairs a semantic color with a short label ("Healthy", "Expired", "Needs attention") and, where space allows, an icon.

**The Honest-Data Rule (unchanged, load-bearing).** Never fabricate a value to fill a visual — donuts, bars, and trend lines only ever plot real numbers from the API. If there's no real data for a visualization, omit it rather than inventing placeholder proportions.

## 3. Typography

Unchanged from the original spec — IBM Plex Sans throughout, same Title/Heading/Body/Label scale. Color richness carries the redesign, not new type sizes.

**Wordmark Font:** "Special Elite" — reserved exclusively for the "سync" logotype in the sidebar/header (see `globals.css` font import and `layout.tsx`). Never used for UI copy, labels, or body text; IBM Plex Sans covers all of that.

## 4. Elevation

Shadow-first for page-level cards (a deliberate change from the original border-only spec): `shadow-sm` at rest, `shadow-md` + slight lift on hover for clickable cards. A thin `border-gray-100` is kept underneath the shadow for crisp edges at all zoom levels, but the shadow — not the border — is what separates a card from the page now.

### Shadow Vocabulary
- **Card resting** (`shadow-sm`, Tailwind default): every page-level card (KPI cards, panel cards, table containers).
- **Card hover** (`shadow-md` + `-translate-y-0.5`): interactive/clickable cards.
- **Dropdown** (`0 4px 16px -2px rgba(0,0,0,0.08), 0 2px 6px -2px rgba(0,0,0,0.04)`): menus, modals, popovers.

## 5. Components

### Buttons
- **Shape:** rounded-xl (12px).
- **Primary:** Violet (#6C5DD3) fill, white text, 8px/16px padding, text-xs font-semibold, subtle violet-tinted shadow.
- **Hover / Focus:** primary darkens to `#5b4bd1`; all interactive elements get a visible focus ring for keyboard users (never `focus:outline-none` without a replacement — inputs get `focus:ring-2 focus:ring-[#0a0a0a]/[0.06]` alongside the border-color change).
- **Secondary / Ghost:** white surface, gray-200 border, ink text.

### Status Badges
- **Style:** pill (rounded-full), pastel-tint background of the semantic color at ~10% opacity, full-strength semantic color text, 1px border of the same color at ~20% opacity.
- **Never icon-only or color-only:** always paired with a short word (Healthy / Error / Pending).

### Cards / Containers
- **Corner Style:** rounded-2xl (16px) for page-level cards, rounded-lg/xl for nested elements.
- **Background:** Surface (#ffffff) on Paper (#F6F6FB) page background.
- **Shadow Strategy:** `shadow-sm` at rest (see Elevation) — this is the one deliberate departure from "border-before-shadow."
- **Border:** thin `border-gray-100`, present but secondary to the shadow.
- **Internal Padding:** 16-20px (spacing.md/lg).

### Inputs / Fields
- **Style:** white background, gray-300 border, rounded-lg, text-sm.
- **Focus:** border shifts to Ink, plus `focus:ring-2 focus:ring-[#0a0a0a]/[0.06]` — applied consistently across every text input, select, and textarea in the app.

### Navigation
- **Style:** left sidebar, white background, hairline right border, items grouped under small uppercase section labels (Overview / Sell / Connections / Operations). Active item: violet-tinted pill background (`bg-[#6C5DD3]/10`) with violet icon and text — not a solid dark fill.

### KPI Cards (signature component)
A Label-weight caption, a large bold number, a one-line Graphite description, and a small icon chip in a pale tint of a rotating accent color (violet, teal, amber, rose, emerald — see Chart/KPI accent rotation) so each metric in a row reads as visually distinct at a glance, not a repeated identical template.

### Data visualizations
Small, real-data-only components (`Donut`, `Sparkline`, `Gauge` in `src/components/`) using the accent rotation and semantic colors. No third-party chart library; kept intentionally simple (SVG arcs/lines) and always driven by actual API numbers.

## 6. Do's and Don'ts

### Do:
- **Do** use the violet primary for actions, links, and active states; use the accent rotation (teal/amber/pink) plus semantic colors for KPI icon chips and charts.
- **Do** give page-level cards a soft shadow (`shadow-sm`) and 16px+ rounded corners.
- **Do** pair every status color with a text label and, where there's room, an icon (Status-Never-Alone Rule).
- **Do** use plain-English labels ("Products to Sell", "Your Online Stores") over technical jargon anywhere non-technical operators will read them, per PRODUCT.md.
- **Do** keep every visualization honest — real proportions and numbers only, never fabricated to "fill out" a chart.

### Don't:
- **Don't** switch to dark mode, neon status colors, or gauge-dial widgets — the crypto-trading-terminal mood is still rejected.
- **Don't** use gradient text or decorative glassmorphism.
- **Don't** show internal version labels, infra stack details, or other jargon that isn't actionable for the person reading it.
- **Don't** rely on a colored dot alone to communicate health/error state with no accompanying word.
