# Product

## Register

product

## Users

A growing team of internal operators (not just the founder) who run day-to-day dropshipping operations: connecting wholesale suppliers, deciding what to sell, setting pricing rules, watching order fulfillment, and reacting to sync errors. Users range from technical (reading raw sync logs, adapter errors) to non-technical staff who just need to know "is everything working and what needs my attention today." The dashboard is checked frequently throughout the day, often as a quick status glance rather than deep analysis.

## Product Purpose

ABS Sync automates multi-marketplace dropshipping: pulling wholesale catalogs, calculating prices and margins, publishing to marketplaces (eBay, Amazon, Shopify), and now running the full order lifecycle (ingestion, supplier routing, purchase orders, tracking, profitability analytics). Success looks like: an operator can tell at a glance whether the business is healthy (suppliers connected, orders flowing, nothing broken) without digging through logs, and can drill into specifics (which SKU is profitable, which supplier is slow) when they need to.

## Brand Personality

**"The Dispatch Desk."** ABS Sync moves physical inventory through real warehouses and freight — the visual identity is grounded in that (manifests, packing slips, warehouse signage), not in generic tech-SaaS conventions. An AI-slop audit found that the prior violet/indigo palette, while colorful and polished, was itself a generic default — arguably the most common current AI-dashboard color choice — chosen to match a reference screenshot rather than anything specific to this product. The current identity (hazard-orange accent, steel/concrete neutrals, a typewriter display face used once per screen) replaced it deliberately. Still trustworthy, never noisy, but now recognizably *this* product rather than swappable onto any other SaaS dashboard.

## Anti-references

- Not a crypto/trading-terminal aesthetic (dark mode, neon greens/reds, gauge dials, ticker-style density) — that mood fits speculative trading, not calm operational monitoring for a team.
- Avoid jargon-heavy technical labels where a plain-English one already works (the existing "Products to Sell" / "Your Online Stores" naming convention should be preserved and extended, not replaced with generic "Catalog" / "Listings").
- Avoid gradient text (`background-clip: text`) and decorative glassmorphism.
- Avoid generic violet/indigo "AI-SaaS" primary accents and warm-cream-plus-terracotta palettes — both are current default clusters, not choices specific to this product.
- Avoid the identical-card-everywhere pattern: every container getting the same radius and the same soft drop-shadow regardless of what it is or how important it is.

## Design Principles

- Glanceable first, detailed second: the most important health signal on any page should be readable in under 2 seconds, with drill-down available but not forced.
- Plain English over technical jargon, since the audience includes non-technical staff.
- Density with clarity: as the team grows and more data accumulates (orders, analytics), pages should scale to more information without becoming cluttered — use hierarchy and grouping, not just smaller text.
- Status is a first-class citizen: health/error states should be visually unmistakable (not buried in a table row), since "is something broken" is the most common question asked of this dashboard.
- Consistency across pages: a user who learns the patterns on the Dashboard should immediately understand Orders, Analytics, and every other page without relearning conventions.

## Accessibility & Inclusion

WCAG AA baseline: sufficient color contrast (especially for status colors: healthy/error/warning must not rely on color alone — pair with icons/text), keyboard-navigable interactive elements, no motion-only indicators of state change.
