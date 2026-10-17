# 6. v2 does not edit v1 jigs

Date: 2026-10-16 · Status: accepted

## Decision
v2 is free to change stored jig parameters; it is not required to read or edit jigs saved by v1. `main` keeps v1 until v2 is printed and tied with, then v2 merges and is tagged `v2.0.0`.
