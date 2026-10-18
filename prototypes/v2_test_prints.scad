// v2 test prints (issue #2), round 2.
// - sheet: mushroom tabs on one end push through straight slits set back
//   from the other end; pin through the overlap;
//   V notches mark the seam
// - bayonet: ceiling ramps down as you twist so the joint draws snug, hard stop
//   at the seat, light detent; matching index marks show "in time"
// part: sheet | lane | socket | plug
part = "sheet";
$fn = 64;

/* ---------------- sheet ---------------- */
// Mushroom tab and straight slit: the slit end has slits set back from its
// edge; the tab end overlaps it and each tab's cap is pushed down through a
// slit, its flat shoulders catching under the slit ends.
D = 40;                 // tube (mandrel) diameter
layer = 0.2;
layers = 2;
T = layer * layers;     // sheet thickness
W = 40;                 // sheet width along the tube
circ = PI * (D + T);    // neutral-axis circumference
overlap = 6;            // tab end lies over this strip of the slit end
neck_w = 6;             // tab neck width (= slit length less clearance)
ear = 1.5;              // each ear sticks out this far beyond the neck
neck_len = 3;           // stem from the tab end's edge to the cap (room to bend down through the slit)
slit_w = 1.2;           // slit opening across (sheet 0.4 + room to bend)
slit_short = 0.8;       // slit is this much shorter than the cap: the cap flexes 0.4 mm
                        // each side to pass, then its shoulders catch
tab_y = [W * 0.25, W * 0.75];
pin_d = 3;
lane_w = 4;
L_sheet = circ + overlap;

module tab2d() {        // mushroom: stem from the edge, half-round cap with flat shoulders
    hw = neck_w + 2 * ear;
    translate([-0.01, -neck_w / 2]) square([neck_len + 0.02, neck_w]);
    translate([neck_len, 0]) intersection() {
        circle(d = hw);
        translate([0, -hw / 2]) square([hw / 2, hw]);
    }
}
module slit2d() {       // straight slit, centred on y = 0, x = 0
    sl = neck_w + 2 * ear - slit_short;
    translate([-slit_w / 2, -sl / 2]) square([slit_w, sl]);
}
// holes: hole 0 in the overlap, through both ends, so one pin locks the seam
function hole_x(i) = overlap / 2 + circ * i / 6;
module holes2d() { for (i = [0:6]) translate([hole_x(i), W / 2]) circle(d = pin_d + 0.2); }
module notch2d() {      // seam marks: the tab end's edge lines up with the slit line
    for (x = [overlap, L_sheet]) translate([x, W]) polygon([[-1.5, 0.01], [1.5, 0.01], [0, -2.5]]);
}
module body2d() {
    difference() {
        square([L_sheet, W]);
        holes2d(); notch2d(); lane2d();
        for (y = tab_y) translate([overlap, y]) slit2d();
    }
    for (y = tab_y) translate([L_sheet, y]) tab2d();
}
// a diagonal colour lane, broken where it "goes under"
module lane2d() {
    intersection() {
        translate([overlap, 0]) square([circ, W]);
        difference() {
            translate([overlap, 2]) rotate(atan2(W - 4, circ)) translate([0, -lane_w / 2]) square([circ * 1.2, lane_w]);
            translate([overlap + circ * 0.5, 0]) square([lane_w + 1, W]);
        }
    }
}

/* ---------------- bayonet ---------------- */
OD = 40;  spig = 30;
cl_r = 0.2;             // radial clearance, spigot and lugs
lug_w = 6; lug_h = 3; lug_r = 1.6;
twist = 30;
entry = 7;              // depth from the socket face to the bottom of the slot
ramp = 0.5;             // extra slot height at the entry, closing to seat_gap
seat_gap = 0.05;        // axial play once seated
detent = 0.12;          // detent interference (radial)
lug_half = lug_w / (PI * spig) * 180;
// hard stop: the slot's far end sits just past the lug's leading inner corner,
// so the lug stops exactly at the seat (round 2 over-rotated by ~1-2 deg + slack)
stop_slack = 0.1;       // mm of travel left past the seat
lead_half = atan((lug_w / 2 + stop_slack) / (spig / 2));
H = 45;                 // socket height (it is also the wrap-test tube)
zb = H - entry - 0.5;   // slot floor in the socket
r_wall = spig / 2 + lug_r + cl_r;   // slot outer wall

module lug() {          // 45-degree underside so it prints upright unsupported
    // outer face relieved 0.4 mm except a ridge on the trailing edge: only the
    // ridge meets the detent, over the last couple of degrees (click, not rub)
    hull() {
        translate([spig / 2 - 0.5, -lug_w / 2, lug_r]) cube([0.5 + lug_r - 0.4, lug_w, lug_h - lug_r]);
        translate([spig / 2 - 0.5, -lug_w / 2, 0]) cube([0.5, lug_w, lug_h]);
    }
    hull() {            // ridge on -y: it trails once the plug is flipped onto the socket
        translate([spig / 2 - 0.5, -lug_w / 2, lug_r]) cube([0.5 + lug_r, 1.0, lug_h - lug_r]);
        translate([spig / 2 - 0.5, -lug_w / 2, 0]) cube([0.5, 1.0, lug_h]);
    }
}
module plug() {         // printed upright, spigot up; flip onto the socket
    difference() {
        cylinder(d = OD, h = 10);
        // index mark: a V groove down the side at angle 0
        translate([OD / 2, 0, -1]) rotate([0, 0, 45]) cube([1.6, 1.6, 12], center = false);
    }
    translate([0, 0, 10]) {
        difference() { cylinder(d = spig, h = entry + 2); translate([0, 0, -1]) cylinder(d = spig - 6, h = entry + 4); }
        // lugs sit in the slot band (zb .. zb + lug_h) once flipped onto the socket
        for (a = [0, 120, 240]) rotate(a) translate([0, 0, entry + 0.5 - lug_h - seat_gap / 2]) lug();
    }
}
// horizontal slot: thin angular slices, roof lowering from +ramp to +seat_gap
module slot(a0) {
    n = 15;
    for (i = [0:n - 1]) {
        t0 = i / n; t1 = (i + 1) / n;
        hull() for (t = [t0, t1]) {
            a = a0 - t * twist;
            roof = lug_h + seat_gap + ramp * (1 - t);
            rotate(a) for (s = [-1, 1])
                rotate(s < 0 ? -lead_half : lug_half + 1) translate([0, -0.01, zb]) cube([r_wall, 0.02, roof]);
        }
    }
}
module socket() {       // printed upright, opening up
    difference() {
        cylinder(d = OD, h = H);
        translate([0, 0, zb - 1.7]) cylinder(d = spig + 2 * cl_r, h = entry + 3);
        translate([0, 0, -1]) cylinder(d = spig - 8, h = H);    // hollow core (storage)
        for (a = [0, 120, 240]) {
            // vertical entry slot
            rotate(a) translate([0, -lug_w / 2 - cl_r - 0.3, zb]) cube([r_wall, lug_w + 2 * cl_r + 0.6, entry + 2]);
            slot(a);
        }
        // index marks: insert at the dot (0 deg), locked when the plug's groove meets the line
        translate([OD / 2, 0, H - 4]) rotate([0, 90, 0]) cylinder(d = 2, h = 2, center = true);
        rotate(-twist) translate([OD / 2, 0, H - 6]) rotate([0, 0, 45]) cube([1.6, 1.6, 7]);
        // pin-hold test: 6 blind 3 mm holes at 20 mm, matching the sheet's holes
        for (i = [0:5]) rotate(i * 60) translate([OD / 2 - 10, 0, 20]) rotate([0, 90, 0]) cylinder(d = pin_d + 0.15, h = 11);
    }
    // detent: small bump on each slot's outer wall just behind the seated lug
    for (a = [0, 120, 240]) rotate(a - twist + lug_half + 2.6)
        translate([spig / 2 + lug_r - detent + 0.6, 0, zb + lug_h / 2]) scale([1, 1, 2]) sphere(r = 0.6, $fn = 16);
}

if (part == "sheet") linear_extrude(T) body2d();
else if (part == "lane") linear_extrude(T) lane2d();
else if (part == "socket") socket();
else if (part == "plug") plug();
