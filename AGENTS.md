# Turk's Head Gaucho Generator

Fusion 360 add-in (`Turks Head Gaucho Generator/`) and OpenSCAD port (`openscad/`) that build 3D-printable jigs for Turk's head, gaucho, herringbone and headhunter's knots. Active development is on the `v2` branch; `main` holds v1.

## Code layout

- `lib/turksHead/knot.py`: knot geometry shared by every output (lanes, over/under, pins, pass numbers, sizing), pure Python in the unrolled plane. Fusion-side code consumes it; do not recompute knot geometry elsewhere.
- `lib/turksHead/geometry.py`: lower-level pure geometry; `builder.py`/`dialog.py`: Fusion only.
- `tests/test_knot.py`: regression hashes of `knot_marks()`; run `python -m unittest discover tests`. Regenerate with `python tests/test_knot.py --update` only for intended geometry changes.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (via the `gh` CLI). See `docs/agents/issue-tracker.md`.

### Triage labels

Default labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `GLOSSARY.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.
