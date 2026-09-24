---
name: ABS Sync
description: "The Dispatch Desk" — a wholesale-distribution ops console grounded in freight paperwork and warehouse signage, not generic SaaS.
colors:
  ink: "#1C201B"
  paper: "#EBEDE7"
  surface: "#FAFAF8"
  hazard: "#D9720F"
  hazard-deep: "#A8560A"
  hazard-tint: "#FCF0E4"
  steel: "#3C5A5E"
  steel-tint: "#EEF3F3"
  graphite: "#767676"
  hairline: "#e5e7eb"
  signal-healthy: "#059669"
  signal-warning: "#d97706"
  signal-critical: "#e11d48"
  signal-info: "#4f46e5"
typography:
  display:
    fontFamily: "Bebas Neue, sans-serif"
    fontSize: "1.375rem"
    fontWeight: 400
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
  data:
    fontFamily: "IBM Plex Mono, monospace"
    fontSize: "0.75rem"
    fontWeight: 500
  arabic:
    fontFamily: "Scheherazade New, serif"
    fontSize: "1.375rem"
    fontWeight: 400
    lineHeight: 1.2
rounded:
  tag: "4px"
  button: "6px"
  container: "8px"
spacing:
  xs: "6px"
  sm: "10px"
  md: "16px"
  lg: "20px"
components:
  button-primary:
    backgroundColor: "{colors.hazard}"
    textColor: "#ffffff"
    rounded: "{rounded.button}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.hazard-deep}"
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.container}"
---

# Design System: ABS Sync — "The Dispatch Desk"

## 1. Overview

ABS Sync moves physical inventory: it pulls live wholesale catalogs from real distributor warehouses (Ingram Micro, D&H — freight, UPC/EAN barcodes, purchase orders, tracking numbers) and pushes them to consumer marketplaces. It's run by a small ops team who check it constantly through a working day.

**Creative North Star: a dispatch desk.** The visual world is warehouse and freight paperwork — manifests, packing slips, shipping tags, customs stamps — not generic tech-SaaS. This replaced an earlier violet/indigo palette that, on audit, turned out to be its own kind of generic default (arguably the single most common current AI-dashboard color), chosen to match a reference screenshot without being grounded in what this product actually is.

**Key characteristics:**
- Cool, concrete/steel-toned paper background — not warm cream, not tech-lavender.
- One considered accent: hazard/safety-orange (`#D9720F`), the color of pallet tags and hi-vis paint — not a decorative brand gradient.
- Border-first elevation: cards get a hairline border, no shadow at rest. Shadow is earned only by things actually floating above the page (modals, dropdowns).
- A rare display face (Bebas Neue, bold condensed) on page titles only — reads like stenciled warehouse signage. Never used for body text or data.
- Status badges read as shipping tags (small, square-cornered, bordered) — not rounded chips.
- Real hierarchy in the radius scale: tags (4px) < buttons (6px) < containers (8px). No more "one radius reused everywhere regardless of what the element is."

## 2. Colors

### Primary
- **Hazard** (`#D9720F`): the one brand accent. Primary buttons, active nav state, links, primary icon chips. Named for what it is — the color of a warehouse pallet tag — not a generic "brand-500."
- **Hazard Deep** (`#A8560A`): hover/active state, and the only safe shade of the accent to use as body text on paper (the base hazard fails AA as small text).

### Secondary
- **Steel** (`#3C5A5E`): secondary accent for things that need to feel calm/neutral rather than urgent — used sparingly, never competing with hazard for attention.

### Neutral
- **Ink** (`#1C201B`): primary text, headings — a near-black with a faint gunmetal-green cast rather than a flat `#0a0a0a`.
- **Graphite** (`#767676`): secondary text, captions, inactive icons.
- **Paper** (`#EBEDE7`): page background — cool grey-green like warehouse concrete or galvanized steel.
- **Surface** (`#FAFAF8`): card/input background, one step lighter than paper.
- **Hairline** (`#e5e7eb`): borders and dividers.

### Semantic status (unchanged, exempt from novelty)
- Healthy `#059669`, Warning `#d97706`, Critical `#e11d48`, Info `#4f46e5`. These are functional, not decorative — accessibility and consistency win over distinctiveness here.

## 3. Typography

**Display: Bebas Neue.** A bold condensed sans, used ONLY for page-level `<h1>` titles — at most one instance per screen. It's a character face, not a reading face; using it anywhere else (body copy, table data, buttons) would hurt legibility and dilute its rarity. The Arabic "س" in the "سync" wordmark uses Scheherazade New instead, wherever it appears as live text rather than the logo image.

**Body/UI: IBM Plex Sans.** Everything else — labels, body copy, dense tables, buttons. Chosen deliberately kept (not a "default go-to" like Inter/Roboto/Arial) rather than replaced wholesale, since a data-dense ops tool's readability matters more than novelty in the 90% of the UI that's tables and forms.

**Data: tabular/monospace treatment** for SKUs, UPCs, prices, tracking numbers, order IDs — these are literally manifest numbers, so a mono/tabular figure treatment is earned here, not decorative.

### Named Rules
**The One-Display Rule.** Bebas Neue appears at most once per screen (the page title). If a screen wants more "character," add hierarchy through weight/color in Plex Sans, never a second display-face instance.

## 4. Elevation

**Border-first, not shadow-first.** A card is a hairline border on a lighter surface — nothing else — at rest. Add a shadow only when something is temporarily floating above the page (a modal, a dropdown, a popover), never as permanent decoration on a static card or table.

### Shadow vocabulary
- **Resting**: none. A hairline border is the only signal a card needs.
- **Dropdown** (`0 4px 16px -2px rgba(0,0,0,0.08), 0 2px 6px -2px rgba(0,0,0,0.04)`): modals, dropdowns, popovers.

## 5. Components

### Buttons
- **Shape:** 6px radius (`rounded-md`).
- **Primary:** Hazard fill, white text.
- **Hover:** darkens to Hazard Deep.
- **Secondary/Ghost:** white surface, hairline border, ink text.

### Status tags
- **Style:** small, square-cornered (4px radius), tinted background at ~10% of the semantic color, full-strength text, 1px border at ~20% opacity. Reads as a shipping label, not a rounded pill.
- Never color-only — always paired with a short word.

### Containers
- **Corner style:** 8px radius.
- **Elevation:** hairline border, no shadow at rest (see Elevation).
- **Data tables:** prefer a flat, ledger-style table (hairline row dividers, no card wrapper) over boxing every table in its own shadowed card, where the table is the primary content of the page.

### Navigation
- Left sidebar, grouped by task (Overview / Sell / Connections / Operations). Active item: hazard-tinted background, hazard text/icon.

## 6. Do's and Don'ts

### Do:
- Use hazard-orange only on the interactive/primary-accent role — buttons, links, active states, primary icon chips.
- Give every card a hairline border and nothing else at rest.
- Use Bebas Neue exactly once per screen for the page title.
- Keep semantic status colors as documented — don't restyle them for novelty.

### Don't:
- Don't add a drop shadow to a static card "because it looks unfinished" — add nothing, the border is the signal.
- Don't use Bebas Neue for body copy, buttons, or table data — it's a display face used once per screen.
- Don't reach for violet, indigo, or cream+terracotta — both are generic defaults this system explicitly moved away from.
- Don't round a status tag into a pill — it's a label, not a badge.
