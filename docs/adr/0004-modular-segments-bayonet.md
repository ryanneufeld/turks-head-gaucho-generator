# 4. Modular mandrel segments joined by bayonets; no threads

Date: 2026-10-16 · Status: accepted

## Context
Longer knots need longer mandrels; threads have proved troublesome to print.

## Decision
- Printed mandrel = identical **segments** (100 mm default, settable) with a male bayonet at one end and female at the other, plus an **end cap** and a **foot**. No handle.
- Bayonet: **3 lugs**, L-slots, ~30° twist; the slot roof ramps down so the joint draws snug as it turns, a hard stop at the seat, and a light detent that only the lug's trailing ridge meets (round 1 was stiff to turn and loose once past the detent, #2). Prints upright with no overhang beyond 45°.
- **Alignment marks**: an insert dot and a locked line on each female end, a groove on each male end, so segments (and the hole grid) stay in time.
- Segment length is a whole number of hole rows and the bayonet locks at one angle only, so the hole grid (including stagger) continues across joints.
- The pin-storage core runs through all segments and is closed by the end cap.
- The solid jig's screw lid also switches to this bayonet; the thread code is removed.
