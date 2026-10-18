# 5. Long templates split into overlapping panels

Date: 2026-10-16 · Status: accepted

## Decision
A template longer than the print bed is split along its length into panels whose ends **overlap** by a band of a few hole rows (~10 mm). Both panels carry the same lanes and pin holes in the band; pins through both layers register them. Matching **alignment marks** on both panels (and on the mandrel segment ends) keep the extensions in time.

## Later
Repeatable start/middle/end sections (one print set for any length) only work where the pattern repeats along the knot; revisit separately.
