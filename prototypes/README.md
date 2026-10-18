# v2 test prints (issue #2), round 2

Round 2 changes: seam is **tab and slot**: three dovetail tabs on one end (1 layer thick) slide under the other end into dovetail slots in its bottom layer, roofed by the top layer, so they lock when wrapped; a pin through the overlap; V notches mark the seam; bayonet roof ramps snug as you twist, hard stop at the seat, lighter detent; index marks (dot = insert, line = locked, plug groove meets the line).

Throwaway prints to check the v2 template/mandrel assumptions before building the generator.

| File | Print | Checks |
|---|---|---|
| `v2_test_sheet.stl` + `v2_test_lane.stl` | flat, 0.2 mm layers (2 layers = 0.4 mm), as one object: sheet in base colour, lane in a second colour | Does a 2-layer sheet wrap the 40 mm socket, do the underlapping tabs close and hold (pin through the first hole locks the seam), does the lane colour read, do 3 mm pins hold through the sheet? |
| `v2_test_socket.stl` | upright, opening up | 40 mm tube for the wrap test (6 blind 3 mm pin holes at 20 mm height, matching the sheet), and the female bayonet |
| `v2_test_plug.stl` | upright, spigot up | Male bayonet: flip onto the socket, drop the 3 lugs into the slots, line its groove up with the dot, twist ~30° until it clicks and the groove meets the line |

Source: `v2_test_prints.scad` (`part = sheet | lane | socket | plug`).
