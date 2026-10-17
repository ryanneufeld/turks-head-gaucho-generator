# 1. Interchangeable templates alongside the solid jig

Date: 2026-10-16 · Status: accepted

## Context
v1 prints one solid jig per knot. A knot change means a new, large print.

## Decision
v2 adds a **template system**: a thin printed sheet carrying the knot, wrapped round a reusable mandrel. It has its own Fusion command and dialog. The solid jig stays. Both share one knot-geometry module (paths, over/under, pin positions, numbering).

## Consequences
- Knot geometry must be pulled out of the solid-jig builder first.
- Two products to maintain; the OpenSCAD port follows both, synced at milestones.
