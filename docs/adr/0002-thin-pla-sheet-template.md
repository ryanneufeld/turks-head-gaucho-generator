# 2. Template is a 2-layer PLA sheet

Date: 2026-10-16 · Status: accepted

## Decision
- Printed flat in PLA, **2 layers** by default (count and layer height settable). One or two layers bend round a mandrel without TPU.
- Knot laid out on the sheet's **outer** surface (knot diameter = mandrel diameter + 2 × sheet thickness).
- Each cord lane is its own colour through the full thickness on a base colour; "under" is a base-colour gap where a lane stops short of the lane crossing it. One body per colour (Bambu export unchanged).
- Pass numbers and start labels as coloured text above/below the knot.
- Seam closes with **mushroom tabs and straight slits**: tabs on one end push through slits set back from the other end, which the tab end overlaps; each slit end has a diagonal relief cut angled back toward the edge so the corners flex open for the cap; the cap's flat shoulders catch under the slit ends; a pin through the overlap locks it (puzzle tabs failed the test print, #2). V notches mark where the ends meet; one **fold-over tab per colour** at the top edge holds the cord ends.
- Fusion output: flat print bodies plus a hidden wrapped preview.

## Rejected
TPU sheet (slower, awkward multi-colour); slatted "roll-top" sheet; paper printout; rigid snap-on shells.
