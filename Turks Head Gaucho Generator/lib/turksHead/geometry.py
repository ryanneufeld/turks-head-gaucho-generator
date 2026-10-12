"""Pure geometry for the Turk's head jig (no Fusion calls). Units: cm."""

import math

PIN_HOLE_DIA = '3 mm'       # hole diameter: pin shank + ~0.2 mm for printing
PIN_HOLE_DEPTH = '10 mm'    # radial depth into the mandrel
PIN_CLEARANCE = 0.02        # cm (0.2 mm) gap between pin hole edge and strand edge

CLEAT_TOP_RATIO = 1.6     # jam-cleat slot mouth width / cord diameter
CLEAT_BOTTOM_RATIO = 0.5  # jam-cleat slot floor width / cord diameter
CLEAT_FLOOR_GAP = 0.9525  # cleat slot floor sits 3/8 in above the top of the engraving
CLEAT_RIDGE_PITCH = 0.7   # barb spacing along each slot wall / cord diameter
CLEAT_RIDGE_HEIGHT = 0.15 # barb height / cord diameter
NUMBER_HEIGHT = 0.5      # cm, pass-number text height (shrinks to fit)
NUMBER_DEPTH = 0.08      # cm, pass-number inlay depth
MIN_PIECE = 0.2          # solid fill pieces shorter than this (cm) are dropped
LEADIN_DEPTH_RATIO = 0.35 # cleat lead-in channel depth / cord diameter

# Screw-on lid with cord clamp notches (cm unless noted)
TOP_MODES = (
    ('lid', 'Screw-on lid, cord clamp notches'),
    ('cleat', 'Jam cleat'),
    ('none', 'Plain end'),
)
LID_GAP = 0.8             # split line sits this far above the top of the engraving
LID_CAP = 0.4             # lid top thickness above the thread
LID_MIN_WALL = 0.25       # lid wall outside the thread
CLAMP_SQUEEZE = 0.3       # notch depth = cord diameter x (1 - this): lid squeezes the cord
CAVITY_WALL = 0.2         # wall left around the pin storage cavity
STORAGE_FLOOR = 0.3       # solid floor left under the pin storage cavity
THREAD_PITCH_PREF = 0.2   # preferred thread pitch (2 mm)
ISO_SIZES_MM = (12, 14, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 42, 45, 48, 52, 56, 60, 64)
END_MARGIN = 2.54  # knot span = mandrel length minus this (1 in), centred

# ---------------------------------------------------------------- geometry (pure)

def knot_valid(leads, bights):
    return leads >= 2 and bights >= 2 and math.gcd(leads, bights) == 1


def bight_points(R, H, z0, L, B):
    """(theta, z) of bight vertices: bottom row then top row."""
    pts = [(2 * i * math.pi / B, z0) for i in range(B)]
    pts += [((2 * i + L) * math.pi / B, z0 + H) for i in range(B)]
    return pts


def crossing_points(R, H, z0, L, B):
    """(theta, z) of all crossings, rows k = 1..L-1."""
    return [((2 * i + k) * math.pi / B, z0 + k * H / L)
            for k in range(1, L) for i in range(B)]


WEAVES = (
    ('OU', 'Over 1 / under 1 (standard Turk\'s head)'),
    ('OOUU', 'Over 2 / under 2 (gaucho)'),
    ('OOOUUU', 'Over 3 / under 3'),
    ('custom', 'Custom pattern'),
)


def up_over(row, weave):
    """Is the ASCENDING strand over at crossing row `row` (1..L-1)?
    `weave` is an O/U string read upward from row 1 and repeated;
    the descending strand at the same crossing gets the opposite."""
    return weave[(row - 1) % len(weave)] == 'O'


def weave_valid(weave):
    return bool(weave) and set(weave) <= {'O', 'U'}


def crossing_state(up, s, L, weave='OU'):
    """Nearest crossing to parameter s on a half-pass.
    Returns (is_over, distance_in_intervals) or None at bight rows."""
    k = round(s * L)
    if k < 1 or k > L - 1:
        return None
    row = k if up else L - k
    f = up_over(row, weave)
    over = f if up else not f
    return over, abs(s * L - k)


def gap_points(R, H, z0, L, B):
    """(theta, z) of diamond-opening centres between strands, rows k = 1..L-1.
    Same heights as crossings, offset half a bight spacing around."""
    return [((2 * i + k + 1) * math.pi / B, z0 + k * H / L)
            for k in range(1, L) for i in range(B)]


def path_length(R, H, L, B):
    half = math.hypot(R * L * math.pi / B, H)
    return 2 * B * half


def strand_pitch(R, H, L, B):
    """Perpendicular spacing between neighbouring parallel strands (surface)."""
    su = R * L * math.pi / B
    return (2 * math.pi * R / B) * H / math.hypot(su, H)



def cord_visits(L, B):
    """Crossing visits in the order the cord meets them.
    Returns {crossing: (n1, n2)}: the two along-cord indices of each crossing.
    Half-pass j (up when even) meets traversal crossings k = 1..L-1; crossing
    identity is (row, position round the jig in units of su/L)."""
    seen = {}
    n = 0
    for j in range(2 * B):
        up = j % 2 == 0
        for k in range(1, L):
            row = k if up else L - k
            seen.setdefault((row, (j * L + k) % (2 * B)), []).append(n)
            n += 1
    return seen


def code_consistent(L, B, code, phase=0):
    """An over/under code read ALONG the cord (repeating) gives exactly one
    over and one under at every crossing for this L x B."""
    if not knot_valid(L, B) or not weave_valid(code):
        return False
    P = len(code)
    for a, b in cord_visits(L, B).values():
        if code[(a + phase) % P] == code[(b + phase) % P]:
            return False
    return True


def consistent_leads(B, code, lo=2, hi=30):
    return [l for l in range(lo, hi + 1) if code_consistent(l, B, code)]


def pass_over(t_self, up_self, t_other, row, weaves):
    """Is pass type t_self ('b' base / 'g' gaucho), travelling up or down, over
    a pass of type t_other at crossing row `row`?
    Same-type crossings follow that type's weave. A base/gaucho crossing
    follows the gaucho weave, seen from the gaucho pass."""
    if t_self == t_other or t_self == 'g':
        f = up_over(row, weaves[t_self])
        return f if up_self else not f
    f = up_over(row, weaves['g'])          # other is the gaucho pass
    other_over = f if not up_self else not f
    return not other_over


def fan_lane_over(t_self, t_other, x_over, j):
    """Gaucho interweave, lanes on fixed sides (shift_of): is lane t_self
    of half-pass j over lane t_other of the strand it crosses? x_over = base
    strand j over the other (along-cord code). Matches every pass of the
    Paracord Guild 7L6B gaucho run list."""
    odd = j % 2 == 1
    if t_self == t_other:
        return x_over if t_self == 'b' else not x_over
    if t_self == 'g':          # B over A
        return x_over != odd
    return x_over == odd       # A over B


def knot_paths(R, H, z0, L, B, offsets, rho, depth, over_under,
               band_h=0.0, step=0.5, weave='OU', split_units=False,
               line_types=None, bands=None, weaves=None, cord_code=None, fan=False,
               end_gap=0.0, end_r=0.0, boxes=False, shift_of=None, grid=None):
    """Groove centrelines for the knot, as lists of ((u, z), depth).

    Works in the unrolled plane (u = R*theta, z). The cord centreline runs
    straight between bights and wraps each bight around a circle of radius
    `rho` centred on the end-bight pin, as a real cord does. Each entry of
    `offsets` is a line parallel to the centreline (0 = centreline, +/-w/2 =
    ribbon edges).

    Over/under: lines of the UNDER strand are broken where they pass inside
    the over strand's band (|dist to its centreline| < band_h), giving
    separate pieces. Straights are sampled every `step`.

    `weave` sets which strand is over at each crossing (see up_over).

    Parallel ribbons: `bands` lists the sub-ribbons of every strand as
    (pass_type, centre_offset, half_width); `line_types` gives the pass type of
    each entry in `offsets`; `weaves` maps pass type -> O/U string. A line is
    broken across every sub-ribbon it passes under (see pass_over).

    cord_code: O/U string applied ALONG the cord (crossing visit n gets
    cord_code[n % len]); e.g. 'OOUU' = over 2 / under 2 gaucho. When given,
    lines are broken across the whole band (half-width band_h) wherever the
    strand is under; check code_consistent() first.

    With cord_code AND bands (two cord lanes per strand, types 'b' = colour A,
    'g' = colour B): whether this strand X is over strand Y comes from
    cord_code; a lane of X is broken across each lane of Y it passes under.
    fan=False (doubled knot): every lane follows the strand.
    fan=True (gaucho fan): same, except B-against-B is reversed, which makes
    every B pass split the pairs it crosses.

    end_gap: broken lines stop this far short of the crossing lane's edge
    (perpendicular distance), so a groove end never touches the outline of
    the lane passing over it.
    end_r: radius of the tube that will follow the line; its flat end cap's
    corners reach end_r*|cos| further toward the crossing lane, so the cut is
    widened by that much.
    boxes=True (solid fills): lines are NOT broken; instead returns
    (points, cut_boxes) per piece, where each cut box is (Q, do, half_w,
    half_len) in the unrolled plane: a strip along the over lane's direction
    `do`, centred at Q, covering the over lane plus end_gap each side, long
    enough to span this line's lane. Cutting the finished tubes with these
    boxes gives straight, clean ends.
    shift_of (gaucho, {lane type: u shift}): each lane is the strand path
    moved sideways round the jig, so a lane stays on the same side of its
    partner the whole way and the two lanes' bights interlock, crossing once
    at every bight (as in the Paracord Guild 7L6B gaucho run list). Offsets
    are then relative to the lane's own centreline, rho is one lane's wrap
    radius, and band centres in `bands` are ignored. Over/under follows
    fan_lane_over; the bight crossing puts B under A at the bottom and over
    A at the top (boxes mode only).
    grid=(N, code): gaucho as a Turk's head of N*L x N*B: N lanes (types in
    shift_of), crossings every 1/(N*L) of a half-pass, over/under by row from
    `code` (Grid Maker row coding). Lanes are all band_h... width from bands.
    split_units=True: also split at every bight apex so each piece belongs to
    one half-pass, keep every piece (so offsets line up piece-for-piece) and
    return (half_pass_index, points) tuples.
    """
    su = R * L * math.pi / B
    n = 2 * B
    V = [(j * su, z0 if j % 2 == 0 else z0 + H) for j in range(n + 3)]
    Vs = list(V)            # the current line's (possibly shifted) strand path
    d_pin = rho / math.sin(math.atan2(su, H))

    def set_shift(t):
        du = shift_of.get(t, 0.0) if shift_of else 0.0
        Vs[:] = [(x + du, z) for x, z in V]

    def seg_dir(j):
        dz = H if j % 2 == 0 else -H
        m = math.hypot(su, dz)
        return (su / m, dz / m)

    def nrm(d):
        return (-d[1], d[0])

    def add(a, b, k=1.0):
        return (a[0] + k * b[0], a[1] + k * b[1])

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1]

    def pin(j):
        return (Vs[j][0], Vs[j][1] + (d_pin if j % 2 == 0 else -d_pin))

    def foot(P, j, off):
        nn = nrm(seg_dir(j))
        A = add(Vs[j], nn, off)
        return add(P, nn, -dot((P[0] - A[0], P[1] - A[1]), nn))

    if bands is None:
        bands_ = [('b', 0.0, band_h)]
        weaves_ = {'b': weave}
    else:
        bands_, weaves_ = bands, weaves
    types_ = line_types or ['b'] * len(offsets)
    ltype = ['b']

    def unders(j):
        """(C, do, f_lo, f_hi) windows where the current line is under.
        f = (P - C) x do is minus the other strand's offset coordinate."""
        up = (j % 2 == 0)
        d = seg_dir(j)
        out = []
        if grid:
            nn_, gcode = grid
            Lg = L * nn_
            hw_o = bands_[0][2]
            for k in range(1, Lg):
                row = k if up else Lg - k
                C = add(Vs[j], (Vs[j + 1][0] - Vs[j][0], Vs[j + 1][1] - Vs[j][1]), k / Lg)
                ov = up_over(row, gcode)
                if not (ov if up else not ov):
                    out.append((C, (d[0], -d[1]), -hw_o, hw_o))
            return out
        for k in range(1, L):
            row = k if up else L - k
            C = add(V[j], (V[j + 1][0] - V[j][0], V[j + 1][1] - V[j][1]), k / L)
            if cord_code:
                n_ = (j % n) * (L - 1) + (k - 1)
                x_over = cord_code[n_ % len(cord_code)] == 'O'
                if bands is None:
                    if not x_over:
                        out.append((C, (d[0], -d[1]), -band_h, band_h))
                    continue
                do = (d[0], -d[1])
                for t_other, co, hw in bands:
                    if shift_of:
                        lane_over = fan_lane_over(ltype[0], t_other, x_over, j)
                        fc = shift_of.get(t_other, 0.0) * do[1]
                    else:
                        flip = fan and ltype[0] == 'g' and t_other == 'g'
                        lane_over = (not x_over) if flip else x_over
                        fc = -co
                    if not lane_over:
                        out.append((C, do, fc - hw, fc + hw))
                continue
            for t_other, co, hw in bands_:
                if not pass_over(ltype[0], up, t_other, row, weaves_):
                    out.append((C, (d[0], -d[1]), -co - hw, -co + hw))
        return out

    pieces = []
    cur = []
    tag = [0]

    def flush():
        nonlocal cur
        if split_units:
            if len(cur) >= 2:
                pieces.append((tag[0], cur))
            cur = []
            return
        if len(cur) >= 3:
            ln = sum(math.hypot(cur[i + 1][0][0] - cur[i][0][0], cur[i + 1][0][1] - cur[i][0][1])
                     for i in range(len(cur) - 1))
            if ln > 0.15:
                pieces.append(cur)
        cur = []

    def sample(a, b, t0, t1, ln, un):
        k = max(1, int(math.ceil((t1 - t0) / step)))
        for i in range(k + 1):
            t = t0 + (t1 - t0) * i / k
            q = (a[0] + (b[0] - a[0]) * t / ln, a[1] + (b[1] - a[1]) * t / ln)
            d = depth
            if cur and math.hypot(q[0] - cur[-1][0][0], q[1] - cur[-1][0][1]) < 1e-6:
                continue
            cur.append((q, d))

    def line(a, b, un):
        ln = math.hypot(b[0] - a[0], b[1] - a[1])
        if not over_under:
            sample(a, b, 0.0, ln, ln, un)
            return
        # break the line where it passes under the over strand's band
        dd = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)
        cuts = []
        for C, do, lo, hi in un:
            s_ = abs(dd[0] * do[1] - dd[1] * do[0])
            if s_ < 1e-9:
                continue
            # signed distance f(t) = ((a + t dd) - C) x do, linear in t
            f0 = (a[0] - C[0]) * do[1] - (a[1] - C[1]) * do[0]
            f1 = dd[0] * do[1] - dd[1] * do[0]
            g_ = end_gap + end_r * abs(dd[0] * do[0] + dd[1] * do[1])
            t1, t2 = (lo - g_ - f0) / f1, (hi + g_ - f0) / f1
            cuts.append((min(t1, t2), max(t1, t2)))
        cuts.sort()
        t = 0.0
        for c0, c1 in cuts:
            if c1 <= t or c0 >= ln:
                continue
            if c0 > t:
                sample(a, b, t, c0, ln, un)
            flush()
            t = max(t, c1)
        if t < ln:
            sample(a, b, t, ln, ln, un)

    def arc(P, a, b):
        r = math.hypot(a[0] - P[0], a[1] - P[1])
        a0 = math.atan2(a[1] - P[1], a[0] - P[0])
        da = math.atan2(b[1] - P[1], b[0] - P[0]) - a0
        while da > math.pi:
            da -= 2 * math.pi
        while da < -math.pi:
            da += 2 * math.pi
        k = max(8, int(math.ceil(abs(da) * r / min(0.05, r * 0.3))))
        for i in range(1, k + 1):
            t = a0 + da * i / k
            cur.append(((P[0] + r * math.cos(t), P[1] + r * math.sin(t)), depth))

    def apex(P, j, off):
        f = foot(P, j, off)
        r = math.hypot(f[0] - P[0], f[1] - P[1])
        return (P[0], P[1] - r) if j % 2 == 0 else (P[0], P[1] + r)

    if split_units:
        for li, off in enumerate(offsets):
            ltype[0] = types_[li]
            set_shift(ltype[0])
            for j in range(n):
                tag[0] = j
                Pa, Pb = pin(j), pin(j + 1)
                cur.append((apex(Pa, j, off), depth))
                arc(Pa, apex(Pa, j, off), foot(Pa, j, off))
                line(foot(Pa, j, off), foot(Pb, j, off), unders(j))
                arc(Pb, foot(Pb, j, off), apex(Pb, j + 1, off))
                flush()
        return pieces

    if boxes:
        lanes = {t: (0.0 if shift_of else c, hw) for t, c, hw in bands_}
        if bands is None:
            lanes = {t: (0.0, band_h) for t in set(types_)}

        def bight_boxes(jp, t_self, hw_self):
            """Cut boxes where this lane's bight at pin jp lies under the
            partner lane's bight (gaucho: B under A at the bottom, A under B
            at the top): a chain of short boxes following the partner's arc,
            each as wide as the partner lane plus end_gap."""
            if grid or not (shift_of and over_under and bands):
                return []
            bottom = jp % 2 == 0
            if (t_self == 'g') != bottom:
                return []
            Ps = pin(jp)

            def foot_at(jd):
                nn = nrm(seg_dir(jd))
                A_ = Vs[jp]                    # both legs pass the bight vertex
                return add(Ps, nn, -dot((Ps[0] - A_[0], Ps[1] - A_[1]), nn))
            f0, f1 = foot_at(jp - 1), foot_at(jp)
            r_ = math.hypot(f0[0] - Ps[0], f0[1] - Ps[1])
            a0 = math.atan2(f0[1] - Ps[1], f0[0] - Ps[0])
            a1 = math.atan2(f1[1] - Ps[1], f1[0] - Ps[0])
            mid = -math.pi / 2 if bottom else math.pi / 2
            # sweep a0 -> a1 the way that passes the apex
            sweep = (a1 - a0) % (2 * math.pi)
            if not (0 < ((mid - a0) % (2 * math.pi)) < sweep):
                sweep -= 2 * math.pi
            out = []
            for t_o, _, hw_o in bands:
                if t_o == t_self:
                    continue
                du = shift_of.get(t_o, 0.0) - shift_of.get(t_self, 0.0)
                Po = (Ps[0] + du, Ps[1])
                hs = hw_o + end_gap
                # the partner's bight band as one smooth ring sector, so the
                # cut ends are clean arcs and straight radial edges
                ext = 0.15 if sweep > 0 else -0.15
                out.append(('ring', Po, max(r_ - hs, 0.0), r_ + hs, a0 - ext, sweep + 2 * ext))
                # and the first stretch of the partner's two legs, which also
                # lie over this bight close to the pin
                Lb = 2.0 * r_
                for jd, sgn in ((jp - 1, -1.0), (jp, 1.0)):
                    dd_ = seg_dir(jd)
                    dv = (sgn * dd_[0], sgn * dd_[1])
                    fo = foot_at(jd)
                    fo = (fo[0] + du, fo[1])
                    Q = (fo[0] + dv[0] * (Lb / 2.0 - 0.05), fo[1] + dv[1] * (Lb / 2.0 - 0.05))
                    out.append((Q, dv, hs, Lb / 2.0))
            return out

        def boxes_for(j, c, hw):
            dd = seg_dir(j)
            A = add(Vs[j], nrm(dd), c)
            out = []
            if not over_under:
                return out
            # merge windows at the same crossing whose leftover piece between
            # them would be a sliver (e.g. the gap between the two over cords)
            wins = []
            for C, do, lo, hi in unders(j):
                if wins and wins[-1][0] is C and lo - wins[-1][3] < 2 * end_gap + MIN_PIECE:
                    wins[-1] = (C, do, min(wins[-1][2], lo), max(wins[-1][3], hi))
                    continue
                if wins and wins[-1][0] is C and wins[-1][2] - hi < 2 * end_gap + MIN_PIECE \
                        and hi <= wins[-1][2]:
                    wins[-1] = (C, do, min(wins[-1][2], lo), max(wins[-1][3], hi))
                    continue
                wins.append((C, do, lo, hi))
            for C, do, lo, hi in wins:
                sx = dd[0] * do[1] - dd[1] * do[0]
                if abs(sx) < 1e-9:
                    continue
                fm = (lo + hi) / 2.0
                acx = (A[0] - C[0]) * do[1] - (A[1] - C[1]) * do[0]
                Q = add(A, dd, (fm - acx) / sx)
                hs = (hi - lo) / 2.0 + end_gap
                # long enough that the box ends clear this lane's edges
                # even where the strip meets them at a slant
                out.append((Q, do, hs, (hw + hs) / abs(sx) + 0.1))
            return out

        # one piece per HALF-pass: a whole pass crosses itself (its up and
        # down halves cross), which a single pipe body cannot do
        for li, off in enumerate(offsets):
            ltype[0] = types_[li]
            set_shift(ltype[0])
            c, hw = lanes[ltype[0]]
            for j in range(n):
                Pa, Pb = pin(j), pin(j + 1)
                cur = [(apex(Pa, j, off), depth)]
                arc(Pa, apex(Pa, j, off), foot(Pa, j, off))
                a_, b_ = foot(Pa, j, off), foot(Pb, j, off)
                ln_ = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
                sample(a_, b_, 0.0, ln_, ln_, None)
                arc(Pb, foot(Pb, j, off), apex(Pb, j + 1, off))
                pieces.append((cur, boxes_for(j, c, hw)
                               + bight_boxes(j, ltype[0], hw)
                               + bight_boxes(j + 1, ltype[0], hw)))
                cur = []
        return pieces

    for li, off in enumerate(offsets):
        ltype[0] = types_[li]
        set_shift(ltype[0])
        for j in range(0, n, 2):
            P0, P1, P2 = pin(j), pin(j + 1), pin(j + 2)
            cur.append((apex(P0, j, off), depth))
            arc(P0, apex(P0, j, off), foot(P0, j, off))
            line(foot(P0, j, off), foot(P1, j, off), unders(j))
            arc(P1, foot(P1, j, off), foot(P1, j + 1, off))
            line(foot(P1, j + 1, off), foot(P2, j + 1, off), unders(j + 1))
            arc(P2, foot(P2, j + 1, off), apex(P2, j + 2, off))
            flush()
    return pieces


def extend_ends(pts, e):
    """Push both ends of a ((u, z), d) polyline out by e along the end
    tangents, so neighbouring pieces overlap instead of meeting cap-to-cap."""
    def ext(a, b):
        (pa, da), (pb, _) = a, b
        L_ = math.hypot(pa[0] - pb[0], pa[1] - pb[1]) or 1.0
        return ((pa[0] + (pa[0] - pb[0]) / L_ * e, pa[1] + (pa[1] - pb[1]) / L_ * e), da)
    if len(pts) < 2:
        return pts
    return [ext(pts[0], pts[1])] + pts + [ext(pts[-1], pts[-2])]


def box_to_3d(R, box, depth):
    """Unrolled cut box -> (centre xyz, length dir, width dir, length, width,
    height) on the cylinder's tangent plane at the box centre.
    A ring sector ('ring', (u, z), r_in, r_out, a0, sweep) is passed through
    as ('ring', theta, z, r_in, r_out, a0, sweep, depth) for the builder."""
    if box[0] == 'ring':
        _, (u, z), r_in, r_out, a0, sweep = box
        return ('ring', u / R, z, r_in, r_out, a0, sweep, depth)
    (u, z), do, hw, hl = box
    th = u / R
    t = (-math.sin(th), math.cos(th), 0.0)
    e = (math.cos(th), math.sin(th), 0.0)
    m = (do[1], -do[0])
    along = (do[0] * t[0], do[0] * t[1], do[1])
    across = (m[0] * t[0], m[0] * t[1], m[1])
    rc = R - depth / 2.0
    return ((rc * e[0], rc * e[1], z), along, across, 2 * hl, 2 * hw, 2 * depth + 0.4)


def to_3d(R, pieces, cut_r):
    out = []
    for pts in pieces:
        o = []
        for (u, z), d in pts:
            th = u / R
            rc = R + cut_r - d
            o.append((rc * math.cos(th), rc * math.sin(th), z))
        out.append(o)
    return out


def u_layers(pieces, r):
    """U-shaped grooves: where a path is deeper than the tube radius, stack
    extra copies of it at increasing depth (spaced <= r apart), so the union
    of the round tubes has the full line width at the surface and a round
    floor at the requested depth."""
    out = []
    for pts in pieces:
        dmax = max(d for _, d in pts)
        if dmax <= r + 1e-9:
            out.append(pts)
            continue
        n = max(1, int(math.ceil((dmax - r) / r - 1e-9)))
        for k in range(n + 1):
            f = k / float(n)
            layer = [(q, r + (d - r) * f if d > r else d) for q, d in pts]
            if k:
                # deeper copies stop short of the top tube's ends: nearly
                # coplanar end caps make the union fail or come out
                # non-manifold
                layer = _trim_ends(layer, 0.6 * r)
            if len(layer) >= 2:
                out.append(layer)
    return out


def _trim_ends(pts, t):
    """Shorten a ((u, z), d) polyline by arc length t at each end."""
    def cut(seq):
        acc = 0.0
        for i in range(len(seq) - 1):
            (a, da), (b, db) = seq[i], seq[i + 1]
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if acc + L >= t and L > 0:
                f = (t - acc) / L
                q = (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
                return [(q, da + (db - da) * f)] + seq[i + 1:]
            acc += L
        return []
    total = sum(math.hypot(pts[i + 1][0][0] - pts[i][0][0], pts[i + 1][0][1] - pts[i][0][1])
                for i in range(len(pts) - 1))
    if total <= 2.5 * t:
        return []
    return cut(cut(pts)[::-1])[::-1]


HOLE_MODES = (
    ('turn', 'Turnaround pins (valid knots only)'),
    ('vertex', 'Beside every crossing (above & below)'),
    ('centre', 'Diamond centres'),
    ('none', 'None'),
)


def strand_half_angle(R, H, L, B):
    """Angle between a strand and the jig axis (half-angle of the axial V)."""
    return math.atan2(R * L * math.pi / B, H)


def vertex_offset(R, H, L, B, clear):
    """Axial distance from a vertex to a pin that sits `clear` from both strands."""
    return clear / math.sin(strand_half_angle(R, H, L, B))


def pin_points(R, H, z0, L, B, mode, end_bights, clear, edge_rows=False, valid=None,
               bight=None):
    """bight=(u_shift, rho): put the end-bight pins at a shifted lane's own
    bight (gaucho colour A) instead of the strand centreline."""
    valid = valid or knot_valid
    """Pin hole positions (theta, z).

    Pins sit in the V just beyond a vertex, `clear` from both strand centrelines.
    End bights: inside each bight apex.
    'turn': a pin row just past crossing row k lets the cord turn there,
            making a shorter knot from that end. Row k from the bottom gives
            k leads; from the top, L-k leads. Rows giving a lead count that
            shares a factor with B (or < 2 leads) are skipped: they would
            need more than one cord.
    'vertex': above and below every crossing.
    'centre': diamond centres.
    """
    d = vertex_offset(R, H, L, B, clear)
    pts = []
    if end_bights:
        if bight:
            dus, rho_ = bight
            if not isinstance(dus, (list, tuple)):
                dus = [dus]
            db = rho_ / math.sin(math.atan2(R * L * math.pi / B, H))
        else:
            dus, db = [0.0], d
        for du in dus:
            dth = du / R
            pts += [(2 * i * math.pi / B + dth, z0 + db) for i in range(B)]
            pts += [((2 * i + L) * math.pi / B + dth, z0 + H - db) for i in range(B)]
    if mode == 'centre':
        pts += gap_points(R, H, z0, L, B)
    elif mode in ('turn', 'vertex'):
        for k in range(1, L):
            zk = z0 + k * H / L
            up_ok = mode == 'vertex' or (k >= 2 and valid(k, B))
            dn_ok = mode == 'vertex' or (L - k >= 2 and valid(L - k, B))
            # pins past the outermost crossing rows sit in the notches
            # between end bights; optional
            if not edge_rows:
                up_ok = up_ok and k != L - 1
                dn_ok = dn_ok and k != 1
            for i in range(B):
                th = (2 * i + k) * math.pi / B
                if up_ok:
                    pts.append((th, zk + d))
                if dn_ok:
                    pts.append((th, zk - d))
    return pts


def turnaround_leads(L, B, edge_rows=False, valid=None):
    valid = valid or knot_valid
    """Lead counts available as shorter knots (from bottom; from top is mirror)."""
    top = L if edge_rows else L - 1
    return [k for k in range(2, top) if valid(k, B)]


def strand_half_width(p, R, H, L, B):
    if not has_ribbon(p):
        return 0.0
    return (p['ribbon_pct'] / 100.0 * strand_pitch(R, H, L, B) + outline_w(p)) / 2.0


def has_ribbon(p):
    """The cord occupies its lanes whether or not outlines are engraved, so
    pins and bights always clear it."""
    return True


def outline_w(p):
    """How far lane marks stick out past the lane edges (outlines only)."""
    if not p['engrave'] or mark_style(p) == 'solid':
        return 0.0
    return p['line_w']


MARK_STYLES = (
    ('solid', 'Solid cord path'),
    ('outline', 'Lane outlines'),
)


def mark_style(p):
    if passes_of(p) >= 2:
        return 'solid'      # gaucho lanes are only built as solid paths
    return p.get('mark_style', 'outline')


def fill_radius(p):
    """Tube radius for solid lane fills: ONE tube per lane whose circle cuts
    the surface in a chord as wide as the lane and reaches `line_d` deep
    (r = (w^2/4 + d^2) / 2d). One tube instead of several side by side
    makes the build several times faster."""
    w, d = p['cord_d'], min(p['line_d'], p['cord_d'] / 2.0)
    return (w * w / 4.0 + d * d) / (2.0 * d)


def fill_depth(p):
    return min(p['line_d'], p['cord_d'] / 2.0)


def fill_offsets(p):
    """One tube centre per cord lane (offset, lane type)."""
    bands = lane_layout(p)[3] or [('b', 0.0, p['cord_d'] / 2.0)]
    fan = passes_of(p) >= 2
    # gaucho lanes are placed by shifting (fan_shifts): offsets are relative
    # to each lane's own centreline
    return [0.0 if fan else c for _, c, _ in bands], [t for t, _, _ in bands]


def knot_ok(p):
    """Validity test for a lead count with this jig's weave (single cord AND
    the along-cord code closes consistently)."""
    code = weave_of(p) if p.get('over_under', True) else 'OU'
    return lambda l, b: code_consistent(l, b, code)


def weave_of(p, key='weave'):
    """Effective O/U string for a weave setting ('weave' = base cord,
    'gaucho_weave' = gaucho cord)."""
    if key == 'weave' and p.get('style') in ('fan', 'headhunter'):
        return 'OU'   # gaucho: standard base knot; headhunter: row weave, always closes
    if key == 'weave' and p.get('style') == 'herringbone':
        return 'OOUU'  # over 2 / under 2 along the cord
    w = p.get(key, 'OU' if key == 'weave' else 'OOUU')
    if w == 'custom':
        w = p.get(key + '_custom', '').strip().upper().replace(' ', '')
    return w


KNOT_STYLES = (
    ('single', "Turk's head"),
    ('fan', 'Gaucho interweave'),
    ('herringbone', 'Herringbone'),
    ('headhunter', "Headhunter's knot"),
)
# no longer offered in the dialog, still built for jigs saved with it
LEGACY_STYLES = {'doubled': 'fan'}


def cord_code_of(p):
    """Along-the-cord O/U code for the build, or None for a row-based weave."""
    if p.get('style') == 'headhunter':
        return None
    return weave_of(p)


def row_weave_of(p):
    """Row-based weave (used when cord_code_of is None): the headhunter's
    knot crosses in pairs of rows, over 2 / under 2 going up."""
    return 'OOUU' if p.get('style') == 'headhunter' else 'OU'


def passes_of(p):
    if p.get('style', 'single') in ('doubled', 'fan'):
        return max(2, int(p.get('strands', 2)))
    return 1


def lane_letter(t):
    """'c0' -> 'A', 'c1' -> 'B', ..."""
    return chr(ord('A') + int(t[1:])) if t and t[0] == 'c' else 'A'


def grid_code(p):
    """Gaucho (Grid Maker 'row coding'): the N-cord knot is a Turk's head of
    N*leads x N*bights whose crossings go by row, U^N O^N repeating upward.
    Checked against every pass of the Paracord Guild 7L6B gaucho run list."""
    n = passes_of(p)
    return 'U' * n + 'O' * n


def fan_shifts(p, R, H, L, B):
    """Gaucho lane u-shifts {type: du}: N cords, each the base knot moved
    round the jig by an equal share of the bight spacing (as in a Turk's head
    of N*L x N*B). swap_lanes mirrors the order."""
    n = passes_of(p)
    g = 2 * math.pi * R / (B * n)
    s = 1.0 if p.get('swap_lanes', True) else -1.0
    return {'c%d' % m: s * (m - (n - 1) / 2.0) * g for m in range(n)}


def lane_rho(p):
    """One gaucho lane's bight wrap radius round its pin."""
    hr = p['hole_d'] / 2.0 if p['bight_holes'] else 0.0
    return p['cord_d'] / 2.0 + hr + PIN_CLEARANCE


def lane_layout(p):
    """Cord lanes, each one cord diameter wide.
    One cord: a single lane on the path. Gaucho: N lanes ('c0'..), each the
    whole path moved round the jig (fan_shifts); W is the share of the strand
    spacing they need together (N x (cord + gap)).
    Returns (band width W, edge offsets, line types, lane bands)."""
    cd = p['cord_d']
    n = passes_of(p)
    if n >= 2:
        g = p['pass_gap']
        types = ['c%d' % m for m in range(n)]
        offs, tys = [], []
        for t in types:
            offs += [-cd / 2.0, cd / 2.0]
            tys += [t, t]
        return (n * (cd + g), tuple(offs), tys, [(t, 0.0, cd / 2.0) for t in types])
    return cd, (cd / 2.0, -cd / 2.0), ['b', 'b'], None


def band_width(p):
    return lane_layout(p)[0]


def ribbon_layout(p, W):
    """Edge-line offsets, pass types and sub-ribbon bands for the engraving.

    Without gaucho: one ribbon of width W centred on the cord path.
    With gaucho: the band W is split into two parallel ribbons with a gap;
    base cord on one side, gaucho cord on the other (swap with gaucho_swap).
    Returns (offsets, line_types, bands, weaves).
    """
    base_w = weave_of(p)
    if not p.get('gaucho'):
        return ((W / 2.0, -W / 2.0), ['b', 'b'], [('b', 0.0, W / 2.0)],
                {'b': base_w, 'g': base_w})
    gap = p['gaucho_gap']
    wc = (W - gap) / 2.0
    c = (wc + gap) / 2.0
    side = -1.0 if p.get('gaucho_swap') else 1.0
    ob, og = -side * c, side * c
    offsets = (ob - wc / 2.0, ob + wc / 2.0, og - wc / 2.0, og + wc / 2.0)
    return (offsets, ['b', 'b', 'g', 'g'],
            [('b', ob, wc / 2.0), ('g', og, wc / 2.0)],
            {'b': base_w, 'g': weave_of(p, 'gaucho_weave')})




def cleat_outline(wt, wb, top, depth, cd, ridges):
    """Closed (x, z) outline of the jam-cleat slot (the region cut away).

    V-slot: mouth half-width wt at the top (extended 1 mm above the end),
    floor half-width wb at top - depth. With ridges, each wall carries
    sawtooth barbs: a gentle ramp facing the mouth so the cord slides in,
    and a steep face toward the mouth so it resists pulling out.
    """
    above = top + 0.1
    floor = top - depth

    def wall(sign):
        """Points down one wall, from the mouth to the floor."""
        a = (sign * wt, above)
        b = (sign * wb, floor)
        pts = [a]
        if ridges:
            ln = math.hypot(b[0] - a[0], b[1] - a[1])
            d = ((b[0] - a[0]) / ln, (b[1] - a[1]) / ln)
            # inward normal: perpendicular to the wall, pointing to slot centre
            nx, nz = -d[1], d[0]
            if nx * sign > 0:
                nx, nz = -nx, -nz
            pitch = cd * CLEAT_RIDGE_PITCH
            h = cd * CLEAT_RIDGE_HEIGHT
            t = (above - top) + pitch  # first barb one pitch below the end face
            while t + pitch <= ln - 0.5 * pitch:
                p0 = (a[0] + d[0] * t, a[1] + d[1] * t)
                tp = t + pitch * 0.8
                pk = (a[0] + d[0] * tp + nx * h, a[1] + d[1] * tp + nz * h)
                p1 = (a[0] + d[0] * (t + pitch), a[1] + d[1] * (t + pitch))
                pts += [p0, pk, p1]
                t += pitch
        pts.append(b)
        return pts

    left = wall(-1)
    right = wall(1)
    return left + right[::-1]


# ---------------------------------------------------------------- derived from settings

def bight_rho(p, R, H, L, B):
    """Cord-centreline wrap radius at end bights (pin inside only if pinned)."""
    hr = p['hole_d'] / 2.0 if p['bight_holes'] else 0.0
    return strand_half_width(p, R, H, L, B) + hr + PIN_CLEARANCE


def max_ribbon_pct(p, R, H, L, B):
    """Widest ribbon whose bight wraps don't overlap neighbouring bights."""
    S = 2 * math.pi * R / B
    hr = p['hole_d'] / 2.0 if p['bight_holes'] else 0.0
    w = (S - 2 * outline_w(p) - 2 * hr - 0.04) / 2.0
    return max(0.0, 100.0 * w / strand_pitch(R, H, L, B))


def engraving_top(p, R, H, L, B, z0):
    """Highest z of the engraved knot (outer edge of the top bight outlines)."""
    if not has_ribbon(p):
        return z0 + H
    su = R * L * math.pi / B
    rho = bight_rho(p, R, H, L, B)
    pin_z = z0 + H - rho / math.sin(math.atan2(su, H))
    W = p['ribbon_pct'] / 100.0 * strand_pitch(R, H, L, B)
    return pin_z + rho + W / 2.0 + outline_w(p) / 2.0


def cleat_floor(p, R, H, L, B, z0):
    return engraving_top(p, R, H, L, B, z0) + CLEAT_FLOOR_GAP


def top_mode(p):
    m = p.get('top_mode')
    if m:
        return m
    return 'cleat' if p.get('cleat') else 'none'   # settings from older versions


def lid_split(p, R, H, L, B, z0):
    """z of the shoulder where the lid sits (and the cord is clamped)."""
    return engraving_top(p, R, H, L, B, z0) + LID_GAP


def lid_thread(p):
    """(nominal diameter cm, metric size mm) of the spigot thread: the largest
    ISO size that leaves a clamp shoulder at least 2.5 cord diameters wide
    and a lid wall of LID_MIN_WALL."""
    R = p['dia'] / 2.0
    shoulder = max(2.5 * p['cord_d'], LID_MIN_WALL)
    target_mm = 2 * (R - shoulder) * 10
    sizes = [s for s in ISO_SIZES_MM if s <= target_mm]
    if not sizes:
        return None, None
    return sizes[-1] / 10.0, sizes[-1]


def cavity_radius(p):
    """Pin storage cavity radius: inside the spigot's thread root and clear
    of the radial pin holes."""
    d, _ = lid_thread(p)
    if d is None:
        return 0.0
    R = p['dia'] / 2.0
    minor = d - 1.0825 * THREAD_PITCH_PREF
    r = min(minor / 2.0 - CAVITY_WALL, R - p['hole_depth'] - CAVITY_WALL)
    if p.get('handle_len', 0) > 0 and p.get('handle_dia', 0) > 0:
        r = min(r, p['handle_dia'] / 2.0 - CAVITY_WALL)   # thinner handle
    return max(0.0, r)


def storage_depth(p, R, H, L, B, z0):
    """Pin storage is as deep as it can be: from the spigot top down to a
    STORAGE_FLOOR above the bottom of the jig (through the handle)."""
    top = lid_split(p, R, H, L, B, z0) + p['thread_len']
    bottom = -p.get('handle_len', 0.0) + STORAGE_FLOOR
    return max(0.0, top - bottom)


def top_end(p, R, H, L, B, z0):
    """z of the top of the finished jig (lid top for the lid)."""
    m = top_mode(p)
    if m == 'cleat':
        return cleat_top(p, R, H, L, B, z0)
    if m == 'lid':
        return lid_split(p, R, H, L, B, z0) + p['thread_len'] + LID_CAP
    return p['length']


def cleat_top(p, R, H, L, B, z0):
    """Top end of the jig when the cleat is on: slot floor + slot depth."""
    return cleat_floor(p, R, H, L, B, z0) + p['cleat_depth']


def cleat_alignment(p, R, H, L, B, z0, step=0.2, offset=0.0, z_exit=None):
    """Where the cord leaves the cleat so it runs straight into the knot.

    The tie-in starts down the first descending strand (from the top bight at
    theta = L*pi/B). That strand's centreline, extended upward past its bight
    pin, meets the cleat slot floor at angle theta_exit. Returns
    (theta_exit, z_exit, lead_in) where lead_in is the (u, z) path from the
    slot down to where the strand leaves the bight pin.
    offset: follow a lane beside the centreline (colour A's lane when two
    cords are used), so the lead-in feeds straight into that lane.
    """
    su = R * L * math.pi / B
    m = math.hypot(su, H)
    d = (su / m, -H / m)                 # descending direction
    nn = (-d[1], d[0])
    V = (su, z0 + H)
    rho = bight_rho(p, R, H, L, B)
    P = (su, z0 + H - rho / math.sin(math.atan2(su, H)))
    A = (V[0] + nn[0] * offset, V[1] + nn[1] * offset)
    k = (P[0] - A[0]) * nn[0] + (P[1] - A[1]) * nn[1]
    foot = (P[0] - nn[0] * k, P[1] - nn[1] * k)   # strand leaves the pin here
    if z_exit is None:
        z_exit = cleat_floor(p, R, H, L, B, z0) + p['cord_d'] / 2.0
    t = (z_exit - foot[1]) / (H / m)              # distance back up the strand
    top = (foot[0] - d[0] * t, foot[1] - d[1] * t)
    n = max(2, int(math.ceil(t / step)))
    lead = [(top[0] + (foot[0] - top[0]) * i / n, top[1] + (foot[1] - top[1]) * i / n)
            for i in range(n + 1)]
    return top[0] / R, z_exit, lead


def pin_clear(p, R, H, L, B):
    """Pin centre to strand centreline: strand half-width + pin radius + 0.2 mm."""
    return strand_half_width(p, R, H, L, B) + p['hole_d'] / 2.0 + PIN_CLEARANCE


def pass_number_spots(p, R, H, L, B, z0):
    """Engraved pass numbers: half-pass n (1..2B, in tying order, starting
    from a top bight going down) gets its number just outside the bight it
    starts from, nudged toward the leg it leaves on.
    Returns (text height, [(text, u, z)]), or (0, []) if there is no room."""
    rho = bight_rho(p, R, H, L, B)
    W = lane_layout(p)[0]
    su = R * L * math.pi / B
    d_pin = rho / math.sin(math.atan2(su, H))
    reach = rho + W / 2.0
    top_edge = z0 + H - d_pin + reach
    bot_edge = z0 + d_pin - reach
    m = top_mode(p)
    if m == 'lid':
        top_room = lid_split(p, R, H, L, B, z0) - top_edge
    elif m == 'cleat':
        top_room = cleat_floor(p, R, H, L, B, z0) - top_edge
    else:
        top_room = p['length'] - p['chamfer'] - top_edge
    bot_room = bot_edge - (0.0 if p['handle_len'] > 0 else p['chamfer'])
    gap = 0.08
    h = min(NUMBER_HEIGHT, top_room - 2 * gap, bot_room - 2 * gap)
    if h < 0.2:
        return 0.0, []
    C = 2 * math.pi * R
    out = []
    zt, zb = top_edge + gap + h / 2.0, bot_edge - gap - h / 2.0
    if passes_of(p) >= 2:
        # number colour A's bights; mark where each colour starts: A1, B1, ...
        sh = fan_shifts(p, R, H, L, B)
        nudge = 0.5 * lane_rho(p)
        for n in range(1, 2 * B + 1):
            u = (n * su + sh['c0'] + nudge) % C
            out.append(('A1' if n == 1 else str(n), u, zt if n % 2 else zb))
        for m in range(1, passes_of(p)):
            t = 'c%d' % m
            out.append((lane_letter(t) + '1', (su + sh[t] + nudge) % C, zt))
        return h, out
    for n in range(1, 2 * B + 1):
        u = (n * su + 0.5 * rho) % C
        out.append((str(n), u, zt if n % 2 else zb))
    return h, out


def grid_edge_ok(p, R, H, L, B):
    """Gaucho: the first/last crossing row (1/(N*L) of the span from a bight
    vertex) must lie on the straight legs, above where each lane starts
    curving round its pin."""
    n = passes_of(p)
    if n < 2:
        return True
    su = R * L * math.pi / B
    m = math.hypot(su, H)
    rho = lane_rho(p)
    d_pin = rho / math.sin(math.atan2(su, H))
    z_foot = d_pin * (H / m) ** 2
    return H / (n * L) >= z_foot + p['cord_d'] / 2.0
