# Printer Skew Correction
#
# This implementation is a port of Marlin's skew correction as
# implemented in planner.h, Copyright (C) Marlin Firmware
#
# https://github.com/MarlinFirmware/Marlin/tree/1.1.x/Marlin
#
# Copyright (C) 2019  Eric Callahan <arksine.code@gmail.com>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import math

def calc_skew_factor(ac, bd, ad, offset=0.):
    side = math.sqrt(2*ac*ac + 2*bd*bd - 4*ad*ad) / 2.
    if offset == 0.:
        return math.tan(math.pi/2 - (math.acos(
            (ac*ac - side*side - ad*ad) / (2*side*ad)) + offset))
    else:
        return math.tan(math.pi/2 + (math.acos(
            (ac*ac - side*side - ad*ad) / (2*side*ad)) + offset))

def side(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def diagonal_AC(cd, bc, bd):
    return math.sqrt(2*cd*cd + 2*bc*bc - bd*bd)

def calc_skew_factor_my(ac, bd, bc):
    """
    This function made spashial for five_d printers.
        b_______c
        |       |
        a_______d
    """
    ac, bd = bd, ac
    cd = math.sqrt(2*ac*ac + 2*bd*bd - 4*bc*bc) / 2.
    cos_a = math.acos((bc*bc + cd*cd - bd*bd) / (2*bc*cd))
    tan_O2 =  math.tan(math.pi/2 - cos_a)
    return tan_O2

def point(first, second):
    return [(first[0] + second[0]) / 2.,
            (first[1] + second[1]) / 2.,
            (first[2] + second[2]) / 2.,
            0,
            0
        ]

def  calc_xy_axis_offset(a1, b1, a2, b2):
    a_vect = [b1[0] - a1[0], b1[1] - a1[1]]
    b_vect = [b2[0] - a2[0], b2[1] - a2[1]]
    ab_mod = abs(a_vect[0] * b_vect[0] + a_vect[1] * b_vect[1]) / (math.sqrt(a_vect[0]**2 + a_vect[1]**2) \
         * math.sqrt(b_vect[0]**2 + b_vect[1]**2))
    return   math.acos(ab_mod)

# Constrain value between min and max
def constrain(val, min_val, max_val):
    return min(max_val, max(min_val, val))


class PrinterSkew:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name()
        self.enabled = False
        self.xy_factor = 0.
        self.xz_factor = 0.
        self.yz_factor = 0.
        self.b_point = None
        self.c_point = None
        self.d_point = None
        self.a_point = None
        self.skew_profiles = {}
        self._load_storage(config)
        self.printer.register_event_handler("klippy:connect",
                                            self._handle_connect)
        self.next_transform = None
        gcode = self.printer.lookup_object('gcode')
        gcode.register_command('GET_CURRENT_SKEW', self.cmd_GET_CURRENT_SKEW,
                               desc=self.cmd_GET_CURRENT_SKEW_help)
        gcode.register_command('CALC_MEASURED_SKEW',
                               self.cmd_CALC_MEASURED_SKEW,
                               desc=self.cmd_CALC_MEASURED_SKEW_help)
        gcode.register_command('SET_SKEW', self.cmd_SET_SKEW,
                               desc=self.cmd_SET_SKEW_help)
        gcode.register_command('SKEW_PROFILE', self.cmd_SKEW_PROFILE,
                               desc=self.cmd_SKEW_PROFILE_help)
        gcode.register_command('SAVE_SKEW_POINT',
                               self.cmd_SAVE_SKEW_POINT,
                               desc=self.cmd_SAVE_SKEW_POINT_help)
        gcode.register_command('CALC_SKEW_COMPENSATION',
                                self.cmd_CALC_SKEW_COMPENSATION,
                                desc=self.cmd_CALC_SKEW_COMPENSATION_help)
        self.point_coords = [
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            # xy offset axis
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
            [0., 0., 0., 0., 0., 0.],
        ]
        # Register transform
        self.next_transform = None
        self.printer.lookup_object('b_axis_compensation').next_transform = self

    def _handle_connect(self):
        # set transform object
        self.next_transform = self.printer.lookup_object('toolhead')
        kin = self.next_transform.get_kinematics()
        self.axes_min = kin.axes_min
        self.axes_max = kin.axes_max

    def cmd_SAVE_SKEW_POINT(self, gcmd):
        point_idx = gcmd.get_int('POINT', 0)
        coords = gcmd.get('COORDS', None)
        if coords is not None:
            try:
                coords = coords.strip().split(",", 2)
                coords = [float(l.strip()) for l in coords]
                if len(coords) != 3:
                    raise Exception
            except Exception:
                raise gcmd.error(
                    "skew_corection: improperly formatted entry for "
                    "point\n%s" % (gcmd.get_commandline()))
            for axis, coord in enumerate(coords):
                self.point_coords[point_idx][axis] = coord
    cmd_SAVE_SKEW_POINT_help = "Save point for align skew"

    cmd_CALC_MEASURED_SKEW_help = "Calculate skew from measured print"
    def cmd_CALC_MEASURED_SKEW(self, gcmd):
        ac = gcmd.get_float("AC", above=0.)
        bd = gcmd.get_float("BD", above=0.)
        ad = gcmd.get_float("AD", above=0.)
        factor = calc_skew_factor(ac, bd, ad)
        gcmd.respond_info("Calculated Skew: %.6f radians, %.2f degrees"
                          % (factor, math.degrees(factor)))

    def cmd_CALC_SKEW_COMPENSATION(self, gcmd):
        """
        b_______c
        |       |
        a_______d
        """

        factors = ['XY', 'XZ', 'YZ']
        factor_name = gcmd.get('FACTOR').upper()
        if factor_name in factors:
            if factor_name == factors[0]:
                # xy_factor
                self.c_point = point(self.point_coords[0], self.point_coords[1])
                self.b_point = list(self.c_point)
                self.b_point[0] = self.c_point[0] - 50
                self.d_point = point(self.point_coords[2], self.point_coords[3])
                self.a_point = list(self.d_point)
                self.a_point[0] = self.d_point[0] - 50
                cd = side(self.c_point[0], self.c_point[1], self.d_point[0], self.d_point[1])
                bc = side(self.b_point[0], self.b_point[1], self.c_point[0], self.c_point[1])
                bd = side(self.b_point[0], self.b_point[1], self.d_point[0], self.d_point[1])
                ac = side(self.a_point[0], self.a_point[1], self.c_point[0], self.c_point[1])
                gcmd.respond_info('cd=%f, bc=%f, bd=%f, ac=%f' % (cd, bc, bd, ac))
                ac, bd = bd, ac
                axis_offset = calc_xy_axis_offset(self.point_coords[4],
                                                  self.point_coords[5],
                                                  self.point_coords[6],
                                                  self.point_coords[7])
                # axis_offset = 0.0
            elif factor_name == factors[1]:
                # xz_factor
                self.c_point = point(self.point_coords[0], self.point_coords[1])
                self.b_point = list(self.c_point)
                self.b_point[0] = self.c_point[0] - 50
                self.d_point = point(self.point_coords[2], self.point_coords[3])
                self.a_point = list(self.d_point)
                self.a_point[0] = self.d_point[0] - 50
                cd = side(self.c_point[0], self.c_point[2], self.d_point[0], self.d_point[2])
                bc = side(self.b_point[0], self.b_point[2], self.c_point[0], self.c_point[2])
                bd = side(self.b_point[0], self.b_point[2], self.d_point[0], self.d_point[2])
                ac = side(self.a_point[0], self.a_point[2], self.c_point[0], self.c_point[2])
                gcmd.respond_info('cd=%f, bc=%f, bd=%f, ac=%f' % (cd, bc, bd, ac))
                axis_offset = 0.0
                # pass
            else:
                # yz_factor
                pass
            sf = calc_skew_factor(ac, bd, bc, axis_offset)
            factor_name = factor_name.lower() + '_factor'
            setattr(self, factor_name, sf)
            out = "Calculated skew compensation %s: %.6f radians, %.2f degrees\n" % (
                factor_name, sf, math.degrees(sf))
            gcmd.respond_info(out)
        else:
            raise gcmd.error(
                    "Error! Factor name %s not in list factors['XY', 'XZ', 'YZ']" % (factor_name))
    cmd_CALC_SKEW_COMPENSATION_help = "Calculate skew compensation"


    def _load_storage(self, config):
        stored_profs = config.get_prefix_sections(self.name)
        # Remove primary skew_correction section, as it is not a stored profile
        stored_profs = [s for s in stored_profs
                        if s.get_name() != self.name]
        for profile in stored_profs:
            name = profile.get_name().split(' ', 1)[1]
            self.skew_profiles[name] = {
                'xy_skew': profile.getfloat("xy_skew"),
                'xz_skew': profile.getfloat("xz_skew"),
                'yz_skew': profile.getfloat("yz_skew"),
            }

    def calc_skew(self, pos):
        newpos = list(pos)
        newpos[0] = pos[0] - pos[1] * self.xy_factor \
            - pos[2] * (self.xz_factor - (self.xy_factor * self.yz_factor))
        newpos[1] = pos[1] - pos[2] * self.yz_factor
        newpos = [constrain(newpos[axis], self.axes_min[axis], self.axes_max[axis]) for axis in range(5)]
        newpos.append(pos[5])
        return newpos

    def calc_unskew(self, pos):
        newpos = list(pos)
        newpos[0] = pos[0] + pos[1] * self.xy_factor \
            + pos[2] * self.xz_factor
        newpos[1] = pos[1] + pos[2] * self.yz_factor
        newpos = [constrain(newpos[axis], self.axes_min[axis], self.axes_max[axis]) for axis in range(5)]
        newpos.append(pos[5])
        return newpos

    def get_position(self):
        if not self.enabled:
            return self.next_transform.get_position()
        return self.calc_unskew(self.next_transform.get_position())

    def move(self, newpos, speed):
        axes_d = [self.next_transform.get_position()[i] - newpos[i] for i in
                                (0, 1, 2, 3, 4, 5)]
        move_d = math.sqrt(sum([d * d for d in axes_d[:5]]))
        if not self.enabled or move_d < .000000001:
            self.next_transform.move(newpos, speed)
            return
        corrected_pos = self.calc_skew(newpos)
        self.next_transform.move(corrected_pos, speed)

    def _update_skew(self, xy_factor, xz_factor, yz_factor):
        self.xy_factor = xy_factor
        self.xz_factor = xz_factor
        self.yz_factor = yz_factor
        gcode_move = self.printer.lookup_object('gcode_move')
        gcode_move.reset_last_position()
    cmd_GET_CURRENT_SKEW_help = "Report current printer skew"

    def cmd_GET_CURRENT_SKEW(self, gcmd):
        out = "Current Printer Skew:"
        planes = ["XY", "XZ", "YZ"]
        factors = [self.xy_factor, self.xz_factor, self.yz_factor]
        for plane, fac in zip(planes, factors):
            out += '\n' + plane
            out += " Skew: %.6f radians, %.2f degrees" % (
                fac, math.degrees(fac))
        gcmd.respond_info(out)

    cmd_SET_SKEW_help = "Set skew based on lengths of measured object"
    def cmd_SET_SKEW(self, gcmd):
        if gcmd.get_int("CLEAR", 0):
            self._update_skew(0., 0., 0.)
            gcmd.respond_info('Skew points cleared.')
            return
        if gcmd.get_int('ENABLE', 0):
            self.enabled = True
            gcmd.respond_info('Skew compensation enabled.')
        else:
            self.enabled = False
            gcmd.respond_info('Skew compensation disabled.')
        planes = ["XY", "XZ", "YZ"]
        for plane in planes:
            skew = gcmd.get_float(plane, None)
            if skew is not None:
                try:
                    factor = plane.lower() + '_factor'
                    setattr(self, factor, skew)
                    out = "Set skew correction %s: %.6f radians, %.2f degrees." % (
                        factor, skew, math.degrees(skew))
                    gcmd.respond_info(out)
                except Exception:
                    raise gcmd.error(
                        "skew_correction: improperly formatted entry for "
                        "plane [%s]\n%s" % (plane, gcmd.get_commandline()))
    cmd_SKEW_PROFILE_help = "Profile management for skew_correction"

    def cmd_SKEW_PROFILE(self, gcmd):
        if gcmd.get('LOAD', None) is not None:
            name = gcmd.get('LOAD')
            prof = self.skew_profiles.get(name)
            if prof is None:
                gcmd.respond_info(
                    "skew_correction:  Load failed, unknown profile [%s]"
                    % (name))
                return
            self._update_skew(prof['xy_skew'], prof['xz_skew'], prof['yz_skew'])
        elif gcmd.get('SAVE', None) is not None:
            name = gcmd.get('SAVE')
            configfile = self.printer.lookup_object('configfile')
            cfg_name = self.name + " " + name
            configfile.set(cfg_name, 'xy_skew', self.xy_factor)
            configfile.set(cfg_name, 'xz_skew', self.xz_factor)
            configfile.set(cfg_name, 'yz_skew', self.yz_factor)
            # Copy to local storage
            self.skew_profiles[name] = {
                'xy_skew': self.xy_factor,
                'xz_skew': self.xz_factor,
                'yz_skew': self.yz_factor
            }
            gcmd.respond_info(
                "Skew Correction state has been saved to profile [%s]\n"
                "for the current session.  The SAVE_CONFIG command will\n"
                "update the printer config file and restart the printer."
                % (name))
        elif gcmd.get('REMOVE', None) is not None:
            name = gcmd.get('REMOVE')
            if name in self.skew_profiles:
                configfile = self.printer.lookup_object('configfile')
                configfile.remove_section('skew_correction ' + name)
                del self.skew_profiles[name]
                gcmd.respond_info(
                    "Profile [%s] removed from storage for this session.\n"
                    "The SAVE_CONFIG command will update the printer\n"
                    "configuration and restart the printer" % (name))
            else:
                gcmd.respond_info(
                    "skew_correction: No profile named [%s] to remove"
                    % (name))

    def get_status(self, eventtime=None):
        return {
            'enable': self.enabled,
            'xy_factor': self.xy_factor,
            'xz_factor': self.xz_factor,
            'yz_factor': self.yz_factor,
            'point_coords': self.point_coords,
            'a_point':self.a_point,
            'b_point': self.b_point,
            'c_point': self.c_point,
            'd_point': self.d_point,
        }
def load_config(config):
    return PrinterSkew(config)
