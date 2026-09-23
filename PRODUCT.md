# Product

## Register

product

## Users

A growing team of internal operators (not just the founder) who run day-to-day dropshipping operations: connecting wholesale suppliers, deciding what to sell, setting pricing rules, watching order fulfillment, and reacting to sync errors. Users range from technical (reading raw sync logs, adapter errors) to non-technical staff who just need to know "is everything working and what needs my attention today." The dashboard is checked frequently throughout the day, often as a quick status glance rather than deep analysis.

## Product Purpose

ABS Sync automates multi-marketplace dropshipping: pulling wholesale catalogs, calculating prices and margins, publishing to marketplaces (eBay, Amazon, Shopify), and now running the full order lifecycle (ingestion, supplier routing, purchase orders, tracking, profitability analytics). Success looks like: an operator can tell at a glance whether the business is healthy (suppliers connected, orders flowing, nothing broken) without digging through logs, and can drill into specifics (which SKU is profitable, which supplier is slow) when they need to.

## Brand Personality

Confident, energetic, modern. As of the Phase 6 redesign the product deliberately reads as a polished, colorful SaaS console (violet primary, teal/amber/rose semantic accents, soft-shadow rounded cards) rather than a muted, purely-hairline "ops tool." It should still feel trustworthy and never noisy — but the earlier "quiet until something needs attention" restraint has been intentionally relaxed in favor of richer color and visual hierarchy across cards, charts, and icon chips.

## Anti-references

- Not a crypto/trading-terminal aesthetic (dark mode, neon greens/reds, gauge dials, ticker-style density) — that mood fits speculative trading, not calm operational monitoring for a team.
- Avoid jargon-heavy technical labels where a plain-English one already works (the existing "Products to Sell" / "Your Online Stores" naming convention should be preserved and extended, not replaced with generic "Catalog" / "Listings").
- Still avoid gradient text (`background-clip: text`) and decorative glassmorphism — color richness comes from solid fills, tinted icon chips, and varied semantic accents, not gradients.

## Design Principles

- Glanceable first, detailed second: the most important health signal on any page should be readable in under 2 seconds, with drill-down available but not forced.
- Plain English over technical jargon, since the audience includes non-technical staff.
- Density with clarity: as the team grows and more data accumulates (orders, analytics), pages should scale to more information without becoming cluttered — use hierarchy and grouping, not just smaller text.
- Status is a first-class citizen: health/error states should be visually unmistakable (not buried in a table row), since "is something broken" is the most common question asked of this dashboard.
- Consistency across pages: a user who learns the patterns on the Dashboard should immediately understand Orders, Analytics, and every other page without relearning conventions.

## Accessibility & Inclusion

WCAG AA baseline: sufficient color contrast (especially for status colors: healthy/error/warning must not rely on color alone — pair with icons/text), keyboard-navigable interactive elements, no motion-only indicators of state change.
