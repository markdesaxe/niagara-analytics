#!/usr/bin/env python3
"""Propose Project Haystack 4 tags for every point in a points.csv inventory.

Usage:
    python3 tools/haystack_tags.py <points.csv> <out_dir>

Writes:
    equipment.csv   one row per piece of equipment, with tags and refs
    point_tags.csv  points.csv plus equipRef, Haystack tags and a match flag
    untagged.csv    points no rule matched (to review by hand)

Rules are matched in order on the point name; the first match wins.
Equipment-family rules run first so that, for example, "FnSts" on an AHU and
on an exhaust fan both become "fan run sensor" without separate rules.
The rules are written for this contractor's naming convention (AHU_n, VAV_n_m,
CH_1, AC_n, EF_n) and are meant to be extended per site, not rewritten.
"""
import csv
import re
import sys

# ---------------------------------------------------------------- equipment
EQUIP_RULES = [
    (r"^AHU_(\d+)$", "ahu", "ahu equip"),
    (r"^VAV_(\d+)_(\d+)$", "vav", "vav airTerminalUnit equip"),
    (r"^AC_[\d_]+$", "ac", "ac packagedUnit equip"),
    (r"^EF_\d+$", "ef", "exhaust fan motor equip"),
    (r"^CH_1$", "chiller", "chiller chilled water plant equip"),
    (r"^CH_1_HLI$", "chillerHli", "chiller equip"),
    (r"^Stage_\d+$", "chStage", "chilled water plant equip"),
    (r"^(CH|CHWP)_LeadLag$", "leadLag", "chilled water plant equip"),
    (r"^B1$", "building", "site equip"),
    (r"^Vaverages$", "zoneAvg", "equip"),
]

# ---------------------------------------------------------------- points
# (equip families or None for any, regex on point name, tags)
POINT_RULES = [
    # common fan / run points
    (None, r"^FnCmd$", "discharge fan run cmd"),
    (None, r"^FnSts$", "discharge fan run sensor"),
    (None, r"^(FnSts|FnOverrun|CO2|SATmp|RATmp|OATmp|CntrlTmp)_Flt$", "fault alarm sensor"),
    (None, r"^SchedSel$", "schedule sp enum"),
    (None, r"^(AHrsCmd|BdgSchedCmd|LocalSchedCmd|HolidayCmd)$", "occupied schedule cmd"),
    (None, r"^AHrsPb$", "occupied override cmd"),
    (None, r"^(AHrsRuntime|Total_OperatingTime|OptStart_Runtime|OptStop_Runtime)$", "run duration sensor"),
    (None, r"^NoStarts$", "run count sensor"),
    (None, r"^Fire$|^Building_Fire$", "fire alarm sensor"),
    # AHU
    (["ahu"], r"^SATmp$", "discharge air temp sensor"),
    (["ahu"], r"^SATmpSP$", "discharge air temp sp effective"),
    (["ahu"], r"^SATmpSP_(High|Low)$", "discharge air temp sp limit"),
    (["ahu"], r"^RATmp$", "return air temp sensor"),
    (["ahu"], r"^RATmpSP$", "return air temp sp"),
    (["ahu"], r"^Ctrl_Tmp$", "air temp sensor control"),
    (["ahu"], r"^OATmp$", "outside air temp sensor"),
    (["ahu"], r"^OAHum$", "outside air humidity sensor"),
    (["ahu"], r"^OAEnth$", "outside air enthalpy sensor"),
    (["ahu"], r"^EnthalpySP$", "outside air enthalpy sp economizing"),
    (["ahu"], r"^EcondT$", "economizing temp sp"),
    (["ahu"], r"^ZnCO2$", "zone air co2 sensor"),
    (["ahu"], r"^ZnCO2_(High|Low)$", "zone air co2 sp limit"),
    (["ahu"], r"^SADp$", "discharge duct air pressure sensor"),
    (["ahu"], r"^SADpSP$", "discharge duct air pressure sp effective"),
    (["ahu"], r"^SADpSP_(High|Low)$", "discharge duct air pressure sp limit"),
    (["ahu"], r"^SAFSpd$", "discharge fan speed cmd"),
    (["ahu"], r"^RAFnSpd(Hi|Low)$", "return fan speed sp"),
    (["ahu"], r"^Chwv$", "chilled water valve cmd"),
    (["ahu"], r"^Econ$", "outside air damper cmd economizing"),
    (["ahu"], r"^CoolDmd$", "cool demand sensor"),
    (["ahu"], r"^HeatDmd$", "heat demand sensor"),
    (["ahu"], r"^AirflowDmd$|^Demand$", "air flow demand sensor"),
    (["ahu"], r"^EDHStg(\d)Call$", "elec heat stage cmd"),
    (["ahu"], r"^HeatStg\dO(n|ff)$", "heat stage sp"),
    (["ahu"], r"^(Cool|Heat)(Db|Range)$", "temp sp deadband"),
    (["ahu"], r"^(Cool|Heat|Fan)[PI]$", "pid sp tuning"),
    (["ahu"], r"^OptSt(art|op)Cmd$", "optimal start cmd"),
    (["ahu"], r"^VAV_(CoolDmd|HeatDmd|AirflowDmd|CtrlTmp)$", "vav aggregate sensor"),
    (["ahu"], r"^VAV_QtyEnabled$", "vav enable count sensor"),
    (["ahu"], r"^(Allow_|Has_|DDC_Allow|TmpCntrl|SAFSpd_Cntrl|SADp_Cntrl|ManualMode|VAV_CAV|AhuDemand_Allowed|Avg_HiAvgSel)", "enable config sp"),
    (["ahu"], r"^(VAV_?[Mm]ode\d?|VAV_SystemMode|VAV_AOMSelect)$", "mode sp enum"),
    (["ahu"], r"^(FltReset|Reset)$", "fault reset cmd"),
    (["ahu"], r"^(Qty_EDH|OATmpVAVEDHLimit)$", "elec heat config sp"),
    # VAV
    (["vav"], r"^(RmT_UnitSel|Zone_Temp)$", "zone air temp sensor"),
    (["vav"], r"^(SpRmT_UnitSel|ZoneTemp_SP)$", "zone air temp sp effective"),
    (["vav"], r"^SpRmT[HL]L_C$", "zone air temp sp limit"),
    (["vav"], r"^AbsAirFlow_UnitSel$", "discharge air flow sensor"),
    (["vav"], r"^SpAbsAirFlow_UnitSel$", "discharge air flow sp effective"),
    (["vav"], r"^V(maxC|maxH|min|nom)_UnitSel$", "discharge air flow sp limit"),
    (["vav"], r"^(Damper_Pos|RelPosDmp)$", "damper sensor"),
    (["vav"], r"^DamperDemand$", "damper cmd"),
    (["vav"], r"^CoolingDemand$", "cool demand sensor"),
    (["vav"], r"^HeatingDemand$", "heat demand sensor"),
    (["vav"], r"^Heater\dState$", "elec reheat run sensor"),
    (["vav"], r"^DeltaP_Pa$", "air pressure sensor velocity"),
    (["vav"], r"^FanState$", "fan run sensor"),
    (["vav"], r"^(Deadband|DeadbandTemp|EcoMode(Cool|Heat)SpShift)$", "zone air temp sp deadband"),
    (["vav"], r"^Status(Actuator|Pressure|System)$", "status sensor enum"),
    (["vav"], r"^(SystemMode|ReheatEn|UnitSelAirFlow|Override)$", "mode sp enum"),
    (["vav"], r"^OverrideValue$", "override sp"),
    (["vav"], r"^(Enabled|Global_Heating_Disabled|DamperDemand_Allowed|TempDemand_Allowed|Allow_\w+)$", "enable config sp"),
    (["vav"], r"^Operation_Alarm$", "fault alarm sensor"),
    (["vav"], r"^(AHU|Area|Name)$", "config str"),
    # AC
    (["ac"], r"^ZnTmp$", "zone air temp sensor"),
    (["ac"], r"^ZnTmpSP$", "zone air temp sp effective"),
    (["ac"], r"^Comp\dCmd$", "cool stage compressor cmd"),
    (["ac"], r"^HeatCmd$", "heat cmd"),
    (["ac"], r"^VentCoolCmd$", "economizing cmd"),
    (["ac"], r"^(Cool|Heat)Dmd$", "demand sensor"),
    (["ac"], r"^AC[\d_]+STS$", "run sensor"),
    (["ac"], r"^AH_Duration$", "occupied override duration sp"),
    (["ac"], r"^(Location|Name)$", "config str"),
    # Chiller plant (CH_1)
    (["chiller"], r"^CH1_COMP\d$", "compressor run sensor"),
    (["chiller"], r"^CH1_COMP\d_NoStarts$", "compressor run count sensor"),
    (["chiller"], r"^CH1_COMP\d_Total_OperatingTime$|^CHWP\d_Total_OperatingTime$", "run duration sensor"),
    (["chiller"], r"^CH1_STS$", "chiller run sensor"),
    (["chiller"], r"^(CH1_FLT|Chiller1_Fault|Ch_OperationAlarm|CHWP\d_Flt)$", "fault alarm sensor"),
    (["chiller"], r"^CH1_Dp$", "chilled water diff pressure sensor"),
    (["chiller"], r"^ChwDpSp$", "chilled water diff pressure sp"),
    (["chiller"], r"^CHWP\dSPD$", "chilled water pump speed cmd"),
    (["chiller"], r"^CHWP\d_CMD$", "chilled water pump run cmd"),
    (["chiller"], r"^CHWP\d_STS$", "chilled water pump run sensor"),
    (["chiller"], r"^CHWP\d_NoStarts$", "pump run count sensor"),
    (["chiller"], r"^CH_Stage_\d$", "chiller stage cmd"),
    (["chiller"], r"^Bypass$", "chilled water bypass valve cmd"),
    (["chiller"], r"^AHU_Demand$", "chilled water demand sensor"),
    (["chiller"], r"^HMI_PumpReset$", "fault reset cmd"),
    # Chiller high-level interface (BACnet from the chiller controller)
    (["chillerHli"], r"^ENTERING\$20CHILLED\$20LIQ\$20TEMP$", "entering chilled water temp sensor"),
    (["chillerHli"], r"^LEAVING\$20CHILLED\$20LIQ\$20TEMP$", "leaving chilled water temp sensor"),
    (["chillerHli"], r"^REMOTE\$20COOLING\$20SETP$", "leaving chilled water temp sp"),
    (["chillerHli"], r"^ChwSp(High|Low)$", "leaving chilled water temp sp limit"),
    (["chillerHli"], r"^CHILLER\$20RUN$", "chiller run cmd"),
    (["chillerHli"], r"^READY\$20TO\$20START$", "chiller enable sensor"),
    (["chillerHli"], r"^FLOW\$20SWITCH\$20STATUS$", "chilled water flow sensor"),
    (["chillerHli"], r"^REM\$20CURRENT\$20LIMIT\$20SETP$|^ChDmdLmt_(Hi|Low)$", "chiller demand limit sp"),
    (["chillerHli"], r"^SYS\$20\d\$20COMP\$20RUN\$20STATUS$", "compressor run sensor"),
    (["chillerHli"], r"^SYS\$20\d\$20COMP\$20PCT\$20FLA$", "compressor current sensor"),
    (["chillerHli"], r"^SYS\$20\d\$20(COND|DISCH)\$20TEMP$", "refrig temp sensor"),
    (["chillerHli"], r"^SYS\$20\d\$20(DISCH|SUCT|OIL)\$20PRESS$", "refrig pressure sensor"),
    (["chillerHli"], r"^SYS\$20\d\$20(ALARM|LOCKOUT)$", "fault alarm sensor"),
    (["chillerHli"], r"^SYS\$20\d\$20(FAULT|WARNING|OPERATIONAL)\$20CODE$|^SYS\$20\d\$20SYSTEM\$20STATE$", "status sensor enum"),
    (["chillerHli"], r"^SYS\$20\d\$20HOURS$", "run duration sensor"),
    (["chillerHli"], r"^SYS\$20\d\$20STARTS$", "run count sensor"),
    (["chillerHli"], r"^(ROC_(Up|Down)|DmdTmp_(Hi|Low)|Demand_Trigger|Trigger_Delay)$", "chiller config sp"),
    # Plant staging
    (["chStage"], r"^Ambient$", "outside air temp sensor"),
    (["chStage"], r"^(AmbientHi|Stage\d_Demand(Hi|Lo)|Stage_TimeDelay|Min_No_Units)$", "chiller stage sp"),
    (["chStage"], r"^(Stage_\d|Stage\d_Dmd)$", "chiller stage cmd"),
    (["chStage"], r"^(Ch_Demand)$", "chilled water demand sensor"),
    (["chStage"], r"^(No_Units_Running|Stage_TimeRemaining)$", "chiller stage sensor"),
    (["chStage"], r"^(Allow_Chw_Plant|ChwPlant_Allowed|Ambient_Enable|NumberUnitsRunningDmd|Bypass_Timer)$", "enable config sp"),
    (["chStage"], r"^Fault$", "fault alarm sensor"),
    (["leadLag"], r".*", "leadLag sp"),
    (["building"], r"^(Average_ChwDemand|HighestChwv|HighestChwDemand)$", "chilled water demand sensor"),
    (["building"], r"^Total_AHUs_Enabled$", "ahu enable count sensor"),
    (["building"], r".*Override.*", "override sp"),
    (["zoneAvg"], r"^VAV_\d+_Avg$", "zone air temp sensor avg"),
]

POINT_RULES_C = [(set(f) if f else None, re.compile(rx), tags) for f, rx, tags in POINT_RULES]
EQUIP_RULES_C = [(re.compile(rx), fam, tags) for rx, fam, tags in EQUIP_RULES]

UNIT_MAP = {"celsius": "°C", "percent": "%", "pascal": "Pa", "kilopascal": "kPa",
            "liters per second": "L/s", "hour": "h", "minute": "min", "bar": "bar",
            "parts per million": "ppm", "kilojoule per kilogram": "kJ/kg"}


def classify_equip(name):
    for rx, fam, tags in EQUIP_RULES_C:
        if rx.match(name):
            return fam, tags
    return "", ""


def main(points_csv, out_dir):
    rows = list(csv.DictReader(open(points_csv)))
    equips = {}
    out, untagged = [], []
    for r in rows:
        fam, etags = classify_equip(r["equip"])
        eq_id = f"{r['station']}:{r['equip']}"
        if fam and eq_id not in equips:
            refs = {}
            m = re.match(r"^VAV_(\d+)_\d+$", r["equip"])
            if m:
                refs["ahuRef"] = f"AHU_{m.group(1)}"
            if fam == "ahu":
                refs["chilledWaterRef"] = "CH_1"
            loc = r["folder"].split("/")
            equips[eq_id] = {
                "id": eq_id, "station": r["station"], "equip": r["equip"], "family": fam,
                "tags": etags, "switchboard": next((x for x in loc if x.startswith("MSSB")), ""),
                **refs,
            }
        tags = ""
        for fams, rx, t in POINT_RULES_C:
            if (fams is None or fam in fams) and rx.match(r["point"]):
                tags = t
                break
        kind_tag = {"Number": "Number", "Bool": "Bool", "Enum": "Str", "Str": "Str"}[r["kind"]]
        unit = UNIT_MAP.get(r["unit"].split(";")[0], "") if r["unit"] else ""
        row = dict(r, equipRef=eq_id if fam else "", haystack=("point his " if r["history"] else "point ") + tags if tags else "",
                   hsKind=kind_tag, hsUnit=unit, matched="yes" if tags else "no")
        out.append(row)
        if not tags and fam:
            untagged.append(row)
    fields = list(out[0].keys())
    for name, data in (("point_tags.csv", out), ("untagged.csv", untagged)):
        with open(f"{out_dir}/{name}", "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fields)
            w.writeheader()
            w.writerows(data)
    ef = ["id", "station", "equip", "family", "tags", "switchboard", "ahuRef", "chilledWaterRef"]
    with open(f"{out_dir}/equipment.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ef, restval="")
        w.writeheader()
        w.writerows(sorted(equips.values(), key=lambda e: (e["family"], e["equip"])))
    tagged = sum(1 for r in out if r["matched"] == "yes")
    print(f"{len(equips)} equipment, {tagged}/{len(out)} points tagged, {len(untagged)} equipment points untagged")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
