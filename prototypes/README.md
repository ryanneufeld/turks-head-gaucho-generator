# v2 test prints (issue #2), round 2

Round 4 bayonet: round 3 lined up and drew tight but was stiff at the end and the click was lost. Roof now reaches seat height 60% through the twist and stays level; seat play 0.05 → 0.1 mm; detent 0.12 → 0.25 mm. Checked: free to ~20°, click 22–27°, free seat 28–30°, stop ~30.5°.

Round 4 sheet (accepted): stem shortened to 1 mm; each slit end gets a papercraft relief cut (2.5 mm, 40° off the slit, angled back toward the sheet edge) so the corners flex open for the cap, then close behind it. Bayonet unchanged from round 3.

Round 2 changes: seam is **mushroom tabs and straight slits**: two tabs (3 mm stem, 9 mm half-round cap) on one end push down through straight slits (8.2 × 1.2 mm) set 6 mm back from the other end, which the tab end overlaps; the cap flexes 0.4 mm each side to pass and its shoulders catch; a pin through the overlap; V notches mark the seam; bayonet roof ramps snug as you twist, hard stop exactly at the seat (~0.1 mm slack), lighter detent; index marks (dot = insert, line = locked, plug groove meets the line).

Throwaway prints to check the v2 template/mandrel assumptions before building the generator.

| File | Print | Checks |
|---|---|---|
| `v2_test_sheet.stl` + `v2_test_lane.stl` | flat, 0.2 mm layers (2 layers = 0.4 mm), as one object: sheet in base colour, lane in a second colour | Does a 2-layer sheet wrap the 40 mm socket, do the underlapping tabs close and hold (a pin through the overlap hole locks the seam), does the lane colour read, do 3 mm pins hold through the sheet? |
| `v2_test_socket.stl` | upright, opening up | 40 mm tube for the wrap test (6 blind 3 mm pin holes at 20 mm height, matching the sheet), and the female bayonet |
| `v2_test_plug.stl` | upright, spigot up | Male bayonet: flip onto the socket, drop the 3 lugs into the slots, line its groove up with the dot, twist ~30° until it clicks and the groove meets the line |

Source: `v2_test_prints.scad` (`part = sheet | lane | socket | plug`).
