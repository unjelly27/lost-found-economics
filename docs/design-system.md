# Premium Aviation Editorial Intelligence

This redesign is a presentation layer over the existing SQLite marts and Decimal financial model. All five analytical sections, filters, exports, source links, and scope rules remain intact.

## Visual system

| Role | Decision |
| --- | --- |
| Canvas | Warm paper `#F6F5F1`, white working surfaces |
| Masthead and navigation | Ink navy `#142B40`, clear white active tab |
| Text | Navy `#172F43`, secondary slate `#576978` |
| Primary data | Aviation teal `#087F83`, paired comparison blue `#4473A0` |
| Meaning | Favorable teal, adverse terracotta `#B85543`, unavailable cool gray |
| Typography | Bundled Geist for controls, tables and numerals; Georgia editorial serif for page titles and featured outcomes |
| Spacing | 8px rhythm, 24–32px section spacing, restrained 6–8px corners |
| Borders | Fine `#DDE3E5` dividers; avoid enclosing every section in identical cards |
| Interaction | Native Streamlit controls, visible focus outlines, subtle hover feedback, reduced-motion support |

## Composition

- The shared masthead combines the identity, source, and coverage. A navy navigation band distinguishes the five sections. Filters form a compact white toolbar.
- Executive Overview uses a large editorial headline, an integrated KPI strip, a primary industry chart, a ranked carrier comparison, and numbered executive notes.
- Airline Explorer uses comparison tiles, a full-width multi-series plot, a ledger-style ranking table, and a chart with a narrative carrier dossier.
- Performance Trends uses a full-width timeline, a matched-year comparison beside volatility, and a full-width heatmap. Long annotations live in explanatory text, away from marks.
- Operational Intelligence separates benchmark gaps and exposure, then pairs the consistency plot with an explanatory reading guide. Reliability is a distinct audit section.
- Baggage Economics Lab has a three-step assumption workbench, a navy modeled-outcome band, readable observed/projected comparisons, and wide scenario and sensitivity sections. Modeled and historical numbers retain explicit labels.

## Chart contract

Chart defaults and palette are centralized in `app/components/chart_theme.py`; analytical chart construction stays in `charts.py` and `financial_charts.py`. Use 12–13px axis labels, generous margins, consistent tooltips, zero-baseline bars, bottom legends with room to wrap, explicit units, and no overlapping quadrant labels. Carrier colors and line styles remain stable. Missing data stays missing. Heatmap values use contrast-aware text and full-width space.

## Responsive behavior and maintenance

Use native layouts and widgets. CSS targets owned HTML classes, explicit Streamlit container keys, semantic state attributes, and only a small documented set of Streamlit test IDs. Do not target generated CSS hashes or positional DOM chains. Stack paired plots at laptop/tablet widths when their labels would become cramped. Keep tables horizontally scrollable. On phones, stack navigation and chart sections, reduce heatmap text density, and retain hover details.

Visual verification and functional checks are recorded in `docs/redesign-verification.md` after actual execution.
