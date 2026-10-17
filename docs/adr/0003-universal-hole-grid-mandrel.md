# 3. Universal hole grid on printed mandrels

Date: 2026-10-16 · Status: accepted

## Context
Bight pins sit at different places for every knot; interchangeable templates need a mandrel that serves many knots.

## Decision
- Pins (3 mm, settable) pass through the sheet into **holes in the mandrel**.
- Printed mandrels carry **rows of holes the full length**, ~5 mm apart, alternate rows staggered half a hole.
- Each mandrel diameter gets the **largest highly-divisible hole count** that fits (hole pitch ≈ pin + 1.5 mm wall): e.g. ~27 at 40 mm, ~41 at 60 mm dia. The template dialog only offers knots whose pins land on holes (single colour: count divisible by 2 × bights, or bights when leads are even; multi-colour grid knots: 2 × bights × colours).
- Template length snaps so top and bottom pin rows land on rows.
- Holes are **blind** (~10 mm); the pin-storage core sits inside them.
- **Bought stock** (pipe, dowel): no grid. Wrap the template and drill through its pin holes, one mandrel per knot.

## Rejected
Sliding/rotating hole collars (locking mechanism); soft cork/foam sleeve (extra material).
