"""Builds, stores and removes jig components in the active Fusion design."""

import json
import math
import re
import traceback

import adsk.core
import adsk.fusion

from .geometry import *

ATTR_GROUP = 'TurksHeadGaucho'
LEGACY_ATTR_GROUP = 'TurksHeadJig'  # jigs from the plain add-in can be edited too
ATTR_NAME = 'params'
PARAMS_VERSION = 1

_app = adsk.core.Application.get()
_ui = _app.userInterface
_building_occ = None
errors = []  # non-fatal problems collected during a build (shown in debug mode)
timings = []  # (stage, seconds) for the debug report
diag = []    # piece-count checks for the debug report
_t0 = [0.0]


def lap(stage):
    import time
    now = time.perf_counter()
    if _t0[0]:
        timings.append((stage, now - _t0[0]))
    _t0[0] = now


def _lumps(body):
    try:
        return body.lumps.count
    except Exception:
        return -1


def note(stage):
    errors.append('{}:\n{}'.format(stage, traceback.format_exc().strip()))


def _pt(x, y, z):
    return adsk.core.Point3D.create(x, y, z)


def _ring_profile(sk, r, bore):
    """Disk of radius r (annulus if bore > 0) in sketch sk; returns the profile."""
    c = sk.sketchCurves.sketchCircles
    c.addByCenterRadius(_pt(0, 0, 0), r)
    if bore > 0:
        c.addByCenterRadius(_pt(0, 0, 0), bore / 2.0)
        for i in range(sk.profiles.count):
            if sk.profiles.item(i).profileLoops.count == 2:
                return sk.profiles.item(i)
    return sk.profiles.item(0)


def _slot_plane(comp, phi):
    """XZ plane turned by phi about Z (verified, since the API's angle sign
    convention isn't documented)."""
    if abs(phi) < 1e-9:
        return comp.xZConstructionPlane
    want = (-math.sin(phi), math.cos(phi))   # slot channel direction = plane normal
    for ang in (phi, -phi):
        ci = comp.constructionPlanes.createInput()
        ci.setByAngle(comp.zConstructionAxis, adsk.core.ValueInput.createByReal(ang),
                      comp.xZConstructionPlane)
        pl = comp.constructionPlanes.add(ci)
        n = pl.geometry.normal
        if abs(n.x * want[0] + n.y * want[1]) > 0.999:
            pl.isLightBulbOn = False
            pl.name = 'Cleat slot plane'
            return pl
        pl.deleteMe()
    raise RuntimeError('could not orient cleat slot plane')


def _jig_body(comp):
    return comp.bRepBodies.itemByName('Jig')


CUT = adsk.fusion.FeatureOperations.CutFeatureOperation
JOIN = adsk.fusion.FeatureOperations.JoinFeatureOperation
INTERSECT = adsk.fusion.FeatureOperations.IntersectFeatureOperation
NEW = adsk.fusion.FeatureOperations.NewBodyFeatureOperation


def _combine(comp, target, tools, op, keep, stage):
    """Combine with error capture; returns True on success."""
    try:
        coll = adsk.core.ObjectCollection.create()
        for b in tools:
            coll.add(b)
        ci = comp.features.combineFeatures.createInput(target, coll)
        ci.operation = op
        ci.isKeepToolBodies = keep
        comp.features.combineFeatures.add(ci)
        return True
    except Exception:
        note(stage)
        return False


def _add_temp_body(comp, tbody, name, parametric):
    """Put a TemporaryBRepManager body into the design (base feature if parametric)."""
    if parametric:
        bf = comp.features.baseFeatures.add()
        bf.startEdit()
        comp.bRepBodies.add(tbody, bf)
        bf.finishEdit()
        bf.name = name
        body = bf.bodies.item(0)  # handle from inside the edit goes stale
    else:
        body = comp.bRepBodies.add(tbody)
    body.name = name
    return body


def _discard(comp, body):
    """Remove a helper body; fall back to deleting, then to hiding."""
    name = getattr(body, 'name', 'body')
    try:
        comp.features.removeFeatures.add(body)
        return
    except Exception:
        pass
    try:
        body.deleteMe()
        return
    except Exception:
        pass
    note('Remove ' + name)
    try:
        body.isLightBulbOn = False
    except Exception:
        pass


def _engrave(comp, paths, r, keep_name=None, fill_args=None):
    """Cut all groove paths.

    Speed-ups vs one cut per path:
      - splines added to one sketch with compute deferred
      - each pipe made as a separate NEW body (no boolean against the
        increasingly complex jig), then ONE combine cut with all tools
      - viewport refresh only every 10 features
    keep_name: keep the groove tools, joined into one body with this name
    (returned), so the grooves can be printed in another colour.
    """
    feats = comp.features
    psk = comp.sketches.add(comp.xYConstructionPlane)
    psk.name = 'Knot paths'
    psk.isComputeDeferred = True
    splines = []
    for pts in paths:
        coll = adsk.core.ObjectCollection.create()
        for x, y, z in pts:
            coll.add(_pt(x, y, z))
        splines.append(psk.sketchCurves.sketchFittedSplines.add(coll))
    psk.isComputeDeferred = False
    psk.isVisible = False

    prog = _ui.createProgressDialog()
    prog.isCancelButtonShown = True
    prog.show("Turk's Head Jig", 'Engraving path %v of %m', 0, len(splines), 0)
    tools = []
    size = adsk.core.ValueInput.createByReal(2 * r)
    for i, sp in enumerate(splines):
        if prog.wasCancelled:
            break
        try:
            pi = feats.pipeFeatures.createInput(
                feats.createPath(sp, False),
                adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            pi.sectionSize = size
            f = feats.pipeFeatures.add(pi)
            for b in f.bodies:
                b.name = 'Groove tool {}'.format(i + 1)
                tools.append(b)
        except Exception:
            note('Pipe for path {}'.format(i + 1))
        prog.progressValue = i + 1
        if i % 10 == 9:
            adsk.doEvents()
    prog.message = 'Cutting grooves…'
    adsk.doEvents()

    if tools and keep_name:
        prog.message = 'Building ' + keep_name + '…'
        adsk.doEvents()
        _combine(comp, _jig_body(comp), tools, CUT, keep=True, stage='Groove cut ' + keep_name)
        fill = None
        try:
            fill = _make_fill(comp, tools, keep_name, *fill_args)
        except Exception:
            note('Build ' + keep_name)
        for b in tools:
            _discard(comp, b)
        prog.hide()
        return fill
    if tools:
        coll = adsk.core.ObjectCollection.create()
        for b in tools:
            coll.add(b)
        try:
            ci = feats.combineFeatures.createInput(_jig_body(comp), coll)
            ci.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
            ci.isKeepToolBodies = False
            feats.combineFeatures.add(ci)
        except Exception:
            note('Combined groove cut (falling back to one at a time)')
            # fall back to one tool at a time so one bad tool doesn't sink all
            for b in tools:
                try:
                    one = adsk.core.ObjectCollection.create()
                    one.add(b)
                    ci = feats.combineFeatures.createInput(_jig_body(comp), one)
                    ci.operation = adsk.fusion.FeatureOperations.CutFeatureOperation
                    ci.isKeepToolBodies = False
                    feats.combineFeatures.add(ci)
                except Exception:
                    note('Groove cut for tool body')
                    try:
                        b.isLightBulbOn = False
                    except Exception:
                        pass
    prog.hide()


def _tbm_op(tbm, a, b, op):
    try:
        return bool(tbm.booleanOperation(a, b, op))
    except Exception:
        return False


def _env(tbm, R, z_lo, z_hi):
    return tbm.createCylinderOrCone(_pt(0, 0, z_lo), R, _pt(0, 0, z_hi), R)


def _inside(body, R, tol=0.002):
    """True if no vertex of a temporary body lies outside radius R."""
    try:
        for v in body.vertices:
            g = v.geometry
            if math.hypot(g.x, g.y) > R + tol:
                return False
        return body.volume > 1e-9
    except Exception:
        return True


def _ring_cutter(tbm, R, th, z, r_in, r_out, a0, sweep, depth):
    """Temporary body: a ring sector (radii r_in..r_out, angles a0..a0+sweep
    in the unrolled u/z plane) laid on the cylinder's tangent plane at
    angle th, height z, reaching from above the surface to below `depth`."""
    try:
        er = adsk.core.Vector3D.create(math.cos(th), math.sin(th), 0)
        et = adsk.core.Vector3D.create(-math.sin(th), math.cos(th), 0)
        ez = adsk.core.Vector3D.create(0, 0, 1)

        def P(k_r, k_t=0.0, k_z=0.0):
            return _pt(R * er.x + k_r * er.x + k_t * et.x,
                       R * er.y + k_r * er.y + k_t * et.y, z + k_z)

        lo, hi = -(depth + 0.15), 0.15
        ring = tbm.createCylinderOrCone(P(lo), r_out, P(hi), r_out)
        if r_in > 1e-4:
            hole = tbm.createCylinderOrCone(P(lo - 0.1), r_in, P(hi + 0.1), r_in)
            if not tbm.booleanOperation(ring, hole, adsk.fusion.BooleanTypes.DifferenceBooleanType):
                return None
        if abs(sweep) < math.pi:
            mid = a0 + sweep / 2.0
            S = 2.0 * (r_out + 0.5)
            for a in (a0, a0 + sweep):
                d = (math.cos(a), math.sin(a))
                m = (math.cos(mid), math.sin(mid))
                k = m[0] * d[0] + m[1] * d[1]
                n = (m[0] - k * d[0], m[1] - k * d[1])
                ln = math.hypot(*n) or 1.0
                n = (n[0] / ln, n[1] / ln)
                d3 = adsk.core.Vector3D.create(d[0] * et.x, d[0] * et.y, d[1])
                n3 = adsk.core.Vector3D.create(n[0] * et.x, n[0] * et.y, n[1])
                c = P((lo + hi) / 2.0, n[0] * S / 2.0, n[1] * S / 2.0)
                half = tbm.createBox(adsk.core.OrientedBoundingBox3D.create(
                    c, d3, n3, 2 * S, S, (hi - lo) + 0.4))
                if not tbm.booleanOperation(ring, half,
                                            adsk.fusion.BooleanTypes.IntersectionBooleanType):
                    return None
        return ring
    except Exception:
        return None


def _pin_tool_tbm(p, R, H, z0, L, B):
    """All pin holes as one temporary body (or None)."""
    gaucho = passes_of(p) >= 2
    spots = pin_points(R, H, z0, L, B, 'none' if gaucho else p['hole_mode'],
                       p['bight_holes'], pin_clear(p, R, H, L, B), p['edge_rows'],
                       knot_ok(p),
                       bight=((list(fan_shifts(p, R, H, L, B).values()), lane_rho(p))
                              if gaucho else None))
    if not spots:
        return None
    tbm = adsk.fusion.TemporaryBRepManager.get()
    rh = p['hole_d'] / 2.0
    outer, inner = R + 0.1, R - p['hole_depth']
    cyls = []
    for th, z in spots:
        cx, cy = math.cos(th), math.sin(th)
        cyls.append(tbm.createCylinderOrCone(_pt(outer * cx, outer * cy, z), rh,
                                             _pt(inner * cx, inner * cy, z), rh))
    tool, left = _union_tree(tbm, cyls)
    for c in left:
        _tbm_op(tbm, tool, c, adsk.fusion.BooleanTypes.UnionBooleanType)
    return tool


def _engrave_solid(comp, paths, boxes, r, name, R, z_lo, z_hi, parametric, keep=True):
    """Solid lane fill with clean ends: continuous tubes, each trimmed in
    memory by the cut boxes of the lanes passing over it (flat faces, so the
    ends are straight), clipped to the mandrel, unioned, then used to cut
    the jig. keep=False: only the groove is cut."""
    feats = comp.features
    psk = comp.sketches.add(comp.xYConstructionPlane)
    psk.name = 'Lane paths'
    psk.isComputeDeferred = True
    splines = []
    for pts in paths:
        coll = adsk.core.ObjectCollection.create()
        for x, y, z in pts:
            coll.add(_pt(x, y, z))
        splines.append(psk.sketchCurves.sketchFittedSplines.add(coll))
    psk.isComputeDeferred = False
    psk.isVisible = False

    prog = _ui.createProgressDialog()
    prog.isCancelButtonShown = True
    prog.show("Turk's Head Jig", name + ': path %v of %m', 0, len(splines), 0)
    tbm = adsk.fusion.TemporaryBRepManager.get()
    D = adsk.fusion.BooleanTypes.DifferenceBooleanType
    I = adsk.fusion.BooleanTypes.IntersectionBooleanType
    size = adsk.core.ValueInput.createByReal(2 * r)
    pieces, made, feats_made = [], [], []
    for i, sp in enumerate(splines):
        if prog.wasCancelled:
            break
        try:
            pi = feats.pipeFeatures.createInput(feats.createPath(sp, False), NEW)
            pi.sectionSize = size
            f = feats.pipeFeatures.add(pi)
        except Exception:
            note('{} pipe {}'.format(name, i + 1))
            continue
        feats_made.append(f)
        for b in f.bodies:
            made.append(b)
            c = tbm.copy(b)
            # clip to the mandrel FIRST, while the tube is simple; a clip
            # attempted after the trims can fail and leave the whole tube
            # standing proud of the surface
            if not _tbm_op(tbm, c, _env(tbm, R, z_lo, z_hi), I):
                note('{} clip {}'.format(name, i + 1))
                continue
            clipped = tbm.copy(c)
            ok = True
            n_clip = _lumps(c)
            for spec in boxes[i]:
                if spec[0] == 'ring':
                    bx = _ring_cutter(tbm, R, *spec[1:])
                    if bx is None:
                        ok = False
                        continue
                else:
                    (cx, cy, cz), ld, wd, L_, W_, H_ = spec
                    bx = tbm.createBox(adsk.core.OrientedBoundingBox3D.create(
                        _pt(cx, cy, cz), adsk.core.Vector3D.create(*ld),
                        adsk.core.Vector3D.create(*wd), L_, W_, H_))
                if not _tbm_op(tbm, c, bx, D):
                    ok = False
            # re-clip as a check: anything outside the mandrel means a trim
            # went wrong, so fall back to the clean clipped tube
            if not _tbm_op(tbm, c, _env(tbm, R, z_lo, z_hi), I) or not _inside(c, R):
                c, ok = clipped, False
            if not ok:
                note('{} trim {}'.format(name, i + 1))
            want = 1 + sum(1 for s_ in boxes[i] if s_[0] != 'ring')
            got_ = _lumps(c)
            if got_ != want:
                diag.append('{} path {}: {} piece(s), expected {} (after clip {})'.format(
                    name, i + 1, got_, want, n_clip))
            pieces.append(c)
        prog.progressValue = i + 1
        if i % 5 == 4:
            adsk.doEvents()
    prog.message = 'Joining ' + name + '…'
    adsk.doEvents()
    for f in feats_made:
        try:
            f.deleteMe()          # drop the pipe from the timeline outright
        except Exception:
            for b in f.bodies:
                _discard(comp, b)
    n_in = sum(max(0, _lumps(c)) for c in pieces)
    u, left = _union_tree(tbm, pieces)
    prog.hide()
    if u is None:
        return None
    n_out = _lumps(u) + sum(max(0, _lumps(b)) for b in left)
    diag.append('{}: {} pieces in, {} after union ({} body/bodies)'.format(
        name, n_in, n_out, 1 + len(left)))
    if keep == 'tbm':
        return [u] + left            # caller places them
    bodies = [_add_temp_body(comp, u, name, parametric)]
    for b in left:
        bodies.append(_add_temp_body(comp, b, name, parametric))
    if left:
        note('{}: {} piece(s) kept as separate bodies'.format(name, len(left)))
    _combine(comp, _jig_body(comp), bodies, CUT, keep=keep, stage='Groove cut ' + name)
    return bodies[0] if keep else None


def _union_tree(tbm, bodies):
    """Union temporary bodies pairwise (much faster than one by one).

    booleanOperation reports failure by returning False rather than raising;
    a failed pair's second body goes to `left` instead of being lost.
    Returns (union, left)."""
    U = adsk.fusion.BooleanTypes.UnionBooleanType
    left = []
    while len(bodies) > 1:
        nxt = []
        for i in range(0, len(bodies) - 1, 2):
            ok = False
            try:
                ok = tbm.booleanOperation(bodies[i], bodies[i + 1], U)
            except Exception:
                ok = False
            nxt.append(bodies[i])
            if not ok:
                left.append(bodies[i + 1])
        if len(bodies) % 2:
            nxt.append(bodies[-1])
        bodies = nxt
        adsk.doEvents()
    main = bodies[0] if bodies else None
    # second chance: retry leftovers one at a time
    still = []
    for b in left:
        ok = False
        if main is not None:
            try:
                ok = tbm.booleanOperation(main, b, U)
            except Exception:
                ok = False
        if not ok:
            still.append(b)
    return main, still


def _make_fill(comp, tools, name, R, z_lo, z_hi, leadin_tools, parametric):
    """Flush fill from groove tool bodies, built in memory: each tube trimmed
    to the mandrel cylinder (minus any cleat lead-in), then all unioned.
    Pieces that refuse to union are kept as extra bodies with the same name
    (the Bambu export merges same-named bodies into one STL)."""
    tbm = adsk.fusion.TemporaryBRepManager.get()
    I = adsk.fusion.BooleanTypes.IntersectionBooleanType
    D = adsk.fusion.BooleanTypes.DifferenceBooleanType
    pieces = []
    for t in tools:
        c = tbm.copy(t)
        env = tbm.createCylinderOrCone(_pt(0, 0, z_lo), R, _pt(0, 0, z_hi), R)
        try:
            if not tbm.booleanOperation(c, env, I):
                note('Trim ' + t.name)
        except Exception:
            note('Trim ' + t.name)
        for lt in leadin_tools or ():
            try:
                tbm.booleanOperation(c, tbm.copy(lt), D)
            except Exception:
                pass
        try:
            if c.volume <= 1e-9:
                continue
        except Exception:
            pass
        pieces.append(c)
    u, left = _union_tree(tbm, pieces)
    if u is None:
        return None
    body = _add_temp_body(comp, u, name, parametric)
    for b in left:
        _add_temp_body(comp, b, name, parametric)
    if left:
        note('{}: {} piece(s) kept as separate bodies'.format(name, len(left)))
    return body


def _plane_at(comp, z):
    ci = comp.constructionPlanes.createInput()
    ci.setByOffset(comp.xYConstructionPlane, adsk.core.ValueInput.createByReal(z))
    pl = comp.constructionPlanes.add(ci)
    pl.isLightBulbOn = False
    return pl


def _cyl_face(body, r, z_lo, z_hi):
    """The cylindrical face of `body` with radius r lying between z_lo..z_hi."""
    best = None
    for f in body.faces:
        g = f.geometry
        if g.surfaceType != adsk.core.SurfaceTypes.CylinderSurfaceType:
            continue
        if abs(g.radius - r) > 1e-3:
            continue
        bb = f.boundingBox
        if bb.minPoint.z > z_lo - 1e-3 and bb.maxPoint.z < z_hi + 1e-3:
            best = f
    return best


def _helix_pipe(comp, r, z0, z1, rope, name):
    """Round-section thread body: a pipe of radius `rope` along a helix of
    radius r and THREAD_PITCH from z0 to z1 (starting at angle 0, so the
    spigot thread and the lid groove share one helix)."""
    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = name + ' helix'
    sk.isComputeDeferred = True
    turns = (z1 - z0) / THREAD_PITCH
    n = max(8, int(math.ceil(turns * 36)))
    coll = adsk.core.ObjectCollection.create()
    for i in range(n + 1):
        t = turns * i / n
        a = 2 * math.pi * t
        coll.add(_pt(r * math.cos(a), r * math.sin(a), z0 + THREAD_PITCH * t))
    sp = sk.sketchCurves.sketchFittedSplines.add(coll)
    sk.isComputeDeferred = False
    sk.isVisible = False
    feats = comp.features
    pi = feats.pipeFeatures.createInput(feats.createPath(sp, False), NEW)
    pi.sectionSize = adsk.core.ValueInput.createByReal(2 * rope)
    body = feats.pipeFeatures.add(pi).bodies.item(0)
    body.name = name
    return body


def _build_lid(comp, p, R, H, L, B, z0, parametric):
    """Threaded spigot + screw-on lid, pin storage cavity, and per-cord
    lead-in grooves ending in clamp notches under the lid.
    Returns the lead-in tool bodies (kept for trimming the outline fills)."""
    feats = comp.features
    VR = adsk.core.ValueInput.createByReal
    OPS = adsk.fusion.FeatureOperations
    zs = lid_split(p, R, H, L, B, z0)
    Lt = p['thread_len']
    cd = p['cord_d']
    d_crest, _ = lid_thread(p)
    clr = max(0.0, p.get('thread_clearance', 0.0))
    rs = d_crest / 2.0 - THREAD_DEPTH            # spigot core
    r_bore = rs + clr                            # lid bore
    r_helix = rs + THREAD_DEPTH - THREAD_ROPE    # centre of the round thread
    plane = _plane_at(comp, zs)
    # spigot (part of the jig)
    sk = comp.sketches.add(plane)
    sk.name = 'Spigot'
    sp = feats.extrudeFeatures.addSimple(_ring_profile(sk, rs, p['bore']), VR(Lt),
                                         OPS.NewBodyFeatureOperation).bodies.item(0)
    sp.name = 'Spigot'
    sk.isVisible = False
    # an extrude 'join' that only touches the jig on a face can come out as a
    # separate body, so join explicitly
    if not _combine(comp, _jig_body(comp), [sp], JOIN, keep=False, stage='Join spigot'):
        raise RuntimeError('spigot could not be joined to the jig')
    # lid (separate body)
    sk = comp.sketches.add(plane)
    sk.name = 'Lid'
    lid_ext = feats.extrudeFeatures.addSimple(_ring_profile(sk, R, 0), VR(Lt + LID_CAP),
                                              OPS.NewBodyFeatureOperation)
    lid = lid_ext.bodies.item(0)
    lid.name = 'Lid'
    sk.isVisible = False
    sk = comp.sketches.add(plane)
    sk.name = 'Lid bore'
    bi = feats.extrudeFeatures.createInput(_ring_profile(sk, r_bore, 0), OPS.CutFeatureOperation)
    bi.setDistanceExtent(False, VR(Lt))
    bi.participantBodies = [lid]
    feats.extrudeFeatures.add(bi)
    sk.isVisible = False
    lid = comp.bRepBodies.itemByName('Lid')
    if p['chamfer'] > 0:
        try:
            edges = adsk.core.ObjectCollection.create()
            for f in lid.faces:
                if (f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
                        and f.boundingBox.minPoint.z > zs + Lt + LID_CAP - 1e-3):
                    for e in f.edges:
                        edges.add(e)
            ci = feats.chamferFeatures.createInput2()
            ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, VR(p['chamfer']), False)
            feats.chamferFeatures.add(ci)
        except Exception:
            note('Lid chamfer')

    # thread lead-ins: chamfer the spigot's top outer edge and the mouth of
    # the lid bore so the lid starts easily
    lead = min(0.05, Lt / 6.0)

    def _circle_edges(body, r, z):
        out = adsk.core.ObjectCollection.create()
        for e in body.edges:
            g = e.geometry
            if (g.curveType == adsk.core.Curve3DTypes.Circle3DCurveType
                    and abs(g.radius - r) < 1e-3 and abs(g.center.z - z) < 1e-3):
                out.add(e)
        return out
    for body, r, z, stage in ((_jig_body(comp), rs, zs + Lt, 'Spigot thread lead-in'),
                              (comp.bRepBodies.itemByName('Lid'), r_bore, zs, 'Lid thread lead-in')):
        try:
            edges = _circle_edges(body, r, z)
            if edges.count:
                ci = feats.chamferFeatures.createInput2()
                ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(edges, VR(lead), False)
                feats.chamferFeatures.add(ci)
        except Exception:
            note(stage)

    # threads: one round-profile helix, raised on the spigot and cut (with
    # clearance) into the lid. The lid groove runs a turn past the lid's mouth
    # so the spigot thread can enter it.
    end = THREAD_ROPE + 0.02
    try:
        t = _helix_pipe(comp, r_helix, zs + end, zs + Lt - end, THREAD_ROPE, 'Spigot thread')
        if not _combine(comp, _jig_body(comp), [t], JOIN, keep=False, stage='Spigot thread'):
            note('Spigot thread join')
    except Exception:
        note('Spigot thread')
    try:
        g = _helix_pipe(comp, r_helix, zs + end - THREAD_PITCH, zs + Lt - end + 0.01,
                        THREAD_ROPE + clr, 'Lid thread groove')
        _combine(comp, comp.bRepBodies.itemByName('Lid'), [g], CUT, keep=False,
                 stage='Lid thread groove')
    except Exception:
        note('Lid thread groove')

    # pin storage cavity, down through the spigot into the mandrel core
    rc = cavity_radius(p)
    depth = storage_depth(p, R, H, L, B, z0)
    if rc > 0 and depth > 0 and p.get('storage', True):
        try:
            sk = comp.sketches.add(_plane_at(comp, zs + Lt))
            sk.name = 'Pin storage'
            ci = feats.extrudeFeatures.createInput(_ring_profile(sk, rc, 0), OPS.CutFeatureOperation)
            ci.setDistanceExtent(False, VR(-depth))
            ci.participantBodies = [_jig_body(comp)]
            feats.extrudeFeatures.add(ci)
            sk.isVisible = False
        except Exception:
            note('Pin storage cavity')

    # One clamp notch per cord, where that cord's first descending strand, run
    # on up past its top bight, meets the shoulder, so the cord lies straight
    # from its notch down into its lane. Each is a vertical slot with a round
    # floor, from the axis out (into the storage cavity) and up through the
    # spigot, so the cords drop in from the top and the lid clamps them on
    # the shoulder.
    bands = lane_layout(p)[3]
    lanes = [b[1] for b in bands] if bands else [0.0]
    tools = []
    try:
        if passes_of(p) >= 2:
            a_base = cleat_alignment(p, R, H, L, B, z0, offset=0.0, z_exit=zs)[0]
            angles = [a_base + du / R for du in fan_shifts(p, R, H, L, B).values()]
        else:
            angles = [cleat_alignment(p, R, H, L, B, z0, offset=o, z_exit=zs)[0]
                      for o in lanes]
        width = cd * 1.1
        rw = width / 2.0
        depth_notch = cd * (1.0 - CLAMP_SQUEEZE)         # lid squeezes the cords
        zc = zs - depth_notch + rw                       # centre of the round floor
        z_hi = zs + Lt + 0.1
        r_out = R + 0.1
        tbm = adsk.fusion.TemporaryBRepManager.get()
        U = adsk.fusion.BooleanTypes.UnionBooleanType
        parts = []
        for th in angles:
            c, s_ = math.cos(th), math.sin(th)
            floor = tbm.createCylinderOrCone(_pt(0, 0, zc), rw, _pt(r_out * c, r_out * s_, zc), rw)
            mid = r_out / 2.0
            box = adsk.core.OrientedBoundingBox3D.create(
                _pt(mid * c, mid * s_, (zc + z_hi) / 2.0), adsk.core.Vector3D.create(c, s_, 0),
                adsk.core.Vector3D.create(-s_, c, 0), r_out, width, z_hi - zc)
            tbm.booleanOperation(floor, tbm.createBox(box), U)
            parts.append(floor)
        if len(angles) > 1:
            # clear the spigot between the outer notches: the narrow stubs of
            # spigot left between neighbouring slots would just snap off
            a0 = angles[0]
            rel = [math.atan2(math.sin(a - a0), math.cos(a - a0)) for a in angles]
            r_cut = d_crest / 2.0 + clr + 0.05
            pad = math.asin(min(1.0, rw / max(rs - 0.3, rw)))
            lo, hi = a0 + min(rel) - pad, a0 + max(rel) + pad
            S = 2 * R + 1.0
            sector = tbm.createCylinderOrCone(_pt(0, 0, zs), r_cut, _pt(0, 0, z_hi), r_cut)
            I = adsk.fusion.BooleanTypes.IntersectionBooleanType
            for ang, side in ((lo, 1.0), (hi, -1.0)):
                n = (-math.sin(ang) * side, math.cos(ang) * side)
                half = adsk.core.OrientedBoundingBox3D.create(
                    _pt(n[0] * S / 2.0, n[1] * S / 2.0, (zs + z_hi) / 2.0),
                    adsk.core.Vector3D.create(math.cos(ang), math.sin(ang), 0),
                    adsk.core.Vector3D.create(n[0], n[1], 0), 2 * S, S, z_hi - zs + 0.2)
                tbm.booleanOperation(sector, tbm.createBox(half), I)
            parts.append(sector)
        tool, left = _union_tree(tbm, parts)
        nbs = [_add_temp_body(comp, b_, 'Notch tool', parametric) for b_ in [tool] + left]
        _combine(comp, _jig_body(comp), nbs, CUT, keep=False, stage='Clamp notches')
    except Exception:
        note('Clamp notches')
    _scallop_lid(comp, R, d_crest / 2.0 + clr, zs, zs + Lt + LID_CAP, parametric)
    _place_lid(comp, zs + Lt + LID_CAP, R)
    return tools


def _engrave_numbers(comp, R, h, spots, depth, parametric=True):
    """Pass numbers / start labels as inlays in their cord's colour: each
    label is sketched once on a tangent plane, extruded, copied into memory,
    rotated into place and trimmed flush with the mandrel; the jig is cut with
    all of them and each colour's labels are added to that cord's component
    ('A1', '2'.. -> Cord A, 'B1' -> Cord B, ...). Without colour components
    they are just engraved."""
    feats = comp.features
    VR = adsk.core.ValueInput.createByReal
    tbm = adsk.fusion.TemporaryBRepManager.get()
    U = adsk.fusion.BooleanTypes.UnionBooleanType
    I = adsk.fusion.BooleanTypes.IntersectionBooleanType
    pi_ = comp.constructionPlanes.createInput()
    pi_.setByOffset(comp.yZConstructionPlane, VR(R + 0.05))
    plane = comp.constructionPlanes.add(pi_)
    plane.isLightBulbOn = False
    Z = adsk.core.Vector3D.create(0, 0, 1)
    groups = {}
    for text, u, z in spots:
        letter = text[0] if text[0].isalpha() else 'A'
        try:
            sk = comp.sketches.add(plane)
            xd, yd = sk.xDirection, sk.yDirection
            nrm = xd.crossProduct(yd)
            ang = math.atan2(Z.dotProduct(yd), Z.dotProduct(xd)) - math.pi / 2.0
            w = 0.72 * h * len(text)
            pos = sk.modelToSketchSpace(_pt(R + 0.05, -w / 2.0, z - h / 2.0))
            ti = sk.sketchTexts.createInput(text, h, pos)
            ti.angle = ang
            try:
                ti.textStyle = adsk.fusion.TextStyles.TextStyleBold
            except Exception:
                pass
            try:
                if nrm.x < 0:
                    ti.isHorizontalFlip = True
            except Exception:
                pass
            st = sk.sketchTexts.add(ti)
            ei = feats.extrudeFeatures.createInput(st, NEW)
            ei.setDistanceExtent(False, VR(-(depth + 0.05) if nrm.x > 0 else (depth + 0.05)))
            f = feats.extrudeFeatures.add(ei)
            m = adsk.core.Matrix3D.create()
            m.setToRotation(u / R, Z, _pt(0, 0, 0))
            for b in f.bodies:
                c = tbm.copy(b)
                tbm.transform(c, m)
                env = tbm.createCylinderOrCone(_pt(0, 0, z - 1.0), R, _pt(0, 0, z + 1.0), R)
                _tbm_op(tbm, c, env, I)          # flush with the surface
                groups.setdefault(letter, []).append(c)
            try:
                f.deleteMe()
                sk.deleteMe()
            except Exception:
                sk.isVisible = False
        except Exception:
            note('Pass number ' + text)
    if not groups:
        return
    all_ = []
    for letter, bodies in groups.items():
        u_, left = _union_tree(tbm, [tbm.copy(b) for b in bodies])
        all_ += [u_] + left
        target = None
        for o in comp.occurrences:
            # component names are unique per document, so a second jig's
            # gets 'Cord A (1)'
            if re.sub(r' \(\d+\)$', '', o.component.name) in ('Cord ' + letter, 'Cord'):
                target = o.component
        if target is not None:
            for b in [u_] + left:
                _add_temp_body(target, tbm.copy(b), re.sub(r' \(\d+\)$', '', target.name),
                               parametric)
    tools = [_add_temp_body(comp, b, 'Number tool', parametric) for b in all_]
    _combine(comp, _jig_body(comp), tools, CUT, keep=False, stage='Pass numbers')


def _lift(comp, dz):
    """Move every body up by dz, so the handle's end sits on the XY plane."""
    try:
        coll = adsk.core.ObjectCollection.create()
        for b in comp.bRepBodies:
            coll.add(b)
        if coll.count == 0:
            return
        m = adsk.core.Matrix3D.create()
        m.translation = adsk.core.Vector3D.create(0, 0, dz)
        mf = comp.features.moveFeatures
        try:
            mi = mf.createInput2(coll)
            mi.defineAsFreeMove(m)
        except Exception:
            mi = mf.createInput(coll, m)
        mf.add(mi)
    except Exception:
        note('Move jig onto the XY plane')
    # inlays already sit in sub-components: move those occurrences too
    for o in comp.occurrences:
        try:
            m = o.transform2
            m.translation = adsk.core.Vector3D.create(m.translation.x, m.translation.y,
                                                      m.translation.z + dz)
            o.transform2 = m
        except Exception:
            note('Move {} onto the XY plane'.format(o.component.name))


def _scallop_lid(comp, R, r_thread, z_lo, z_hi, parametric):
    """Vertical scallops round the lid for grip."""
    try:
        depth = min(0.09, (R - r_thread) / 3.0)
        if depth < 0.03:
            return
        rf = 0.15                                   # flute radius
        n = max(8, int(round(2 * math.pi * R / 0.7)))
        rc = R + rf - depth
        tbm = adsk.fusion.TemporaryBRepManager.get()
        flutes = []
        for i in range(n):
            a = 2 * math.pi * i / n
            x, y = rc * math.cos(a), rc * math.sin(a)
            flutes.append(tbm.createCylinderOrCone(_pt(x, y, z_lo - 0.1), rf,
                                                   _pt(x, y, z_hi + 0.1), rf))
        u, left = _union_tree(tbm, flutes)
        tools = [_add_temp_body(comp, b, 'Lid scallops', parametric) for b in [u] + left]
        _combine(comp, comp.bRepBodies.itemByName('Lid'), tools, CUT, keep=False,
                 stage='Lid scallops')
    except Exception:
        note('Lid scallops')


def _split_components(comp):
    """Move each part (jig, lid, each cord colour) into its own
    sub-component, so component colour cycling tells them apart."""
    # the jig body itself stays in the parent component (moving the big body
    # is the slow part); the parent gets its own colour anyway
    order = ('Lid', 'Cord') + tuple('Cord ' + chr(ord('A') + i) for i in range(8))
    groups = {}
    for b in list(comp.bRepBodies):
        base = re.sub(r' \(\d+\)$', '', b.name)   # Fusion renames duplicates 'X (1)'
        if base in order and b.isSolid:
            groups.setdefault(base, []).append(b)
    for name in order:
        if name not in groups:
            continue
        try:
            sub = comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
            sub.component.name = name
            for b in groups[name]:
                b.moveToComponent(sub)
            lap('component ' + name)
        except Exception:
            note('Move {} to its own component'.format(name))


LID_SPACING = 1.0   # cm between jig and the laid-out lid


def _place_lid(comp, z_top, R):
    """Lay the lid out for printing: flipped top-down, standing on the same
    plane as the bottom of the jig, beside it."""
    try:
        lid = comp.bRepBodies.itemByName('Lid')
        bb = _jig_body(comp).boundingBox
        m = adsk.core.Matrix3D.create()
        m.setToRotation(math.pi, adsk.core.Vector3D.create(1, 0, 0), _pt(0, 0, 0))
        m.translation = adsk.core.Vector3D.create(bb.maxPoint.x + LID_SPACING + R, 0,
                                                  bb.minPoint.z + z_top)
        coll = adsk.core.ObjectCollection.create()
        coll.add(lid)
        mf = comp.features.moveFeatures
        try:
            mi = mf.createInput2(coll)
            mi.defineAsFreeMove(m)
        except Exception:
            mi = mf.createInput(coll, m)
        mf.add(mi)
    except Exception:
        note('Place lid beside jig')


def build(p, transform=None):
    del errors[:]
    del diag[:]
    design = adsk.fusion.Design.cast(_app.activeProduct)
    if not design:
        _app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(_app.activeProduct)

    parametric = design.designType == adsk.fusion.DesignTypes.ParametricDesignType
    tl_start = design.timeline.markerPosition if parametric else None

    R = p['dia'] / 2.0
    H = p['span']
    Lz = p['length']
    L, B = p['leads'], p['bights']
    z0 = (Lz - H) / 2.0

    root = design.rootComponent
    occ = root.occurrences.addNewComponent(transform or adsk.core.Matrix3D.create())
    comp = occ.component
    comp.name = "{} Jig {}L {}B".format(dict(KNOT_STYLES).get(p.get('style'), "Turk's head"), L, B)
    occ.isLightBulbOn = False  # skip viewport redraws while building
    global _building_occ
    _building_occ = occ
    feats = comp.features

    # --- mandrel (z 0..Lz), cleat section (z Lz..Lz+cl), handle (z -hl..0)
    mode = top_mode(p)
    if mode == 'cleat':
        cl = cleat_top(p, R, H, L, B, z0) - Lz
    elif mode == 'lid':
        cl = lid_split(p, R, H, L, B, z0) - Lz    # jig body stops at the shoulder
    else:
        cl = 0.0
    hl = p['handle_len']
    rh = (p['handle_dia'] if p['handle_dia'] > 0 else p['dia']) / 2.0
    VR = adsk.core.ValueInput.createByReal
    OPS = adsk.fusion.FeatureOperations

    sk = comp.sketches.add(comp.xYConstructionPlane)
    sk.name = 'Mandrel'
    same = hl > 0 and abs(rh - R) < 1e-6
    ei = feats.extrudeFeatures.createInput(_ring_profile(sk, R, p['bore']), NEW)
    if same:
        # handle the same size as the mandrel: one solid from -hl up
        ei.setTwoSidesDistanceExtent(VR(Lz + cl), VR(hl))
    else:
        ei.setDistanceExtent(False, VR(Lz + cl))
    ext = feats.extrudeFeatures.add(ei)
    ext.bodies.item(0).name = 'Jig'
    sk.isVisible = False
    if hl > 0 and not same:
        hsk = comp.sketches.add(comp.xYConstructionPlane)
        hsk.name = 'Handle'
        hb = feats.extrudeFeatures.addSimple(
            _ring_profile(hsk, rh, p['bore']), VR(-hl), NEW).bodies.item(0)
        hb.name = 'Handle'
        hsk.isVisible = False
        # a join extrude that only touches on a face can stay a separate
        # body, so join explicitly
        if not _combine(comp, _jig_body(comp), [hb], JOIN, keep=False, stage='Join handle'):
            note('Handle is a separate body')
    jb = _jig_body(comp)
    z_ends = (jb.boundingBox.minPoint.z, jb.boundingBox.maxPoint.z)
    end_faces = [[f for f in jb.faces
                  if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType
                  and any(abs(f.boundingBox.minPoint.z - z) < 1e-4
                          and abs(f.boundingBox.maxPoint.z - z) < 1e-4 for z in z_ends)]]

    if p['chamfer'] > 0:
        try:
            edges = adsk.core.ObjectCollection.create()
            for faces in end_faces:
                for f in faces:
                    for e in f.edges:
                        edges.add(e)
            ci = feats.chamferFeatures.createInput2()
            ci.chamferEdgeSets.addEqualDistanceChamferEdgeSet(
                edges, VR(p['chamfer']), False)
            feats.chamferFeatures.add(ci)
        except Exception:
            note('End chamfer')

    leadin_tools = []
    if mode == 'lid':
        try:
            lap('mandrel')
            leadin_tools = _build_lid(comp, p, R, H, L, B, z0, parametric)
            lap('lid + threads')
        except Exception:
            note('Screw-on lid')
    # --- jam cleat: tapered slot across the top end. Cord pressed into the
    # narrowing slot wedges tight.
    if mode == 'cleat':
        try:
            cd = p['cord_d']
            top = cleat_top(p, R, H, L, B, z0)
            wt, wb = cd * CLEAT_TOP_RATIO / 2.0, cd * CLEAT_BOTTOM_RATIO / 2.0
            # turn the slot so the cord leaves it along the first strand
            phi = 0.0
            lead = None
            if p.get('cleat_align', True):
                _bands = lane_layout(p)[3]
                th_e, z_e, lead = cleat_alignment(
                    p, R, H, L, B, z0, offset=_bands[0][1] if _bands else 0.0)
                phi = th_e - math.pi / 2.0   # slot runs along theta = 90 deg before turning
            plane = _slot_plane(comp, phi)
            csk = comp.sketches.add(plane)
            csk.name = 'Jam cleat'
            m2s = csk.modelToSketchSpace
            outline = cleat_outline(wt, wb, top, p['cleat_depth'], cd, p['cleat_ridges'])
            cph, sph = math.cos(phi), math.sin(phi)
            pts = [m2s(_pt(x * cph, x * sph, z)) for x, z in outline]
            csk.isComputeDeferred = True
            lines = csk.sketchCurves.sketchLines
            for i in range(len(pts)):
                lines.addByTwoPoints(pts[i], pts[(i + 1) % len(pts)])
            csk.isComputeDeferred = False
            ei = feats.extrudeFeatures.createInput(
                csk.profiles.item(0), OPS.CutFeatureOperation)
            ei.setSymmetricExtent(VR(R + 0.2), False)  # each side
            ei.participantBodies = [_jig_body(comp)]
            feats.extrudeFeatures.add(ei)
            csk.isVisible = False
        except Exception:
            note('Jam cleat')
        # lead-in channel from the slot down to the start of the first strand
        if mode == 'cleat' and p.get('cleat_align', True) and p.get('cleat_leadin', True) and lead:
            try:
                depth = p['cord_d'] * LEADIN_DEPTH_RATIO
                pts3 = to_3d(R, [[(q, depth) for q in lead]], p['cord_d'] / 2.0)[0]
                lsk = comp.sketches.add(comp.xYConstructionPlane)
                lsk.name = 'Cleat lead-in'
                coll = adsk.core.ObjectCollection.create()
                for x, y, z in pts3:
                    coll.add(_pt(x, y, z))
                spl = lsk.sketchCurves.sketchFittedSplines.add(coll)
                lsk.isVisible = False
                pi_ = feats.pipeFeatures.createInput(feats.createPath(spl, False), NEW)
                pi_.sectionSize = VR(p['cord_d'])
                leadin_tool = feats.pipeFeatures.add(pi_).bodies.item(0)
                leadin_tool.name = 'Lead-in tool'
                _combine(comp, _jig_body(comp), [leadin_tool], CUT, keep=True,
                         stage='Cleat lead-in cut')
                leadin_tools.append(leadin_tool)
            except Exception:
                note('Cleat lead-in channel')

    lap('before lanes')
    # --- lane marks: solid cord paths or lane outlines
    if p['engrave']:
        rho = bight_rho(p, R, H, L, B)
        W, offsets, types, bands = lane_layout(p)
        fan = p.get('style') == 'fan'
        solid = mark_style(p) == 'solid'
        if solid:
            # tubes of radius r centred on the surface, side by side across
            # each lane; ends stop short of the lane passing over
            r = fill_radius(p)
            depth = fill_depth(p)
            offsets, types = fill_offsets(p)
            gap, end_r = 2.5 * PIN_CLEARANCE, r
            labels = ('Cord', 'Cord A', 'Cord B')
        else:
            r = p['line_w'] / 2.0
            depth = p['line_d']
            gap, end_r = p['line_w'] + PIN_CLEARANCE, 0.0  # clear the crossing outline
            labels = ('Cord outline', 'Cord A outline', 'Cord B outline')

        def paths_for(offs, tys):
            # outlines: gaucho lanes keep the older concentric bights
            return knot_paths(R, H, z0, L, B, offs, rho, depth, p['over_under'],
                              band_h=W / 2.0, cord_code=cord_code_of(p), weave=row_weave_of(p), line_types=tys,
                              bands=bands, fan=fan, end_gap=gap, end_r=end_r)

        def to3(pieces):
            return to_3d(R, pieces if solid else u_layers(pieces, r), r)

        fan = passes_of(p) >= 2
        shifts = fan_shifts(p, R, H, L, B) if fan else None
        rho_l = lane_rho(p) if fan else rho
        grid = (passes_of(p), grid_code(p)) if fan else None
        if solid:
            env = (R, -p['handle_len'] - 1.0, Lz + 5.0, parametric)
            tbm_ = adsk.fusion.TemporaryBRepManager.get()
            DIFF = adsk.fusion.BooleanTypes.DifferenceBooleanType
            pin_tbm = _pin_tool_tbm(p, R, H, z0, L, B)
            groove_tools, sub_occs = [], []
            colour = p.get('colour_bodies', True)
            groups = sorted(set(types)) if (colour or fan) else [None]
            for t in groups:
                idx = [i for i, x in enumerate(types) if t is None or x == t]
                r_t, depth_t = r, depth
                if fan and not colour and t != 'c0':
                    # one-colour print: colour B is a narrow centre groove,
                    # colour A the full-width recess, so they read apart
                    idx, r_t = [idx[len(idx) // 2]], min(0.06, r)
                    depth_t = r_t
                    offsets = list(offsets)
                    offsets[idx[0]] = 0.0
                res = knot_paths(R, H, z0, L, B, [offsets[i] for i in idx], rho_l, depth_t,
                                 p['over_under'], band_h=W / 2.0, cord_code=cord_code_of(p),
                                 weave=row_weave_of(p),
                                 line_types=[types[i] for i in idx], bands=bands, fan=fan,
                                 end_gap=gap, boxes=True, shift_of=shifts, grid=grid)
                paths = to_3d(R, [extend_ends(pts, 0.3 * r_t) for pts, _ in res], r_t)
                bx = [[box_to_3d(R, b, depth) for b in bb] for _, bb in res]
                name = ('Lane grooves' if t is None else labels[0] if len(groups) == 1
                        else 'Cord ' + lane_letter(t))
                if not colour:
                    name = 'Lane grooves ' + lane_letter(t) if t else 'Lane grooves'
                got = _engrave_solid(comp, paths, bx, r_t, name, *env, keep='tbm') or []
                groove_tools += [tbm_.copy(g) for g in got]
                if colour and t is not None and got:
                    # the inlay goes straight into its own sub-component (far
                    # faster than moving it there afterwards); pin holes are
                    # cut in memory
                    if pin_tbm is not None:
                        for g in got:
                            n0 = _lumps(g)
                            okp = _tbm_op(tbm_, g, tbm_.copy(pin_tbm), DIFF)
                            diag.append('{}: pin holes {} -> {} pieces{}'.format(
                                name, n0, _lumps(g), '' if okp else ' (FAILED)'))
                    sub = comp.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                    sub.component.name = name
                    for g in got:
                        _add_temp_body(sub.component, g, name, parametric)
                    sub_occs.append(sub)
            # one groove cut for every lane
            # (each colour is already one unioned body; joining the colours
            # too can fail and silently drop pieces, leaving inlays uncut)
            if groove_tools:
                tb = [_add_temp_body(comp, b, 'Groove tool', parametric) for b in groove_tools]
                if not _combine(comp, _jig_body(comp), tb, CUT, keep=False, stage='Groove cut'):
                    for b in tb:
                        _combine(comp, _jig_body(comp), [b], CUT, keep=False,
                                 stage='Groove cut ' + b.name)
        elif p.get('colour_bodies', True):
            groups = sorted(set(types))
            for t in groups:
                idx = [i for i, x in enumerate(types) if x == t]
                part = paths_for([offsets[i] for i in idx], [t] * len(idx))
                name = (labels[0] if len(groups) == 1 else
                        labels[1] if t == 'b' else labels[2])
                _engrave(comp, to3(part), r, keep_name=name,
                         fill_args=(R, -p['handle_len'] - 1.0, Lz + 5.0,
                                    leadin_tools, parametric))
        else:
            _engrave(comp, to3(paths_for(offsets, types)), r)

    for t in leadin_tools:
        _discard(comp, t)

    lap('lanes')
    # --- pin holes (the inlays already had theirs cut in memory)
    tool = _pin_tool_tbm(p, R, H, z0, L, B)
    if tool is not None:
        tool_body = _add_temp_body(comp, tool, 'Pin hole tools', parametric)
        for b in list(comp.bRepBodies):
            if re.sub(r' \(\d+\)$', '', b.name).startswith('Cord'):
                _combine(comp, b, [tool_body], CUT, keep=True, stage='Pin holes in ' + b.name)
        _combine(comp, _jig_body(comp), [tool_body], CUT, keep=False, stage='Pin holes')

    lap('pin holes')
    if p.get('pass_numbers', True) and p['engrave']:
        nh, spots = pass_number_spots(p, R, H, L, B, z0)
        if spots:
            _engrave_numbers(comp, R, nh, spots, NUMBER_DEPTH, parametric)
        else:
            note('No room for pass numbers')
    if hl > 0:
        _lift(comp, hl)
    lap('numbers + lift')
    _split_components(comp)
    lap('components')
    save_params(comp, p)
    occ.isLightBulbOn = True
    if parametric:
        try:
            end = design.timeline.markerPosition - 1
            if end > tl_start:
                g = design.timeline.timelineGroups.add(tl_start, end)
                g.name = comp.name
        except Exception:
            note('Timeline group')
    return occ


def save_params(comp, p):
    data = dict(p)
    data.pop('debug', None)
    data['_version'] = PARAMS_VERSION
    comp.attributes.add(ATTR_GROUP, ATTR_NAME, json.dumps(data))


def jig_params(occ):
    """Stored settings for a jig occurrence, or None if it isn't one."""
    try:
        attrs = occ.component.attributes
        a = (attrs.itemByName(ATTR_GROUP, ATTR_NAME)
             or attrs.itemByName(LEGACY_ATTR_GROUP, ATTR_NAME))
        return json.loads(a.value) if a else None
    except Exception:
        return None


def as_occurrence(entity):
    o = adsk.fusion.Occurrence.cast(entity)
    if o:
        return o
    for attr in ('assemblyContext',):
        try:
            o = getattr(entity, attr)
            if o:
                return o
        except Exception:
            pass
    try:
        return entity.body.assemblyContext  # face / edge
    except Exception:
        return None


def jig_occurrence(entity):
    """The jig occurrence for a picked entity: the occurrence itself, or the
    nearest parent occurrence that carries jig settings (e.g. when a cord
    body in a sub-component is picked)."""
    o = as_occurrence(entity)
    while o is not None:
        if jig_params(o):
            return o
        try:
            o = o.assemblyContext
        except Exception:
            return None
    return None


def all_jigs():
    design = adsk.fusion.Design.cast(_app.activeProduct)
    if not design:
        return []
    return [o for o in design.rootComponent.allOccurrences if jig_params(o)]


def preselected_jig():
    for i in range(_ui.activeSelections.count):
        o = jig_occurrence(_ui.activeSelections.item(i).entity)
        if o:
            return o
    jigs = all_jigs()
    return jigs[0] if len(jigs) == 1 else None


def remove_jig(occ):
    """Delete a jig occurrence and its (now empty) timeline group."""
    name = occ.component.name
    occ.deleteMe()
    design = adsk.fusion.Design.cast(_app.activeProduct)
    try:
        groups = design.timeline.timelineGroups
        for i in range(groups.count - 1, -1, -1):
            g = groups.item(i)
            if g.name == name and g.count == 0:
                g.deleteMe(False)
    except Exception:
        pass


def run_build(p, edit_occ=None):
    """Build a jig from settings p. With edit_occ, replace that jig in place.
    Returns the list of non-fatal problems."""
    global _building_occ
    try:
        transform = None
        del timings[:]
        _t0[0] = 0.0
        lap('start')
        if edit_occ is not None:
            transform = edit_occ.transform2.copy()
            remove_jig(edit_occ)
            lap('remove old jig')
        build(p, transform)
        lap('finish')
    finally:
        try:
            if _building_occ:
                _building_occ.isLightBulbOn = True
        except Exception:
            pass
        _building_occ = None
    out = list(errors)
    if p.get('debug') and timings:
        out.append('Timings: ' + ', '.join('{} {:.1f}s'.format(n, t) for n, t in timings))
    if p.get('debug') and diag:
        out.append('Pieces:\n' + '\n'.join(diag))
    return out
