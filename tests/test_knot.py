"""Regression check for the shared knot geometry (lib/turksHead/knot.py).

Each case's knot_marks() output is rounded and hashed; a change in the
geometry changes the hash. Run from the repo root:

    python -m unittest discover tests          # check
    python tests/test_knot.py --update         # rewrite knot_hashes.json

Update only when a geometry change is intended."""
# pylint: disable=use-dict-literal

import hashlib
import json
import os
import sys
import unittest
from dataclasses import asdict
from unittest import mock

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'Turks Head Gaucho Generator', 'lib'))
if 'adsk' not in sys.modules:
    # the package also loads the Fusion-side modules; stub Fusion's API
    _adsk = mock.MagicMock()
    sys.modules.update({'adsk': _adsk, 'adsk.core': _adsk.core, 'adsk.fusion': _adsk.fusion})

from turksHead import geometry as G  # noqa: E402
from turksHead.knot import knot_marks, ribbon_pct_for  # noqa: E402

HASHES = os.path.join(HERE, 'knot_hashes.json')

BASE = dict(line_w=0.1, line_d=0.1, dia=4.3, length=15.0, span=15.0 - G.END_MARGIN,
            edge_rows=False, bights=6, leads=7, engrave=True, over_under=True,
            bight_holes=True, hole_mode='turn', hole_d=0.3, hole_depth=1.0,
            chamfer=0.1, bore=0.0, handle_len=0.0, handle_dia=0.0, top_mode='lid',
            thread_len=0.6, thread_clearance=0.003, storage=True, auto_size=False,
            max_height=0.0, cleat_ridges=True, cleat_align=True, cleat_leadin=True,
            cleat_depth=2.0, colour_bodies=True, pass_numbers=True, strands=2,
            colour_layout='single', mark_style='solid', cord_d=0.4, pass_gap=0.15,
            swap_lanes=True, style='fan', weave='OU', weave_custom='OU', debug=False)

CASES = {
    'fan_7L6B': {},
    'fan_7L6B_onecolour': dict(colour_bodies=False),
    'single_solid': dict(style='single', leads=5, bights=4),
    'single_outline': dict(style='single', leads=5, bights=4, mark_style='outline'),
    'single_outline_mono': dict(style='single', leads=5, bights=4, mark_style='outline',
                                colour_bodies=False),
    'single_vertex_cleat': dict(style='single', leads=5, bights=4, hole_mode='vertex',
                                top_mode='cleat'),
    'single_centre_none': dict(style='single', leads=3, bights=4, hole_mode='centre',
                               top_mode='none', handle_len=3.0),
    'single_edge_rows': dict(style='single', leads=7, bights=6, edge_rows=True),
    'herring_single': dict(style='herringbone', leads=4, bights=3),
    'herring_follow': dict(style='herringbone', leads=4, bights=3, colour_layout='follow'),
    'herring_inter3': dict(style='herringbone', leads=5, bights=4, colour_layout='interweave',
                           strands=3),
    'headhunter': dict(style='headhunter', leads=5, bights=4),
    'gaucho_oouu': dict(style='single', leads=5, bights=4, weave='OOUU'),
    'fan_3col': dict(strands=3, leads=7, bights=6, dia=6.0),
    'no_engrave': dict(engrave=False),
    'no_numbers': dict(pass_numbers=False, style='single', leads=5, bights=4),
}


def params(over):
    p = dict(BASE, **over)
    p['cleat'] = p['top_mode'] == 'cleat'
    p['ribbon_pct'] = ribbon_pct_for(p)
    return p


def _round(x):
    if isinstance(x, float):
        return round(x, 6) + 0.0   # + 0.0 folds -0.0 into 0.0
    if isinstance(x, (list, tuple)):
        return [_round(i) for i in x]
    if isinstance(x, dict):
        return {k: _round(v) for k, v in x.items()}
    return x


def digest(over):
    data = json.dumps(_round(asdict(knot_marks(params(over)))), sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


class KnotMarksTest(unittest.TestCase):
    """knot_marks() output is unchanged and well formed."""

    def test_unchanged(self):
        with open(HASHES, encoding='utf-8') as f:
            want = json.load(f)
        for name, over in CASES.items():
            with self.subTest(name):
                self.assertEqual(digest(over), want[name])

    def test_shape(self):
        m = knot_marks(params({}))
        self.assertEqual(m.style, 'solid')
        self.assertEqual([g.name for g in m.groups], ['Cord A', 'Cord B'])
        self.assertTrue(all(len(g.pieces) == len(g.boxes) for g in m.groups))
        self.assertTrue(m.pins)
        self.assertIsNone(knot_marks(params({'engrave': False})).numbers)


if __name__ == '__main__':
    if '--update' in sys.argv:
        with open(HASHES, 'w', encoding='utf-8') as fh:
            json.dump({n: digest(o) for n, o in CASES.items()}, fh, indent=1, sort_keys=True)
        print('wrote', HASHES)
    else:
        unittest.main()
