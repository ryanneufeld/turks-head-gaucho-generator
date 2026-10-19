"""Knot geometry shared by every output (solid jig now, templates next): where
each cord lane runs, how it is broken for over/under, where the pins and pass
numbers go. Pure Python, no Fusion calls (ADR 1).

Everything is in the unrolled plane: u = R*theta along the circumference,
z along the axis, cm. Lane points are ((u, z), depth below the surface). Pins
are (theta, z). The solid jig wraps these onto its mandrel (to_3d,
box_to_3d); a template lays them flat."""

from dataclasses import dataclass, field
from typing import Optional

from .geometry import (
    PIN_CLEARANCE, band_width, bight_rho, cord_code_of, extend_ends, fan_shifts,
    fill_depth, fill_offsets, fill_radius, grid_code, is_grid, knot_ok, knot_paths, lane_layout,
    lane_letter, lane_rho, mark_style, pass_number_spots, passes_of, pin_clear,
    pin_points, row_weave_of, knot_valid, max_ribbon_pct, strand_pitch)


@dataclass
class LaneGroup:  # pylint: disable=too-many-instance-attributes
    """One body's worth of cord lanes.

    pieces: polylines of ((u, z), depth).
    boxes: solid style only, per piece, the unrolled cut boxes that trim it
        where it passes under (see knot_paths boxes=True); cut to box_depth.
    r: tube radius that follows each polyline; depth: groove depth.
    name: body name; inlay: True when it is a separate colour body."""
    type: Optional[str]
    name: Optional[str]
    r: float
    depth: float
    pieces: list
    boxes: Optional[list] = None
    box_depth: Optional[float] = None
    inlay: bool = False


@dataclass
class KnotMarks:  # pylint: disable=too-many-instance-attributes
    """Knot geometry for one set of parameters.

    R, H, z0, L, B: mandrel radius, knot span, span start, leads, bights.
    style: 'solid' (cord-path tubes cut by boxes) or 'outline' (lane outlines).
    groups: [LaneGroup] (empty when lanes are not marked).
    colour: groups are separate colour bodies.
    pins: [(theta, z)] pin hole centres.
    numbers: (text height, [(text, u, z)]) or None when not wanted;
        an empty list means there was no room."""
    R: float
    H: float
    z0: float
    L: int
    B: int
    style: str
    groups: list = field(default_factory=list)
    colour: bool = True
    pins: list = field(default_factory=list)
    numbers: Optional[tuple] = None


def knot_dims(p):
    """(R, H, z0, L, B) for a parameter set."""
    R = p['dia'] / 2.0
    H = p['span']
    return R, H, (p['length'] - H) / 2.0, p['leads'], p['bights']


def ribbon_pct_for(p, dia=None):
    """Band width (all cord lanes) as % of strand pitch: the internal measure
    the pin/bight geometry is built on."""
    R = (dia or p['dia']) / 2.0
    if p['span'] <= 0 or not knot_valid(p['leads'], p['bights']):
        return 0.0
    return 100.0 * band_width(p) / strand_pitch(R, p['span'], p['leads'], p['bights'])


def min_diameter(p):
    """Smallest mandrel diameter (cm, 1 mm steps) where the cord lanes fit."""
    d = 0.5
    while d < 30:
        q = dict(p, dia=d)
        q['ribbon_pct'] = ribbon_pct_for(q)
        if q['ribbon_pct'] <= max_ribbon_pct(q, d / 2.0, q['span'], q['leads'], q['bights']):
            return d
        d += 0.1
    return None


def pin_spots(p, R, H, z0, L, B):
    """Pin hole centres (theta, z) for the chosen pin mode."""
    gaucho = is_grid(p)
    return pin_points(R, H, z0, L, B, 'none' if passes_of(p) >= 2 else p['hole_mode'],
                      p['bight_holes'], pin_clear(p, R, H, L, B), p['edge_rows'],
                      knot_ok(p),
                      bight=((list(fan_shifts(p, R, H, L, B).values()), lane_rho(p))
                             if gaucho else None))


def _solid_groups(p, R, H, z0, L, B, W, types, bands):
    r = fill_radius(p)
    depth = fill_depth(p)
    offsets, types = fill_offsets(p)
    gap = 2.5 * PIN_CLEARANCE
    fan = is_grid(p)
    multi = passes_of(p) >= 2
    shifts = fan_shifts(p, R, H, L, B) if fan else None
    rho_l = lane_rho(p) if fan else bight_rho(p, R, H, L, B)
    grid = (passes_of(p), grid_code(p)) if fan else None
    colour = p.get('colour_bodies', True)
    keys = sorted(set(types)) if (colour or multi) else [None]
    out = []
    for t in keys:
        idx = [i for i, x in enumerate(types) if t is None or x == t]
        r_t, depth_t = r, depth
        if multi and not colour and t != 'c0':
            # one-colour print: colour B is a narrow centre groove,
            # colour A the full-width recess, so they read apart
            idx, r_t = [idx[len(idx) // 2]], min(0.06, r)
            depth_t = r_t
            if fan:
                offsets = list(offsets)
                offsets[idx[0]] = 0.0
        res = knot_paths(R, H, z0, L, B, [offsets[i] for i in idx], rho_l, depth_t,
                         p['over_under'], band_h=W / 2.0, cord_code=cord_code_of(p),
                         weave=row_weave_of(p),
                         line_types=[types[i] for i in idx], bands=bands, fan=fan,
                         end_gap=gap, boxes=True, shift_of=shifts, grid=grid)
        name = ('Lane grooves' if t is None else 'Cord' if len(keys) == 1
                else 'Cord ' + lane_letter(t))
        if not colour:
            name = 'Lane grooves ' + lane_letter(t) if t else 'Lane grooves'
        out.append(LaneGroup(
            t, name, r_t, depth_t,
            [extend_ends(pts, 0.3 * r_t) for pts, _ in res],
            boxes=[bb for _, bb in res], box_depth=depth,
            inlay=colour and t is not None))
    return out


def _outline_groups(p, R, H, z0, L, B, W, offsets, types, bands):
    r = p['line_w'] / 2.0
    depth = p['line_d']
    rho = bight_rho(p, R, H, L, B)

    def paths_for(offs, tys):
        return knot_paths(R, H, z0, L, B, offs, rho, depth, p['over_under'],
                          band_h=W / 2.0, cord_code=cord_code_of(p), weave=row_weave_of(p),
                          line_types=tys, bands=bands, fan=is_grid(p),
                          end_gap=p['line_w'] + PIN_CLEARANCE, end_r=0.0)

    if not p.get('colour_bodies', True):
        return [LaneGroup(None, None, r, depth, paths_for(offsets, types))]
    keys = sorted(set(types))
    out = []
    for t in keys:
        idx = [i for i, x in enumerate(types) if x == t]
        name = ('Cord outline' if len(keys) == 1 else
                'Cord A outline' if t == 'b' else 'Cord B outline')
        out.append(LaneGroup(t, name, r, depth,
                             paths_for([offsets[i] for i in idx], [t] * len(idx)), inlay=True))
    return out


def knot_marks(p):
    """All knot geometry for parameter set p (see KnotMarks)."""
    R, H, z0, L, B = knot_dims(p)
    style = mark_style(p)
    groups = []
    if p['engrave']:
        W, offsets, types, bands = lane_layout(p)
        if style == 'solid':
            groups = _solid_groups(p, R, H, z0, L, B, W, types, bands)
        else:
            groups = _outline_groups(p, R, H, z0, L, B, W, offsets, types, bands)
    numbers = None
    if p.get('pass_numbers', True) and p['engrave']:
        numbers = pass_number_spots(p, R, H, L, B, z0)
    return KnotMarks(R=R, H=H, z0=z0, L=L, B=B, style=style, groups=groups,
                     colour=p.get('colour_bodies', True),
                     pins=pin_spots(p, R, H, z0, L, B), numbers=numbers)
