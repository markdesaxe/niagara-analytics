# Haystack tagging

The rule engine and charts never refer to point names like `SATmp` or `RmT_UnitSel`.
They ask for tags, for example `discharge air temp sensor` on an `ahu` equip. That is what
lets the same rules run on another site with a different naming convention: only the
tagging rules change.

Tags follow Project Haystack 4 (https://project-haystack.org). `tools/haystack_tags.py`
holds the rules:

- **Equipment rules** match the folder name (`AHU_3`, `VAV_3_2`, `CH_1`) and give the equip
  tags. VAV boxes get an `ahuRef` from their number (VAV_3_x is served by AHU_3), and AHUs
  get a `chilledWaterRef` to `CH_1`.
- **Point rules** match the point name within an equipment family. The first match wins.
  Points with a history extension also get `his`.

At step 2 the module applies these tags in the station (Niagara's Haystack tag dictionary
is already installed on the supervisor), so they can be edited in Workbench afterwards.

Things to check by hand on Kitchener:

- VAV `AHU` string slots exist on only 4 boxes, so `ahuRef` is inferred from the name. Worth
  confirming against the points list PDF.
- `OATmp` exists on all 12 AHUs but is trended on one; it is probably one shared outside air
  sensor. If so, one trend is enough and the rules should use it for every AHU.
