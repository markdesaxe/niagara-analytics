# Niagara Analytics

Fault detection, analytics and alarm raising for Niagara 4 stations, delivered as a
signed Niagara module with HTML5 views. First site: Kitchener (61 Kitchener Ave, WA).

## Layout

| Path | What |
|---|---|
| `docs/plan.md` | The agreed plan and design decisions |
| `docs/haystack-tagging.md` | How points are tagged and why |
| `tools/` | Python tools that read a station backup (no running station needed) |
| `sites/<site>/` | Generated inventory, tags and trend-gap report per site |
| `module/` | The Niagara module (step 2, not started) |

## Regenerating a site's inventory

```
python3 tools/bog_inventory.py <backup.dist> sites/<site>
python3 tools/haystack_tags.py sites/<site>/points.csv sites/<site>
python3 tools/gap_report.py   sites/<site>/point_tags.csv sites/<site>/trend-gaps.md
```

Python 3.8+ standard library only. Station backups (`*.dist`, `*.bog`) hold
credentials and are git-ignored: never commit them.
