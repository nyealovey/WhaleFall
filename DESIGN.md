# Design System: WhaleFall Operations Console

## 1. Visual Theme & Atmosphere

DBA cockpit dense. This interface is a working console for database operations, not a marketing product. Density: 8/10. Variance: 3/10. Motion: 2/10.

The screen should feel like a calibrated operations desk: compact, quiet, scan-first, and exact. The layout favors information grouping, stable table rhythm, low visual noise, and immediate comparison across instances, accounts, risk signals, and task status.

Hero sections are not required for this product. Page headers are compact command headers: title, one sentence of context, and a small action cluster. Inline image typography, decorative hero treatments, and cinematic section choreography do not apply to this system.

Core data structures stay unchanged. New screens must keep existing identifiers, endpoint contracts, Grid.js data shapes, Jinja context fields, and `data-*` hooks unless a separate migration explicitly changes them.

## 2. Color Palette & Roles

- **Control Canvas** (#E8EDF1) - Primary app background, cool neutral, low glare.
- **Panel White** (#F8FAFB) - Raised panels, cards, modal bodies, and table shells.
- **Rail White** (#F3F6F8) - Sidebar, topbar, filter command strips.
- **Charcoal Ink** (#17202A) - Primary text and high-emphasis labels.
- **Steel Ink** (#4C5C69) - Secondary text, help text, timestamps.
- **Hairline Steel** (rgba(36, 47, 59, 0.12)) - Default 1px borders and table dividers.
- **Signal Copper** (#B85C1E) - Primary actions, active nav, focus rings, and selected states.
- **Operational Green** (#288766) - Healthy state only.
- **Audit Amber** (#CB8A1F) - Warning state only.
- **Incident Red** (#CB5D49) - Danger state only.
- **Telemetry Blue** (#2C96C6) - Informational state only.

Rules: keep the background neutral and mostly flat. Use Signal Copper as the only decorative accent. Status colors are semantic, never decorative. No purple or neon blue gradients. Never use pure black.

## 3. Typography Rules

- **Display:** IBM Plex Sans Condensed - compact page titles, section labels, and large KPI values.
- **Body:** IBM Plex Sans - all readable interface text.
- **Mono/Data:** IBM Plex Mono - all numbers, percentages, timestamps, IDs, short codes, and table metadata.
- **Density:** high-density numbers use tabular figures or the mono stack. KPI values must align visually across cards.
- **Headers:** sentence case where possible. Do not force large uppercase titles inside dense panels.
- **Body copy:** short and literal. Avoid marketing language.

## 4. Component Stylings

- **Buttons:** compact rectangular controls with small radius, clear border, visible focus ring, and tactile active translate. Primary buttons use Signal Copper fill. Secondary and icon buttons keep borders.
- **Metric cards:** low-height data blocks. The label is quiet, the value is the focal point, and meta chips stay compact. Use cards for top-level KPIs only.
- **Tables:** table rows are dense and stable. Header labels use mono. Row actions stay icon-first where the action is familiar and include accessible names.
- **Filter strips:** use command-strip styling, not large cards. Labels sit above controls. Dense pages should keep filters on one row where viewport allows.
- **Risk cards:** compact tiles with a severity rail, database type, instance name, severity icon, and five fixed signal cells. No visible action menu in the tile.
- **Progress bars:** no inline width in templates. Server output provides data attributes; JS applies visual widths after mount.
- **Empty states:** compact and useful. Explain what is missing and keep the layout footprint controlled.

## 5. Layout Principles

- Use the existing Flask, Jinja, Bootstrap, Grid.js, and vanilla CSS stack.
- Keep `.layout-shell > .layout-shell-inner` as the page width contract.
- Dense sample pages use `page_density = 'dense'`.
- Prefer grid layout for dashboard and risk-board composition.
- Avoid full-page hero sections, oversized cards, and decorative section bands.
- The first viewport should show operational data, not introductory copy.
- Mobile layouts collapse to one column and may trade density for readability.

## 6. Motion & Interaction

Perpetual motion is banned in the operations console. Motion should confirm action, not entertain. Use short transitions on `transform`, `opacity`, `background-color`, `border-color`, and `box-shadow`. Do not animate `top`, `left`, `width`, or `height`.

Hover states may shift by 1px or change background/border. Active states may translate down by 1px. Loading states should use existing button loading or skeleton-like placeholders where available.

## 7. Anti-Patterns

Never use: pure black, purple neon gradients, marketing hero sections, inline image typography, oversized rounded cards, decorative outer glows, always-on animations, generic 3-card feature rows, fake round demo numbers, generic placeholder names, cliche product copy, browser `confirm()`, or template inline layout widths.

For this application, avoid replacing dense data screens with sparse editorial layouts. The premium quality target is precision, not emptiness.
