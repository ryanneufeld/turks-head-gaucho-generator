"""Shared dialog: inputs, reading/loading settings, validation and info text."""

import math

import adsk.core
import adsk.fusion

from .geometry import *
from .builder import jig_occurrence

_app = adsk.core.Application.get()
DEBUG_DEFAULT = False


def read_inputs(inputs):
    v = lambda i: inputs.itemById(i).value
    p = {
        'line_w': v('line_w'), 'line_d': v('line_d'),
        'dia': v('dia'), 'length': v('length'),
        'span': v('length') - END_MARGIN,
        'edge_rows': v('edge_rows'),
        'bights': v('bights'), 'leads': v('leads'),
        'engrave': v('engrave'), 'over_under': v('over_under'),
        'bight_holes': v('bight_holes'),
        'hole_mode': HOLE_MODES[[n for _, n in HOLE_MODES].index(
            inputs.itemById('hole_mode').selectedItem.name)][0],
        'hole_d': v('hole_d'), 'hole_depth': v('hole_depth'),
        'chamfer': v('chamfer'), 'bore': v('bore'),
        'handle_len': v('handle_len'), 'handle_dia': v('handle_dia'),
        'top_mode': TOP_MODES[[n for _, n in TOP_MODES].index(
            inputs.itemById('top_mode').selectedItem.name)][0],
        'thread_len': v('thread_len'), 'thread_clearance': v('thread_clearance'),
        'storage': v('storage'), 'auto_size': v('auto_size'),
        'max_height': v('max_height') if inputs.itemById('max_height') else 0.0,
        'cleat_ridges': v('cleat_ridges'),
        'cleat_align': v('cleat_align'), 'cleat_leadin': v('cleat_leadin'),
        'cleat_depth': v('cleat_depth'),
        'colour_bodies': v('colour_bodies'),
        'pass_numbers': v('pass_numbers'),
        'strands': v('strands'),
        'colour_layout': (HERRING_LAYOUTS[[n for _, n in HERRING_LAYOUTS].index(
            inputs.itemById('colour_layout').selectedItem.name)][0]
            if inputs.itemById('colour_layout') else 'single'),
        'mark_style': MARK_STYLES[[n for _, n in MARK_STYLES].index(
            inputs.itemById('mark_style').selectedItem.name)][0],
        'cord_d': v('cord_d'), 'pass_gap': v('pass_gap'), 'swap_lanes': v('swap_lanes'),
        'style': KNOT_STYLES[[n for _, n in KNOT_STYLES].index(
            inputs.itemById('style').selectedItem.name)][0],
        'weave': WEAVES[[n for _, n in WEAVES].index(
            inputs.itemById('weave').selectedItem.name)][0],
        'weave_custom': inputs.itemById('weave_custom').value,
        'debug': v('debug'),
    }
    p['cleat'] = p['top_mode'] == 'cleat'
    p['ribbon_pct'] = ribbon_pct_for(p)
    return p


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


def problems(p):
    R = p['dia'] / 2.0
    L, B = p['leads'], p['bights']
    errs = []
    code = weave_of(p)
    if not knot_valid(L, B):
        errs.append('Leads and bights must share no common factor (gcd = 1); '
                    '{}L × {}B would be {} separate loops.'.format(L, B, math.gcd(L, B)))
    elif p['over_under'] and not weave_valid(code):
        errs.append('Custom weave must use only O and U, e.g. OOUU.')
    elif p['over_under'] and p.get('style') == 'herringbone' and is_grid(p):
        n_ = passes_of(p)
        if not knot_ok(p)(L, B):
            good = [l for l in range(2, 26) if knot_ok(p)(l, B)]
            errs.append('Interwoven herringbone (over 2 / under 2) does not close with {} '
                        'colours on {}L × {}B. {}'.format(
                            n_, L, B,
                            'With {} bights try {} leads.'.format(B, ', '.join(map(str, good[:6])))
                            if good else
                            'It needs an odd number of colours (3 or 5); for 2 colours use '
                            'Gaucho interweave (already over 2 / under 2) or Followed passes.'))
    elif p['over_under'] and not code_consistent(L, B, code):
        ok = consistent_leads(B, code, 2, 25)
        errs.append('This weave does not close on {}L × {}B (some crossings would need '
                    'both cords on top). With {} bights try {} leads.'.format(
                        L, B, B, ', '.join(str(x) for x in ok[:6]) or 'other'))
    if p['length'] <= END_MARGIN:
        errs.append('Mandrel length must be more than 25.4 mm.')
    elif p.get('max_height', 0) > 0 and knot_valid(L, B) \
            and print_height(p) > p['max_height'] + 1e-6:
        if p.get('auto_size'):
            hm = min_print_height(p)
            errs.append('Too tall for the {:.0f} mm print height limit: with this cord, '
                        'colours and leads the knot needs at least {} even on a much '
                        'wider mandrel (the lanes need room between rows). Use fewer '
                        'leads or thinner cord.'.format(
                            p['max_height'] * 10,
                            '{:.0f} mm'.format(hm * 10) if hm else 'more height'))
        else:
            errs.append('Jig is {:.1f} mm tall, over the {:.0f} mm print height limit: '
                        'shorten it or use automatic size.'.format(
                            print_height(p) * 10, p['max_height'] * 10))
    if p['bore'] >= p['dia']:
        errs.append('Bore must be smaller than diameter.')
    if p['handle_len'] < 0:
        errs.append('Handle length must be ≥ 0.')
    if p['handle_len'] > 0 and p['handle_dia'] > 0 and p['handle_dia'] <= p['bore'] + 0.2:
        errs.append('Handle diameter must exceed bore by at least 2 mm.')
    if p['cord_d'] <= 0:
        errs.append('Cord diameter must be > 0.')
    solid = mark_style(p) == 'solid'
    if passes_of(p) >= 2 and not solid and p['pass_gap'] < max(1.5 * p['line_w'], 0.05) - 1e-6:
        errs.append('Gap between the two cords must be at least 1.5 × line width.')
    if passes_of(p) >= 2 and p['pass_gap'] < 0:
        errs.append('Gap between the two cords must be ≥ 0.')
    if knot_valid(L, B) and p['span'] > 0 and not grid_edge_ok(p, R, p['span'], L, B):
        errs.append('Too short for {} colours: the crossings next to the bights would '
                    'fall on the bight curves. Lengthen the mandrel.'.format(passes_of(p)))
    if p['top_mode'] == 'lid':
        if lid_thread(p)[0] is None:
            errs.append('Diameter too small for a screw-on lid with this cord '
                        '(needs room for a clamp shoulder and a 12 mm thread).')
        if p['thread_len'] < 0.4:
            errs.append('Lid thread length must be at least 4 mm.')
        if p['thread_clearance'] < 0 or p['thread_clearance'] > 0.1:
            errs.append('Thread clearance must be 0–1 mm.')
    if p['cleat']:
        if p['cord_d'] * CLEAT_TOP_RATIO >= p['dia'] * 0.8:
            errs.append('Cord too thick for a cleat slot on this diameter.')
        if p['cleat_depth'] <= 0 or p['cleat_depth'] >= p['length']:
            errs.append('Cleat slot depth must be > 0 and less than mandrel length.')
    if p['engrave'] and solid and (p['line_d'] <= 0 or p['line_d'] > p['cord_d'] / 2.0 + 1e-9):
        errs.append('Depth must be > 0 and ≤ half the cord diameter.')
    if p['engrave'] and not solid and (p['line_d'] <= 0
                                       or p['line_d'] > min(3 * p['line_w'], 0.3) + 1e-9):
        errs.append('Line depth must be > 0 and ≤ 3 × line width (max 3 mm).')
    if p['engrave'] and p.get('colour_bodies') and p['line_d'] < 0.04 - 1e-9:
        errs.append('Colour marks need depth ≥ 0.4 mm or the slicer '
                    'drops them (thinner than one extrusion line).')
    if p['engrave'] and not solid and p['cord_d'] < 2 * p['line_w']:
        errs.append('Cord lane too narrow for the outline line width.')
    if knot_valid(L, B) and p['span'] > 0 and p['cord_d'] > 0:
        mx = max_ribbon_pct(p, R, p['span'], L, B)
        if p['ribbon_pct'] > mx:
            md = min_diameter(p)
            errs.append('Cord lanes too wide for this mandrel: neighbouring bights overlap. '
                        'Needs ≥ {} diameter, fewer bights, or thinner cord.'.format(
                            '{:.1f} mm'.format(md * 10) if md else 'a larger'))
        if p['ribbon_pct'] >= 90:
            errs.append('Cord lanes nearly as wide as the strand spacing; lengthen the '
                        'mandrel or use fewer leads.')
        pitch = strand_pitch(R, p['span'], L, B)
        if p['hole_mode'] == 'centre' and (pitch - band_width(p)) / 2.0 < p['hole_d'] / 2.0:
            errs.append('Openings too small for pin holes.')
    if p['hole_depth'] <= 0 or p['hole_depth'] >= R:
        errs.append('Pin hole depth must be > 0 and < radius.')
    if p['hole_d'] <= 0:
        errs.append('Pin hole diameter must be > 0.')
    if p['chamfer'] < 0 or p['chamfer'] >= (p['dia'] - p['bore']) / 2.0:
        errs.append('Chamfer too large.')
    if (knot_valid(L, B) and p['span'] > 0 and L >= 2 and passes_of(p) < 2
            and (p['bight_holes'] or p['hole_mode'] in ('turn', 'vertex'))):
        d = vertex_offset(R, p['span'], L, B, pin_clear(p, R, p['span'], L, B))
        if d >= p['span'] / L * 0.9:
            errs.append('Pins beside vertices would reach the next crossing row: '
                        'thinner cord, smaller pins, or a longer mandrel.')
    if p['cleat'] and knot_valid(L, B) and p['length'] > END_MARGIN and cleat_floor(
            p, R, p['span'], L, B, END_MARGIN / 2.0) <= END_MARGIN / 2.0:
        errs.append('Cleat slot would reach the knot.')
    return errs


def info_text(p):
    errs = problems(p)
    if errs:
        return '<b>Check:</b><br>' + '<br>'.join(errs)
    um = _app.activeProduct.unitsManager if adsk.fusion.Design.cast(_app.activeProduct) else None
    fmt = lambda x: '{:.1f} mm'.format(x * 10)
    L, B = p['leads'], p['bights']
    R = p['dia'] / 2.0
    n = passes_of(p)
    if is_follow(p):
        n_holes = 2 * B if p['bight_holes'] else 0
    elif n >= 2:
        n_holes = 2 * B * n if p['bight_holes'] else 0
    else:
        n_holes = len(pin_points(R, p['span'], 0, L, B, p['hole_mode'], p['bight_holes'],
                                 pin_clear(p, R, p['span'], L, B), p['edge_rows'], knot_ok(p)))
    top = top_end(p, R, p['span'], L, B, END_MARGIN / 2.0)
    pitch = strand_pitch(R, p['span'], L, B)
    txt = ('Overall length: {}<br>Knot span: {}<br>Crossings: {}<br>Pin holes: {}'
           '<br>Cord per pass ≈ {}'.format(
               fmt(top + p['handle_len']), fmt(p['span']),
               n * n * B * (L - 1) if is_follow(p) else n * B * (n * L - 1), n_holes,
               fmt(path_length(R, p['span'], L, B))))
    txt += '<br>Cord lanes: {} wide in {} spacing ({:.0f}% of max)'.format(
        fmt(band_width(p)), fmt(pitch),
        100.0 * p['ribbon_pct'] / max(max_ribbon_pct(p, R, p['span'], L, B), 1e-9))
    n = passes_of(p)
    if is_follow(p):
        letters = ', '.join(chr(ord('A') + i) for i in range(1, n))
        txt += ('<br>{} colours side by side. Tie colour A first (follow the numbers), '
                'then follow it with {} in turn, each in its own lane beside A, '
                'starting at the A1 bight. The whole band goes over or under '
                'together.'.format(n, letters))
    elif n >= 2:
        letters = ', '.join(chr(ord('A') + i) for i in range(1, n))
        txt += ('<br>{} colours. Tie colour A first on its bight pins (follow the '
                'numbers), then {} in turn, each from its own start label '
                '(B1, C1, …) along its own lane. Every colour has bight pins; '
                'over/under is shown by where the lanes stop.'.format(n, letters))
    if p['top_mode'] == 'lid':
        d, size = lid_thread(p)
        rc = cavity_radius(p)
        n_ = passes_of(p)
        txt += '<br>Lid: {} mm bottle-style thread ({:g} mm pitch), {}'.format(
            size, THREAD_PITCH * 10,
            'a clamp notch per cord' if n_ > 1 and not is_follow(p) else 'one clamp notch')
        sd = storage_depth(p, R, p['span'], L, B, END_MARGIN / 2.0)
        if not p['storage']:
            txt += '<br>Pin storage: off'
        else:
            txt += ('<br>Pin storage: {} dia × {} deep'.format(fmt(2 * rc), fmt(sd))
                    if rc > 0.15 and sd > 0 else '<br>Pin storage: no room')
    if p['over_under'] and not is_grid(p):
        code = weave_of(p)
        seq = ''.join(code[n % len(code)] for n in range(L - 1))
        txt += '<br>First strand from the bottom: {}'.format(' '.join(seq))
    if p['hole_mode'] == 'turn':
        txt += '<br>Shorter knots available: {} leads × {} bights'.format(
            ', '.join(str(k) for k in turnaround_leads(L, B, p['edge_rows'], knot_ok(p)))
            or 'none', B)
    return txt


def sync_visibility(ins):
    adv = ins.itemById('advanced')
    show = adv is None or adv.value
    for gid in ADV_GROUPS:
        g = ins.itemById(gid)
        if g:
            g.isVisible = show
    auto = ins.itemById('auto_size').value
    for i in ('dia', 'length'):
        ins.itemById(i).isEnabled = not auto
    hm_in, edge_in = ins.itemById('hole_mode'), ins.itemById('edge_rows')
    if hm_in and edge_in:
        # gaucho jigs only get bight pins: body pins are ignored there
        gaucho = passes_of(read_inputs(ins)) >= 2   # multi-colour: bight pins only
        hm_in.isEnabled = not gaucho
        hm = hm_in.selectedItem
        edge_in.isEnabled = not gaucho and hm is not None and hm.name in (
            HOLE_MODES[0][1], HOLE_MODES[1][1])
    eng = ins.itemById('engrave').value
    ins.itemById('pass_numbers').isEnabled = eng
    for i in ('mark_style', 'line_d', 'colour_bodies'):
        ins.itemById(i).isEnabled = eng
    ms = ins.itemById('mark_style').selectedItem
    ins.itemById('line_w').isEnabled = eng and ms is not None and ms.name == dict(MARK_STYLES)['outline']
    ou = ins.itemById('over_under').value
    ins.itemById('weave').isEnabled = ou
    sel = ins.itemById('weave').selectedItem
    ins.itemById('weave_custom').isEnabled = (
        ou and sel is not None and sel.name == dict(WEAVES)['custom'])
    st = ins.itemById('style').selectedItem
    key = {n: k for k, n in KNOT_STYLES}.get(st.name) if st else None
    cl = ins.itemById('colour_layout')
    herring = key == 'herringbone'
    cl.isVisible = herring
    layout = {n: k for k, n in HERRING_LAYOUTS}.get(cl.selectedItem.name) if cl.selectedItem else 'single'
    two = key == 'fan' or (herring and layout != 'single')
    ins.itemById('strands').isVisible = two
    ins.itemById('pass_gap').isEnabled = two
    ins.itemById('swap_lanes').isEnabled = two
    # the weave choice only applies to a plain Turk's head
    ins.itemById('weave').isEnabled = ou and key == 'single'
    ins.itemById('weave_custom').isEnabled = (
        ins.itemById('weave_custom').isEnabled and key == 'single')
    tm = ins.itemById('top_mode').selectedItem
    cleat = tm is not None and tm.name == dict(TOP_MODES)['cleat']
    lid = tm is not None and tm.name == dict(TOP_MODES)['lid']
    for i in ('cleat_depth', 'cleat_ridges', 'cleat_align'):
        ins.itemById(i).isEnabled = cleat
    ins.itemById('cleat_leadin').isEnabled = cleat and ins.itemById('cleat_align').value
    for i in ('thread_len', 'thread_clearance', 'storage'):
        ins.itemById(i).isEnabled = lid


ADV_GROUPS = ('g_size', 'g_weave', 'g_cord', 'g_ends', 'g_pins', 'g_dbg')


def add_inputs(ins):
    VI = adsk.core.ValueInput.createByString

    # --- basic: just the knot
    stl = ins.addDropDownCommandInput('style', 'Knot',
                                      adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, (_, name) in enumerate(KNOT_STYLES):
        stl.listItems.add(name, i == 1)
    cl = ins.addDropDownCommandInput('colour_layout', 'Colours',
                                     adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, (_, name) in enumerate(HERRING_LAYOUTS):
        cl.listItems.add(name, i == 0)
    ins.addIntegerSpinnerCommandInput('strands', 'Colours (cords)', 2, 6, 1, 2)
    ins.addIntegerSpinnerCommandInput('bights', 'Bights', 2, 99, 1, 6)
    ins.addIntegerSpinnerCommandInput('leads', 'Leads', 2, 99, 1, 7)
    ins.addBoolValueInput('pass_numbers', 'Number the passes (tying order)', True, '', True)
    ins.addTextBoxCommandInput('info', '', '', 8, True)
    ins.addBoolValueInput('advanced', 'Show advanced options', True, '', False)

    # --- advanced
    def group(gid, title):
        g = ins.addGroupCommandInput(gid, title)
        g.isExpanded = False
        return g.children

    g = group('g_size', 'Size')
    g.addBoolValueInput('auto_size', 'Size the mandrel automatically', True, '', True)
    g.addValueInput('dia', 'Diameter', 'mm', VI('43 mm'))
    g.addValueInput('length', 'Length (knot span = length − 25.4 mm)', 'mm', VI('150 mm'))
    g.addValueInput('max_height', 'Max print height (0 = no limit)', 'mm', VI('0 mm'))
    g.addValueInput('bore', 'Centre bore (0 = none)', 'mm', VI('0 mm'))
    g.addValueInput('chamfer', 'End chamfer', 'mm', VI('1 mm'))

    g = group('g_weave', 'Weave')
    g.addBoolValueInput('over_under', 'Show over/under', True, '', True)
    wv = g.addDropDownCommandInput('weave', 'Weave (along the cord)',
                                   adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, (_, name) in enumerate(WEAVES):
        wv.listItems.add(name, i == 0)
    g.addStringValueInput('weave_custom', 'Custom (O/U along the cord)', 'OU')

    g = group('g_cord', 'Cord and marking')
    g.addValueInput('cord_d', 'Cord diameter (550 paracord ≈ 4 mm)', 'mm', VI('4 mm'))
    g.addValueInput('pass_gap', 'Gap between the two cords', 'mm', VI('1.5 mm'))
    g.addBoolValueInput('swap_lanes', 'Swap colour A / B lanes', True, '', True)
    g.addBoolValueInput('engrave', 'Mark the cord lanes', True, '', True)
    ms = g.addDropDownCommandInput('mark_style', 'Marking',
                                   adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, (_, name) in enumerate(MARK_STYLES):
        ms.listItems.add(name, i == 0)
    g.addValueInput('line_w', 'Outline width', 'mm', VI('1.0 mm'))
    g.addValueInput('line_d', 'Depth', 'mm', VI('1.0 mm'))
    g.addBoolValueInput('colour_bodies', 'Marks as separate bodies (multi-colour print)',
                        True, '', True)

    g = group('g_ends', 'Ends')
    g.addValueInput('handle_len', 'Handle length (0 = none)', 'mm', VI('0 mm'))
    g.addValueInput('handle_dia', 'Handle diameter (0 = same)', 'mm', VI('0 mm'))
    tm = g.addDropDownCommandInput('top_mode', 'Top end',
                                   adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, (_, name) in enumerate(TOP_MODES):
        tm.listItems.add(name, i == 0)
    g.addValueInput('thread_len', 'Lid thread length', 'mm', VI('6 mm'))
    g.addValueInput('thread_clearance', 'Thread print clearance', 'mm', VI('0.03 mm'))
    g.addBoolValueInput('storage', 'Pin storage (as large as fits)', True, '', True)
    g.addValueInput('cleat_depth', 'Cleat slot depth', 'mm', VI('20 mm'))
    g.addBoolValueInput('cleat_ridges', 'Barbed slot walls', True, '', True)
    g.addBoolValueInput('cleat_align', 'Line slot up with the first strand', True, '', True)
    g.addBoolValueInput('cleat_leadin', 'Lead-in channel to the knot', True, '', True)

    g = group('g_pins', 'Pin holes')
    g.addBoolValueInput('bight_holes', 'At end bights', True, '', True)
    hm = g.addDropDownCommandInput('hole_mode', 'Body pins',
                                   adsk.core.DropDownStyles.TextListDropDownStyle)
    for i, (_, name) in enumerate(HOLE_MODES):
        hm.listItems.add(name, i == 0)
    g.addBoolValueInput('edge_rows', 'Include first/last-row turnarounds',
                        True, '', False)
    g.addValueInput('hole_d', 'Hole diameter', 'mm', VI(PIN_HOLE_DIA))
    g.addValueInput('hole_depth', 'Hole depth', 'mm', VI(PIN_HOLE_DEPTH))

    g = group('g_dbg', 'Diagnostics')
    g.addBoolValueInput('debug', 'Report skipped steps', True, '', DEBUG_DEFAULT)


# inputs whose stored value maps straight onto input.value
_PLAIN_KEYS = ('dia', 'length', 'bore', 'chamfer', 'handle_len', 'handle_dia',
               'cord_d', 'cleat_depth', 'cleat_ridges', 'cleat_align',
               'thread_len', 'thread_clearance', 'storage', 'auto_size', 'max_height',
               'cleat_leadin', 'bights', 'leads', 'pass_gap', 'swap_lanes', 'colour_bodies', 'pass_numbers', 'strands',
               'engrave', 'over_under', 'line_w', 'line_d',
               'bight_holes', 'edge_rows', 'hole_d', 'hole_depth', 'weave_custom')


def load_inputs(ins, p):
    """Fill the dialog from stored settings (missing keys keep defaults)."""
    for k in _PLAIN_KEYS:
        if k in p:
            try:
                ins.itemById(k).value = p[k]
            except Exception:
                pass
    if 'top_mode' not in p and 'leads' in p:
        p = dict(p, top_mode='cleat' if p.get('cleat') else 'none')
    if p.get('style') in LEGACY_STYLES:
        p = dict(p, style=LEGACY_STYLES[p['style']])
    if 'mark_style' not in p and 'leads' in p:
        p = dict(p, mark_style='outline')   # jigs saved before solid marking
    for key, table in (('hole_mode', HOLE_MODES), ('weave', WEAVES),
                       ('style', KNOT_STYLES), ('top_mode', TOP_MODES),
                       ('mark_style', MARK_STYLES), ('colour_layout', HERRING_LAYOUTS)):
        if key in p:
            target = dict(table).get(p[key])
            items = ins.itemById(key).listItems
            for i in range(items.count):
                if items.item(i).name == target:
                    items.item(i).isSelected = True
    if 'style' not in p and 'leads' in p:
        # jig from an older version: row-based weave, keep standard
        ins.itemById('weave').listItems.item(0).isSelected = True


def size_issue(p):
    """'dia' or 'length' if the mandrel is too small for these settings, else None."""
    if p['span'] <= 0 or not knot_valid(p['leads'], p['bights']):
        return None
    L, B = p['leads'], p['bights']
    R = p['dia'] / 2.0
    q = dict(p)
    q['ribbon_pct'] = ribbon_pct_for(q)
    if q['ribbon_pct'] > max_ribbon_pct(q, R, q['span'], L, B):
        return 'dia'
    if q['top_mode'] == 'lid' and lid_thread(q)[0] is None:
        return 'dia'
    if q['top_mode'] == 'cleat' and q['cord_d'] * CLEAT_TOP_RATIO >= q['dia'] * 0.8:
        return 'dia'
    if q['ribbon_pct'] >= 90:
        return 'length'
    if not grid_edge_ok(q, R, q['span'], L, B):
        return 'length'
    # single-cord pins sit beside the strand vertices; gaucho bight pins are
    # covered by grid_edge_ok above
    if passes_of(q) < 2 and (q['bight_holes'] or q['hole_mode'] in ('turn', 'vertex')):
        d = vertex_offset(R, q['span'], L, B, pin_clear(q, R, q['span'], L, B))
        if d >= q['span'] / L * 0.9:
            return 'length'
    return None


AUTO_DIA = 4.0      # cm: smallest automatic diameter
AUTO_LENGTH = 15.0  # cm: smallest automatic length
AUTO_MAX_DIA = 30.0


def print_height(p):
    """Height of the jig as printed (handle to spigot top; the lid prints
    separately)."""
    R = p['dia'] / 2.0
    top = top_end(p, R, p['span'], p['leads'], p['bights'], END_MARGIN / 2.0)
    if top_mode(p) == 'lid':
        top -= LID_CAP
    return top + p.get('handle_len', 0.0)


def min_print_height(p):
    """Lowest print height any automatic size can reach (widest mandrel)."""
    length = END_MARGIN + 1.0
    while length < 60:
        q = dict(p, dia=AUTO_MAX_DIA, length=length, span=length - END_MARGIN)
        q['ribbon_pct'] = ribbon_pct_for(q)
        if size_issue(q) is None:
            return print_height(q)
        length += 0.5
    return None


def autosize(ins):
    """Automatic size: the smallest diameter (>= AUTO_DIA, 1 mm steps), then
    length (>= AUTO_LENGTH, 5 mm steps), at which the knot fits. With a max
    print height the length is capped there and the diameter grows instead
    (a fatter mandrel spreads the crossings, so a shorter knot fits)."""
    p = read_inputs(ins)
    if not p.get('auto_size') or not knot_valid(p['leads'], p['bights']):
        return
    if p['over_under'] and not knot_ok(p)(p['leads'], p['bights']):
        return
    hmax = p.get('max_height', 0.0)

    def q_of(dia, length):
        q = dict(p, dia=dia, length=length, span=length - END_MARGIN)
        q['ribbon_pct'] = ribbon_pct_for(q)
        return q

    def too_tall(dia, length):
        return hmax > 0 and print_height(q_of(dia, length)) > hmax + 1e-6

    dia, length = AUTO_DIA, AUTO_LENGTH
    while too_tall(dia, length) and length - 0.5 > END_MARGIN + 1.0:
        length = round(length - 0.5, 4)
    for _ in range(3000):
        issue = size_issue(q_of(dia, length))
        if issue is None:
            break
        if issue == 'length' and not too_tall(dia, length + 0.5):
            length = round(length + 0.5, 4)
        else:
            dia = round(dia + 0.1, 4)
            if dia > AUTO_MAX_DIA:
                return
            # the taller top end of a bigger jig may push it over the limit
            while too_tall(dia, length) and length - 0.5 > END_MARGIN + 1.0:
                length = round(length - 0.5, 4)
    else:
        return
    if abs(dia - p['dia']) > 1e-9:
        ins.itemById('dia').value = dia
    if abs(length - p['length']) > 1e-9:
        ins.itemById('length').value = length


def nearest_coprime(n, other, lo=2, hi=99):
    """Closest value to n (n itself if already coprime with other, ties go
    up) that shares no factor with other."""
    for d in range(0, hi):
        for c in (n + d, n - d):
            if lo <= c <= hi and math.gcd(c, other) == 1:
                return c
    return n


def fix_gcd(ins, changed):
    """Keep leads x bights tieable: on a leads/bights edit, move the OTHER
    number to the nearest value that shares no factor with it (and, for
    herringbone, lets over-2/under-2 close). On a knot change, move leads."""
    if changed not in ('leads', 'bights', 'style', 'weave', 'weave_custom', 'over_under',
                       'strands', 'colour_layout', 'swap_lanes'):
        return
    p = read_inputs(ins)
    ok = knot_ok(p)
    if changed == 'bights':
        fixed, other = 'bights', 'leads'
    else:
        fixed, other = 'leads', 'bights'
        if changed != 'leads':
            fixed, other = 'bights', 'leads'
    a, b = ins.itemById(fixed).value, ins.itemById(other).value
    L_B = (lambda o: (o, a)) if other == 'leads' else (lambda o: (a, o))
    if ok(*L_B(b)):
        return
    for d in range(1, 98):
        for c in (b + d, b - d):
            if 2 <= c <= 99 and ok(*L_B(c)):
                ins.itemById(other).value = c
                return


_AUTO_TRIGGERS = ('leads', 'bights', 'style', 'strands', 'cord_d', 'pass_gap', 'hole_d', 'hole_mode',
                  'bight_holes', 'edge_rows', 'top_mode', 'line_w', 'engrave', 'weave', 'mark_style',
                  'weave_custom', 'over_under', 'auto_size', 'max_height')


def refresh(ins, changed=None):
    fix_gcd(ins, changed)
    if changed not in ('dia', 'length', 'info', 'advanced', 'target', 'debug'):
        try:
            autosize(ins)
        except Exception:
            pass
    sync_visibility(ins)
    ins.itemById('info').formattedText = info_text(read_inputs(ins))


def target_occ(ins):
    t = ins.itemById('target')
    if t is None or t.selectionCount == 0:
        return None
    return jig_occurrence(t.selection(0).entity)
