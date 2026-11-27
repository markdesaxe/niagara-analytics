# UI mock-ups (layout only, sample data)

Live canvas: https://claude.ai/artifact/HUo7SF8CBEyKMGUuFZUH2d

| File | Screen |
|---|---|
| `Main.dc.html` | Site overview |
| `Trends.dc.html` | Trend explorer |
| `Faults.dc.html` | Fault and alarm console |

These are the sources of the design canvas above (`.dc.html` design components plus
`canvas.json` for the layout). They render on the canvas, not as standalone pages,
because they rely on the canvas runtime. Every number on them is sample data except the
equipment names, rule counts and trend gaps, which come from `sites/kitchener/`.

The real views will be built as Niagara bajaux HTML5 views in step 4.
