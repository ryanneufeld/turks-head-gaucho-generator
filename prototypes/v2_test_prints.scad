// v2 test prints (issue #2): thin wrap sheet + bayonet joint at 40 mm.
// Throwaway: answers "does a 2-layer PLA sheet wrap, close and hold pins?"
// and "does a 3-lug 30-degree bayonet print and lock well?"
// part: sheet | lane | socket | plug
part = "sheet";

/* sheet */
D = 40;                 // tube (mandrel) diameter
layer = 0.2;
layers = 2;
T = layer * layers;     // sheet thickness
W = 40;                 // sheet width along the tube
circ = PI * (D + T);    // neutral-axis circumference
knob = 6;               // puzzle-tab knob diameter
neck = 3.5;
clr = 0.15;             // tab clearance
pin_d = 3;
lane_w = 4;
$fn = 48;

module tab2d(c = 0) {   // knob pointing +x, its base on x = 0
    translate([-0.01, -neck / 2 - c]) square([knob * 0.6 + 0.01, neck + 2 * c]);
    translate([knob * 0.6, 0]) circle(d = knob + 2 * c);
}
tabs_y = [W * 0.2, W * 0.5, W * 0.8];

module sheet2d() {
    difference() {
        union() {
            square([circ, W]);
            for (y = tabs_y) translate([circ, y]) tab2d();          // male end
        }
        for (y = tabs_y) translate([0, y]) tab2d(clr);              // female end
        // pin holes: one row, 6 holes round the tube
        for (i = [0:5]) translate([circ * (i + 0.5) / 6, W / 2]) circle(d = pin_d + 0.2);
        lane2d();
    }
}
// a diagonal colour lane crossing the sheet, broken where it "goes under"
module lane2d() {
    intersection() {
        square([circ, W]);
        difference() {
            translate([0, 2]) rotate(atan2(W - 4, circ)) translate([0, -lane_w / 2]) square([circ * 1.2, lane_w]);
            translate([circ * 0.5, 0]) square([lane_w + 1, W]);     // the gap
        }
    }
}

/* bayonet (3 lugs, 30 deg twist, detent) */
OD = 40;  spig = 30;  cl = 0.25;   // spigot dia, radial clearance
lug_w = 6; lug_h = 3; lug_r = 1.6; // lug width (arc), height, radial depth
twist = 30;
entry = 7;                          // depth to the horizontal slot
module lug() {                      // 45-degree underside: prints without support
    // the outer face is relieved 0.5 mm except a ridge on the trailing edge, so
    // the detent only catches over the last degree of twist (a click, not a rub)
    hull() {
        translate([spig / 2 - 0.5, -lug_w / 2, lug_r]) cube([0.5 + lug_r - 0.5, lug_w, lug_h - lug_r]);
        translate([spig / 2 - 0.5, -lug_w / 2, 0]) cube([0.5, lug_w, lug_h]);
    }
    hull() {   // ridge: on the -y side, which trails once the plug is flipped onto the socket
        translate([spig / 2 - 0.5, -lug_w / 2, lug_r]) cube([0.5 + lug_r, 1.2, lug_h - lug_r]);
        translate([spig / 2 - 0.5, -lug_w / 2, 0]) cube([0.5, 1.2, lug_h]);
    }
}
module plug() {                     // printed upright, spigot up
    cylinder(d = OD, h = 10);
    translate([0, 0, 10]) {
        difference() { cylinder(d = spig, h = entry + 2); translate([0, 0, -1]) cylinder(d = spig - 6, h = entry + 4); }
        // lug height matches the socket's horizontal slot once the plug is flipped onto it
        for (a = [0, 120, 240]) rotate(a) translate([0, 0, entry + 0.5 - cl - lug_h]) lug();
    }
}
module socket() {                   // printed upright, opening up; also the wrap test tube
    H = 45;
    difference() {
        cylinder(d = OD, h = H);
        translate([0, 0, H - entry - 2.2]) cylinder(d = spig + 2 * cl, h = entry + 3);
        translate([0, 0, -1]) cylinder(d = spig - 8, h = H);   // hollow core (storage)
        for (a = [0, 120, 240]) rotate(a) {
            r = spig / 2 + lug_r + cl + 0.2;
            // vertical entry slot
            translate([0, -lug_w / 2 - cl, H - entry - 0.5]) cube([r, lug_w + 2 * cl, entry + 1]);
            // horizontal slot, 30 deg, roof chamfered 45 deg for printing
            translate([0, 0, H - entry - 0.5])
                rotate_extrude(angle = -twist - lug_w / (PI * spig) * 360 / 2 - 2)
                    polygon([[0, 0], [r, 0], [r, lug_h + 2 * cl], [spig / 2 - 0.5, lug_h + 2 * cl + lug_r], [0, lug_h + 2 * cl + lug_r]]);
        }
        // pin-hold test: 6 blind 3 mm holes, 10 mm deep, matching the sheet's holes
        for (i = [0:5]) rotate(i * 60) translate([OD / 2 - 10, 0, 20]) rotate([0, 90, 0]) cylinder(d = pin_d + 0.15, h = 11);
    }
    // detent: a bump on the slot's outer wall just behind the seated lug's trailing
    // edge (0.25 mm interference); the wall flexes, the lug clicks past and stays
    lug_half = lug_w / (PI * spig) * 180;
    r_wall = spig / 2 + lug_r + cl + 0.2;
    for (a = [0, 120, 240]) rotate(a - twist + lug_half + 1)
        translate([r_wall, 0, H - entry - 0.5 + (lug_h + 2 * cl) / 2]) scale([1, 1, 2.5]) sphere(r = 0.7, $fn = 16);
}

if (part == "sheet") linear_extrude(T) sheet2d();
else if (part == "lane") linear_extrude(T) lane2d();
else if (part == "socket") socket();
else if (part == "plug") plug();
