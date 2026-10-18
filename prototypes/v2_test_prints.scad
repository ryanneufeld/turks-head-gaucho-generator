// v2 test prints (issue #2), round 2.
// - sheet: tab and slot. Dovetail tabs on one end slide UNDER the other end
//   (1 layer thick) into dovetail slots in its bottom layer; pin through the overlap; V notches at both ends mark the seam
// - bayonet: ceiling ramps down as you twist so the joint draws snug, hard stop
//   at the seat, light detent; matching index marks show "in time"
// part: sheet | lane | socket | plug
part = "sheet";
$fn = 64;

/* ---------------- sheet ---------------- */
D = 40;                 // tube (mandrel) diameter
layer = 0.2;
layers = 2;
T = layer * layers;     // sheet thickness
W = 40;                 // sheet width along the tube
circ = PI * (D + T);    // neutral-axis circumference
tab_len = 10;           // how far each tab slides under the other end
tab_gap = 0.4;          // side clearance between interleaved tabs
bands = 5;              // tab positions: the even bands
tab_bands = [0, 2, 4];  // tabs only on the +x end, slots only on the 0 end
pin_d = 3;
lane_w = 4;
band_w = W / bands;

// dovetail tab: narrow at the root (the seam), wide at the tip
tab_root = 0.5;         // root width as a fraction of the band
tab_tip = 0.85;         // tip width as a fraction of the band
tab_clr = 0.15;         // clearance between a tab and its pocket
module dovetail2d(c = 0) {      // root on x = 0, pointing +x, centred on y = 0
    polygon([[-0.01, -band_w * tab_root / 2 - c], [tab_len + c, -band_w * tab_tip / 2 - c],
             [tab_len + c, band_w * tab_tip / 2 + c], [-0.01, band_w * tab_root / 2 + c]]);
}
module tab2d(b) {               // tab in band b, sticking out past the +x end
    translate([circ, (b + 0.5) * band_w]) dovetail2d();
}
// slots: where the tabs land on the 0 end, dovetail pockets in the bottom
// layer, roofed by the top layer, so a wrapped tab drops in and locks
module pockets2d() {
    for (b = tab_bands) translate([0, (b + 0.5) * band_w]) dovetail2d(tab_clr);
}
// hole 0 sits in the overlap (x = tab_len/2): through the body at one end and
// the tab from the other end, so one pin locks the seam
function hole_x(i) = tab_len / 2 + circ * i / 6;
module holes2d(x_shift = 0) {
    for (i = [0:5]) translate([hole_x(i) + x_shift, W / 2]) circle(d = pin_d + 0.2);
}
module notch2d() {              // seam marks: V notches in the top edge at both ends
    for (x = [0, circ]) translate([x, W]) polygon([[-1.5, 0.01], [1.5, 0.01], [0, -2.5]]);
}
module body2d() { difference() { square([circ, W]); holes2d(); notch2d(); lane2d(); } }
module tabs2d() {
    difference() {
        union() for (b = tab_bands) tab2d(b);
        holes2d(circ);          // the middle tab carries hole 0 at circ + tab_len/2
    }
}
// a diagonal colour lane, broken where it "goes under"
module lane2d() {
    intersection() {
        square([circ, W]);
        difference() {
            translate([0, 2]) rotate(atan2(W - 4, circ)) translate([0, -lane_w / 2]) square([circ * 1.2, lane_w]);
            translate([circ * 0.5, 0]) square([lane_w + 1, W]);
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
                rotate(s * (lug_half + 1)) translate([0, -0.01, zb]) cube([r_wall, 0.02, roof]);
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

if (part == "sheet") {
    // bottom layer (inner face): body with dovetail pockets, plus the tabs
    linear_extrude(layer) { difference() { body2d(); pockets2d(); } tabs2d(); }
    // upper layers: full body, roofing the pockets
    translate([0, 0, layer]) linear_extrude(T - layer) body2d();
} else if (part == "lane") {
    linear_extrude(layer) difference() { lane2d(); pockets2d(); }   // keep the pockets clear
    translate([0, 0, layer]) linear_extrude(T - layer) lane2d();
}
else if (part == "socket") socket();
else if (part == "plug") plug();
