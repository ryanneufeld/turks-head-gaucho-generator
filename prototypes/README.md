# v2 test prints (issue #2)

Throwaway prints to check the v2 template/mandrel assumptions before building the generator.

| File | Print | Checks |
|---|---|---|
| `v2_test_sheet.stl` + `v2_test_lane.stl` | flat, 0.2 mm layers (2 layers = 0.4 mm), as one object: sheet in base colour, lane in a second colour | Does a 2-layer sheet wrap the 40 mm socket, do the 3 puzzle tabs close and hold, does the lane colour read, do 3 mm pins hold through the sheet? |
| `v2_test_socket.stl` | upright, opening up | 40 mm tube for the wrap test (6 blind 3 mm pin holes at 20 mm height, matching the sheet), and the female bayonet |
| `v2_test_plug.stl` | upright, spigot up | Male bayonet: flip onto the socket, drop the 3 lugs into the slots, twist ~30° until it clicks |

Source: `v2_test_prints.scad` (`part = sheet | lane | socket | plug`).
