#!/usr/bin/env python3
"""Build a point inventory from a Niagara station backup (.dist) or config.bog.

Usage:
    python3 tools/bog_inventory.py <backup.dist|config.bog> <out_dir>

Writes:
    points.csv   one row per control point (Numeric/Boolean/Enum/String)
    summary.json counts per station / equipment

The parser only reads the XML. It never needs a running station.
"""
import csv
import io
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict

POINT_TYPES = {
    "c:NumericPoint": "Number", "c:NumericWritable": "Number",
    "c:BooleanPoint": "Bool", "c:BooleanWritable": "Bool",
    "c:EnumPoint": "Enum", "c:EnumWritable": "Enum",
    "c:StringPoint": "Str", "c:StringWritable": "Str",
}
HISTORY_EXTS = {
    "h:NumericIntervalHistoryExt": "interval",
    "h:NumericCovHistoryExt": "cov",
    "h:BooleanCovHistoryExt": "cov",
    "h:BooleanIntervalHistoryExt": "interval",
    "h:EnumCovHistoryExt": "cov",
    "h:EnumIntervalHistoryExt": "interval",
}


def load_bog_xml(path):
    """Return the config.bog XML bytes from a .dist, a zipped .bog or plain XML."""
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            names = z.namelist()
            bog = [n for n in names if n.endswith("/config.bog") and "/stations/" in n]
            if bog:  # a .dist backup: config.bog is itself a zip
                inner = z.read(bog[0])
                with zipfile.ZipFile(io.BytesIO(inner)) as zi:
                    return zi.read(zi.namelist()[0])
            return z.read(names[0])  # a zipped config.bog
    with open(path, "rb") as f:
        return f.read()


def slot(el, name):
    for c in el:
        if c.tag == "p" and c.get("n") == name:
            return c
    return None


def facets_dict(v):
    out = {}
    for part in (v or "").split("|"):
        if "=" in part:
            k, val = part.split("=", 1)
            out[k] = val.split(":", 1)[1] if ":" in val else val
    return out


def walk(el, path, rows, ctx):
    for c in el:
        if c.tag != "p":
            continue
        name, typ = c.get("n"), c.get("t")
        if typ == "nd:NiagaraStation":
            ctx = dict(ctx, station=name)
        if typ in POINT_TYPES:
            rows.append(point_row(c, path, name, typ, ctx))
            continue
        walk(c, path + [name] if name else path, rows, ctx)


def point_row(p, path, name, typ, ctx):
    fs = slot(p, "facets")
    facets = facets_dict(fs.get("v") if fs is not None else "")
    proxy = slot(p, "proxyExt")
    remote = ""
    if proxy is not None:
        pid = slot(proxy, "pointId")
        remote = pid.get("v", "") if pid is not None else ""
    hist_kind = hist_id = hist_interval = ""
    alarm_algos = []
    for c in p:
        t = c.get("t", "")
        if t in HISTORY_EXTS:
            en = slot(c, "enabled")
            if en is None or en.get("v") != "false":
                hist_kind = HISTORY_EXTS[t]
                hc = slot(c, "historyConfig")
                hid = slot(hc, "id") if hc is not None else None
                hist_id = hid.get("v", "") if hid is not None else ""
                iv = slot(c, "interval")
                hist_interval = iv.get("v", "") if iv is not None else ""
        elif t == "a:AlarmSourceExt":
            for a in c:
                at = a.get("t", "")
                if at.startswith("a:") and at.endswith("Algorithm"):
                    alarm_algos.append(at[2:].replace("Algorithm", ""))
    # Equipment = folder that directly holds the point; the folder path above
    # the station's "points" folder gives location (WA/KITCHENER/B1/RTP/MSSB1/HVAC).
    try:
        i = path.index("points")
        rel = path[i + 1:]
    except ValueError:
        rel = path
    equip = rel[-1] if rel else ""
    return {
        "station": ctx.get("station", "(local)"),
        "equip": equip,
        "folder": "/".join(rel),
        "point": name,
        "kind": POINT_TYPES[typ],
        "type": typ,
        "unit": facets.get("units", ""),
        "range": facets.get("range", "") or (
            f"{facets.get('trueText','')}/{facets.get('falseText','')}" if "trueText" in facets else ""),
        "history": hist_kind,
        "history_id": hist_id,
        "history_interval_ms": hist_interval,
        "alarm": "+".join(alarm_algos),
        "remote_ord": remote,
    }


def main(src, out_dir):
    root = ET.fromstring(load_bog_xml(src))
    rows = []
    walk(root, [], rows, {})
    fields = list(rows[0].keys()) if rows else []
    with open(f"{out_dir}/points.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    by_eq = defaultdict(Counter)
    for r in rows:
        k = f"{r['station']}|{r['equip']}"
        by_eq[k]["points"] += 1
        by_eq[k]["trended"] += bool(r["history"])
        by_eq[k]["alarmed"] += bool(r["alarm"])
    summary = {
        "points": len(rows),
        "trended": sum(bool(r["history"]) for r in rows),
        "alarmed": sum(bool(r["alarm"]) for r in rows),
        "by_station": Counter(r["station"] for r in rows),
        "equipment": {k: dict(v) for k, v in sorted(by_eq.items())},
    }
    with open(f"{out_dir}/summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    print(f"{len(rows)} points, {summary['trended']} trended, {summary['alarmed']} alarmed")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
