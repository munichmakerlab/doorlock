$fn=30;

module visor(xdim, zdim, rdim) {
	hull() {
		translate([rdim, rdim, 0]) cylinder(r=rdim,h=zdim);
		translate([xdim-rdim,rdim,0]) cylinder(r=rdim,h=zdim);
	}
}

module baseplate(xdim_base,ydim_base,zdim_base,rdim_base) {	
	hull() {
		visor(xdim_base,zdim_base,rdim_base);
		translate([0,ydim_base,0]) visor(xdim_base,zdim_base,rdim_base);
	}
}

module keypad_part(xdim,ydim,zdim,length) {
	translate([length/2-xdim/2,length/2-ydim/2,0]) cube([xdim,ydim,zdim]);
}

module basebody() {
	hull() {
		hull() {
			baseplate(length,length,5,3);
			rotate([20,0,0]) visor(length,20,20);
		}
		keypad_part(76,100,30,length);
	}
	rotate([20,0,0]) visor(length,22,20);
}

module mounting_points() {
	translate([length/2-old_plate[0]/2,length/2-old_plate[1]/2+15,-1]) {
		cube(old_plate);
		
		translate([15,15,-10]) {
			cylinder(r=1.5,h=100);
			translate([0,0,30])
			cylinder(r=4,h=100);	
		}
	
		translate([old_plate[0]-15,old_plate[1]-15,-10]) {
			cylinder(r=1.5,h=100);	
			translate([0,0,25])
			cylinder(r=4,h=100);	
		}
	}
}

module rfid_reader() {
	
	rotate([-6,-40,0])
	translate([7,45,-25])
	cube([40,70,30]);

}

module rfid_hull(length) {
	color("red"){ 
		hull() {
			translate([7,43,0])
			cube([2,70.5,8]);
		
			translate([38.5,43,0])
			cube([2,70.5,2]);
		
			translate([40.5,43,27])
			cube([2,70.5,2]);
		}

		hull() {
			translate([length-7,43,0])
			cube([2,70.5,8]);
		
			translate([length-38.5,43,0])
			cube([2,70.5,2]);
		
			translate([length-40.5,43,27])
			cube([2,70.5,2]);
		}

	}
}


module display_cable_pipe() {
	translate([110,50,-1])
	rotate([90,0,0])
	cylinder(r=7,h=20);
}


length = 140;
keypad_size = [59,73,100];
keypad_mounting_space = [45,92,21];
keypad_mounting_space_center = [20,92,21];

display_size = [95,36,100];
display_mounting_space = [120,38,35.5];

old_plate = [122,122,1];

difference() {
	union() {
		difference() {
			basebody();
			translate([length/2-keypad_size[0]/2,length/2-keypad_size[1]/2+7,0]) cube(keypad_size);
		
			difference() {
				translate([length/2-keypad_mounting_space[0]/2,length/2-keypad_mounting_space[1]/2+7,0]) cube(keypad_mounting_space);
				translate([length/2-keypad_mounting_space_center[0]/2,length/2-keypad_mounting_space_center[1]/2+7,0]) cube(keypad_mounting_space_center);
			}
		
			translate([length/2-display_size[0]/2,2,0]) rotate([20,0,0]) translate([0,0,-20])
			cube(display_size);
		
			translate([length/2-display_mounting_space[0]/2,2,0]) rotate([20,0,0]) translate([0,0,-20])
			cube(display_mounting_space);
		
		}
	
	translate([0,36.5,0])
	cube([length,4,8]);
	}

	rfid_hull(length-2);
	mounting_points();
	//display_cable_pipe();	
}
	

	
