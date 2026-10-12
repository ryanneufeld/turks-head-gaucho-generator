// Turk's Head Gaucho Generator - OpenSCAD version
// 3D-printable jigs for Turk's head, gaucho interweave (2-6 colours),
// herringbone and headhunter's knots. Port of the Fusion add-in
// https://github.com/ryanneufeld/turks-head-gaucho-generator
//
// All sizes in mm. Use the Customizer (Window > Customizer).
//
// Multi-colour printing: export each `part` (jig, cord_A, cord_B, ...) as
// its own STL - they share coordinates - then load them together in your
// slicer as one object with several parts and give each its filament.
// Rendering is slow with the old CGAL engine: use a recent OpenSCAD build
// with the Manifold backend (Preferences > Advanced > Backend: Manifold).
//
// Licence: CC BY-NC 4.0 - https://creativecommons.org/licenses/by-nc/4.0/

/* [Knot] */
// Knot type
knot = "gaucho"; // [turkshead:Turk's head, gaucho:Gaucho interweave, herringbone:Herringbone, headhunter:Headhunter's knot]
// Number of cords / colours (gaucho only)
colours = 2; // [2:1:6]
// Bights (must share no factor with leads)
bights = 6; // [2:1:30]
// Leads
leads = 7; // [2:1:30]

/* [What to show / export] */
// all = preview with colours; export jig, lid and each cord_X as separate STLs
part = "all"; // [all, jig, lid, cord_A, cord_B, cord_C, cord_D, cord_E, cord_F]

/* [Cord] */
// Cord diameter (550 paracord about 4 mm)
cord_d = 4;
// Gap between neighbouring cords (gaucho)
cord_gap = 1.5;
// Depth of the coloured lanes
lane_depth = 1.0;
// Show over/under (lanes stop short where a cord goes under)
over_under = true;

/* [Size] */
// Diameter, 0 = automatic (smallest that fits)
diameter = 0;
// Length, 0 = automatic (knot span = length - 25.4 mm)
length = 0;
// Handle length below the knot (0 = none)
handle_len = 0;
// Handle diameter (0 = same as the jig)
handle_dia = 0;
// End chamfer
chamfer = 1;

/* [Pins] */
// Pin holes at the bights
bight_pins = true;
pin_d = 3;
pin_depth = 10;

/* [Markings] */
// Number the passes in tying order (A1, 2, 3 ... and B1, C1 start labels)
pass_numbers = true;
number_h = 5;
number_depth = 0.8;

/* [Lid] */
// Screw-on lid with pin storage
lid = true;
thread_len = 6;
thread_pitch = 2;
// Radial play between lid and spigot threads
thread_clearance = 0.3;
pin_storage = true;

/* [Quality] */
// Sphere facets for the lane tubes (more = smoother, slower)
lane_fn = 16;
// Sample spacing along the straight legs
leg_step = 3;

/* [Hidden] */
$fn = 64;
END_MARGIN = 25.4;
PIN_CLEAR = 0.2;
END_GAP = 0.5;
LID_GAP = 8;
LID_CAP = 4;
CLAMP_SQUEEZE = 0.3;
STORAGE_FLOOR = 3;
NUM_GAP = 0.8;
COLOURS = ["royalblue", "crimson", "forestgreen", "gold", "purple", "darkcyan"];
ISO = [12, 14, 16, 18, 20, 22, 24, 27, 30, 33, 36, 39, 42, 45, 48, 52, 56, 60, 64, 68, 72, 76, 80];

// ---------------------------------------------------------------- knot model
L = leads;
B = bights;
N = knot == "gaucho" ? colours : 1;
Lg = L * N;                        // crossings per half-pass in the N-cord grid
hr = bight_pins ? pin_d / 2 : 0;
rho = cord_d / 2 + hr + PIN_CLEAR; // lane wrap radius round its bight pin
W = N == 1 ? cord_d : N * (cord_d + cord_gap);

function gcd(a, b) = b == 0 ? a : gcd(b, a % b);
assert(gcd(L, B) == 1, str("Leads and bights must share no factor: ", L, "L x ", B, "B is ", gcd(L, B), " separate loops."));

// over/under codes
//  - gaucho: Turk's head of N*L x N*B, row coding U^N O^N (checked against the
//    Paracord Guild 7L6B gaucho run list)
//  - Turk's head / headhunter: row coding OU / OOUU
//  - herringbone: over 2 / under 2 along the cord
function rep(c, n) = n <= 0 ? "" : str(c, rep(c, n - 1));
row_code = knot == "gaucho" ? str(rep("U", N), rep("O", N))
         : knot == "headhunter" ? "OOUU" : "OU";
along_code = "OOUU";
function herring_ok(l, b) = let(v = cord_visits(l, b))
    len([for (p = v) if (along_code[p[0] % 4] == along_code[p[1] % 4]) 1]) == 0;
// crossing visits along the cord for a single L x B knot: [[n1, n2], ...]
function cross_id(j, k) = let(up = j % 2 == 0, row = up ? k : L - k) [row, (j * L + k) % (2 * B)];
function cord_visits(l, b) = [
    for (j = [0:2 * b - 1], k = [1:l - 1])
        let(id = cross_id(j, k), n1 = j * (l - 1) + k - 1,
            others = [for (j2 = [0:2 * b - 1], k2 = [1:l - 1])
                         if ((j2 != j || k2 != k) && cross_id(j2, k2) == id) j2 * (l - 1) + k2 - 1])
        if (len(others) > 0 && n1 < others[0]) [n1, others[0]]];
if (knot == "herringbone" && over_under)
    assert(herring_ok(L, B), str("Over 2 / under 2 does not close on ", L, "L x ", B, "B - try other leads."));

function up_over(row, code) = code[(row - 1) % len(code)] == "O";
// is half-pass j over at its k-th crossing?
function lane_over(j, k) =
    let(up = j % 2 == 0)
    knot == "herringbone"
        ? along_code[((j % (2 * B)) * (L - 1) + k - 1) % 4] == "O"
        : let(row = up ? k : Lg - k, o = up_over(row, row_code)) up ? o : !o;

// ---------------------------------------------------------------- sizing
function circ(d) = PI * d;
function su_of(d) = d / 2 * L * PI / B;
function pitch_of(d, h) = circ(d) / B * h / norm([su_of(d), h]);
function dia_ok(d) =
    N == 1 ? W <= (circ(d) / B - 2 * hr - 0.4) / 2
           : circ(d) / (B * N) >= 2 * (rho + cord_d / 2) + 0.4;
function thread_d(d) = let(c = [for (s = ISO) if (s <= d - 5 * cord_d) s]) len(c) ? c[len(c) - 1] : 0;
function grid_ok(d, h) = N < 2 ? true :
    let(s = su_of(d), m = norm([s, h]), dp = rho / sin(atan2(s, h)), zf = dp * pow(h / m, 2))
    h / (N * L) >= zf + cord_d / 2;
function len_ok(d, len_) = let(h = len_ - END_MARGIN)
    h > 0 && W / pitch_of(d, h) < 0.9 && grid_ok(d, h);
function auto_dia(d = 40) = (dia_ok(d) && (!lid || thread_d(d) >= 12)) || d > 300 ? d : auto_dia(d + 1);
function auto_len(d, l_ = 150) = len_ok(d, l_) || l_ > 1000 ? l_ : auto_len(d, l_ + 5);

D = diameter > 0 ? diameter : auto_dia();
LEN = length > 0 ? length : auto_len(D);
R = D / 2;
H = LEN - END_MARGIN;
z0 = END_MARGIN / 2;
C = circ(D);
su = su_of(D);
segm = norm([su, H]);
d_pin = rho / sin(atan2(su, H));
g_shift = C / (B * N);
function shift(m) = (m - (N - 1) / 2) * g_shift;

assert(dia_ok(D), str("Diameter too small for these cords/bights: needs about ", auto_dia(), " mm."));
assert(len_ok(D, LEN), str("Length too short for this knot: needs about ", auto_len(D), " mm."));

echo(str("Jig: ", D, " mm dia x ", LEN, " mm, knot span ", H, " mm, ", N, " cord(s)"));

// ---------------------------------------------------------------- 2D paths
// unrolled plane: u = R * theta, z
function V(j, du) = [j * su + du, z0 + (j % 2 == 0 ? 0 : H)];
function sdir(j) = [su, j % 2 == 0 ? H : -H] / segm;
function nrm(d) = [-d[1], d[0]];
function pinp(j, du) = V(j, du) + [0, j % 2 == 0 ? d_pin : -d_pin];
function foot(P, j, du) = let(n = nrm(sdir(j)), A = V(j, du)) P - n * ((P - A) * n);
function apex(P, j) = P + [0, j % 2 == 0 ? -rho : rho];
function arc(P, a, b, n = 10) =
    let(a0 = atan2(a[1] - P[1], a[0] - P[0]), a1 = atan2(b[1] - P[1], b[0] - P[0]),
        da0 = a1 - a0, da = da0 > 180 ? da0 - 360 : da0 < -180 ? da0 + 360 : da0)
    [for (i = [0:n]) P + rho * [cos(a0 + da * i / n), sin(a0 + da * i / n)]];
function line(a, b) = let(n = max(1, ceil(norm(b - a) / leg_step)))
    [for (i = [0:n]) a + (b - a) * i / n];
// one half-pass of lane du: top/bottom of bight j -> round pin j -> leg -> round pin j+1
function half_pass(j, du) =
    let(Pa = pinp(j, du), Pb = pinp(j + 1, du), fa = foot(Pa, j, du), fb = foot(Pb, j, du))
    concat(arc(Pa, apex(Pa, j), fa), line(fa, fb), arc(Pb, fb, apex(Pb, j + 1)));

// cut boxes where half-pass j goes under: [Q, direction, half width, half length]
function cuts(j, du) =
    let(d = sdir(j), do = [d[0], -d[1]], sx = abs(d[0] * do[1] - d[1] * do[0]),
        hs = cord_d / 2 + END_GAP, hl = (cord_d / 2 + hs) / sx + 1)
    !over_under ? [] :
    [for (k = [1:Lg - 1]) if (!lane_over(j, k))
        [V(j, du) + (V(j + 1, du) - V(j, du)) * k / Lg, do, hs, hl]];

// ---------------------------------------------------------------- 3D helpers
fill_d = min(lane_depth, cord_d / 2);
rr = (cord_d * cord_d / 4 + fill_d * fill_d) / (2 * fill_d); // one tube per lane:
                                                           // chord = cord width
function to3(p, r) = let(a = p[0] / R * 180 / PI) [r * cos(a), r * sin(a), p[1]];

module tube(pts) {
    rc = R + rr - fill_d;
    for (i = [0:len(pts) - 2])
        hull() {
            translate(to3(pts[i], rc)) sphere(r = rr, $fn = lane_fn);
            translate(to3(pts[i + 1], rc)) sphere(r = rr, $fn = lane_fn);
        }
}

// a box lying on the cylinder's tangent plane at unrolled point Q
module tangent_box(Q, dir, hw, hl, h) {
    a = Q[0] / R * 180 / PI;
    t = [-sin(a), cos(a), 0];
    e = [cos(a), sin(a), 0];
    al = [dir[0] * t[0], dir[0] * t[1], dir[1]];
    m = [dir[1], -dir[0]];
    ac = [m[0] * t[0], m[0] * t[1], m[1]];
    P = R * e + [0, 0, Q[1]];
    multmatrix([[al[0], ac[0], e[0], P[0]],
                [al[1], ac[1], e[1], P[1]],
                [al[2], ac[2], e[2], P[2]],
                [0, 0, 0, 1]])
        cube([2 * hl, 2 * hw, h], center = true);
}

module mandrel_clip() { translate([0, 0, -1]) cylinder(r = R, h = LEN + 50, $fn = 180); }

// lane m (colour index): every half-pass trimmed where it goes under,
// clipped flush with the mandrel
module lane(m) {
    du = shift(m);
    render(convexity = 4) intersection() {
        mandrel_clip();
        union()
            for (j = [0:2 * B - 1])
                difference() {
                    tube(half_pass(j, du));
                    for (c = cuts(j, du)) tangent_box(c[0], c[1], c[2], c[3], 4 * rr + 4);
                }
    }
}

// ---------------------------------------------------------------- pins, numbers
module pin_holes() {
    if (bight_pins)
        for (m = [0:N - 1], j = [0:2 * B - 1]) {
            pz = pinp(j, shift(m));
            {
                a = pz[0] / R * 180 / PI;
                rotate([0, 0, a]) translate([R - pin_depth, 0, pz[1]])
                    rotate([0, 90, 0]) cylinder(d = pin_d, h = pin_depth + 1, $fn = 24);
            }
        }
}

top_edge = z0 + H - d_pin + rho + cord_d / 2;
bot_edge = z0 + d_pin - rho - cord_d / 2;
num_h = min(number_h, LID_GAP - 2 * NUM_GAP);
function number_spots() =
    let(nudge = rho / 2, zt = top_edge + NUM_GAP + num_h / 2, zb = bot_edge - NUM_GAP - num_h / 2)
    concat([for (n = [1:2 * B]) [n == 1 ? (N > 1 ? "A1" : "1") : str(n), 0,
                                  n * su + shift(0) + nudge, n % 2 == 1 ? zt : zb]],
           [for (m = [1:N - 1]) if (N > 1) [str(chr(65 + m), "1"), m, su + shift(m) + nudge, zt]]);

module label(txt, u, z) {
    a = u / R * 180 / PI;
    intersection() {
        mandrel_clip();
        rotate([0, 0, a]) translate([R - number_depth, 0, z]) rotate([90, 0, 90])
            linear_extrude(number_depth + 2)
                text(txt, size = num_h * 0.8, font = "Liberation Sans:style=Bold",
                     halign = "center", valign = "center");
    }
}
module labels(m = -1) {
    if (pass_numbers) render()
        for (s = number_spots()) if (m < 0 || s[1] == m) label(s[0], s[2], s[3]);
}

// ---------------------------------------------------------------- lid & thread
zs = top_edge + LID_GAP;            // shoulder: top of the jig body, lid sits here
TD = lid ? thread_d(D) : 0;
e_thr = 0.3 * thread_pitch;         // thread = twisted eccentric circle, depth 0.6 * pitch
r_minor = TD / 2 - 2 * e_thr;
rc_store = min(r_minor - 2, R - pin_depth - 2);

module thread(r_major, h) {
    linear_extrude(height = h, twist = -360 * h / thread_pitch,
                   slices = max(8, ceil(h / thread_pitch * 24)), convexity = 6)
        translate([e_thr, 0]) circle(r = r_major - e_thr, $fn = 48);
}

module spigot() {
    lead = 0.6 * thread_pitch + 0.2;
    translate([0, 0, zs - 0.01])
        intersection() {
            thread(TD / 2, thread_len + 0.01);
            cylinder(r1 = TD / 2 + thread_len, r2 = TD / 2 - lead + 0.01, h = thread_len + 0.01);
        }
}

notch_th = (su + (shift(0) + shift(N - 1)) / 2) / R * 180 / PI;
notch_w = abs(shift(N - 1) - shift(0)) + cord_d + 1;
module clamp_notch() {
    rw = notch_w / 2;
    zc = zs - cord_d * (1 - CLAMP_SQUEEZE) + rw;
    rotate([0, 0, notch_th]) {
        translate([0, 0, zc]) rotate([0, 90, 0]) cylinder(r = rw, h = R + 2, $fn = 48);
        translate([0, -rw, zc]) cube([R + 2, 2 * rw, thread_len + LID_CAP + 10]);
    }
}

module storage() {
    if (pin_storage && rc_store > 1.5)
        translate([0, 0, -handle_len + STORAGE_FLOOR]) cylinder(r = rc_store, h = zs + thread_len + handle_len + 1);
}

module lid_part() {
    hl = thread_len + LID_CAP;
    lead = 0.6 * thread_pitch + 0.2;
    n = max(8, round(2 * PI * R / 7));
    dep = min(0.9, (R - TD / 2) / 3);
    // printed top down: closed cap at z = 0, threaded bore opening upward
    difference() {
        hull() {
            cylinder(r = R - chamfer, h = 0.01);
            translate([0, 0, chamfer]) cylinder(r = R, h = hl - chamfer);
        }
        translate([0, 0, LID_CAP]) thread(TD / 2 + thread_clearance, thread_len + 0.01);
        translate([0, 0, hl - lead]) cylinder(r1 = TD / 2 + thread_clearance - 2 * e_thr,
                                              r2 = TD / 2 + thread_clearance + 0.5, h = lead + 0.01);
        for (i = [0:n - 1]) rotate([0, 0, 360 * i / n])
            translate([R + 1.5 - dep, 0, -1]) cylinder(r = 1.5, h = hl + 2, $fn = 24);
    }
}

// ---------------------------------------------------------------- jig
module jig_body() {
    hd = handle_dia > 0 ? handle_dia : D;
    hull() {
        translate([0, 0, 0]) cylinder(r = R - chamfer, h = 0.01, $fn = 180);
        translate([0, 0, chamfer]) cylinder(r = R, h = zs - chamfer, $fn = 180);
    }
    if (handle_len > 0)
        translate([0, 0, -handle_len]) hull() {
            cylinder(r = hd / 2 - chamfer, h = 0.01, $fn = 120);
            translate([0, 0, chamfer]) cylinder(r = hd / 2, h = handle_len - chamfer + 0.01, $fn = 120);
        }
    if (lid) spigot();
}

module jig() {
    difference() {
        jig_body();
        for (m = [0:N - 1]) lane(m);
        pin_holes();
        labels();
        if (lid) { storage(); clamp_notch(); }
    }
}

module cord(m) {
    difference() {
        union() { lane(m); labels(m); }
        pin_holes();
    }
}

// ---------------------------------------------------------------- output
// everything sits on z = 0 (handle bottom); the lid stands beside the jig
lift = handle_len;
idx = part == "cord_A" ? 0 : part == "cord_B" ? 1 : part == "cord_C" ? 2
    : part == "cord_D" ? 3 : part == "cord_E" ? 4 : part == "cord_F" ? 5 : -1;

if (part == "all") {
    translate([0, 0, lift]) {
        color("dimgray") jig();
        for (m = [0:N - 1]) color(COLOURS[m]) cord(m);
    }
    if (lid) color("slategray") translate([2 * R + 10, 0, 0]) lid_part();
} else if (part == "jig") {
    translate([0, 0, lift]) jig();
} else if (part == "lid") {
    if (lid) translate([2 * R + 10, 0, 0]) lid_part();
} else if (idx >= 0 && idx < N) {
    translate([0, 0, lift]) cord(idx);
} else {
    echo(str("Nothing to export: ", part, " (this knot has ", N, " cord(s))"));
}
