# Plan

Agreed with MD on 2026-11-27.

## Requirements

- Goals: energy saving, early fault detection and comfort.
- Users: service technicians, building owners, and a product reusable across sites.
- Runs **inside Niagara** (N4.15, signed module). Builds happen on MD's PC, which has the
  Niagara developer kit and code-signing certificate.
- Data access and export: industry-standard protocols (Haystack tagging, MQTT, Haystack JSON/REST, oBIX).
- Alarms must be flexible: Niagara alarm console, email, SMS, the module's own console, and an
  externally hosted data server.
- UI: a small set of charts with selectable data sets plus an alarm/fault console. The
  look will be revisited later.

## Steps

1. **Map and tag the site.** Equipment and point inventory from the backup, Haystack tags,
   and a report of trends the fault rules need but the station doesn't log. *(done for Kitchener: see `sites/kitchener/`)*
2. **Niagara module: rule engine.** Java module for N4.15. Rules find equipment by tags, run
   on live values and histories, and raise faults as standard Niagara alarms with severity and
   estimated impact.
3. **External export.** Pluggable exporter (MQTT first, Haystack JSON/REST optional) for
   histories and faults, with buffering when the link drops.
4. **HTML5 views.** Site overview, chart page with selectable equipment and points, and a
   fault/alarm console with filtering, acknowledge and notes.
