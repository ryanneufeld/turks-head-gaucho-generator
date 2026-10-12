"""5-lead x 3-bight Turk's head tied on a rod, two-colour gaucho (over 2 / under 2) weave.

Usage: python3 mkicon3.py OUTDIR
Writes OUTDIR/AddInIcon.svg and OUTDIR/{new,edit}/{16x16,32x32,64x64}[.png|@2x.png]
"""
import math, os, sys

L, B = 5, 3
ROPE, ROPE_EDGE = '#C8832E', '#3E2410'
ROPE_B = '#2F6FD6'
WEAVE = 'OOUU'
ROD, ROD_EDGE, ROD_SHADE = '#EEDDBD', '#6E5030', '#D8BE92'


def crossing_over(up, k):
    row = k if up else L - k
    f = WEAVE[(row - 1) % len(WEAVE)] == 'O'
    return f if up else not f


def cord(R, H, gap_len, n=90, phase=0.0):
    """Visible pieces of the cord centreline, projected: x across rod, y along rod.
    Back half (cos<0) and under-crossings are removed."""
    step = L * math.pi / B
    half_len = math.hypot(R * step, H)
    gs = gap_len / half_len  # gap half-width in half-pass parameter units
    pieces, cur = [], []
    for j in range(2 * B):
        up = j % 2 == 0
        if len(cur) > 1:
            pieces.append((cur, (j - 1) % 2))
        cur = []
        for i in range(n + (1 if j == 2 * B - 1 else 0)):
            s = i / n
            k = round(s * L)
            cut = 1 <= k <= L - 1 and abs(s - k / L) < gs and not crossing_over(up, k)
            th = phase + j * step + s * step
            y = (0.5 - s) * H if up else (s - 0.5) * H
            if math.cos(th) > -0.25 and not cut:
                cur.append((R * math.sin(th), y))
            elif cur:
                if len(cur) > 1:
                    pieces.append((cur, j % 2))
                cur = []
    if len(cur) > 1:
        pieces.append((cur, (2 * B - 1) % 2))
    return pieces


def svg(size, badge=False):
    small = size <= 16
    R, H, rod_len = 11.5, 36.0, 60.0
    w = 6.0 if small else (4.6 if size <= 32 else 4.0)
    ol = 1.6 if small else 1.1
    pcs = cord(R, H, (w / 2 + ol + 0.6) * 1.15, phase=0.35)
    common = 'fill="none" stroke-linecap="round" stroke-linejoin="round"'
    rod = (f'x="{-R:.2f}" y="{-rod_len/2:.2f}" width="{2*R:.2f}" height="{rod_len:.2f}" '
           f'rx="{R*0.5:.2f}"')
    parts = [f'<defs><clipPath id="rod"><rect {rod}/></clipPath></defs>',
             f'<rect {rod} fill="{ROD}"/>',
             f'<rect x="{R*0.3:.2f}" y="{-rod_len/2:.2f}" width="{R*0.55:.2f}" height="{rod_len:.2f}" '
             f'fill="{ROD_SHADE}" clip-path="url(#rod)"/>',
             '<g clip-path="url(#rod)">']
    for p, grp in pcs:
        d = 'M' + ' L'.join(f'{x:.2f},{y:.2f}' for x, y in p)
        parts.append(f'<path d="{d}" {common} stroke="{ROPE_EDGE}" stroke-width="{w + 2*ol:.2f}"/>')
        parts.append(f'<path d="{d}" {common} stroke="{(ROPE, ROPE_B)[grp]}" stroke-width="{w:.2f}"/>')
    parts.append('</g>')
    parts.append(f'<rect {rod} fill="none" stroke="{ROD_EDGE}" stroke-width="{2.4 if small else 1.6}"/>')
    g = '<g transform="translate(32,32) rotate(-45)">\n' + '\n'.join(parts) + '\n</g>'
    extra = ''
    if badge:
        extra = '''<g transform="translate(38,38)">
  <circle cx="13" cy="13" r="12.5" fill="#1F9D55" stroke="#FFFFFF" stroke-width="2"/>
  <path d="M7 19 L8.5 14.5 L16 7 L19 10 L11.5 17.5 Z" fill="#FFFFFF"/>
  <path d="M16 7 L17.5 5.5 L20.5 8.5 L19 10 Z" fill="#FFFFFF"/>
</g>'''
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
            f'viewBox="0 0 64 64">\n{g}\n{extra}\n</svg>\n')


if __name__ == '__main__':
    import cairosvg
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, 'AddInIcon.svg'), 'w').write(svg(64))
    for badge, name in ((False, 'new'), (True, 'edit')):
        d = os.path.join(out, name)
        os.makedirs(d, exist_ok=True)
        for px in (16, 32, 64):
            cairosvg.svg2png(bytestring=svg(px, badge).encode(), write_to=f'{d}/{px}x{px}.png',
                             output_width=px, output_height=px)
            if px < 64:
                cairosvg.svg2png(bytestring=svg(px * 2, badge).encode(),
                                 write_to=f'{d}/{px}x{px}@2x.png',
                                 output_width=px * 2, output_height=px * 2)
